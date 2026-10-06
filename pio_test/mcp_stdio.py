"""Dependency-free, fixed MCP 2025-06-18 stdio subset. No HTTP path.

Synchronous calls are serialized. Cancellation notifications do not interrupt
native work and are never advertised as rollback. No resources/prompts/tasks.
"""
import argparse
import math
import sys

from .errors import Rejected, require
from .schema import MAX_FRAME, tools_list
from .transport import Client
from .wire import dumps, loads, read_config


class Server:
    def __init__(self, client):
        self.client = client
        self.initialized = False
        self.ready = False

    def handle(self, message):
        request_id = None
        try:
            require(type(message) is dict and set(message) <= {'jsonrpc', 'id', 'method', 'params'} and
                    message.get('jsonrpc') == '2.0' and type(message.get('method')) is str, 'INVALID_REQUEST')
            request_id = message.get('id')
            require(request_id is None or type(request_id) is int or
                    (type(request_id) is str and len(request_id) <= 128), 'INVALID_REQUEST')
            method = message['method']
            params = message.get('params', {})
            require(type(params) is dict, 'INVALID_PARAMS')
            if '_meta' in params:
                metadata = params['_meta']
                require(type(metadata) is dict and
                        all(type(key) is str for key in metadata), 'INVALID_PARAMS')
                if request_id is not None and 'progressToken' in metadata:
                    token = metadata['progressToken']
                    require(type(token) in (str, int, float) and
                            (type(token) is str or math.isfinite(token)), 'INVALID_PARAMS')
                # Reserved MCP envelope metadata is ignored, never forwarded to
                # command validation/IPC, echoed, or used to grant authority.
                params = {key: value for key, value in params.items() if key != '_meta'}
            if request_id is None:
                if method == 'notifications/initialized' and self.initialized and params == {}:
                    self.ready = True
                # Cancellation is best effort; no guaranteed interruption/rollback.
                return None
            if method == 'initialize':
                require(not self.initialized and set(params) == {'protocolVersion', 'capabilities', 'clientInfo'} and
                        type(params['protocolVersion']) is str and type(params['capabilities']) is dict and
                        type(params['clientInfo']) is dict, 'INVALID_PARAMS')
                self.initialized = True
                result = {'protocolVersion': '2025-06-18', 'capabilities': {'tools': {'listChanged': False}},
                          'serverInfo': {'name': 'av-pio-test-only', 'version': '0.1.0'}}
            elif method == 'ping':
                require(params == {}, 'INVALID_PARAMS')
                result = {}
            else:
                require(self.ready, 'NOT_INITIALIZED')
                if method == 'tools/list':
                    require(params == {}, 'INVALID_PARAMS')
                    result = {'tools': tools_list()}
                elif method in ('resources/list', 'resources/templates/list', 'prompts/list'):
                    require(params == {}, 'INVALID_PARAMS')
                    result = { {'resources/list': 'resources', 'resources/templates/list': 'resourceTemplates',
                                'prompts/list': 'prompts'}[method]: []}
                elif method == 'tools/call':
                    require(set(params) == {'name', 'arguments'}, 'INVALID_PARAMS')
                    try:
                        answer = self.client.call(params['name'], params['arguments'])
                    except Exception as error:
                        answer = {'ok': False, 'code': error.code if isinstance(error, Rejected) else 'TRANSPORT_FAILURE',
                                  'retry_safe': False, 'rollback': False}
                    result = {'isError': not answer['ok'],
                              'content': [{'type': 'text', 'text': dumps(answer).decode('utf-8')}]}
                else:
                    return {'jsonrpc': '2.0', 'id': request_id,
                            'error': {'code': -32601, 'message': 'Method not found'}}
            return {'jsonrpc': '2.0', 'id': request_id, 'result': result}
        except Exception as error:
            return {'jsonrpc': '2.0', 'id': request_id,
                    'error': {'code': -32600, 'message': error.code if isinstance(error, Rejected) else 'Invalid request'}}


def serve(server, source, destination):
    while True:
        line = source.readline(MAX_FRAME + 1)
        if not line:
            return
        if len(line) > MAX_FRAME or not line.endswith(b'\n'):
            # Close instead of draining an unbounded attacker-controlled frame.
            return
        try:
            result = server.handle(loads(line))
        except Rejected:
            result = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'Parse error'}}
        if result is not None:
            destination.write(dumps(result) + b'\n')
            destination.flush()


def main():
    parser = argparse.ArgumentParser(description='Restricted AV PIO stdio server; no native deployment')
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    try:
        cfg, key = read_config(args.config)
        serve(Server(Client(cfg, key)), sys.stdin.buffer, sys.stdout.buffer)
    except Exception:
        # No traceback/config/secret disclosure during startup or shutdown.
        print('AV PIO test server stopped: verify private configuration and IPC state.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
