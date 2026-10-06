import copy
import unittest

from pio_test.errors import Rejected
from pio_test.inspection import inspect_owned_children


class FakeReader:
    """Synthetic primitives test traversal/schema, not the AV PIO drawing logic."""
    def __init__(self, tool='AV Post'):
        self.tool = tool
        self.first = {1: 2}
        self.next = {2: 3}
        self.parents = {2: 1, 3: 1}
        self.nodes = {2: {'kind': 'line', 'class': 'AV-MCP-TEST', 'start': [0, 0], 'end': [20, 0]},
                      3: {'kind': 'text', 'class': 'AV-MCP-TEST', 'text': 'literal text',
                          'origin': [0, 1], 'baseline_direction': [1, 0], 'font_size_points': 12,
                          'width': 15, 'height': 2, 'bounds': [[0, 1], [15, 3]]}}
        self.described = []

    def frame(self, root):
        return {'space': 'pio_local_document_units', 'units': 'inches', 'layer_scale': 48,
                'pio_to_document': [1, 0, 0, 1, 10, 20],
                'native_linear_endpoints': [[0, 0], [20, 0]] if self.tool == 'AV Callout' else []}

    def first_child(self, parent):
        return self.first.get(parent)

    def next_sibling(self, child):
        return self.next.get(child)

    def parent(self, child):
        return self.parents.get(child)

    def describe(self, child, root):
        self.described.append(child)
        return copy.deepcopy(self.nodes[child])


class InspectionTests(unittest.TestCase):
    def inspect(self, reader):
        return inspect_owned_children(1, reader, lambda: None, reader.tool)

    def test_bounded_geometry_and_text_metrics(self):
        value = self.inspect(FakeReader())
        self.assertTrue(value['complete'])
        self.assertEqual(len(value['children']), 2)
        self.assertEqual(value['children'][1]['path'], [1])
        self.assertEqual(value['children'][1]['width'], 15)
        self.assertNotIn('handle', str(value))

    def test_callout_endpoints_separate_from_elbow_fields(self):
        value = self.inspect(FakeReader('AV Callout'))
        self.assertEqual(value['frame']['native_linear_endpoints'], [[0, 0], [20, 0]])

    def test_parent_leak_rejected_before_describe_or_advance(self):
        reader = FakeReader()
        reader.parents[2] = 999
        with self.assertRaisesRegex(Rejected, 'FOREIGN_CHILD'):
            self.inspect(reader)
        self.assertEqual(reader.described, [])

    def test_cycle_is_bounded(self):
        reader = FakeReader()
        reader.next[3] = 2
        with self.assertRaisesRegex(Rejected, 'CHILD_CYCLE'):
            self.inspect(reader)

    def test_child_count_and_depth_limits(self):
        reader = FakeReader()
        for index in range(2, 132):
            reader.parents[index] = 1
            reader.next[index] = index + 1 if index < 131 else None
            reader.nodes[index] = {'kind': 'line', 'class': 'test', 'start': [0, 0], 'end': [1, 1]}
        with self.assertRaisesRegex(Rejected, 'CHILD_INSPECTION_LIMIT'):
            self.inspect(reader)
        reader = FakeReader()
        reader.next = {}
        for index in range(2, 8):
            reader.parents[index] = index - 1
            reader.first[index - 1] = index
            reader.nodes[index] = {'kind': 'group', 'class': 'test'}
        with self.assertRaisesRegex(Rejected, 'CHILD_INSPECTION_LIMIT'):
            self.inspect(reader)

    def test_unsupported_kind_and_unbounded_metrics_reject(self):
        for update in [{'kind': 'arbitrary_record'}, {'text': 'x' * 1025}, {'width': float('nan')},
                       {'bounds': [[0, 0], [100001, 1]]}, {'script': 'anything'},
                       {'baseline_direction': [0, 0]}, {'bounds': [[5, 0], [0, 2]]}]:
            reader = FakeReader()
            reader.nodes[3].update(update)
            with self.assertRaises(Rejected):
                self.inspect(reader)

    def test_ellipse_arc_geometry_and_degenerate_axes(self):
        for kind in ('ellipse', 'arc'):
            reader = FakeReader()
            node = {'kind': kind, 'class': 'test', 'center': [0, 0], 'axis_u': [2, 0], 'axis_v': [0, 2]}
            if kind == 'arc':
                node.update(start_degrees=30, sweep_degrees=90)
            reader.nodes[2] = node
            self.assertTrue(self.inspect(reader)['complete'])
            node['axis_v'] = [4, 0]
            with self.assertRaisesRegex(Rejected, 'GEOMETRY_AXES'):
                self.inspect(reader)

    def test_guard_rechecked_during_traversal(self):
        calls = []
        def guard():
            calls.append(1)
            if len(calls) == 4:
                raise Rejected('DOCUMENT_MISMATCH')
        reader = FakeReader()
        with self.assertRaisesRegex(Rejected, 'DOCUMENT_MISMATCH'):
            inspect_owned_children(1, reader, guard, 'AV Post')
        self.assertEqual(reader.described, [2])

    def test_aggregate_text_budget(self):
        reader = FakeReader()
        for index in range(3, 8):
            reader.nodes[index] = dict(reader.nodes[3], text='x' * 1024)
            reader.parents[index] = 1
            reader.next[index] = index + 1 if index < 7 else None
        with self.assertRaisesRegex(Rejected, 'CHILD_TEXT_LIMIT'):
            self.inspect(reader)
