"""Explicit operator-only file preparation. Does not install or contact VW.

Directories and private ACLs must already exist. No overwrite, cleanup, package
installation, settings changes, key printing, or automatic privilege elevation.
"""
import argparse
import os
import secrets
import sys

from .errors import require
from .paths import local_absolute, no_links, private
from .schema import POST_SIZES
from .wire import dumps, write_bytes


def prepare(test_root, ipc_root, confirm_post_catalog):
    require(confirm_post_catalog is True, 'OPERATOR_CATALOG_CONFIRMATION_REQUIRED')
    test_root, ipc_root = local_absolute(test_root), private(ipc_root, True)
    require(test_root.is_dir() and test_root != ipc_root and test_root not in ipc_root.parents and
            ipc_root not in test_root.parents, 'ROOTS_MUST_BE_SEPARATE')
    require(not any(ipc_root.iterdir()), 'EMPTY_PRIVATE_DIRECTORY_REQUIRED')
    config_path = no_links(ipc_root / 'config.json')
    cfg = {'test_root': str(test_root), 'ipc_root': str(ipc_root), 'post_sizes': POST_SIZES}
    write_bytes(ipc_root, 'key.bin', secrets.token_bytes(32))
    fd = os.open(str(config_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(dumps(cfg))
        stream.flush()
        os.fsync(stream.fileno())
    private(config_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test-root', required=True)
    parser.add_argument('--ipc-root', required=True)
    parser.add_argument('--confirm-post-catalog', action='store_true')
    args = parser.parse_args()
    try:
        prepare(args.test_root, args.ipc_root, args.confirm_post_catalog)
    except Exception:
        print('Preparation refused. Verify paths, empty private IPC directory, ACLs and catalog confirmation.', file=sys.stderr)
        return 1
    print('Private configuration prepared; no Vectorworks installation or connection performed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
