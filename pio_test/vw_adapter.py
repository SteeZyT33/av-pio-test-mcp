"""Small VW adapter; native integration is deliberately gated in this draft.

Never infer a document lifetime from a saved path, layer handle, marker or UUID.
Never infer completed regeneration from ResetObject returning, a sleep, matching
parameter strings, or a bounding-box change. NativeProof must be implemented
and reviewed against the operator's 2026 SDK/build before native arming works.
It is a code interface, NOT a configurable/importable client-supplied provider.
"""
import uuid

from .errors import Rejected, require
from .schema import PARAMETERS, DIAGNOSTICS, POST_SIZES
from .inspection import inspect_owned_children

NATIVE_BLOCKERS = ['NATIVE_DOCUMENT_LIFETIME_UNAVAILABLE', 'NATIVE_REGEN_COMPLETION_UNAVAILABLE',
                   'NATIVE_LINEAR_CREATION_UNVERIFIED', 'NATIVE_FIELD_CODEC_UNVERIFIED',
                   'NATIVE_GEOMETRY_METRICS_UNVERIFIED']


class NativeProof:
    """No fallback. See docs/NATIVE_ACCEPTANCE.md for required SDK evidence.

Future integration must provide identity, preflight, object_lifetime,
validate_creation/create_linear, encode/decode, regenerate_completed,
validate_transform and assert_menu_context. No PIO code changes are required
or authorized. C++ lifecycle policy in native/ is not an SDK implementation.
"""
    def identity(self):
        raise Rejected('NATIVE_DOCUMENT_LIFETIME_UNAVAILABLE')

    def preflight(self):
        raise Rejected('NATIVE_REGEN_COMPLETION_UNAVAILABLE')

    def assert_menu_context(self):
        raise Rejected('NATIVE_MENU_CONTEXT_UNVERIFIED')

    def object_lifetime(self, handle):
        raise Rejected('NATIVE_OBJECT_LIFETIME_UNAVAILABLE')

    def validate_creation(self, args, post_catalog):
        raise Rejected('NATIVE_CREATION_UNVERIFIED')

    def create_linear(self, start, end):
        raise Rejected('NATIVE_LINEAR_CREATION_UNVERIFIED')

    def encode(self, name, value, schema):
        raise Rejected('NATIVE_FIELD_CODEC_UNVERIFIED')

    def decode(self, name, value, schema):
        raise Rejected('NATIVE_FIELD_CODEC_UNVERIFIED')

    def regenerate_completed(self, handle):
        raise Rejected('NATIVE_REGEN_COMPLETION_UNAVAILABLE')

    def validate_transform(self, handle, args):
        raise Rejected('NATIVE_TRANSFORM_EXTENTS_UNVERIFIED')

    def geometry_frame(self, handle):
        raise Rejected('NATIVE_GEOMETRY_METRICS_UNVERIFIED')

    def describe_child(self, handle, root):
        raise Rejected('NATIVE_GEOMETRY_METRICS_UNVERIFIED')


class VwAdapter:
    blockers = NATIVE_BLOCKERS

    def __init__(self, vs_module):
        self.vs = vs_module
        self.proof = NativeProof()

    def identity(self):
        identity = self.proof.identity()
        # This documented path call is only corroboration, never lifetime proof.
        require(self.vs.GetFPathName() == identity.path, 'NATIVE_FULL_PATH_MISMATCH')
        return identity

    def preflight(self):
        self.proof.preflight()
        # Future preflight must verify exact universal field types and catalog,
        # ordinary reset (Event-Based OFF, move/rotate ON), point Post and Linear
        # Callout, an empty initial AV-MCP-TEST design layer and AV-MCP-TEST class,
        # inches/mm units, and 1:24/48/96. No creation/definition edits here.

    def handle(self, object_id):
        self.proof.assert_menu_context()
        h = self.vs.GetObjectByUuid(object_id)
        require(h and self.vs.GetTypeN(h) == 86, 'PIO_MISSING')
        return h

    def object_identity(self, object_id):
        h = self.handle(object_id)
        record = self.vs.GetParametricRecord(h)
        require(record, 'PARAMETRIC_RECORD_MISSING')
        name = self.vs.GetName(record)
        require(name in PARAMETERS, 'TOOL_NOT_ALLOWED')
        # Must also verify direct parent = the bound synthetic design layer,
        # no wall/container/reference object, and native object lifetime.
        return name, self.proof.object_lifetime(h)

    def validate_creation(self, args):
        self.proof.validate_creation(args, POST_SIZES)

    def create(self, args):
        self.proof.assert_menu_context()
        if args['tool'] == 'AV Post':
            h = self.vs.CreateCustomObjectN('AV Post', tuple(args['origin']), args['rotation'], False)
        elif args['tool'] == 'AV Callout':
            # Linear endpoints are NOT ControlPoint01X/Y (the elbow).
            h = self.proof.create_linear(tuple(args['origin']), tuple(args['end']))
        else:
            raise Rejected('TOOL_NOT_ALLOWED')
        require(h, 'CREATE_FAILED')
        return str(uuid.UUID(self.vs.GetObjectUuid(h)))

    def read(self, object_id, tool):
        h = self.handle(object_id)
        result = {}
        for category, fields in (('parameters', PARAMETERS[tool]), ('diagnostics', DIAGNOSTICS[tool])):
            result[category] = {name: self.proof.decode(name, self.vs.GetRField(h, tool, name), schema)
                                for name, schema in fields.items()}
        return result

    def set_parameter(self, object_id, tool, name, value):
        require(name in PARAMETERS[tool], 'READ_ONLY_FIELD')
        h = self.handle(object_id)
        self.vs.SetRField(h, tool, name, self.proof.encode(name, value, PARAMETERS[tool][name]))

    def regenerate_completed(self, object_id):
        # The proof implementation owns reset and completion observation. Do not
        # insert ResetObject here and then return a fabricated completion flag.
        return self.proof.regenerate_completed(self.handle(object_id))

    def validate_transform(self, object_id, args):
        self.proof.validate_transform(self.handle(object_id), args)

    def transform(self, object_id, args):
        h = self.handle(object_id)
        if args['action'] == 'move':
            self.vs.HMove(h, *args['offset'])
        elif args['action'] == 'rotate':
            self.vs.HRotate(h, tuple(args['center']), args['angle'])
        elif args['action'] == 'mirror':
            result = self.vs.MirrorN(h, False, tuple(args['axis_start']), tuple(args['axis_end']), True)
            require(result == h, 'MIRROR_REPLACED_OBJECT')
        else:
            raise Rejected('INVALID_TRANSFORM')

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

        return inspect_owned_children(self.handle(object_id), ChildReader(), guard, tool)
