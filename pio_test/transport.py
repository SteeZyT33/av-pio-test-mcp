"""One-slot authenticated file IPC; no sockets, retries, filenames from clients."""
import os
import secrets
import time

from . import audit_log
from .engine import Engine
from .errors import Rejected, require
from .paths import ipc_path
from .schema import validate_command
from .wire import (BRIDGE_FIELDS, CID, REQUEST_FIELDS, RESULT_FIELDS, authenticate,
                   exclusive, loads, read_bytes, request, sign, token, write_json)


class Pump:
    """Construct once per VW Python runtime. Invoke run_once only from its
    Python MENU-COMMAND runner. Restart changes bridge nonce and loses ownership.
    Never reload this module automatically, including during PIO source reload.
    """
    def __init__(self, config, key, adapter):
        self.root, self.key = config['ipc_root'], key
        self.bridge = secrets.token_hex(32)
        self.engine = Engine(config['test_root'], adapter)
        self.sequence = 0
        self.seen = set()
        with exclusive(self.root, 'pump.lock'):
            require(not ipc_path(self.root, 'claimed.json').exists(), 'UNRESOLVED_CLAIM')
            write_json(self.root, 'bridge.json', sign(self.key, {
                'v': 1, 'kind': 'bridge', 'bridge': self.bridge,
                'native_blockers': adapter.blockers}))

    def run_once(self):
        with exclusive(self.root, 'pump.lock'):
            descriptor = authenticate(self.key, loads(read_bytes(self.root, 'bridge.json')),
                                      BRIDGE_FIELDS, 'bridge')
            require(descriptor['bridge'] == self.bridge, 'BRIDGE_SUPERSEDED')
            require(not ipc_path(self.root, 'claimed.json').exists(), 'UNRESOLVED_CLAIM')
            path = ipc_path(self.root, 'request.json')
            if not path.exists():
                return {'processed': False}
            require(not ipc_path(self.root, 'result.json').exists(), 'RESULT_NOT_CONSUMED')
            os.replace(str(path), str(ipc_path(self.root, 'claimed.json')))
            started = time.perf_counter()
            authenticated = None
            try:
                message = loads(read_bytes(self.root, 'claimed.json'))
                authenticated = authenticate(self.key, message, REQUEST_FIELDS, 'request')
                job = request(self.key, message, self.bridge, self.sequence)
                require(job['cid'] not in self.seen and len(self.seen) < 4096, 'REPLAY_OR_SESSION_LIMIT')
                # Reserve BEFORE execution; exceptions cannot cause another dispatch.
                self.sequence = job['sequence']
                self.seen.add(job['cid'])
                result = self.engine.execute(job['command'], job['args'], job['session'], job['binding'], job['expires'])
            except Exception as error:
                result = {'ok': False, 'code': error.code if isinstance(error, Rejected) else 'IPC_FAILURE',
                          'partial': False, 'retry_safe': False, 'rollback': False}
            # Invalid unauthenticated envelopes never select an output pathname.
            # Even authenticated bad IDs receive no result; their MAC is not logged.
            if (authenticated is not None and isinstance(authenticated['cid'], str) and
                    CID.fullmatch(authenticated['cid']) and
                    type(authenticated['sequence']) is int):
                write_json(self.root, 'result.json', sign(self.key, {
                    'v': 1, 'kind': 'result', 'bridge': self.bridge,
                    'cid': authenticated['cid'], 'sequence': authenticated['sequence'], 'result': result}))
                outcome = 'ok' if result['ok'] else ('partial' if result.get('partial') else 'rejected')
                try:
                    audit_log.event(self.root, authenticated['command'], authenticated['cid'], outcome,
                                    (time.perf_counter() - started) * 1000)
                except Exception:
                    # Logging failure must never rerun a completed operation.
                    pass
            ipc_path(self.root, 'claimed.json').unlink()
            return result


