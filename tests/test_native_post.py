"""Synthetic host-contract tests, never native Vectorworks acceptance."""

import json
import unittest
import uuid

from pio_test.errors import Rejected
from pio_test.field_codec import decode, encode, native_type
from pio_test.native_geometry import describe
from pio_test.native_proof import NativeProof
from pio_test.schema import DIAGNOSTICS, PARAMETERS
from pio_test.vw_adapter import VwAdapter
from pio_test.engine import Engine
from tests.support import Fixture, POST_CREATE


class HostContract:
    """A deterministic ABI/VS simulation. Does not prove SDK callback delivery."""

    def __init__(self, path):
        self.path = str(path)
        self.generation = 1
        self.invocation = 1
        self.scope = True
        self.plugin = "AV PIO Test Pump"
        self.pio_context = 0
        self.version = (31, 7, 0, 2, 879357)
        self.objects = {}
        self.resets = 0
        self.child_uuid = str(uuid.uuid4())
        self.stale_children = False
        self.enum_error = False
        self.child_limit = 4
        self.fields = dict(PARAMETERS["AV Post"], **DIAGNOSTICS["AV Post"])
        self.enabled = False
        self.control_epoch = 1
        self.native_types = {
            name: native_type(name, schema) for name, schema in self.fields.items()
        }

    def AVPIOTestSnapshot(self):
        return json.dumps(
            {
                "abi": 1,
                "ok": True,
                "menu_scope": self.scope,
                "instance": "a" * 64,
                "generation": self.generation,
                "fixture": "b" * 64,
                "path": self.path,
                "top_plan": True,
                "post_plugin_object": True,
                "fixture_class": True,
                "invocation": self.invocation,
            }
        )

    def local_enable(self):
        self.enabled = True
        self.control_epoch += 1

    def local_disable(self):
        self.enabled = False
        self.control_epoch += 1

    def AVPIOTestGate(self):
        return json.dumps(
            {
                "abi": 1,
                "ok": True,
                "enabled": self.enabled,
                "epoch": self.control_epoch,
                "generation": self.generation,
                "busy": False,
                "disable_pending": False,
                "unconfirmed": False,
            }
        )

    def AVPIOTestBridgeStarted(self):
        self.local_disable()
        return json.dumps({"abi": 1, "ok": True})

    def AVPIOTestOperatorReport(self, value):
        return json.dumps({"abi": 1, "ok": True})

    def AVPIOTestObject(self, h):
        data = self.objects[h]
        return json.dumps(
            {
                "abi": 1,
                "ok": True,
                "lifetime": data["lifetime"],
                "matrix": [1, 0, 0, 1, 0, 0],
                "invocation": self.invocation,
                "reset_ticket": data.get("ticket", ""),
                "immediate_reset_returned": data.get("reset", False),
            }
        )

    def AVPIOTestReset(self, h):
        self.resets += 1
        if not self.stale_children:
            self.child_uuid = str(uuid.uuid4())
        self.objects[h].update(ticket="c" * 64, reset=True)
        return json.dumps(
            {
                "abi": 1,
                "ok": True,
                "submitted": True,
                "ticket": "c" * 64,
                "invocation": self.invocation,
                "vw_ms": 3.5,
            }
        )

    def GetPluginInfo(self):
        return True, self.plugin, 20

    def GetCustomObjectInfo(self):
        return bool(self.pio_context), "", self.pio_context, 0, 0

    def GetVersionEx(self):
        return self.version

    def GetUnits(self):
        return 0, 0, 0, 1, '"', ""

    def ActLayer(self):
        return 1

    def GetLName(self, h):
        return "AV-MCP-TEST"

    def GetObjectVariableInt(self, h, selector):
        return 1

    def GetLScale(self, h):
        return 48

    def GetObject(self, name):
        return 20 if name == "AV Post" else 0

    def NumFields(self, h):
        return len(self.fields)

    def GetFldName(self, h, index):
        return list(self.fields)[index - 1]

    def GetFldType(self, h, index):
        return self.native_types[self.GetFldName(h, index)]

    def NumCustomObjectChoices(self, tool, name):
        return len(self.fields[name]["enum"])

    def GetCustomObjectChoice(self, tool, name, index):
        return "wrong" if self.enum_error else self.fields[name]["enum"][index - 1]

    def FInLayer(self, h):
        return next(iter(self.objects), 0)

    def GetFPathName(self):
        return self.path

    def GetTypeN(self, h):
        return 47 if h == 20 else 86 if h in self.objects else 5 if h == 100 else 0

    def GetParent(self, h):
        return 1 if h in self.objects else next(iter(self.objects))

    def GetCustomObjectPath(self, h):
        return 0

    def GetClass(self, h):
        return "AV-MCP-TEST"

    def GetParametricRecord(self, h):
        return 20

    def GetName(self, h):
        return "AV Post"

    def GetObjectUuid(self, h):
        return self.child_uuid if h == 100 else self.objects[h]["uuid"]

    def GetObjectByUuid(self, key):
        return next((h for h, data in self.objects.items() if data["uuid"] == key), 0)

    def SetClass(self, h, name):
        assert name == "AV-MCP-TEST"

    def CreateCustomObjectN(self, tool, origin, rotation, insert):
        h = len(self.objects) + 30
        values = {}
        for name, schema in self.fields.items():
            kind = schema["type"]
            value = (
                schema["enum"][0]
                if "enum" in schema
                else False if kind == "boolean" else "" if kind == "string" else 1
            )
            if name == "TextSize":
                value = 8.5
            if name == "PlacementScale":
                value = 48
            if name == "KingSize":
                value = "2x6"
            values[name] = encode(self, name, value, schema, "inches")
        self.objects[h] = {
            "uuid": str(uuid.uuid4()),
            "lifetime": "d" * 64,
            "fields": values,
        }
        return h

    def ValidNumStr(self, value):
        try:
            return True, float(value.removesuffix("mm").removesuffix('"'))
        except ValueError:
            return False, 0

    def GetRField(self, h, tool, name):
        return self.objects[h]["fields"][name]

    def SetRField(self, h, tool, name, value):
        self.objects[h]["fields"][name] = value

    def FInGroup(self, h):
        return 100

    def NextObj(self, h):
        return 0

    def GetVertNum(self, h):
        return self.child_limit

    def GetPolyPt(self, h, index):
        return ((-2, -2), (2, -2), (2, 2), (-2, 2))[index - 1]

    def IsPolyClosed(self, h):
        return True


