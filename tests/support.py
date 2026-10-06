"""Minimal record-store double, deliberately not an AV PIO implementation."""
from dataclasses import replace
from pathlib import Path
import copy
import os
import secrets
import tempfile
import threading
import time
import uuid

from pio_test.authorization import DocumentIdentity
from pio_test.errors import Rejected
from pio_test.schema import PARAMETERS, DIAGNOSTICS, POST_SIZES, RESET_FIELD
from pio_test.wire import dumps


def default(schema):
    if 'default' in schema:
        return schema['default']
    if 'enum' in schema:
        return schema['enum'][0]
    return {'boolean': False, 'string': '', 'integer': 1, 'number': schema.get('minimum', 1)}[schema['type']]


class FakeAdapter:
    blockers = ['MOCK_ONLY_NO_NATIVE_EVIDENCE']

    def __init__(self, drawing):
        self.current = DocumentIdentity(str(drawing), secrets.token_hex(32), 1, secrets.token_hex(32))
        self.objects = {}
        self.mutations = 0
        self.regen_complete = True
        self.fail_readback = False
        self.fail_write = False
        self.create_delay = 0

    def identity(self):
        if self.current is None:
            raise Rejected('DOCUMENT_IDENTITY_UNCERTAIN')
        return self.current

    def preflight(self):
        pass

    def validate_creation(self, args):
        pass

    def create(self, args):
        self.mutations += 1
        time.sleep(self.create_delay)
        object_id = str(uuid.uuid4())
        tool = args['tool']
        self.objects[object_id] = {
            'tool': tool, 'lifetime': secrets.token_hex(32), 'fixture': self.current.fixture,
            'parameters': {k: default(s) for k, s in PARAMETERS[tool].items()},
            'diagnostics': {k: default(s) for k, s in DIAGNOSTICS[tool].items()},
        }
        return object_id

    def object_identity(self, object_id):
        o = self.objects.get(object_id)
        if not o or o['fixture'] != self.current.fixture:
            raise Rejected('FOREIGN_OBJECT')
        return o['tool'], o['lifetime']

    def set_parameter(self, object_id, tool, name, value):
        self.mutations += 1
        if self.fail_write:
            raise ValueError('sensitive native exception must not be logged')
        self.objects[object_id]['parameters'][name] = value

    def regenerate_completed(self, object_id):
        self.mutations += 1
        if self.regen_complete:
            o = self.objects[object_id]
            o['parameters'][RESET_FIELD[o['tool']]] = False
        return {'completed': self.regen_complete, 'vw_ms': 2.0}

    def read(self, object_id, tool):
        o = self.objects[object_id]
        result = copy.deepcopy({k: o[k] for k in ('parameters', 'diagnostics')})
        if self.fail_readback:
            result['parameters']['TextSize'] = 10
        return result

    def inspect_geometry(self, object_id, tool, guard):
        from pio_test.inspection import inspect_owned_children
        from tests.test_inspection import FakeReader
        guard()
        return inspect_owned_children(1, FakeReader(tool), guard, tool)

    def validate_transform(self, object_id, args):
        pass

    def transform(self, object_id, args):
        self.mutations += 1

    def delete(self, object_id):
        self.mutations += 1
        del self.objects[object_id]

    def absent(self, object_id):
        return object_id not in self.objects


class Fixture:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        if os.name == 'nt':
            self.private_windows_temp(self.base)
        self.root = self.base / 'drawings'
        self.ipc = self.base / 'ipc'
        self.root.mkdir(mode=0o700)
        self.ipc.mkdir(mode=0o700)
        if os.name == 'nt':
            self.private_windows_temp(self.ipc)
        self.drawing = self.root / 'disposable.vwx'
        self.drawing.touch()  # zero-byte MOCK fixture, never sent to real Vectorworks
        self.key = secrets.token_bytes(32)
        self.config = {'test_root': self.root, 'ipc_root': self.ipc, 'post_sizes': POST_SIZES}
        self.write('key.bin', self.key)
        self.adapter = FakeAdapter(self.drawing)

    @staticmethod
    def private_windows_temp(path):
        # TEST-ONLY, limited to our just-created TemporaryDirectory. Runtime
        # code never shells out or changes ACLs. No elevation or VW install.
        import csv
        import re
        import subprocess
        output = subprocess.check_output(['whoami', '/user', '/fo', 'csv', '/nh'], text=True)
        sid = next(csv.reader(output.splitlines()))[1]
        if re.fullmatch(r'S-1-[0-9-]+', sid) is None:
            raise AssertionError('Could not establish test directory owner SID')
        subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r',
                        '*' + sid + ':(OI)(CI)F', '*S-1-5-18:(OI)(CI)F'],
                       check=True, capture_output=True)

    def write(self, name, value):
        path = self.ipc / name
        path.write_bytes(value)
        path.chmod(0o600)

    def config_file(self):
        path = self.base / 'config.json'
        path.write_bytes(dumps(dict(self.config, test_root=str(self.root), ipc_root=str(self.ipc))))
        path.chmod(0o600)
        return path

    def close(self):
        self.temp.cleanup()


def client_call_with_pump(client, pump, command, args):
    answer = []
    def run():
        try:
            answer.append(client.call(command, args))
        except Exception as error:
            answer.append(error)
    thread = threading.Thread(target=run)
    thread.start()
    deadline = time.monotonic() + 2
    while not (pump.root / 'request.json').exists() and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.001)
    pump.run_once()
    thread.join(2)
    if thread.is_alive():
        raise AssertionError('test client did not complete')
    if isinstance(answer[0], Exception):
        raise answer[0]
    return answer[0]


POST_CREATE = {'tool': 'AV Post', 'origin': [0, 0], 'rotation': 0, 'parameters': {'PostSize': '(2) 2x4', 'TextSize': 12}}
CALLOUT_CREATE = {'tool': 'AV Callout', 'origin': [0, 0], 'rotation': 0, 'end': [20, 10],
                  'parameters': {'Callout': 'data only', 'TextSize': 12}}
