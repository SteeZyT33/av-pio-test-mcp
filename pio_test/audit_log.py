"""Metadata-only logging: no paths, record data, tokens, MACs or exception text."""
import os
import time

from .paths import ipc_path
from .schema import COMMANDS
from .wire import CID, dumps


def event(root, command, cid, outcome, elapsed_ms):
    if command not in COMMANDS or not isinstance(cid, str) or not CID.fullmatch(cid):
        return
    if outcome not in ('ok', 'rejected', 'partial', 'uncertain'):
        return
    path = ipc_path(root, 'audit.jsonl')
    # Bounded log; no automatic deletion/rotation of operator evidence.
    if path.exists() and path.stat().st_size >= 60000:
        return
    record = {'time': int(time.time()), 'command': command, 'cid': cid,
              'outcome': outcome, 'elapsed_ms': min(3600000, max(0, int(elapsed_ms)))}
    fd = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT |
                 getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'ab') as stream:
        stream.write(dumps(record) + b'\n')
