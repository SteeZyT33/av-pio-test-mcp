"""Local OFF is authoritative across IPC, sessions and process reconnects."""

import secrets
import threading
import time
import unittest

from pio_test.engine import Engine
from pio_test.errors import Rejected
from pio_test.transport import Client, Pump
from pio_test.wire import sign, write_json
from tests.support import Fixture, POST_CREATE


class OperatorControlTests(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()
        self.addCleanup(self.f.close)
        self.f.adapter.local_disable()
        self.engine = Engine(self.f.root, self.f.adapter)

    def call(self, command, args=None):
        auth = self.engine.auth
        return self.engine.execute(command, args or {}, auth.session, auth.binding)

    def enable_and_arm(self):
        self.f.adapter.local_enable()
        result = self.call("test_arm", {"drawing": "disposable.vwx"})
        self.assertTrue(result["ok"], result)

    def test_default_off_rejects_arm_before_any_document_query(self):
        self.f.adapter.identity = lambda: self.fail("OFF must not query a drawing")
        self.assertEqual(self.call("test_status")["result"]["state"], "OFF")
        self.assertEqual(
            self.call("test_arm", {"drawing": "disposable.vwx"})["code"],
            "PIO_TESTING_OFF",
        )
        self.assertEqual(self.f.adapter.mutations, 0)

    def test_enable_only_ready_explicit_arm_then_disable_preserves_objects(self):
        self.f.adapter.local_enable()
        self.assertEqual(self.call("test_status")["result"]["state"], "READY")
        self.assertIsNone(self.engine.auth.session)
        self.assertTrue(self.call("test_arm", {"drawing": "disposable.vwx"})["ok"])
        created = self.call("test_create", POST_CREATE)
        self.assertTrue(created["ok"], created)
        key = created["result"]["object_id"]
        self.assertEqual(self.engine.operator_status()["state"], "ARMED")
        self.f.adapter.current = None
        self.f.adapter.local_disable()
        status = self.engine.operator_status()
        self.assertEqual(status["state"], "OFF")
        self.assertFalse(status["armed"])
        self.assertFalse(self.engine.auth.owned)
        self.assertIn(key, self.f.adapter.objects)
        self.assertEqual(
            self.call("test_read", {"object_id": key})["code"], "PIO_TESTING_OFF"
        )

    def test_old_session_cannot_return_after_disable_enable(self):
        self.enable_and_arm()
        old_session, old_binding = self.engine.auth.session, self.engine.auth.binding
        self.f.adapter.local_disable()
        self.f.adapter.local_enable()
        result = self.engine.execute(
            "test_create", POST_CREATE, old_session, old_binding
        )
        self.assertEqual(result["code"], "SESSION_MISMATCH")
        self.assertEqual(self.f.adapter.mutations, 0)
        self.assertEqual(self.engine.operator_status()["state"], "READY")

    def test_local_status_revokes_switched_document_without_document_queries(self):
        self.enable_and_arm()
        from dataclasses import replace

        self.f.adapter.current = replace(self.f.adapter.current, generation=2)
        self.f.adapter.identity = lambda: self.fail(
            "local status must not query drawing"
        )
        self.assertEqual(self.engine.operator_status()["state"], "READY")
        self.assertIsNone(self.engine.auth.session)

    def job(self, pump, command, args):
        auth = pump.engine.auth
        now = time.time()
        return sign(
            self.f.key,
            {
                "v": 1,
                "kind": "request",
                "bridge": pump.bridge,
                "session": auth.session,
                "binding": auth.binding,
                "sequence": pump.sequence + 1,
                "cid": secrets.token_hex(16),
                "issued": now,
                "expires": now + 30,
                "command": command,
                "args": args,
            },
        )

    def ready_pump(self):
        pump = Pump(self.f.config, self.f.key, self.f.adapter)
        self.assertFalse(self.f.adapter.enabled)  # bridge startup forces OFF
        self.f.adapter.local_enable()
        pump.operator_sync()
        write_json(
            self.f.ipc,
            "request.json",
            self.job(pump, "test_arm", {"drawing": "disposable.vwx"}),
        )
        self.assertTrue(pump.run_once()["ok"])
        (self.f.ipc / "result.json").unlink()
        return pump

    def test_queued_job_invalidated_before_claim_and_cannot_return_after_enable(self):
        pump = self.ready_pump()
        old_bridge = pump.bridge
        write_json(
            self.f.ipc, "request.json", self.job(pump, "test_create", POST_CREATE)
        )
        self.f.adapter.local_disable()
        self.assertEqual(pump.operator_sync()["state"], "OFF")
        self.assertNotEqual(pump.bridge, old_bridge)
        with self.assertRaisesRegex(Rejected, "PIO_TESTING_OFF"):
            pump.run_once()
        self.assertTrue((self.f.ipc / "request.json").exists())
        self.assertFalse((self.f.ipc / "claimed.json").exists())
        self.assertEqual(self.f.adapter.mutations, 0)
        self.f.adapter.local_enable()
        pump.operator_sync()
        self.assertEqual(pump.run_once()["code"], "BRIDGE_MISMATCH")
        self.assertFalse((self.f.ipc / "claimed.json").exists())
        self.assertEqual(self.f.adapter.mutations, 0)

    def test_disable_revokes_even_when_ipc_authentication_is_broken(self):
        pump = self.ready_pump()
        self.f.write("bridge.json", b"{}")
        self.f.adapter.local_disable()
        with self.assertRaises(Rejected):
            pump.operator_sync()
        self.assertIsNone(pump.engine.auth.session)
        self.assertEqual(pump.engine.operator_status()["state"], "OFF")

    def test_external_client_restart_does_not_enable_or_arm(self):
        pump = Pump(self.f.config, self.f.key, self.f.adapter)
        for _ in range(2):
            client = Client(self.f.config, self.f.key)
            self.assertEqual(client.descriptor()["operator_state"], "OFF")
            self.assertIsNone(client.session)
            self.assertFalse(self.f.adapter.enabled)
            status = client.call("test_status", {})
            self.assertEqual(status["result"]["state"], "OFF")
            self.assertFalse(status["result"]["live_status_verified"])
            self.assertEqual(
                client.call("test_arm", {"drawing": "disposable.vwx"})["code"],
                "PIO_TESTING_OFF",
            )
            self.assertFalse((self.f.ipc / "request.json").exists())
        self.assertEqual(pump.engine.operator_status()["state"], "OFF")

    def test_shutdown_with_claim_starts_off_and_requires_local_recovery(self):
        self.f.adapter.local_enable()
        self.f.write("claimed.json", b"{}")
        with self.assertRaisesRegex(Rejected, "UNRESOLVED_CLAIM"):
            Pump(self.f.config, self.f.key, self.f.adapter)
        self.assertFalse(self.f.adapter.enabled)
        self.assertTrue((self.f.ipc / "claimed.json").exists())
        self.assertEqual(self.engine.operator_status()["state"], "OFF")

    def test_disable_during_claimed_operation_waits_and_never_claims_rollback(self):
        self.enable_and_arm()
        entered, release = threading.Event(), threading.Event()
        original = self.f.adapter.create
        original_control = self.f.adapter.operator_control
        running = [False]

        def control():
            value = original_control()
            value["busy"] = running[0]
            value["disable_pending"] = running[0] and not value["enabled"]
            return value

        def delayed(args):
            running[0] = True
            entered.set()
            if not release.wait(3):
                raise AssertionError("test release timed out")
            return original(args)

        self.f.adapter.operator_control = control
        self.f.adapter.create = delayed
        result = []
        worker = threading.Thread(
            target=lambda: result.append(self.call("test_create", POST_CREATE))
        )
        worker.start()
        try:
            self.assertTrue(entered.wait(2))
            self.f.adapter.local_disable()
            status = self.engine.operator_status()
            self.assertEqual(status["state"], "BUSY")
            self.assertTrue(status["disable_pending"])
            self.assertTrue(worker.is_alive())
        finally:
            release.set()
            worker.join(3)
            running[0] = False
        self.assertFalse(worker.is_alive())
        self.assertTrue(result[0]["partial"])
        self.assertFalse(result[0]["rollback"])
        self.assertFalse(result[0]["retry_safe"])
        status = self.engine.operator_status()
        self.assertEqual(status["state"], "OFF")
        self.assertTrue(status["outcome_unconfirmed"])
        self.assertEqual(len(self.f.adapter.objects), 1)
