"""Ephemeral authority: saved path AND runtime identity, never a copied marker."""
from dataclasses import dataclass
import hashlib
import os
import secrets
import time

from .errors import require
from .paths import local_absolute, relative_drawing
from .schema import MAX_OBJECTS, PARAMETERS, UUID, validate
from .wire import dumps, token


@dataclass(frozen=True)
class DocumentIdentity:
    path: str
    instance: str      # native, process-lifetime token; NOT stored in drawing
    generation: int    # must invalidate on switch-away, close/reopen, undo/redo
    fixture: str       # runtime identity of operator-created AV-MCP-TEST design layer

    def fingerprint(self):
        require(token(self.instance) and type(self.generation) is int and
                self.generation > 0 and token(self.fixture), 'DOCUMENT_IDENTITY_UNCERTAIN')
        canonical = local_absolute(self.path)
        return hashlib.sha256(dumps([os.path.normcase(str(canonical)), self.instance,
                                     self.generation, self.fixture])).hexdigest()


class Authority:
    def __init__(self, root, adapter):
        self.root = root
        self.adapter = adapter
        self.session = None
        self.binding = None
        self.identity = None
        self.drawing = None
        self.owned = {}
        self.uncertain = False
        self.deadline = None

    def arm(self, drawing):
        require(self.session is None, 'ALREADY_ARMED')
        target = relative_drawing(self.root, drawing)
        current = self.adapter.identity()
        require(type(current) is DocumentIdentity, 'DOCUMENT_IDENTITY_UNCERTAIN')
        require(local_absolute(current.path) == target, 'DOCUMENT_MISMATCH')
        # Preflight proves lifecycle, fixture, definitions, codec and regeneration
        # capabilities before authority is minted. Operator config cannot waive it.
        self.adapter.preflight()
        binding = current.fingerprint()
        require(self.adapter.identity().fingerprint() == binding, 'DOCUMENT_MISMATCH')
        self.identity, self.drawing = current, drawing
        self.binding, self.session = binding, secrets.token_hex(32)
        self.owned = {}
        self.uncertain = False

    def guard(self):
        require(self.session is not None, 'NOT_ARMED')
        try:
            require(self.deadline is None or time.time() <= self.deadline, 'STALE_JOB')
            target = relative_drawing(self.root, self.drawing)
            current = self.adapter.identity()
            require(type(current) is DocumentIdentity and
                    current.fingerprint() == self.binding and
                    local_absolute(current.path) == target, 'DOCUMENT_MISMATCH')
        except Exception:
            # Revoke immediately, including ownership; never re-adopt saved UUIDs.
            self.disarm()
            raise

    def check_envelope(self, session, binding):
        if self.session is None:
            require(session is None and binding is None, 'SESSION_MISMATCH')
        else:
            require(session == self.session and binding == self.binding, 'SESSION_MISMATCH')
            self.guard()

    def claim(self, object_id, tool):
        self.guard()
        validate(object_id, UUID)
        require(tool in PARAMETERS and object_id not in self.owned and
                len(self.owned) < MAX_OBJECTS, 'OWNERSHIP_LIMIT_OR_COLLISION')
        actual, lifetime = self.adapter.object_identity(object_id)
        require(actual == tool and token(lifetime), 'WRONG_PARAMETRIC_RECORD')
        self.owned[object_id] = (tool, lifetime)

    def object(self, object_id):
        self.guard()
        require(object_id in self.owned, 'FOREIGN_OBJECT')
        expected = self.owned[object_id]
        actual = self.adapter.object_identity(object_id)
        require(actual == expected and actual[0] in PARAMETERS, 'OWNERSHIP_CHANGED')
        return expected[0]

    def disarm(self):
        self.session = self.binding = self.identity = self.drawing = None
        self.owned = {}
        self.uncertain = False
