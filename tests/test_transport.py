from dataclasses import replace
import os
import secrets
import time
import unittest
import uuid
from unittest.mock import patch

from pio_test.errors import Rejected
from pio_test.transport import Client, Pump
from pio_test.wire import (authenticate, dumps, loads, read_bytes, request, sign,
                           write_json, RESULT_FIELDS)
from tests.support import Fixture, POST_CREATE, client_call_with_pump


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()
        self.addCleanup(self.f.close)
        self.pump = Pump(self.f.config, self.f.key, self.f.adapter)
        self.f.adapter.local_enable()
        self.pump.operator_sync()

    def job(self, command='test_status', args=None, **changes):
        now = time.time()
        a = self.pump.engine.auth
        value = {'v': 1, 'kind': 'request', 'bridge': self.pump.bridge,
                 'session': a.session, 'binding': a.binding, 'sequence': self.pump.sequence + 1,
                 'cid': secrets.token_hex(16), 'issued': now, 'expires': now + 30,
                 'command': command, 'args': args or {}}
        value.update(changes)
        return sign(self.f.key, value)

    def submit(self, job):
        write_json(self.f.ipc, 'request.json', job)
        result = self.pump.run_once()
        path = self.f.ipc / 'result.json'
        if path.exists():
            path.unlink()
        return result

    def arm(self):
        self.assertTrue(self.submit(self.job('test_arm', {'drawing': 'disposable.vwx'}))['ok'])

    def test_authenticated_roundtrip_and_secrets_not_returned(self):
        client = Client(self.f.config, self.f.key, timeout=1)
        arm = client_call_with_pump(client, self.pump, 'test_arm', {'drawing': 'disposable.vwx'})
        self.assertTrue(arm['ok'])
        self.assertNotIn(client.session, str(arm))
        self.assertNotIn(client.binding, str(arm))
        created = client_call_with_pump(client, self.pump, 'test_create', POST_CREATE)
        self.assertTrue(created['ok'])
        self.assertEqual(len(self.f.adapter.objects), 1)

    def test_default_manual_window_is_wire_valid_and_expires_at_60_seconds(self):
        client = Client(self.f.config, self.f.key)
        # Advance only the external wait clock; retain the actual signed request.
        # No native pump executes and this test does not wait a real minute.
        with patch('pio_test.transport.time.monotonic', side_effect=[100, 160]):
            result = client.call('test_status', {})
        self.assertEqual(result['code'], 'AMBIGUOUS_TIMEOUT')
        message = loads(read_bytes(self.f.ipc, 'request.json'))
        self.assertEqual(message['expires'] - message['issued'], 60)
        job = request(self.f.key, message, self.pump.bridge, self.pump.sequence,
                      now=message['issued'] + 59.999)
        self.assertEqual(job['command'], 'test_status')
        with self.assertRaisesRegex(Rejected, 'STALE_JOB'):
            request(self.f.key, message, self.pump.bridge, self.pump.sequence,
                    now=message['issued'] + 60.001)
        self.assertEqual(self.f.adapter.mutations, 0)

    def test_client_timeout_remains_bounded_to_60_seconds(self):
        for timeout in (0, -1, 60.001, float('inf'), float('nan'), True, '60'):
            with self.subTest(timeout=timeout):
                with self.assertRaisesRegex(Rejected, 'INVALID_TIMEOUT'):
                    Client(self.f.config, self.f.key, timeout=timeout)
        self.assertEqual(Client(self.f.config, self.f.key, timeout=60).timeout, 60)

    def test_wrong_auth_never_dispatches(self):
        self.arm()
        bad = self.job('test_create', POST_CREATE)
        bad['mac'] = '0' * 64
        self.assertEqual(self.submit(bad)['code'], 'AUTH_FAILED')
        self.assertEqual(self.f.adapter.mutations, 0)

    def test_wrong_bridge_session_and_document(self):
        self.arm()
        for field, code in [('bridge', 'BRIDGE_MISMATCH'), ('session', 'SESSION_MISMATCH'), ('binding', 'SESSION_MISMATCH')]:
            with self.subTest(field=field):
                result = self.submit(self.job('test_create', POST_CREATE, **{field: secrets.token_hex(32)}))
                self.assertEqual(result['code'], code)
        self.assertEqual(self.f.adapter.mutations, 0)

    def test_document_switch_between_queue_and_execution(self):
        self.arm()
        queued = self.job('test_create', POST_CREATE)
        write_json(self.f.ipc, 'request.json', queued)
        self.f.adapter.current = replace(self.f.adapter.current, generation=2)
        result = self.pump.run_once()
        self.assertEqual(result['code'], 'DOCUMENT_MISMATCH')
        self.assertEqual(self.f.adapter.mutations, 0)

    def test_direct_ipc_cannot_bypass_tool_or_parameter_schema(self):
        self.arm()
        for cmd, args in [('execute_script', {'code': 'x'}), ('vwx', {'command': 'create_wall'}),
                          ('test_create', dict(POST_CREATE, tool='AV Beam')),
                          ('test_create', dict(POST_CREATE, tool='AV Beam Tool')),
                          ('test_create', dict(POST_CREATE, parameters={'SavedControlX': 5})),
                          ('test_create', dict(POST_CREATE, force=True))]:
            with self.subTest(cmd=cmd, args=args):
                self.assertFalse(self.submit(self.job(cmd, args))['ok'])
        self.assertEqual(self.f.adapter.mutations, 0)

    def test_malicious_cid_cannot_choose_result_filename(self):
        for cid in ['../../stolen', 'C:\\temp\\x', '\\\\server\\share', 'a' * 500, 'x\nname', 'a' * 32 + '.json']:
            with self.subTest(cid=cid):
                result = self.submit(self.job(cid=cid))
                self.assertEqual(result['code'], 'INVALID_CORRELATION_ID')
                self.assertFalse((self.f.ipc / 'result.json').exists())
        self.assertFalse((self.f.base / 'stolen.json').exists())

    def test_unknown_envelope_fields_rejected(self):
        for field in ['result_filename', '_cid', 'path', 'callback', 'async']:
            self.assertEqual(self.submit(self.job(**{field: '../outside'}))['code'], 'INVALID_ENVELOPE')

    def test_replay_does_not_duplicate_mutation(self):
        self.arm()
        job = self.job('test_create', POST_CREATE)
        self.assertTrue(self.submit(job)['ok'])
        count = self.f.adapter.mutations
        self.assertEqual(self.submit(job)['code'], 'REPLAY')
        new_seq_same_cid = self.job('test_create', POST_CREATE, cid=job['cid'])
        self.assertEqual(self.submit(new_seq_same_cid)['code'], 'REPLAY_OR_SESSION_LIMIT')
        self.assertEqual(count, self.f.adapter.mutations)

    def test_stale_future_and_excessive_ttl(self):
        self.arm()
        now = time.time()
        for issued, expires in [(now-100, now-70), (now+20, now+30), (now, now+61), (now, now)]:
            result = self.submit(self.job('test_create', POST_CREATE, issued=issued, expires=expires))
            self.assertEqual(result['code'], 'STALE_JOB')
        self.assertEqual(self.f.adapter.mutations, 0)

    def test_restart_invalidates_old_bridge_nonce_and_ownership(self):
        self.arm()
        job = self.job('test_create', POST_CREATE)
        old_bridge = self.pump.bridge
        self.pump = Pump(self.f.config, self.f.key, self.f.adapter)
        self.assertNotEqual(old_bridge, self.pump.bridge)
        self.assertFalse(self.f.adapter.enabled)
        self.f.adapter.local_enable()
        self.pump.operator_sync()
        self.assertEqual(self.submit(job)['code'], 'BRIDGE_MISMATCH')
        self.assertEqual(self.f.adapter.mutations, 0)

    def test_timeout_expired_unclaimed_job_and_no_retry_after_client_restart(self):
        client = Client(self.f.config, self.f.key, timeout=0.04)
        result = client.call('test_arm', {'drawing': 'disposable.vwx'})
        self.assertEqual(result['code'], 'AMBIGUOUS_TIMEOUT')
        self.assertFalse(result['rollback'])
        self.assertEqual(self.pump.run_once()['code'], 'STALE_JOB')
        restarted = Client(self.f.config, self.f.key, timeout=0.04)
        with self.assertRaisesRegex(Rejected, 'LOCAL_REVIEW'):
            restarted.call('test_arm', {'drawing': 'disposable.vwx'})
        status = restarted.call('test_status', {})
        self.assertEqual(status['late_result']['code'], 'STALE_JOB')
        self.assertEqual(self.f.adapter.mutations, 0)

    def test_timeout_claimed_job_never_duplicates_native_mutation(self):
        # Let Windows ACL validation finish while arming; exercise the timeout
        # during the fake mutation, not during the prerequisite arm operation.
        client = Client(self.f.config, self.f.key, timeout=1)
        self.assertTrue(client_call_with_pump(client, self.pump, 'test_arm', {'drawing': 'disposable.vwx'})['ok'])
        client.timeout = 0.5
        self.f.adapter.create_delay = 1
        result = client_call_with_pump(client, self.pump, 'test_create', POST_CREATE)
        self.assertEqual(result['code'], 'AMBIGUOUS_TIMEOUT')
        self.assertEqual(self.f.adapter.mutations, 1)
        self.assertEqual(len(self.f.adapter.objects), 1)
        with self.assertRaises(Rejected):
            client.call('test_create', POST_CREATE)
        self.pump.run_once()
        self.assertEqual(self.f.adapter.mutations, 1)

    def test_unresolved_claim_and_busy_lock_fail_closed(self):
        self.f.write('claimed.json', b'{}')
        with self.assertRaisesRegex(Rejected, 'UNRESOLVED_CLAIM'):
            self.pump.run_once()
        with self.assertRaisesRegex(Rejected, 'UNRESOLVED_CLAIM'):
            Pump(self.f.config, self.f.key, self.f.adapter)
        (self.f.ipc / 'claimed.json').unlink()
        self.f.write('pump.lock', b'')
        with self.assertRaisesRegex(Rejected, 'LOCK'):
            self.pump.run_once()

    def test_result_mac_cid_sequence_and_nonce_checked(self):
        client = Client(self.f.config, self.f.key)
        client.descriptor()
        cid = secrets.token_hex(16)
        value = {'v': 1, 'kind': 'result', 'bridge': self.pump.bridge,
                 'cid': cid, 'sequence': 1, 'result': {'ok': True}}
        for changes in [{'bridge': '0'*64}, {'cid': '1'*32}, {'sequence': 2}]:
            write_json(self.f.ipc, 'result.json', sign(self.f.key, dict(value, **changes)))
            with self.assertRaisesRegex(Rejected, 'RESULT_MISMATCH'):
                client.read_result(cid, 1)
        forged = sign(self.f.key, value)
        forged['mac'] = '0' * 64
        write_json(self.f.ipc, 'result.json', forged)
        with self.assertRaisesRegex(Rejected, 'AUTH_FAILED'):
            client.read_result(cid, 1)

    def test_credential_and_payload_free_logs(self):
        self.arm()
        a = self.pump.engine.auth
        secret_label = 'PRIVATE TEXT DO NOT LOG'
        job = self.job('test_create', dict(POST_CREATE, parameters={'Notes': secret_label}))
        self.submit(job)
        log = (self.f.ipc / 'audit.jsonl').read_text()
        for secret in [self.f.key.hex(), a.session, a.binding, self.pump.bridge, job['mac'], secret_label, str(self.f.root)]:
            self.assertNotIn(secret, log)
        for line in log.splitlines():
            self.assertEqual(set(loads(line)), {'time', 'command', 'cid', 'outcome', 'elapsed_ms'})

    def test_json_duplicate_nonfinite_oversize(self):
        for data in [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b' ' * 65537]:
            with self.assertRaises(Rejected):
                loads(data)

    def test_no_second_pump_can_reuse_runtime(self):
        old = self.pump
        Pump(self.f.config, self.f.key, self.f.adapter)
        with self.assertRaisesRegex(Rejected, 'BRIDGE_SUPERSEDED'):
            old.run_once()
