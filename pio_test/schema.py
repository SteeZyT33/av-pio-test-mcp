"""One command/parameter contract used by MCP AND the in-VW dispatcher.

Only the small JSON Schema subset below is accepted. No coercion, dynamic
discovery, field aliases, trimmed enum values, code, or arbitrary batch payloads.
"""
import math
import re

from .errors import Rejected, require

MAX_FRAME = 65536
MAX_OBJECTS = 500
MAX_SUITE_WORK = 100
POST_SIZES = ['(2) 2x4', '(2) 2x6', '(2) 2x8', '(3) 2x6', '4x4', '4x6',
              '4x8', '6x6', '6x8', '6x10', '6x12', '8x8', '8x10', '8x12',
              '10x10', '10x12', '12x12']
KING_SIZES = ['2x4', '2x6', '2x8', '4x4', '4x6', '4x8', '6x6', '6x8',
              '6x10', '6x12', '8x8', '8x10', '8x12', '10x10', '10x12', '12x12']


def obj(properties, required=None):
    return {'type': 'object', 'properties': properties,
            'required': list(properties) if required is None else required,
            'additionalProperties': False}


def enum(values):
    return {'type': 'string', 'enum': list(values), 'maxLength': 80}


def number(low, high):
    return {'type': 'number', 'minimum': low, 'maximum': high}


BOOL = {'type': 'boolean'}
TEXT = {'type': 'string', 'maxLength': 512}
COORD = number(-100000, 100000)  # document units; native model extents checked too
POINT = {'type': 'array', 'items': COORD, 'minItems': 2, 'maxItems': 2}
ANGLE = number(-360, 360)
SIZE = number(0.1, 144)  # points
COUNT = {'type': 'integer', 'minimum': 1, 'maximum': 20}
UUID = {'type': 'string', 'pattern': r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',
        'maxLength': 36}
IDS = {'type': 'array', 'items': UUID, 'minItems': 1, 'maxItems': 25,
       'uniqueItems': True}
POST = {
    'ShowMode': enum(['Post', 'Trmr + King']), 'PostSize': enum(POST_SIZES),
    'StudSize': dict(enum(['2x4', '2x6', '2x8']), description='Trimmer size (universal name unchanged)'),
    'Rotate90': BOOL,
    'KingSize': dict(enum(KING_SIZES), default='2x6', description='Independent king member size; AV Post 0.1.0.dev5'),
    'Trimmers': COUNT,
    'KingStuds': dict(COUNT, description='King members per side: count of individual KingSize members'),
    'KingSide': enum(['Left', 'Right', 'Both']),
    'Reference': dict(TEXT, description='Note above leader; shown with the post description'),
    'Notes': dict(TEXT, description='Note below leader'), 'ShowLabel': BOOL, 'TextSize': SIZE,
    'ResetLeader': BOOL, 'ControlPoint01X': COORD, 'ControlPoint01Y': COORD,
}
CALLOUT = {
    'Callout': TEXT, 'Line2': TEXT,
    'Shape': enum(['Circle', 'Square', 'Hexagon', 'Diamond']),
    'UseElbow': BOOL, 'TextSize': SIZE, 'ResetElbow': BOOL,
    'ControlPoint01X': COORD, 'ControlPoint01Y': COORD,
}
PARAMETERS = {'AV Post': POST, 'AV Callout': CALLOUT}
TOOL = enum(PARAMETERS)
DIAGNOSTICS = {
    'AV Post': {'LabelInitialized': BOOL, 'LeaderAutomatic': BOOL},
    'AV Callout': {'ElbowInitialized': BOOL},
}
for _fields in DIAGNOSTICS.values():
    _fields.update({'PlacementScale': number(0.01, 100000),
                    'SavedControlX': number(-100000, 100000),
                    'SavedControlY': number(-100000, 100000)})
RESET_FIELD = {'AV Post': 'ResetLeader', 'AV Callout': 'ResetElbow'}


def parameter_variants(extra, required, nonempty=False):
    variants = []
    for tool, fields in PARAMETERS.items():
        params = obj(fields, [])
        if nonempty:
            params['minProperties'] = 1
        variants.append(obj(dict(extra, tool=enum([tool]), parameters=params), required))
    return {'oneOf': variants}