class CodecTests(unittest.TestCase):
    def setUp(self):
        self.host = HostContract("unused.vwx")

    def test_exact_strings_booleans_and_dimensionless_reals(self):
        fields = PARAMETERS["AV Post"]
        for name, value in [
            ("Notes", "  two lines\n next  "),
            ("ShowLabel", False),
            ("TextSize", 8.50000000001),
            ("KingStuds", 2),
            ("KingSize", "6x6"),
        ]:
            raw = encode(self.host, name, value, fields[name], "inches")
            self.assertEqual(decode(self.host, name, raw, fields[name]), value)

    def test_coordinate_units_and_nonfinite_rejected(self):
        schema = PARAMETERS["AV Post"]["ControlPoint01X"]
        self.assertEqual(
            encode(self.host, "ControlPoint01X", -2.5, schema, "mm"), "-2.5mm"
        )
        for raw in ["NaN", "Infinity", "invalid"]:
            with self.assertRaises(Rejected):
                decode(self.host, "ControlPoint01X", raw, schema)

    def test_no_enum_or_number_coercion(self):
        for name, value in [
            ("KingSize", " 6x6"),
            ("KingStuds", True),
            ("ShowLabel", 1),
        ]:
            with self.assertRaises(Rejected):
                encode(self.host, name, value, PARAMETERS["AV Post"][name], "inches")


