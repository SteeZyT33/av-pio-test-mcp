"""Fixed SDK-observer ABI, available only inside the supervised Python menu.

There is no provider path, import name, success flag or script in configuration.
The private observer must register lifecycle callbacks and surround a real menu
invocation before any native call succeeds. Source/build/native calibration are
reviewed separately. This module does not install or load a DLL itself.
"""

import math
import uuid

from .authorization import DocumentIdentity
from .errors import Rejected, require
from .field_codec import decode, encode, native_type
from .native_geometry import describe
from .schema import DIAGNOSTICS, PARAMETERS, validate
from .wire import loads, token

MENU = "AV PIO Test Pump"
FIXTURE = "AV-MCP-TEST"
FUNCTIONS = ("AVPIOTestSnapshot", "AVPIOTestObject", "AVPIOTestReset")


class NativeProof:
    def __init__(self, vs):
        self.vs = vs
        self.expected = {}
        self.pending = {}

    def call(self, function, *args):
        require(function in FUNCTIONS, "INVALID_NATIVE_FUNCTION")
        routine = getattr(self.vs, function, None)
        require(callable(routine), "NATIVE_OBSERVER_UNAVAILABLE")
        raw = routine(*args)
        require(
            type(raw) is str and len(raw.encode("utf-8")) <= 8192,
            "INVALID_NATIVE_PROOF",
        )
        value = loads(raw.encode("utf-8"))
        require(type(value) is dict and value.get("abi") == 1, "INVALID_NATIVE_PROOF")
        require(value.get("ok") is True, "NATIVE_PROOF_REJECTED")
        return value

    def assert_menu_context(self):
        # Check availability before asking any host document question.
        require(
            all(callable(getattr(self.vs, name, None)) for name in FUNCTIONS),
            "NATIVE_OBSERVER_UNAVAILABLE",
        )
        current = self.vs.GetPluginInfo()
        require(
            type(current) is tuple
            and len(current) == 3
            and current[0]
            and current[1] == MENU,
            "NATIVE_MENU_CONTEXT_UNVERIFIED",
        )
        pio = self.vs.GetCustomObjectInfo()
        require(
            type(pio) is tuple and len(pio) == 5 and not pio[2], "PIO_REENTRANT_CONTEXT"
        )
        snapshot = self.call("AVPIOTestSnapshot")
        require(snapshot.get("menu_scope") is True, "NATIVE_MENU_CONTEXT_UNVERIFIED")
        return snapshot

    def identity(self):
        state = self.assert_menu_context()
        require(
            token(state.get("instance"))
            and token(state.get("fixture"))
            and type(state.get("generation")) is int
            and state["generation"] > 0
            and type(state.get("path")) is str,
            "INVALID_NATIVE_PROOF",
        )
        return DocumentIdentity(
            state["path"], state["instance"], state["generation"], state["fixture"]
        )

    def environment(self):
        state = self.assert_menu_context()
        upi = self.vs.GetUnits()[3]
        units = "inches" if upi == 1 else "mm" if upi == 25.4 else None
        layer = self.vs.ActLayer()
        require(
            layer
            and self.vs.GetLName(layer) == FIXTURE
            and self.vs.GetObjectVariableInt(layer, 154) == 1,
            "WRONG_FIXTURE_LAYER",
        )
        scale = self.vs.GetLScale(layer)
        require(state.get("fixture_class") is True, "WRONG_FIXTURE_CLASS")
        require(
            units is not None
            and scale in (24, 48, 96)
            and state.get("top_plan") is True,
            "UNSUPPORTED_NATIVE_ENVIRONMENT",
        )
        version = self.vs.GetVersionEx()
        require(
            type(version) is tuple
            and len(version) == 5
            and version[0] == 31
            and version[3] == 2
            and version[4] == 879357,
            "UNREVIEWED_NATIVE_HOST",
        )
        return state, units, int(scale), layer

    def metadata(self):
        record = self.vs.GetObject("AV Post")
        require(
            record and self.vs.GetTypeN(record) == 47, "POST_DEFINITION_UNAVAILABLE"
        )
        fields = dict(PARAMETERS["AV Post"], **DIAGNOSTICS["AV Post"])
        count = self.vs.NumFields(record)
        require(type(count) is int and count == len(fields), "POST_DEFINITION_MISMATCH")
        seen = set()
        for index in range(1, count + 1):
            name = self.vs.GetFldName(record, index)
            require(name in fields and name not in seen, "POST_DEFINITION_MISMATCH")
            seen.add(name)
            schema = fields[name]
            require(
                self.vs.GetFldType(record, index) == native_type(name, schema),
                "POST_FIELD_TYPE_MISMATCH",
            )
            if "enum" in schema:
                choices = self.vs.NumCustomObjectChoices("AV Post", name)
                require(choices == len(schema["enum"]), "POST_CATALOG_MISMATCH")
                require(
                    [
                        self.vs.GetCustomObjectChoice("AV Post", name, n)
                        for n in range(1, choices + 1)
                    ]
                    == schema["enum"],
                    "POST_CATALOG_MISMATCH",
                )
        # Exact schema excludes native LineLength/BoxWidth/BoxHeight fields;
        # explicit unsupported Path definitions are rejected after creation too.

    def preflight(self):
        state, _units, _scale, layer = self.environment()
        require(state.get("post_plugin_object") is True, "POST_DEFINITION_UNAVAILABLE")
        self.metadata()
        require(not self.vs.FInLayer(layer), "INITIAL_FIXTURE_NOT_EMPTY")

    def object_state(self, handle):
        self.environment()
        require(
            handle
            and self.vs.GetTypeN(handle) == 86
            and self.vs.GetParent(handle) == self.vs.ActLayer()
            and self.vs.GetClass(handle) == FIXTURE,
            "FOREIGN_NATIVE_OBJECT",
        )
        require(not self.vs.GetCustomObjectPath(handle), "PATH_PIO_UNSUPPORTED")
        state = self.call("AVPIOTestObject", handle)
        require(token(state.get("lifetime")), "NATIVE_OBJECT_LIFETIME_UNAVAILABLE")
        matrix = state.get("matrix")
        require(
            type(matrix) is list
            and len(matrix) == 6
            and all(type(x) in (int, float) and math.isfinite(x) for x in matrix),
            "INVALID_NATIVE_GEOMETRY_FRAME",
        )
        return state

    def object_lifetime(self, handle):
        return self.object_state(handle)["lifetime"]

    def validate_creation(self, args, post_catalog):
        self.environment()
        self.metadata()
        require(args["tool"] == "AV Post", "NATIVE_LINEAR_CREATION_UNSUPPORTED")
        require(
            args["origin"] == [0, 0] and args["rotation"] == 0,
            "POST_PLACEMENT_CALIBRATION_REQUIRED",
        )
        require(
            PARAMETERS["AV Post"]["PostSize"]["enum"] == post_catalog,
            "POST_CATALOG_MISMATCH",
        )
        for name, value in args["parameters"].items():
            self.encode(name, value, PARAMETERS["AV Post"][name])

    def create_linear(self, start, end):
        raise Rejected("NATIVE_LINEAR_CREATION_UNSUPPORTED")

    def encode(self, name, value, schema):
        _state, units, _scale, _layer = self.environment()
        return encode(self.vs, name, value, schema, units)

    def decode(self, name, value, schema):
        self.assert_menu_context()
        return decode(self.vs, name, value, schema)

    def parameter_written(self, handle, name, value):
        key = self.vs.GetObjectUuid(handle)
        self.expected.setdefault(key, {})[name] = value

    def regenerate_completed(self, handle):
        self.object_state(handle)
        before = self.child_identities(handle)
        submitted = self.call("AVPIOTestReset", handle)
        require(
            submitted.get("submitted") is True
            and token(submitted.get("ticket"))
            and type(submitted.get("invocation")) is int
            and type(submitted.get("vw_ms")) in (int, float)
            and math.isfinite(submitted["vw_ms"])
            and 0 <= submitted["vw_ms"] <= 3600000,
            "REGENERATION_UNCONFIRMED",
        )
        after = self.child_identities(handle)
        require(
            after and not before.intersection(after), "FRESH_REGENERATION_UNCONFIRMED"
        )
        submitted["fresh_children"] = after
        self.pending[self.vs.GetObjectUuid(handle)] = submitted
        return {
            "completed": False,
            "vw_ms": submitted["vw_ms"],
            "confirmation": "later_menu_inspection",
        }

    def child_identities(self, root):
        # Read only actual direct children; never advance a leaked parent list.
        children = set()
        handles = []
        initial = self.assert_menu_context()
        binding = tuple(
            initial[key] for key in ("instance", "generation", "fixture", "path")
        )
        child = self.vs.FInGroup(root)
        while child:
            current = self.assert_menu_context()
            require(
                tuple(
                    current[key]
                    for key in ("instance", "generation", "fixture", "path")
                )
                == binding,
                "DOCUMENT_MISMATCH",
            )
            if self.vs.GetParent(child) != root:
                require(not children, "FOREIGN_CHILD")
                return set()  # known empty-container FInGroup leak, not a traversal
            require(
                child not in handles and len(handles) < 128, "CHILD_INSPECTION_LIMIT"
            )
            handles.append(child)
            try:
                identity = str(uuid.UUID(self.vs.GetObjectUuid(child)))
            except (ValueError, TypeError, AttributeError):
                raise Rejected("CHILD_LIFETIME_UNAVAILABLE")
            require(identity not in children, "CHILD_CYCLE")
            children.add(identity)
            child = self.vs.NextObj(child)
        return children

    def confirm_inspection(self, handle, state):
        native = self.object_state(handle)
        key = self.vs.GetObjectUuid(handle)
        pending = self.pending.get(key)
        if pending is None:
            return {"completed": False, "reason": "no_observed_reset"}
        require(
            native.get("reset_ticket") == pending["ticket"], "RESET_TICKET_MISMATCH"
        )
        require(
            native.get("immediate_reset_returned") is True, "REGENERATION_UNCONFIRMED"
        )
        require(
            type(native.get("invocation")) is int
            and native["invocation"] > pending["invocation"],
            "REGENERATION_PENDING",
        )
        require(state["geometry"]["children"], "EMPTY_GENERATED_GEOMETRY")
        require(
            self.child_identities(handle) == pending["fresh_children"],
            "GENERATED_CHILDREN_CHANGED_AFTER_RESET",
        )
        expected = dict(self.expected.get(key, {}))
        if expected.get("ResetLeader") is True:
            expected["ResetLeader"] = False
        for name, value in expected.items():
            actual = state["parameters"][name]
            matches = (
                math.isclose(actual, value, rel_tol=1e-9, abs_tol=1e-7)
                if type(value) in (int, float)
                else actual == value
            )
            require(matches, "READBACK_MISMATCH")
        require(
            state["parameters"]["ResetLeader"] is False, "PLACEMENT_RESET_NOT_CLEARED"
        )
        children = state["geometry"]["children"]
        require(
            any(child["kind"] == "polyline" for child in children),
            "POST_FOOTPRINT_UNCONFIRMED",
        )
        if state["parameters"]["ShowLabel"]:
            texts = [child["text"] for child in children if child["kind"] == "text"]
            require(
                texts and sum(child["kind"] == "line" for child in children) >= 2,
                "POST_LABEL_UNCONFIRMED",
            )
            reference = state["parameters"]["Reference"].strip()
            notes = state["parameters"]["Notes"].strip()
            require(
                not reference or any(reference in text for text in texts),
                "POST_LABEL_UNCONFIRMED",
            )
            require(not notes or notes in texts, "POST_LABEL_UNCONFIRMED")
        return {
            "completed": True,
            "vw_ms": pending["vw_ms"],
            "boundary": "immediate_reset_and_later_menu_readback",
            "semantic_geometry_validation": False,
        }

    def validate_transform(self, handle, args):
        raise Rejected("NATIVE_TRANSFORM_CALIBRATION_REQUIRED")

    def geometry_frame(self, handle):
        native = self.object_state(handle)
        _state, units, scale, _layer = self.environment()
        require(
            native["matrix"] == [1, 0, 0, 1, 0, 0],
            "POST_PLACEMENT_CALIBRATION_REQUIRED",
        )
        return {
            "space": "pio_local_document_units",
            "units": units,
            "layer_scale": scale,
            "pio_to_document": native["matrix"],
            "native_linear_endpoints": [],
        }

    def describe_child(self, handle, root):
        native = self.object_state(root)
        native["top_plan"] = self.assert_menu_context()["top_plan"]
        return describe(self.vs, handle, root, native)
