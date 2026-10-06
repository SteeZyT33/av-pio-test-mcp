import os
import unittest

from pio_test.errors import Rejected
from pio_test.prepare import prepare
from pio_test.wire import read_config
from tests.support import Fixture


class PreparationTests(unittest.TestCase):
    def test_explicit_preparation_does_not_overwrite_or_touch_drawings(self):
        fixture = Fixture()
        self.addCleanup(fixture.close)
        target = fixture.base / 'new-private'
        target.mkdir(mode=0o700)
        if os.name == 'nt':
            fixture.private_windows_temp(target)
        before = fixture.drawing.read_bytes()
        with self.assertRaisesRegex(Rejected, 'CONFIRMATION'):
            prepare(fixture.root, target, False)
        prepare(fixture.root, target, True)
        cfg, key = read_config(target / 'config.json')
        self.assertEqual(len(key), 32)
        self.assertEqual(cfg['test_root'], fixture.root)
        with self.assertRaisesRegex(Rejected, 'EMPTY_PRIVATE_DIRECTORY'):
            prepare(fixture.root, target, True)
        self.assertEqual(key, (target / 'key.bin').read_bytes())
        self.assertEqual(before, fixture.drawing.read_bytes())
        self.assertEqual({p.name for p in target.iterdir()}, {'config.json', 'key.bin'})
