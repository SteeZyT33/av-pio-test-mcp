"""Local canonical paths, no reparse points, and fixed IPC filenames.

ACLs are part of this boundary. Checks cannot sandbox a process running as the
same OS identity; such a process can replace code, keys or files between checks.
"""
import os
from pathlib import Path, PureWindowsPath
import re
import stat

from .errors import require

IPC_FILES = frozenset({'key.bin', 'bridge.json', 'request.json', 'claimed.json',
                       'result.json', 'client.lock', 'pump.lock', 'uncertain.json',
                       'audit.jsonl'})
RESERVED = re.compile(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', re.I)


def no_links(path):
    path = Path(os.path.abspath(str(path)))
    for part in (path,) + tuple(path.parents):
        if not part.exists() and not part.is_symlink():
            continue
        info = part.lstat()
        require(not stat.S_ISLNK(info.st_mode) and
                not (getattr(info, 'st_file_attributes', 0) & 0x400), 'PATH_REPARSE_POINT')
        if stat.S_ISREG(info.st_mode):
            require(info.st_nlink == 1, 'PATH_HARDLINK')
    return path


def local_absolute(path):
    require(isinstance(path, (str, Path)), 'INVALID_PATH')
    path = Path(path)
    require(path.is_absolute(), 'ABSOLUTE_CONFIG_REQUIRED')
    no_links(path)
    if os.name == 'nt':
        import ctypes
        require(not str(path).startswith(('\\\\', '//')), 'REMOTE_PATH')
        require(ctypes.windll.kernel32.GetDriveTypeW(str(path.anchor)) == 3, 'LOCAL_FIXED_DRIVE_REQUIRED')
    return path.resolve(strict=True)


def relative_drawing(root, payload):
    require(type(payload) is str and 5 <= len(payload) <= 240, 'INVALID_PATH')
    require(not PureWindowsPath(payload).drive and not payload.startswith('/') and
            '\\' not in payload and ':' not in payload, 'INVALID_PATH')
    parts = payload.split('/')
    for part in parts:
        require(part not in ('', '.', '..') and not part.endswith((' ', '.')) and
                re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9 _.-]{0,79}', part) is not None and
                RESERVED.match(part) is None, 'INVALID_PATH')
    require(parts[-1].lower().endswith('.vwx'), 'VWX_REQUIRED')
    root = local_absolute(root)
    candidate = local_absolute(root.joinpath(*parts))
    require(candidate.is_file() and candidate != root and root in candidate.parents, 'PATH_ESCAPE')
    return candidate


def private(path, directory=False):
    path = local_absolute(path)
    require(path.is_dir() if directory else path.is_file(), 'PRIVATE_PATH_TYPE')
    if os.name == 'nt':
        from .windows_acl import check_private_acl
        check_private_acl(path, directory)
    else:
        info = path.stat()
        require(info.st_uid == os.getuid() and not (info.st_mode & 0o077), 'PRIVATE_PERMISSIONS_REQUIRED')
    return path


def ipc_path(root, name):
    require(name in IPC_FILES or (name.endswith('.tmp') and name[:-4] in IPC_FILES), 'INVALID_IPC_FILENAME')
    root = private(root, True)
    path = no_links(root / name)
    if path.exists():
        private(path)
    return path