COMMANDS = {
    'test_status': (obj({}), 'Bridge status; if armed, verifies the bound document. No document query when unarmed.'),
    'test_arm': (obj({'drawing': {'type': 'string', 'minLength': 5, 'maxLength': 240}}),
                 'Arm the exact saved disposable .vwx relative to the configured test root. Never activates a drawing.'),
    'test_disarm': (obj({}), 'Revoke ownership and session authority. Leaves objects and drawing unchanged.'),
    'test_create': (parameter_variants({'origin': POINT, 'rotation': ANGLE, 'end': POINT},
                                    ['tool', 'origin', 'rotation', 'parameters']),
                    'Create AV Post or Linear AV Callout. Callout requires a distinct end point; Post forbids end.'),
    'test_read': (obj({'object_id': UUID}), 'Read one owned PIO: fields, diagnostics and bounded owned-child geometry/text metrics. No document query.'),
    'test_set_parameters': (parameter_variants({'object_id': UUID},
                                              ['tool', 'object_id', 'parameters'], True),
                            'Set exact universal writable fields; verify after proven completed regeneration.'),
    'test_transform': ({'oneOf': [
        obj({'object_id': UUID, 'action': enum(['move']), 'offset': POINT}),
        obj({'object_id': UUID, 'action': enum(['rotate']), 'center': POINT, 'angle': ANGLE}),
        obj({'object_id': UUID, 'action': enum(['mirror']), 'axis_start': POINT, 'axis_end': POINT}),
    ]}, 'Move, rotate, or reflect one owned PIO in place. No copying or scaling.'),
    'test_regenerate': (obj({'object_id': UUID}), 'Regenerate one owned PIO; queued reset alone is not success.'),
    'test_case': (obj({'case': enum(['regenerate_owned', 'text_roundtrip', 'placement_reset']),
                       'object_ids': IDS,
                       'iterations': {'type': 'integer', 'minimum': 1, 'maximum': 4}}),
                  'Run a named case, at most 100 object-iterations. Stops on first failure; no rollback.'),
    'test_cleanup': (obj({'object_ids': IDS}), 'Delete only the listed PIOs created by this session. No layer/class/document cleanup.'),
}
MUTATIONS = frozenset({'test_create', 'test_set_parameters', 'test_transform',
                       'test_regenerate', 'test_case', 'test_cleanup'})


def validate(value, schema):
    """Strict validation independent of the MCP client or framework."""
    if 'oneOf' in schema:
        matches = 0
        for candidate in schema['oneOf']:
            try:
                validate(value, candidate)
                matches += 1
            except Rejected:
                pass
        require(matches == 1, 'INVALID_FIELDS')
        return
    kind = schema['type']
    if kind == 'object':
        require(type(value) is dict, 'INVALID_FIELDS')
        require(set(schema['required']) <= set(value) <= set(schema['properties']), 'INVALID_FIELDS')
        require(len(value) >= schema.get('minProperties', 0), 'INVALID_FIELDS')
        for key, item in value.items():
            validate(item, schema['properties'][key])
    elif kind == 'array':
        require(type(value) is list and schema['minItems'] <= len(value) <= schema['maxItems'], 'INVALID_FIELDS')
        for item in value:
            validate(item, schema['items'])
        if schema.get('uniqueItems'):
            require(len(set(value)) == len(value), 'INVALID_FIELDS')
    elif kind in ('number', 'integer'):
        require(type(value) in ((int,) if kind == 'integer' else (int, float)), 'INVALID_FIELDS')
        require(schema['minimum'] <= value <= schema['maximum'] and math.isfinite(value), 'INVALID_FIELDS')
    elif kind == 'boolean':
        require(type(value) is bool, 'INVALID_FIELDS')
    elif kind == 'string':
        require(type(value) is str and schema.get('minLength', 0) <= len(value) <= schema['maxLength'], 'INVALID_FIELDS')
        require(not any(ord(c) < 32 and c not in '\n\t' for c in value), 'INVALID_FIELDS')
        require(not any(0xD800 <= ord(c) <= 0xDFFF for c in value), 'INVALID_FIELDS')
        if 'pattern' in schema:
            require(re.fullmatch(schema['pattern'], value) is not None, 'INVALID_FIELDS')
    else:
        raise AssertionError('unsupported schema type')
    if 'enum' in schema:
        require(value in schema['enum'], 'INVALID_FIELDS')


def validate_command(command, args):
    require(type(command) is str and command in COMMANDS, 'UNKNOWN_COMMAND')
    validate(args, COMMANDS[command][0])
    if command == 'test_create':
        require(('end' in args) == (args['tool'] == 'AV Callout'), 'LINEAR_ENDPOINT_REQUIRED')
        if 'end' in args:
            require(args['end'] != args['origin'] and args['rotation'] == 0, 'INVALID_LINEAR_GEOMETRY')
    if command == 'test_transform' and args['action'] == 'mirror':
        require(args['axis_start'] != args['axis_end'], 'INVALID_MIRROR_AXIS')
    if command == 'test_case':
        require(len(args['object_ids']) * args['iterations'] <= MAX_SUITE_WORK, 'SUITE_TOO_LARGE')


def tools_list():
    return [{'name': name, 'description': desc, 'inputSchema': dict(schema, type='object'),
             'annotations': {'readOnlyHint': name in ('test_status', 'test_read'),
                             'destructiveHint': name in MUTATIONS,
                             'idempotentHint': False, 'openWorldHint': False}}
            for name, (schema, desc) in COMMANDS.items()]