class Client:
    def __init__(self, config, key, timeout=30):
        require(type(timeout) in (int, float) and 0 < timeout <= 60, 'INVALID_TIMEOUT')
        self.root, self.key, self.timeout = config['ipc_root'], key, timeout
        self.bridge = self.session = self.binding = None
        self.sequence = 0
        self.pending = None

    def descriptor(self):
        value = authenticate(self.key, loads(read_bytes(self.root, 'bridge.json')), BRIDGE_FIELDS, 'bridge')
        require(value['v'] == 1 and token(value['bridge']), 'INVALID_ENVELOPE')
        if self.bridge is not None:
            require(value['bridge'] == self.bridge, 'BRIDGE_RESTARTED_RESTART_CLIENT')
        self.bridge = value['bridge']
        return value

    def read_result(self, cid, sequence):
        path = ipc_path(self.root, 'result.json')
        if not path.exists():
            return None
        value = authenticate(self.key, loads(read_bytes(self.root, 'result.json')), RESULT_FIELDS, 'result')
        require(value['v'] == 1 and value['bridge'] == self.bridge and
                value['cid'] == cid and value['sequence'] == sequence, 'RESULT_MISMATCH')
        result = value['result']
        require(type(result) is dict and type(result.get('ok')) is bool, 'INVALID_RESULT')
        path.unlink()
        return result

    @staticmethod
    def public(result):
        # Capability material never appears in MCP tool content or audit logs.
        result = dict(result)
        if type(result.get('result')) is dict:
            result['result'] = {k: v for k, v in result['result'].items() if k not in ('session', 'binding')}
        return result

    def call(self, command, args):
        validate_command(command, args)
        with exclusive(self.root, 'client.lock'):
            self.descriptor()
            uncertainty = ipc_path(self.root, 'uncertain.json')
            if uncertainty.exists():
                # This tombstone survives client restarts. It is never a job retry.
                record = authenticate(self.key, loads(read_bytes(self.root, 'uncertain.json')),
                                      {'kind', 'bridge', 'cid', 'sequence'}, 'uncertain')
                if record['bridge'] == self.bridge:
                    if command == 'test_status':
                        late = self.read_result(record['cid'], record['sequence'])
                        return {'ok': False, 'code': 'AMBIGUOUS_TIMEOUT', 'retry_safe': False,
                                'rollback': False, 'late_result': self.public(late) if late else None}
                    raise Rejected('AMBIGUOUS_TIMEOUT_REQUIRES_LOCAL_REVIEW')
                raise Rejected('OLD_UNCERTAINTY_REQUIRES_LOCAL_REVIEW')
            for name in ('request.json', 'claimed.json', 'result.json'):
                require(not ipc_path(self.root, name).exists(), 'IPC_SLOT_BUSY')
            self.sequence += 1
            cid = secrets.token_hex(16)
            issued = time.time()
            job = sign(self.key, {'v': 1, 'kind': 'request', 'bridge': self.bridge,
                                  'session': self.session, 'binding': self.binding,
                                  'sequence': self.sequence, 'cid': cid, 'issued': issued,
                                  'expires': issued + self.timeout, 'command': command, 'args': args})
            # Persist uncertainty *before* publishing the request. A killed client
            # cannot lose its uncertainty and silently retry on its next launch.
            write_json(self.root, 'uncertain.json', sign(self.key, {
                'kind': 'uncertain', 'bridge': self.bridge, 'cid': cid, 'sequence': self.sequence}))
            write_json(self.root, 'request.json', job)
            self.pending = (cid, self.sequence)
            deadline = time.monotonic() + self.timeout
            while time.monotonic() < deadline:
                result = self.read_result(cid, self.sequence)
                if result is not None:
                    if result['ok'] and command == 'test_arm':
                        require(token(result['result'].get('session')) and token(result['result'].get('binding')),
                                'INVALID_ARM_RESULT')
                        self.session, self.binding = result['result']['session'], result['result']['binding']
                    elif result['ok'] and command == 'test_disarm':
                        self.session = self.binding = None
                    uncertainty.unlink()
                    self.pending = None
                    return self.public(result)
                time.sleep(0.02)
            # Do not delete, requeue or resubmit a possibly executing mutation.
            return {'ok': False, 'code': 'AMBIGUOUS_TIMEOUT', 'retry_safe': False, 'rollback': False}
