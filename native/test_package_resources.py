"""Regression checks for resources that can hide native menu titles."""

import codecs
from pathlib import Path
import tempfile
import unittest
import zipfile

from native.package_resources import build_archive, resource_bytes, validate_archive


class ResourcePackageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / "AVPIOTestObserver.vwr"

    def write_fixture(self, name, raw, compression=zipfile.ZIP_STORED):
        with zipfile.ZipFile(self.output, "w", compression=compression) as archive:
            archive.writestr(name, raw)

    def test_delivered_resource_has_native_lookup_path_and_visible_titles(self):
        build_archive(self.output)
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(archive.namelist(), ["Strings/Supervisor.vwstrings"])
            raw = archive.read("Strings/Supervisor.vwstrings")
        self.assertEqual(raw[:2], codecs.BOM_UTF16_LE)
        text = raw.decode("utf-16")
        for title in (
            "AV PIO Test Supervisor",
            "Enable PIO Testing",
            "Disable PIO Testing",
            "PIO Testing Status",
            "AV PIO Test Development",
        ):
            self.assertIn('"' + title + '";', text)
        self.assertEqual(validate_archive(self.output)["encoding"], "UTF-16LE with BOM")

    def test_previous_ascii_resource_is_rejected(self):
        # The previous package had this encoding even though all text was ASCII.
        raw = resource_bytes().decode("utf-16").encode("ascii")
        self.write_fixture("Strings/Supervisor.vwstrings", raw)
        with self.assertRaisesRegex(ValueError, "UTF-16LE BOM"):
            validate_archive(self.output)

    def test_obsolete_namespace_prefix_is_rejected(self):
        self.write_fixture(
            "AVPIOTestObserver/Strings/Supervisor.vwstrings", resource_bytes()
        )
        with self.assertRaisesRegex(ValueError, "archive path"):
            validate_archive(self.output)

    def test_modern_sdk_directory_entry_is_accepted(self):
        with zipfile.ZipFile(
            self.output, "w", compression=zipfile.ZIP_STORED
        ) as archive:
            archive.writestr("Strings/", b"")
            archive.writestr("Strings/Supervisor.vwstrings", resource_bytes())
        validate_archive(self.output)

    def test_compressed_resources_are_rejected(self):
        self.write_fixture(
            "Strings/Supervisor.vwstrings", resource_bytes(), zipfile.ZIP_DEFLATED
        )
        with self.assertRaisesRegex(ValueError, "ZIP_STORED"):
            validate_archive(self.output)

    def test_missing_disable_title_is_rejected(self):
        raw = resource_bytes().replace("Disable PIO Testing".encode("utf-16-le"), b"")
        self.write_fixture("Strings/Supervisor.vwstrings", raw)
        with self.assertRaisesRegex(ValueError, "content"):
            validate_archive(self.output)


if __name__ == "__main__":
    unittest.main()
