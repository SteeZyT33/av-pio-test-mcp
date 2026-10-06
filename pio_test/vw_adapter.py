"""Restricted Post adapter for the separately reviewed native observer.

Never infer a document lifetime from a saved path, layer handle, marker or UUID.
Never infer completed regeneration from ResetObject returning, a sleep, matching
parameter strings, or a bounding-box change. NativeProof requires an actual
SDK observer, a verified menu scope, fresh children and later native inspection.
It is a code interface, NOT a configurable/importable client-supplied provider.
"""

import uuid

from .errors import Rejected, require
from .schema import PARAMETERS, DIAGNOSTICS, POST_SIZES
from .inspection import inspect_owned_children
from .native_proof import NativeProof

NATIVE_BLOCKERS = [
    "NATIVE_OBSERVER_REQUIRED",
    "NATIVE_ACCEPTANCE_PENDING",
    "NATIVE_LINEAR_CREATION_UNSUPPORTED",
    "NATIVE_TRANSFORM_CALIBRATION_REQUIRED",
]


class VwAdapter:
    blockers = NATIVE_BLOCKERS

    def __init__(self, vs_module):
        self.vs = vs_module
        self.proof = NativeProof(vs_module)

    def identity(self):
        identity = self.proof.identity()
        # This documented path call is only corroboration, never lifetime proof.
        require(self.vs.GetFPathName() == identity.path, "NATIVE_FULL_PATH_MISMATCH")
        return identity

    def operator_control(self):
        return self.proof.control()

    def bridge_started(self):
        self.proof.call("AVPIOTestBridgeStarted")

    def pending_confirmation(self):
        return bool(self.proof.pending)

    def preflight(self):
        self.proof.preflight()
        # Event-Based OFF, move/rotate reset flags and Point configuration still
        # require operator verification in the native definition manager.

    def handle(self, object_id):
        self.proof.assert_menu_context()
        h = self.vs.GetObjectByUuid(object_id)
        require(h and self.vs.GetTypeN(h) == 86, "PIO_MISSING")
        return h

    def object_identity(self, object_id):
        h = self.handle(object_id)
        record = self.vs.GetParametricRecord(h)
        require(record, "PARAMETRIC_RECORD_MISSING")
        name = self.vs.GetName(record)
        require(name in PARAMETERS, "TOOL_NOT_ALLOWED")
        # Must also verify direct parent = the bound synthetic design layer,
        # no wall/container/reference object, and native object lifetime.
        return name, self.proof.object_lifetime(h)

    def validate_creation(self, args):
        self.proof.validate_creation(args, POST_SIZES)

    def create(self, args):
        self.proof.assert_menu_context()
        if args["tool"] == "AV Post":
            h = self.vs.CreateCustomObjectN(
                "AV Post", tuple(args["origin"]), args["rotation"], False
            )
        elif args["tool"] == "AV Callout":
            # Linear endpoints are NOT ControlPoint01X/Y (the elbow).
            h = self.proof.create_linear(tuple(args["origin"]), tuple(args["end"]))
        else:
            raise Rejected("TOOL_NOT_ALLOWED")
        require(h, "CREATE_FAILED")
        # Apply only to the new PIO; never change the active class or layer.
        self.vs.SetClass(h, "AV-MCP-TEST")
        return str(uuid.UUID(self.vs.GetObjectUuid(h)))

    def read(self, object_id, tool):
        h = self.handle(object_id)
        result = {}
        for category, fields in (
            ("parameters", PARAMETERS[tool]),
            ("diagnostics", DIAGNOSTICS[tool]),
        ):
            result[category] = {
                name: self.proof.decode(name, self.vs.GetRField(h, tool, name), schema)
                for name, schema in fields.items()
            }
        return result

    def set_parameter(self, object_id, tool, name, value):
        require(name in PARAMETERS[tool], "READ_ONLY_FIELD")
        h = self.handle(object_id)
        self.vs.SetRField(
            h, tool, name, self.proof.encode(name, value, PARAMETERS[tool][name])
        )
        self.proof.parameter_written(h, name, value)

    def regenerate_completed(self, object_id):
        # The proof implementation owns reset and completion observation. Do not
        # insert ResetObject here and then return a fabricated completion flag.
        return self.proof.regenerate_completed(self.handle(object_id))

    def confirm_inspection(self, object_id, state):
        return self.proof.confirm_inspection(self.handle(object_id), state)

    def has_pending(self, object_id):
        key = self.vs.GetObjectUuid(self.handle(object_id))
        return key in self.proof.pending

    def validate_case(self, args):
        # Multi-reset named cases need a continuation protocol; reject before
        # the first mutation rather than executing a partially confirmed suite.
        raise Rejected("NATIVE_CASE_REQUIRES_CONTINUATIONS")

    def validate_transform(self, object_id, args):
        self.proof.validate_transform(self.handle(object_id), args)

    def transform(self, object_id, args):
        h = self.handle(object_id)
        if args["action"] == "move":
            self.vs.HMove(h, *args["offset"])
        elif args["action"] == "rotate":
            self.vs.HRotate(h, tuple(args["center"]), args["angle"])
        elif args["action"] == "mirror":
            result = self.vs.MirrorN(
                h, False, tuple(args["axis_start"]), tuple(args["axis_end"]), True
            )
            require(result == h, "MIRROR_REPLACED_OBJECT")
        else:
            raise Rejected("INVALID_TRANSFORM")

    def delete(self, object_id):
        self.vs.DelObject(self.handle(object_id))

    def absent(self, object_id):
        self.proof.assert_menu_context()
        return not self.vs.GetObjectByUuid(object_id)

    def inspect_geometry(self, object_id, tool, guard):
        adapter = self

        class ChildReader:
            def frame(self, root):
                return adapter.proof.geometry_frame(root)

            def first_child(self, parent):
                return adapter.vs.FInGroup(parent)

            def next_sibling(self, child):
                return adapter.vs.NextObj(child)

            def parent(self, child):
                return adapter.vs.GetParent(child)

            def describe(self, child, root):
                return adapter.proof.describe_child(child, root)

        return inspect_owned_children(
            self.handle(object_id), ChildReader(), guard, tool
        )
