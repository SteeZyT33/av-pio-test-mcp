import os
from pathlib import Path
import types
import unittest
from unittest.mock import patch

from pio_test.errors import Rejected
from pio_test.paths import relative_drawing, ipc_path, no_links, private
from pio_test.wire import read_config
from tests.support import Fixture


class PathTests(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()
        self.addCleanup(self.f.close)

    def test_exact_saved_path_required(self):
        self.assertEqual(relative_drawing(self.f.root, 'disposable.vwx'), self.f.drawing)
        for value in ['../disposable.vwx', '/tmp/disposable.vwx', 'C:/a.vwx', 'D:\\a.vwx',
                      '\\\\server\\x.vwx', '//server/x.vwx', 'a/../disposable.vwx', 'a//x.vwx',
                      'a.vwx:stream', 'a.vwx ', 'CON.vwx', 'LPT1.vwx', 'x.json', 'missing.vwx']:
            with self.subTest(value=value), self.assertRaises((Rejected, FileNotFoundError)):
                relative_drawing(self.f.root, value)

    def test_symlink_directory_and_file_escapes(self):
        outside = self.f.base / 'outside'
        outside.mkdir()
        (outside / 'other.vwx').touch()
        (self.f.root / 'link').symlink_to(outside, target_is_directory=True)
        (self.f.root / 'linked.vwx').symlink_to(outside / 'other.vwx')
        for value in ['link/other.vwx', 'linked.vwx']:
            with self.assertRaisesRegex(Rejected, 'REPARSE'):
                relative_drawing(self.f.root, value)

    def test_junction_reparse_attribute_is_rejected_portably(self):
        original = Path.lstat
        def attributes(path):
            info = original(path)
            if path == self.f.root:
                return types.SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
            return info
        with patch.object(Path, 'lstat', attributes), self.assertRaisesRegex(Rejected, 'REPARSE'):
            no_links(self.f.drawing)

    @unittest.skipUnless(os.name == 'nt', 'Actual NTFS junction creation/rejection is a Windows-local acceptance check')
    def test_real_windows_junction(self):
        import subprocess
        junction = self.f.root / 'junction'
        outside = self.f.base / 'outside'
        outside.mkdir()
        (outside / 'file.vwx').touch()
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(outside)], check=True, capture_output=True)
        try:
            with self.assertRaisesRegex(Rejected, 'REPARSE'):
                relative_drawing(self.f.root, 'junction/file.vwx')
        finally:
            junction.rmdir()

    def test_hardlinked_drawing_rejected(self):
        os.link(self.f.drawing, self.f.root / 'alias.vwx')
        with self.assertRaisesRegex(Rejected, 'HARDLINK'):
            relative_drawing(self.f.root, 'alias.vwx')

    def test_ipc_names_fixed_and_symlink_results_rejected(self):
        for value in ['../file', 'results/cid.json', 'C:/out.json', 'anything.json', 'request.json.tmp.tmp']:
            with self.assertRaisesRegex(Rejected, 'FILENAME'):
                ipc_path(self.f.ipc, value)
        (self.f.ipc / 'result.json').symlink_to(self.f.drawing)
        with self.assertRaisesRegex(Rejected, 'REPARSE'):
            ipc_path(self.f.ipc, 'result.json')

    @unittest.skipIf(os.name == 'nt', 'POSIX mode test')
    def test_private_permissions_fail_closed(self):
        self.f.ipc.chmod(0o755)
        with self.assertRaisesRegex(Rejected, 'PERMISSIONS'):
            private(self.f.ipc, True)

    def test_config_catalog_and_separate_roots(self):
        path = self.f.config_file()
        config, key = read_config(path)
        self.assertEqual(key, self.f.key)
        self.assertEqual(config['test_root'], self.f.root)
        import json
        data = json.loads(path.read_text())
        data['post_sizes'][0] = '(2)2x4'
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(Rejected, 'CATALOG'):
            read_config(path)
