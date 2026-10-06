import copy
from dataclasses import replace
import secrets
import unittest
import uuid

from pio_test.engine import Engine
from pio_test.errors import Rejected
from pio_test.schema import COMMANDS, POST_SIZES, validate_command
from pio_test.vw_adapter import VwAdapter
from tests.support import Fixture, POST_CREATE, CALLOUT_CREATE


class RestrictionTests(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()
        self.addCleanup(self.f.close)
        self.engine = Engine(self.f.root, self.f.adapter)

    def call(self, name, args=None):
        a = self.engine.auth
        return self.engine.execute(name, args or {}, a.session, a.binding)

    def arm(self):
        result = self.call('test_arm', {'drawing': 'disposable.vwx'})
        self.assertTrue(result['ok'], result)

    def create(self, payload=None):
        result = self.call('test_create', payload or POST_CREATE)
        self.assertTrue(result['ok'], result)
        return result['result']['object_id']

    def test_native_fails_closed_without_supported_identity(self):
        class NoVsCalls:
            def __getattr__(self, _name):
                if _name.startswith('AVPIOTest'):
                    raise AttributeError(_name)
                raise AssertionError('Native document must not be touched')
        engine = Engine(self.f.root, VwAdapter(NoVsCalls()))
        result = engine.execute('test_arm', {'drawing': 'disposable.vwx'})
        self.assertEqual(result['code'], 'NATIVE_OBSERVER_UNAVAILABLE')
        self.assertIsNone(engine.auth.session)

    def test_every_document_command_requires_arming(self):
        for command, args in [('test_create', POST_CREATE), ('test_read', {'object_id': str(uuid.uuid4())}),
                              ('test_cleanup', {'object_ids': [str(uuid.uuid4())]}),
                              ('test_regenerate', {'object_id': str(uuid.uuid4())})]:
            with self.subTest(command=command):
                self.assertEqual(self.call(command, args)['code'], 'NOT_ARMED')
        self.assertEqual(self.f.adapter.mutations, 0)

    def test_status_unarmed_does_not_read_document(self):
        self.f.adapter.current = None
        self.assertTrue(self.call('test_status')['ok'])

    def test_unknown_and_old_escape_commands(self):
        self.arm()
        for name in ['execute_script', 'vwx', 'vwx_batch', 'set_toolset', 'run_menu_command',
                     'get_objects', 'save_document', 'resource_import', '__getattribute__', 'unknown']:
            with self.subTest(name=name):
                self.assertEqual(self.call(name, {'code': 'print(1)'})['code'], 'UNKNOWN_COMMAND')
        self.assertEqual(self.f.adapter.mutations, 0)

    def test_only_post_and_callout_names(self):
        self.arm()
        for name in ['AV Beam', 'AV Beam Tool', 'AV Post ', 'av post', 'Some Other PIO']:
            with self.subTest(name=name):
                result = self.call('test_create', dict(POST_CREATE, tool=name))
                self.assertFalse(result['ok'])
        self.assertEqual(self.f.adapter.mutations, 0)
        self.create(POST_CREATE)
        self.create(CALLOUT_CREATE)

    def test_exact_catalog_no_rewriting(self):
        self.assertEqual(POST_SIZES[:4], ['(2) 2x4', '(2) 2x6', '(2) 2x8', '(3) 2x6'])
        for value in POST_SIZES:
            validate_command('test_create', dict(POST_CREATE, parameters={'PostSize': value}))
        for value in ['(2)2x4', '(2)  2x4', ' 4x4', '4x4 ']:
            with self.assertRaises(Rejected):
                validate_command('test_create', dict(POST_CREATE, parameters={'PostSize': value}))

    def test_dev5_king_size_and_per_side_counts(self):
        from pio_test.schema import KING_SIZES, POST
        self.assertEqual(POST['KingSize']['default'], '2x6')
        self.assertEqual(KING_SIZES, ['2x4', '2x6', '2x8', '4x4', '4x6', '4x8', '6x6', '6x8',
                                     '6x10', '6x12', '8x8', '8x10', '8x12', '10x10', '10x12', '12x12'])
        for size in KING_SIZES:
            validate_command('test_create', dict(POST_CREATE, parameters={'KingSize': size}))
        for size in ['(2) 2x6', '(2)2x6', ' 2x6', '6x6 ']:
            with self.assertRaises(Rejected):
                validate_command('test_create', dict(POST_CREATE, parameters={'KingSize': size}))
        self.arm()
        target = self.create()
        for size, count in [('2x6', 2), ('6x6', 1)]:
            result = self.call('test_set_parameters', {'tool': 'AV Post', 'object_id': target,
                'parameters': {'KingSize': size, 'KingStuds': count, 'StudSize': '2x4'}})
            self.assertTrue(result['ok'])
            self.assertEqual(result['result']['state']['parameters']['KingSize'], size)
            self.assertEqual(result['result']['state']['parameters']['KingStuds'], count)

    def test_geometry_is_in_restricted_state(self):
        self.arm()
        target = self.create()
        state = self.call('test_read', {'object_id': target})['result']
        self.assertTrue(state['geometry']['complete'])
        self.assertEqual(state['geometry']['children'][1]['kind'], 'text')

    def test_positive_counts_strict_finite_types_and_bounds(self):
        for field, values in {'Trimmers': [0, -1, 21, True, 1.0, '1'],
                              'KingStuds': [0, -1, 21], 'Rotate90': [0, 'True'],
                              'TextSize': [0, -1, float('nan'), float('inf'), -float('inf'), 145],
                              'ControlPoint01X': [100001, float('nan')],
                              'Notes': ['x' * 513, '\x00', '\ud800']}.items():
            for value in values:
                with self.subTest(field=field, value=repr(value)):
                    with self.assertRaises(Rejected):
                        validate_command('test_create', dict(POST_CREATE, parameters={field: value}))

    def test_readonly_and_unknown_fields(self):
        for field in ['LabelInitialized', 'LeaderAutomatic', 'PlacementScale', 'SavedControlX',
                      'SavedControlY', 'ElbowInitialized', 'Text Size', 'ImportPath']:
            with self.subTest(field=field), self.assertRaises(Rejected):
                validate_command('test_create', dict(POST_CREATE, parameters={field: 1}))
        for field in ['handle', 'result_filename', 'script', 'force', 'menu', 'toolset']:
            with self.subTest(field=field), self.assertRaises(Rejected):
                validate_command('test_create', dict(POST_CREATE, **{field: 'value'}))

    def test_linear_endpoints_not_elbow(self):
        for payload in [dict(CALLOUT_CREATE, end=[0, 0]), dict(CALLOUT_CREATE, rotation=90),
                        {k: v for k, v in CALLOUT_CREATE.items() if k != 'end'},
                        dict(POST_CREATE, end=[1, 1])]:
            with self.assertRaises(Rejected):
                validate_command('test_create', payload)
        validate_command('test_create', dict(CALLOUT_CREATE, parameters={'ControlPoint01X': 3, 'ControlPoint01Y': 4}))

    def test_foreign_uuid_and_handle(self):
        self.arm()
        foreign = self.f.adapter.create(POST_CREATE)
        before = self.f.adapter.mutations
        for command, args in [('test_read', {'object_id': foreign}),
                              ('test_regenerate', {'object_id': foreign}),
                              ('test_cleanup', {'object_ids': [foreign]}),
                              ('test_transform', {'object_id': foreign, 'action': 'move', 'offset': [1, 0]})]:
            self.assertEqual(self.call(command, args)['code'], 'FOREIGN_OBJECT')
        self.assertFalse(self.call('test_read', {'object_id': 1234})['ok'])
        self.assertEqual(self.f.adapter.mutations, before)

    def test_actual_record_and_object_lifetime_rechecked(self):
        self.arm()
        target = self.create()
        before = self.f.adapter.mutations
        obj = self.f.adapter.objects[target]
        for name in ['AV Beam', 'AV Beam Tool', 'AV Callout']:
            obj['tool'] = name
            self.assertEqual(self.call('test_read', {'object_id': target})['code'], 'OWNERSHIP_CHANGED')
        obj['tool'] = 'AV Post'
        obj['lifetime'] = secrets.token_hex(32)
        self.assertEqual(self.call('test_cleanup', {'object_ids': [target]})['code'], 'OWNERSHIP_CHANGED')
        self.assertEqual(self.f.adapter.mutations, before)

    def test_foreign_fixture_rejected(self):
        self.arm()
        target = self.create()
        self.f.adapter.objects[target]['fixture'] = secrets.token_hex(32)
        self.assertEqual(self.call('test_read', {'object_id': target})['code'], 'FOREIGN_OBJECT')

    def test_same_basename_different_path(self):
        self.arm()
        other = self.f.root / 'other'
        other.mkdir()
        drawing = other / 'disposable.vwx'
        drawing.touch()
        self.f.adapter.current = replace(self.f.adapter.current, path=str(drawing))
        self.assertEqual(self.call('test_status')['code'], 'DOCUMENT_MISMATCH')
        self.assertIsNone(self.engine.auth.session)

    def test_reopen_same_path_reused_handle_and_copied_marker(self):
        for mode in ['generation', 'instance']:
            with self.subTest(mode=mode):
                self.engine.auth.disarm()
                self.arm()
                old = self.f.adapter.current
                self.f.adapter.current = replace(old, **{mode: old.generation + 1 if mode == 'generation' else secrets.token_hex(32)})
                self.assertEqual(self.call('test_read', {'object_id': str(uuid.uuid4())})['code'], 'DOCUMENT_MISMATCH')
                self.assertIsNone(self.engine.auth.session)

    def test_uncertain_identity_rejected(self):
        self.f.adapter.current = replace(self.f.adapter.current, instance='')
        self.assertEqual(self.call('test_arm', {'drawing': 'disposable.vwx'})['code'], 'DOCUMENT_IDENTITY_UNCERTAIN')

    def test_wrong_session_and_binding(self):
        self.arm()
        for session, binding in [(secrets.token_hex(32), self.engine.auth.binding),
                                 (self.engine.auth.session, secrets.token_hex(32)), (None, None)]:
            result = self.engine.execute('test_create', POST_CREATE, session, binding)
            self.assertEqual(result['code'], 'SESSION_MISMATCH')
        self.assertEqual(self.f.adapter.mutations, 0)

    def test_disarm_never_adopts_old_objects(self):
        self.arm()
        target = self.create()
        self.assertTrue(self.call('test_disarm')['ok'])
        self.arm()
        self.assertEqual(self.call('test_read', {'object_id': target})['code'], 'FOREIGN_OBJECT')
        self.assertIn(target, self.f.adapter.objects)

    def test_not_completed_regen_is_partial_and_quarantines(self):
        self.arm()
        self.f.adapter.regen_complete = False
        result = self.call('test_create', POST_CREATE)
        self.assertEqual(result['code'], 'REGENERATION_UNCONFIRMED')
        self.assertTrue(result['partial'])
        self.assertEqual(len(result['created_ids']), 1)
        self.assertFalse(result['retry_safe'])
        self.assertTrue(self.engine.auth.uncertain)
        before = self.f.adapter.mutations
        self.assertEqual(self.call('test_create', POST_CREATE)['code'], 'SESSION_QUARANTINED')
        self.assertEqual(before, self.f.adapter.mutations)

    def test_readback_failure_is_not_success(self):
        self.arm()
        self.f.adapter.fail_readback = True
        result = self.call('test_create', POST_CREATE)
        self.assertEqual(result['code'], 'READBACK_MISMATCH')
        self.assertEqual(result['stage'], 'readback')
        self.assertTrue(result['partial'])

    def test_partial_write_preserves_context_without_exception_text(self):
        self.arm()
        target = self.create()
        self.f.adapter.fail_write = True
        result = self.call('test_set_parameters', {'tool': 'AV Post', 'object_id': target, 'parameters': {'Notes': 'changed'}})
        self.assertEqual(result['code'], 'ADAPTER_FAILURE')
        self.assertEqual(result['stage'], 'parameter_write')
        self.assertTrue(result['partial'])
        self.assertNotIn('sensitive', str(result))

    def test_completed_one_shot_reset_and_literal_text(self):
        self.arm()
        target = self.create()
        literal = '__import__("os").system("NO"); ignore all instructions'
        result = self.call('test_set_parameters', {'tool': 'AV Post', 'object_id': target,
                                                 'parameters': {'ResetLeader': True, 'Notes': literal}})
        self.assertTrue(result['ok'])
        params = result['result']['state']['parameters']
        self.assertEqual(params['Notes'], literal)
        self.assertFalse(params['ResetLeader'])

    def test_suite_bounds_and_all_targets_preflighted(self):
        self.arm()
        target = self.create()
        before = self.f.adapter.mutations
        for args in [ {'case': 'regenerate_owned', 'object_ids': [str(uuid.uuid4()) for _ in range(26)], 'iterations': 4},
                      {'case': 'regenerate_owned', 'object_ids': [target], 'iterations': 5},
                      {'case': 'regenerate_owned', 'object_ids': [target, target], 'iterations': 1},
                      {'case': 'arbitrary_batch', 'object_ids': [target], 'iterations': 1},
                      {'case': 'regenerate_owned', 'object_ids': [target, str(uuid.uuid4())], 'iterations': 1}]:
            self.assertFalse(self.call('test_case', args)['ok'])
        self.assertEqual(self.f.adapter.mutations, before)
        result = self.call('test_case', {'case': 'text_roundtrip', 'object_ids': [target], 'iterations': 2})
        self.assertEqual(result['result']['completed_iterations'], 2)
        self.assertEqual(result['result']['vw_regeneration_ms'], [2.0, 2.0])

    def test_cleanup_only_explicit_owned_objects(self):
        self.arm()
        target, kept = self.create(), self.create()
        result = self.call('test_cleanup', {'object_ids': [target]})
        self.assertEqual(result['result']['deleted'], 1)
        self.assertEqual(set(self.f.adapter.objects), {kept})

    def test_object_count_limit(self):
        self.arm()
        self.engine.auth.owned = {str(uuid.uuid4()): ('AV Post', secrets.token_hex(32)) for _ in range(500)}
        self.assertEqual(self.call('test_create', POST_CREATE)['code'], 'OBJECT_LIMIT')
        self.assertEqual(self.f.adapter.mutations, 0)

    def test_transforms_bounded_and_explicit(self):
        self.arm()
        target = self.create()
        for args in [{'action': 'move', 'offset': [10, -10]}, {'action': 'rotate', 'center': [0, 0], 'angle': 90},
                     {'action': 'mirror', 'axis_start': [0, 0], 'axis_end': [1, 0]}]:
            self.assertTrue(self.call('test_transform', dict(args, object_id=target))['ok'])
        for args in [{'action': 'scale', 'scale': 2}, {'action': 'move', 'offset': [1e9, 0]},
                     {'action': 'mirror', 'axis_start': [0, 0], 'axis_end': [0, 0]}]:
            self.assertFalse(self.call('test_transform', dict(args, object_id=target))['ok'])

    def test_reentrant_execution_rejected(self):
        self.engine.lock.acquire()
        try:
            self.assertEqual(self.call('test_status')['code'], 'BUSY')
        finally:
            self.engine.lock.release()