class NativeContractTests(unittest.TestCase):
    def setUp(self):
        self.fixture = Fixture()
        self.addCleanup(self.fixture.close)
        self.host = HostContract(self.fixture.root / "disposable.vwx")
        self.host.local_enable()
        self.adapter = VwAdapter(self.host)
        self.engine = Engine(self.fixture.root, self.adapter)

    def call(self, command, args):
        a = self.engine.auth
        return self.engine.execute(command, args, a.session, a.binding)

    def arm(self):
        result = self.call("test_arm", {"drawing": "disposable.vwx"})
        self.assertTrue(result["ok"], result)

    def create(self):
        self.arm()
        result = self.call("test_create", POST_CREATE)
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["result"]["pending"])
        self.assertFalse(result["result"]["completed"])
        return result["result"]["object_id"]

    def test_point_creation_returns_pending_then_later_read_confirms(self):
        key = self.create()
        self.assertEqual(self.host.resets, 1)
        self.host.invocation += 1
        result = self.call("test_read", {"object_id": key})
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["result"]["regeneration"]["completed"])
        self.assertFalse(
            result["result"]["regeneration"]["semantic_geometry_validation"]
        )
        self.assertEqual(self.host.resets, 1)

    def test_same_menu_cannot_confirm_or_repeat_a_reset(self):
        key = self.create()
        result = self.call("test_read", {"object_id": key})
        self.assertEqual(result["code"], "REGENERATION_PENDING")
        self.assertFalse(self.engine.auth.uncertain)
        self.assertEqual(self.host.resets, 1)

    def test_disable_pending_reset_preserves_uncertainty_and_cannot_rearm(self):
        key = self.create()
        self.host.local_disable()
        status = self.engine.operator_status()
        self.assertEqual(status["state"], "OFF")
        self.assertTrue(status["outcome_unconfirmed"])
        self.assertFalse(status["armed"])
        self.assertTrue(self.host.GetObjectByUuid(key))
        self.host.local_enable()
        self.assertEqual(self.engine.operator_status()["state"], "UNCONFIRMED")
        result = self.call("test_arm", {"drawing": "disposable.vwx"})
        self.assertEqual(result["code"], "SESSION_QUARANTINED")

    def test_reset_return_with_stale_children_is_partial_and_quarantined(self):
        self.arm()
        self.host.stale_children = True
        result = self.call("test_create", POST_CREATE)
        self.assertEqual(result["code"], "FRESH_REGENERATION_UNCONFIRMED")
        self.assertTrue(result["partial"])
        self.assertTrue(self.engine.auth.uncertain)
        self.assertEqual(self.host.resets, 1)

    def test_children_changed_between_reset_and_inspection_never_confirm(self):
        key = self.create()
        self.host.invocation += 1
        self.host.child_uuid = str(uuid.uuid4())
        result = self.call("test_read", {"object_id": key})
        self.assertEqual(result["code"], "GENERATED_CHILDREN_CHANGED_AFTER_RESET")
        self.assertTrue(result["partial"])
        self.assertTrue(self.engine.auth.uncertain)

    def test_lifecycle_change_revokes_all_issued_objects(self):
        key = self.create()
        self.host.generation += 1
        self.host.invocation += 1
        result = self.call("test_read", {"object_id": key})
        self.assertEqual(result["code"], "DOCUMENT_MISMATCH")
        self.assertFalse(self.engine.auth.owned)

    def test_real_menu_name_scope_and_non_pio_context_required(self):
        for attribute, value in [
            ("plugin", "other"),
            ("scope", False),
            ("pio_context", 100),
        ]:
            host = HostContract("unused.vwx")
            host.local_enable()
            setattr(host, attribute, value)
            with self.assertRaises(Rejected):
                NativeProof(host).assert_menu_context()

    def test_observed_host_build_and_exact_field_metadata_required(self):
        self.host.version = (31, 7, 0, 2, 111111)
        result = self.call("test_arm", {"drawing": "disposable.vwx"})
        self.assertEqual(result["code"], "UNREVIEWED_NATIVE_HOST")
        self.host.version = (31, 7, 0, 2, 879357)
        self.host.native_types["KingSize"] = 4
        result = self.call("test_arm", {"drawing": "disposable.vwx"})
        self.assertEqual(result["code"], "POST_FIELD_TYPE_MISMATCH")

    def test_popup_catalog_rejected_before_creation(self):
        self.host.enum_error = True
        result = self.call("test_arm", {"drawing": "disposable.vwx"})
        self.assertEqual(result["code"], "POST_CATALOG_MISMATCH")
        self.assertFalse(self.host.objects)

    def test_readback_mismatch_quarantines_prior_pending_mutation(self):
        key = self.create()
        self.host.invocation += 1
        handle = self.host.GetObjectByUuid(key)
        self.host.objects[handle]["fields"]["PostSize"] = "12x12"
        self.adapter.proof.expected[key]["PostSize"] = "6x6"
        result = self.call("test_read", {"object_id": key})
        self.assertEqual(result["code"], "READBACK_MISMATCH")
        self.assertTrue(self.engine.auth.uncertain)
        self.assertTrue(result["partial"])

    def test_bad_ticket_never_confirms_and_quarantines(self):
        key = self.create()
        self.host.invocation += 1
        handle = self.host.GetObjectByUuid(key)
        self.host.objects[handle]["ticket"] = "e" * 64
        result = self.call("test_read", {"object_id": key})
        self.assertEqual(result["code"], "RESET_TICKET_MISMATCH")
        self.assertTrue(self.engine.auth.uncertain)

    def test_geometry_bounds_checked_before_vertex_reads(self):
        key = self.create()
        self.host.invocation += 1
        self.host.child_limit = 65
        result = self.call("test_read", {"object_id": key})
        self.assertEqual(result["code"], "CHILD_VERTEX_LIMIT")

    def test_unverified_callout_transform_and_cases_reject_before_mutation(self):
        self.arm()
        payload = dict(POST_CREATE, tool="AV Callout", end=[3, 4], parameters={})
        result = self.call("test_create", payload)
        self.assertEqual(result["code"], "NATIVE_LINEAR_CREATION_UNSUPPORTED")
        self.assertFalse(result["partial"])
        self.assertFalse(self.host.objects)

    def test_flat_geometry_rejects_foreign_class_and_nested_containers(self):
        self.host.CreateCustomObjectN("AV Post", (0, 0), 0, False)
        native = {"top_plan": True, "matrix": [1, 0, 0, 1, 0, 0]}
        self.host.GetClass = lambda _: "production"
        with self.assertRaisesRegex(Rejected, "FOREIGN_CHILD_CLASS"):
            describe(self.host, 100, 30, native)
        self.host.GetParent = lambda _: 999
        with self.assertRaisesRegex(Rejected, "NESTED_GEOMETRY_UNSUPPORTED"):
            describe(self.host, 100, 30, native)


