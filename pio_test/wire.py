"""Authenticated, bounded JSON. Requests and responses have distinct MAC domains."""
import hashlib
import hmac
import json
import math
import os
import re
import time
from contextlib import contextmanager

from .errors import Rejected, require
from .paths import ipc_path, private, local_absolute
from .schema import MAX_FRAME, POST_SIZES, validate_command

TOKEN = re.compile(r'[0-9a-f]{64}')
CID = re.compile(r'[0-9a-f]{32}')


def token(value):
    return type(value) is str and TOKEN.fullmatch(value) is not None


def dumps(value):
    return json.dumps(value, allow_nan=False, ensure_ascii=True,
                      sort_keys=True, separators=(',', ':')).encode('utf-8')


def loads(raw):
    require(len(raw) <= MAX_FRAME, 'FRAME_TOO_LARGE')

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'DUPLICATE_FIELD')
            result[key] = value
        return result

    def constant(_value):
        raise Rejected('NONFINITE_NUMBER')

    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError):
        raise Rejected('INVALID_JSON') from None


def sign(key, message):
    require(len(key) == 32 and 'mac' not in message, 'INVALID_ENVELOPE')
    return dict(message, mac=hmac.new(key, dumps(message), hashlib.sha256).hexdigest())


def authenticate(key, message, fields, kind):
    require(type(message) is dict and set(message) == set(fields) | {'mac'}, 'INVALID_ENVELOPE')
    require(message['kind'] == kind and token(message['mac']), 'INVALID_ENVELOPE')
    unsigned = {k: v for k, v in message.items() if k != 'mac'}
    require(hmac.compare_digest(message['mac'], sign(key, unsigned)['mac']), 'AUTH_FAILED')
    return unsigned


REQUEST_FIELDS = {'v', 'kind', 'bridge', 'session', 'binding', 'sequence', 'cid',
                  'issued', 'expires', 'command', 'args'}
RESULT_FIELDS = {'v', 'kind', 'bridge', 'cid', 'sequence', 'result'}
BRIDGE_FIELDS = {'v', 'kind', 'bridge', 'native_blockers', 'operator_state'}


def request(key, message, bridge, last_sequence, now=None):
    job = authenticate(key, message, REQUEST_FIELDS, 'request')
    require(job['v'] == 1 and type(job['v']) is int, 'INVALID_ENVELOPE')
    require(token(job['bridge']) and job['bridge'] == bridge, 'BRIDGE_MISMATCH')
    require(type(job['cid']) is str and CID.fullmatch(job['cid']), 'INVALID_CORRELATION_ID')
    require(type(job['sequence']) is int and last_sequence < job['sequence'] <= 1000000, 'REPLAY')
    for name in ('session', 'binding'):
        require(job[name] is None or token(job[name]), 'INVALID_ENVELOPE')
    for name in ('issued', 'expires'):
        value = job[name]
        require(type(value) in (int, float) and 0 <= value <= 1e12 and math.isfinite(value), 'INVALID_ENVELOPE')
    now = time.time() if now is None else now
    require(job['issued'] - 2 <= now <= job['expires'] and
            0 < job['expires'] - job['issued'] <= 60, 'STALE_JOB')
    validate_command(job['command'], job['args'])
    return job


def read_bytes(root, name):
    path = ipc_path(root, name)
    with path.open('rb') as stream:
        raw = stream.read(MAX_FRAME + 1)
    require(len(raw) <= MAX_FRAME, 'FRAME_TOO_LARGE')
    return raw


def write_bytes(root, name, raw):
    require(len(raw) <= MAX_FRAME, 'FRAME_TOO_LARGE')
    target, temporary = ipc_path(root, name), ipc_path(root, name + '.tmp')
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(str(temporary), flags, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        private(temporary)
        ipc_path(root, name)  # recheck before replace; same-user races are out of scope
        os.replace(str(temporary), str(target))
    finally:
        if temporary.exists():
            temporary.unlink()


def write_json(root, name, value):
    write_bytes(root, name, dumps(value))


@contextmanager
def exclusive(root, name):
    path = ipc_path(root, name)
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     getattr(os, 'O_NOFOLLOW', 0), 0o600)
    except FileExistsError:
        raise Rejected('BUSY_OR_UNCERTAIN_LOCK') from None
    os.close(fd)
    try:
        private(path)
        yield
    finally:
        ipc_path(root, name).unlink()


def read_config(path):
    path = private(path)
    with path.open('rb') as stream:
        raw = stream.read(MAX_FRAME + 1)
    cfg = loads(raw)
    require(type(cfg) is dict and set(cfg) == {'test_root', 'ipc_root', 'post_sizes'}, 'INVALID_CONFIG')
    require(cfg['post_sizes'] == POST_SIZES, 'CATALOG_MISMATCH')
    cfg['test_root'] = local_absolute(cfg['test_root'])
    cfg['ipc_root'] = private(cfg['ipc_root'], True)
    require(cfg['test_root'].is_dir() and cfg['test_root'] != cfg['ipc_root'] and
            cfg['ipc_root'] not in cfg['test_root'].parents and
            cfg['test_root'] not in cfg['ipc_root'].parents, 'ROOTS_MUST_BE_SEPARATE')
    key = read_bytes(cfg['ipc_root'], 'key.bin')
    require(len(key) == 32, 'INVALID_KEY')
    return cfg, key
