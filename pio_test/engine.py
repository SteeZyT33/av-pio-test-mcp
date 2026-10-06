"""Second authorization boundary, inside VW. Direct IPC uses this same path."""

import threading

from .authorization import Authority
from .errors import Rejected, require
from .operations import Operations
from .operator_control import snapshot, state
from .schema import MUTATIONS, validate_command


class Engine:
    def __init__(self, root, adapter):
        self.lock = threading.Lock()
        self.control_epoch = None
        self.auth = Authority(root, adapter, self.control_guard)

    def synchronize_control(self, strict_document=False, check_document=True):
        value = snapshot(self.auth.adapter)
        if self.control_epoch != value["epoch"] or not value["enabled"]:
            pending = getattr(
                self.auth.adapter, "pending_confirmation", lambda: False
            )()
            uncertain = self.auth.uncertain or value["unconfirmed"] or pending
            self.auth.disarm()
            self.auth.uncertain = uncertain
            self.control_epoch = value["epoch"]
        if (
            check_document
            and self.auth.identity is not None
            and value["generation"] != self.auth.identity.generation
        ):
            uncertain = (
                self.auth.uncertain
                or getattr(self.auth.adapter, "pending_confirmation", lambda: False)()
            )
            self.auth.disarm()
            self.auth.uncertain = uncertain
            require(not strict_document, "DOCUMENT_MISMATCH")
        if value["unconfirmed"]:
            self.auth.uncertain = True
        return value

    def control_guard(self):
        value = self.synchronize_control(strict_document=True)
        require(value["enabled"] and not value["disable_pending"], "PIO_TESTING_OFF")
        require(not value["unconfirmed"], "NATIVE_OUTCOME_UNCONFIRMED")
        return value

    def operator_status(self, check_document=True):
        value = self.synchronize_control(check_document=check_document)
        pending = getattr(self.auth.adapter, "pending_confirmation", lambda: False)()
        return {
            "state": state(
                value, self.auth.session is not None, self.auth.uncertain, pending
            ),
            "enabled": value["enabled"],
            "disable_pending": value["disable_pending"],
            "outcome_unconfirmed": self.auth.uncertain
            or value["unconfirmed"]
            or pending,
            "armed": self.auth.session is not None,
            "owned_count": len(self.auth.owned),
            "objects_left_in_drawing": True,
            "rollback": False,
        }

    def preclaim(self, command, args, session, binding):
        validate_command(command, args)
        self.control_guard()
        if command != "test_status":
            self.auth.check_envelope(session, binding)
        if self.auth.session is not None or command not in (
            "test_status",
            "test_arm",
            "test_disarm",
        ):
            self.auth.guard()

    def execute(self, command, args, session=None, binding=None, deadline=None):
        # Nonblocking rejects recursive invocations from a PIO rather than deadlock.
        if not self.lock.acquire(False):
            return {"ok": False, "code": "BUSY", "partial": False}
        op = Operations(self.auth)
        try:
            self.auth.deadline = deadline
            validate_command(command, args)
            if command == "test_status":
                self.synchronize_control(strict_document=True)
                if self.auth.session is not None:
                    self.auth.guard()
            else:
                self.control_guard()
                self.auth.check_envelope(session, binding)
            if command not in ("test_status", "test_arm", "test_disarm"):
                self.auth.guard()
                require(not self.auth.uncertain, "SESSION_QUARANTINED")
            if command == "test_arm":
                self.auth.arm(args["drawing"])
                result = {
                    "armed": True,
                    "session": self.auth.session,
                    "binding": self.auth.binding,
                }
            elif command == "test_disarm":
                self.auth.disarm()
                result = {"armed": False, "objects_left_in_drawing": True}
            elif command == "test_status":
                result = dict(
                    self.operator_status(),
                    **{
                        "armed": self.auth.session is not None,
                        "owned_count": len(self.auth.owned),
                        "quarantined": self.auth.uncertain,
                        "native_blockers": self.auth.adapter.blockers,
                    },
                )
            elif command == "test_create":
                result = op.create(args)
            elif command == "test_read":
                result = op.read(args["object_id"])
            elif command == "test_set_parameters":
                result = op.set_parameters(args)
            elif command == "test_transform":
                result = op.transform(args)
            elif command == "test_regenerate":
                result = op.regenerate(args["object_id"])
            elif command == "test_case":
                result = op.case(args)
            elif command == "test_cleanup":
                result = op.cleanup(args)
            else:
                raise Rejected("UNKNOWN_COMMAND")
            if self.auth.session is not None:
                self.auth.guard()
            return {"ok": True, "result": result}
        except Exception as error:
            # Partial effects are never automatically undone or retried. A PIO may
            # fail after making changes even when its call did not return a UUID.
            failed_confirmation = op.previous_mutation and not (
                isinstance(error, Rejected) and error.code == "REGENERATION_PENDING"
            )
            if op.attempted or failed_confirmation:
                self.auth.uncertain = True
            return {
                "ok": False,
                "code": (
                    error.code if isinstance(error, Rejected) else "ADAPTER_FAILURE"
                ),
                "command": (
                    command
                    if isinstance(command, str) and command in MUTATIONS
                    else "validation"
                ),
                "stage": op.stage,
                "partial": op.attempted or failed_confirmation,
                "completed": op.completed,
                "created_ids": op.created,
                "rollback": False,
                "retry_safe": False,
            }
        finally:
            self.auth.deadline = None
            self.lock.release()
