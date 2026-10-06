"""Second authorization boundary, inside VW. Direct IPC uses this same path."""
import threading

from .authorization import Authority
from .errors import Rejected, require
from .operations import Operations
from .schema import MUTATIONS, validate_command


class Engine:
    def __init__(self, root, adapter):
        self.auth = Authority(root, adapter)
        self.lock = threading.Lock()

    def execute(self, command, args, session=None, binding=None, deadline=None):
        # Nonblocking rejects recursive invocations from a PIO rather than deadlock.
        if not self.lock.acquire(False):
            return {'ok': False, 'code': 'BUSY', 'partial': False}
        op = Operations(self.auth)
        try:
            self.auth.deadline = deadline
            validate_command(command, args)
            self.auth.check_envelope(session, binding)
            if command not in ('test_status', 'test_arm', 'test_disarm'):
                self.auth.guard()
                require(not self.auth.uncertain, 'SESSION_QUARANTINED')
            if command == 'test_arm':
                self.auth.arm(args['drawing'])
                result = {'armed': True, 'session': self.auth.session, 'binding': self.auth.binding}
            elif command == 'test_disarm':
                self.auth.disarm()
                result = {'armed': False, 'objects_left_in_drawing': True}
            elif command == 'test_status':
                result = {'armed': self.auth.session is not None,
                          'owned_count': len(self.auth.owned), 'quarantined': self.auth.uncertain,
                          'native_blockers': self.auth.adapter.blockers}
            elif command == 'test_create':
                result = op.create(args)
            elif command == 'test_read':
                result = op.read(args['object_id'])
            elif command == 'test_set_parameters':
                result = op.set_parameters(args)
            elif command == 'test_transform':
                result = op.transform(args)
            elif command == 'test_regenerate':
                result = op.regenerate(args['object_id'])
            elif command == 'test_case':
                result = op.case(args)
            elif command == 'test_cleanup':
                result = op.cleanup(args)
            else:
                raise Rejected('UNKNOWN_COMMAND')
            if self.auth.session is not None:
                self.auth.guard()
            return {'ok': True, 'result': result}
        except Exception as error:
            # Partial effects are never automatically undone or retried. A PIO may
            # fail after making changes even when its call did not return a UUID.
            if op.attempted:
                self.auth.uncertain = True
            return {'ok': False, 'code': error.code if isinstance(error, Rejected) else 'ADAPTER_FAILURE',
                    'command': command if isinstance(command, str) and command in MUTATIONS else 'validation',
                    'stage': op.stage, 'partial': op.attempted, 'completed': op.completed,
                    'created_ids': op.created, 'rollback': False, 'retry_safe': False}
        finally:
            self.auth.deadline = None
            self.lock.release()
