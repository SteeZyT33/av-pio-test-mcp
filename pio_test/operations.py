"""Explicit test operations. No function name is resolved from client input."""

import math

from .errors import require
from .schema import DIAGNOSTICS, MAX_OBJECTS, PARAMETERS, RESET_FIELD, obj, validate


class Operations:
    def __init__(self, authority):
        self.auth = authority
        self.vw = authority.adapter
        self.stage = "validation"
        self.attempted = False
        self.previous_mutation = False
        self.completed = 0
        self.created = []

    def mark(self, stage):
        self.auth.guard()
        self.stage = stage
        self.attempted = True

    def read(self, object_id):
        tool = self.auth.object(object_id)
        has_pending = getattr(self.vw, "has_pending", None)
        self.previous_mutation = has_pending is not None and has_pending(object_id)
        self.stage = "readback"
        state = self.vw.read(object_id, tool)
        validate(
            state,
            obj(
                {
                    "parameters": obj(PARAMETERS[tool]),
                    "diagnostics": obj(DIAGNOSTICS[tool]),
                }
            ),
        )
        state["geometry"] = self.vw.inspect_geometry(
            object_id, tool, lambda: self.auth.object(object_id)
        )
        confirmation = getattr(self.vw, "confirm_inspection", None)
        if confirmation is not None:
            state["regeneration"] = confirmation(object_id, state)
        self.auth.object(object_id)
        return state

    def regenerate(self, object_id, expected=None):
        tool = self.auth.object(object_id)
        self.mark("regeneration")
        proof = self.vw.regenerate_completed(object_id)
        if (
            type(proof) is dict
            and proof.get("completed") is False
            and set(proof) == {"completed", "vw_ms", "confirmation"}
            and proof["confirmation"] == "later_menu_inspection"
        ):
            require(
                type(proof["vw_ms"]) in (int, float)
                and math.isfinite(proof["vw_ms"])
                and 0 <= proof["vw_ms"] <= 3600000,
                "REGENERATION_UNCONFIRMED",
            )
            return {
                "object_id": object_id,
                "completed": False,
                "pending": True,
                "next_action": "test_read_in_later_menu_invocation",
                "rollback": False,
                "retry_safe": False,
                "vw_reset_call_ms": proof["vw_ms"],
            }
        require(
            type(proof) is dict
            and set(proof) == {"completed", "vw_ms"}
            and proof["completed"] is True
            and type(proof["vw_ms"]) in (int, float)
            and math.isfinite(proof["vw_ms"])
            and 0 <= proof["vw_ms"] <= 3600000,
            "REGENERATION_UNCONFIRMED",
        )
        state = self.read(object_id)
        expected = dict(expected or {})
        # These are one-shot placement requests, cleared by successful native draw.
        if expected.get(RESET_FIELD[tool]) is True:
            expected[RESET_FIELD[tool]] = False
        for name, value in expected.items():
            actual = state["parameters"][name]
            matches = (
                math.isclose(actual, value, rel_tol=1e-9, abs_tol=1e-7)
                if type(value) in (int, float)
                else actual == value
            )
            require(matches, "READBACK_MISMATCH")
        require(
            state["parameters"][RESET_FIELD[tool]] is False,
            "PLACEMENT_RESET_NOT_CLEARED",
        )
        return {
            "object_id": object_id,
            "state": state,
            "vw_regeneration_ms": proof["vw_ms"],
        }

    def create(self, args):
        self.auth.guard()
        require(len(self.auth.owned) < MAX_OBJECTS, "OBJECT_LIMIT")
        self.vw.validate_creation(
            args
        )  # capabilities/metadata/endpoints before mutation
        self.mark("creation")
        object_id = self.vw.create(args)
        self.auth.claim(object_id, args["tool"])
        self.created.append(object_id)
        return self.set_parameters(
            {
                "object_id": object_id,
                "tool": args["tool"],
                "parameters": args["parameters"],
            }
        )

    def set_parameters(self, args):
        object_id = args["object_id"]
        tool = self.auth.object(object_id)
        require(tool == args["tool"], "WRONG_PARAMETRIC_RECORD")
        for name, value in args["parameters"].items():
            self.auth.object(object_id)
            self.mark("parameter_write")
            self.vw.set_parameter(object_id, tool, name, value)
        return self.regenerate(object_id, args["parameters"])

    def transform(self, args):
        object_id = args["object_id"]
        self.auth.object(object_id)
        self.vw.validate_transform(object_id, args)
        self.mark("transform")
        self.vw.transform(object_id, args)
        self.auth.object(object_id)  # mirror must keep UUID and object lifetime
        return self.regenerate(object_id)

    def case(self, args):
        validate_case = getattr(self.vw, "validate_case", None)
        if validate_case is not None:
            validate_case(args)
        # Validate the entire object list before the first mutation.
        for object_id in args["object_ids"]:
            self.auth.object(object_id)
        timings = []
        for iteration in range(args["iterations"]):
            for object_id in args["object_ids"]:
                tool = self.auth.object(object_id)
                if args["case"] == "regenerate_owned":
                    result = self.regenerate(object_id)
                else:
                    field = (
                        RESET_FIELD[tool]
                        if args["case"] == "placement_reset"
                        else ("Reference" if tool == "AV Post" else "Callout")
                    )
                    value = (
                        True
                        if args["case"] == "placement_reset"
                        else "AV test %d\nsecond line" % iteration
                    )
                    result = self.set_parameters(
                        {
                            "object_id": object_id,
                            "tool": tool,
                            "parameters": {field: value},
                        }
                    )
                self.completed += 1
                timings.append(result["vw_regeneration_ms"])
        return {
            "case": args["case"],
            "completed_iterations": self.completed,
            "vw_regeneration_ms": timings,
            "rollback": False,
        }

    def cleanup(self, args):
        for object_id in args["object_ids"]:
            self.auth.object(object_id)
        for object_id in args["object_ids"]:
            self.auth.object(object_id)
            self.mark("delete_owned")
            self.vw.delete(object_id)
            self.auth.guard()
            require(self.vw.absent(object_id), "DELETE_UNCONFIRMED")
            del self.auth.owned[object_id]
            self.completed += 1
        return {"deleted": self.completed, "rollback": False}
