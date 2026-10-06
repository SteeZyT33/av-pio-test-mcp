"""Bounded owned-descendant inspection, never a document query or export.

This traversal is useful even with an uncertain VW iterator: no next/describe
call is made for an item whose direct parent is not the expected container.
Native geometry extraction/coordinate transforms are a separate gated adapter.
"""
from .errors import require
from .schema import BOOL, COORD, POINT, SIZE, TEXT, enum, number, obj, validate
from .wire import dumps

LIMIT_CHILDREN = 128
LIMIT_DEPTH = 4
LIMIT_TEXT = 4096
MATRIX = {'type': 'array', 'items': COORD, 'minItems': 6, 'maxItems': 6}
BOUNDS = {'type': 'array', 'items': POINT, 'minItems': 2, 'maxItems': 2}
VERTICES = {'type': 'array', 'items': POINT, 'minItems': 2, 'maxItems': 64}
FRAME = obj({'space': enum(['pio_local_document_units']), 'units': enum(['inches', 'mm']),
             'layer_scale': {'type': 'integer', 'minimum': 24, 'maximum': 96, 'enum': [24, 48, 96]},
             'pio_to_document': MATRIX,
             'native_linear_endpoints': {'type': 'array', 'items': POINT, 'minItems': 0, 'maxItems': 2}})
CHILD = {'oneOf': [
    obj({'kind': enum(['group']), 'class': TEXT}),
    obj({'kind': enum(['line']), 'class': TEXT, 'start': POINT, 'end': POINT}),
    obj({'kind': enum(['polyline']), 'class': TEXT, 'vertices': VERTICES, 'closed': BOOL}),
    obj({'kind': enum(['ellipse']), 'class': TEXT, 'center': POINT, 'axis_u': POINT, 'axis_v': POINT}),
    obj({'kind': enum(['arc']), 'class': TEXT, 'center': POINT, 'axis_u': POINT, 'axis_v': POINT,
         'start_degrees': number(-360, 360), 'sweep_degrees': number(-360, 360)}),
    obj({'kind': enum(['text']), 'class': TEXT,
         'text': {'type': 'string', 'maxLength': 1024}, 'origin': POINT,
         'baseline_direction': POINT, 'font_size_points': SIZE,
         'width': number(0, 200000), 'height': number(0, 200000), 'bounds': BOUNDS}),
]}


def inspect_owned_children(root, reader, guard, tool):
    """Reader is trusted source, not a client-supplied object/function name.

All coordinates/metrics must be normalized by the native adapter into the root
PIO's local document-unit frame, including nested group/text transforms. Paths
are snapshot-local ordinal arrays, not persistent object handles or ownership.
"""
    guard()
    frame = reader.frame(root)
    validate(frame, FRAME)
    a, b, c, d, _tx, _ty = frame['pio_to_document']
    require(abs(a*d - b*c) > 1e-12, 'INVALID_GEOMETRY_FRAME')
    endpoints = frame['native_linear_endpoints']
    require(len(endpoints) == (2 if tool == 'AV Callout' else 0), 'NATIVE_ENDPOINTS_UNCONFIRMED')
    if tool == 'AV Callout':
        require(endpoints[0] != endpoints[1], 'NATIVE_ENDPOINTS_UNCONFIRMED')
    seen = [root]
    children = []
    text_count = 0

    def walk(parent, path):
        nonlocal text_count
        guard()
        child = reader.first_child(parent)
        ordinal = 0
        while child:
            guard()
            # Do not describe or advance a leaked parent/sibling handle.
            require(reader.parent(child) == parent, 'FOREIGN_CHILD')
            require(child not in seen, 'CHILD_CYCLE')
            require(len(children) < LIMIT_CHILDREN and len(path) < LIMIT_DEPTH, 'CHILD_INSPECTION_LIMIT')
            seen.append(child)
            node = reader.describe(child, root)
            validate(node, CHILD)
            if node['kind'] == 'text':
                dx, dy = node['baseline_direction']
                require(abs(dx*dx + dy*dy - 1) <= 1e-6, 'INVALID_TEXT_METRICS')
                lower, upper = node['bounds']
                require(lower[0] <= upper[0] and lower[1] <= upper[1], 'INVALID_TEXT_METRICS')
            if node['kind'] in ('ellipse', 'arc'):
                ux, uy = node['axis_u']
                vx, vy = node['axis_v']
                require(abs(ux*vy - uy*vx) > 1e-12, 'INVALID_GEOMETRY_AXES')
            text_count += len(node.get('text', ''))
            require(text_count <= LIMIT_TEXT, 'CHILD_TEXT_LIMIT')
            child_path = path + [ordinal]
            children.append(dict(node, path=child_path))
            if node['kind'] == 'group':
                walk(child, child_path)
            child = reader.next_sibling(child)
            ordinal += 1

    walk(root, [])
    guard()
    result = {'complete': True, 'frame': frame, 'children': children}
    require(len(dumps(result)) <= 32768, 'CHILD_SNAPSHOT_TOO_LARGE')
    return result