class TextHost:
    def GetParent(self, _):
        return 30

    def GetTypeN(self, _):
        return 10

    def GetClass(self, _):
        return "AV-MCP-TEST"

    def GetTextLength(self, _):
        return 8

    def GetText(self, _):
        return "two\nrows"

    def GetTextOrientation(self, _):
        return (3, 4), 0, False

    def GetBBox(self, _):
        return (3, 7), (11, 4)

    def GetTextSize(self, _, index):
        return 8.5


class TextContractTests(unittest.TestCase):
    def test_native_origin_and_local_bounds_are_distinct_and_measured(self):
        state = describe(
            TextHost(), 100, 30, {"top_plan": True, "matrix": [1, 0, 0, 1, 0, 0]}
        )
        self.assertEqual(state["origin"], [3, 4])
        self.assertEqual(state["bounds"], [[3, 4], [11, 7]])
        self.assertEqual((state["width"], state["height"]), (8, 3))
        self.assertEqual(state["font_size_points"], 8.5)
        self.assertEqual(state["text"], "two\nrows")

    def test_rotated_and_mirrored_text_rejected_before_projected_box_read(self):
        for angle, mirrored in [(30, False), (0, True)]:
            host = TextHost()
            host.GetTextOrientation = lambda _: ((3, 4), angle, mirrored)
            host.GetBBox = lambda _: self.fail("Projected box must not be read")
            with self.assertRaisesRegex(Rejected, "ROTATED_TEXT_METRICS_UNSUPPORTED"):
                describe(
                    host, 100, 30, {"top_plan": True, "matrix": [1, 0, 0, 1, 0, 0]}
                )
