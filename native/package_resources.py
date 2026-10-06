"""Build/check our menu resources offline; never install or load a native module."""

import argparse
import codecs
import hashlib
import json
from pathlib import Path
import zipfile


RESOURCE_PATH = "Strings/Supervisor.vwstrings"
CATALOG_PATH = Path(__file__).with_name("menu_strings.json")
VISIBLE = {
    "title": "AV PIO Test Supervisor",
    "category": "AV PIO Test Development",
    "enable": "Enable PIO Testing",
    "disable": "Disable PIO Testing",
    "status": "PIO Testing Status",
}
KEYS = set(VISIBLE) | {"help", "enable_help", "disable_help", "status_help"}


def _unique_pairs(pairs):
    values = {}
    for key, value in pairs:
        if key in values:
            raise ValueError("Duplicate menu resource key")
        values[key] = value
    return values


def resource_bytes(catalog_path=CATALOG_PATH):
    values = json.loads(
        Path(catalog_path).read_text(encoding="utf-8"),
        object_pairs_hook=_unique_pairs,
    )
    if not isinstance(values, dict) or set(values) != KEYS:
        raise ValueError("Menu resource keys do not match the native definitions")
    for key, expected in VISIBLE.items():
        if values[key] != expected:
            raise ValueError("Menu title/category does not match the native contract")
    for value in values.values():
        if (
            not isinstance(value, str)
            or not value
            or len(value) > 1024
            or any(ord(character) < 32 for character in value)
        ):
            raise ValueError("Invalid menu resource value")
    lines = [
        json.dumps(key, ensure_ascii=False)
        + " = "
        + json.dumps(value, ensure_ascii=False)
        + ";\r\n"
        for key, value in values.items()
    ]
    return codecs.BOM_UTF16_LE + "".join(lines).encode("utf-16-le")


def validate_archive(path, catalog_path=CATALOG_PATH):
    """Accept the current SDK layout, including its optional Strings/ entry."""
    with zipfile.ZipFile(path) as archive:
        items = archive.infolist()
        names = [item.filename for item in items]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive entry")
        if any(name not in {"Strings/", RESOURCE_PATH} for name in names):
            raise ValueError("Unexpected resource archive path")
        if [item.filename for item in items if not item.is_dir()] != [RESOURCE_PATH]:
            raise ValueError("Missing exact native menu resource path")
        if any(item.compress_type != zipfile.ZIP_STORED for item in items):
            raise ValueError("Resources must use ZIP_STORED")
        if archive.testzip() is not None:
            raise ValueError("Resource archive CRC failure")
        raw = archive.read(RESOURCE_PATH)
    if not raw.startswith(codecs.BOM_UTF16_LE):
        raise ValueError("Menu strings require a UTF-16LE BOM")
    # Read back the delivered bytes, including every key and visible label.
    if raw != resource_bytes(catalog_path):
        raise ValueError("Menu resource encoding/content does not match the catalog")
    path = Path(path)
    return {
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "lookup_path": RESOURCE_PATH,
        "encoding": "UTF-16LE with BOM",
        "keys": sorted(KEYS),
    }


def build_archive(path, catalog_path=CATALOG_PATH):
    raw = resource_bytes(catalog_path)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # A fixed timestamp makes our package reproducible. SDK-generated packages
    # may contain different metadata; validate their content with --check.
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        item = zipfile.ZipInfo(RESOURCE_PATH, date_time=(1980, 1, 1, 0, 0, 0))
        item.compress_type = zipfile.ZIP_STORED
        archive.writestr(item, raw)
    return validate_archive(path, catalog_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Output .vwr, or input with --check")
    parser.add_argument("--check", action="store_true", help="Validate an existing VWR")
    options = parser.parse_args()
    function = validate_archive if options.check else build_archive
    print(json.dumps(function(options.archive), indent=2))


if __name__ == "__main__":
    main()
