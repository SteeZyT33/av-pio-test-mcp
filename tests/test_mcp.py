import ast
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock

from pio_test.mcp_stdio import Server, serve
from pio_test.schema import COMMANDS
from pio_test.wire import dumps, loads
from tests.support import Fixture


class RejectingClient:
    def call(self, command, args):
        from pio_test.schema import validate_command
        validate_command(command, args)
        return {'ok': True}


class McpTests(unittest.TestCase):
    def setUp(self):
        self.server = Server(RejectingClient())
        self.server.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                            'params': {'protocolVersion': '2025-06-18', 'capabilities': {},
                                       'clientInfo': {'name': 'offline-test', 'version': '1'}}})
        self.server.handle({'jsonrpc': '2.0', 'method': 'notifications/initialized'})

    def request(self, method, params=None):
        return self.server.handle({'jsonrpc': '2.0', 'id': 2, 'method': method, 'params': params or {}})

    def test_exact_tools(self):
        tools = self.request('tools/list')['result']['tools']
        self.assertEqual({t['name'] for t in tools}, {'test_status', 'test_arm', 'test_disarm', 'test_create',
                         'test_read', 'test_set_parameters', 'test_transform', 'test_regenerate', 'test_case', 'test_cleanup'})
        self.assertEqual(len(tools), 10)
        for tool in tools:
            self.assertEqual(tool['inputSchema']['type'], 'object')
            self.assertFalse(tool['annotations']['openWorldHint'])

    def test_discovery_accepts_standard_request_metadata(self):
        for token in ('discovery', 0, 1.5):
            metadata = {'progressToken': token,
                        'io.modelcontextprotocol/clientInfo': {'name': 'codex'}}
            with self.subTest(token=token):
                tools = self.request('tools/list', {'_meta': metadata})['result']['tools']
                self.assertEqual({tool['name'] for tool in tools}, set(COMMANDS))
                self.assertEqual(len(tools), 10)
                for method in ('ping', 'resources/list',
                               'resources/templates/list', 'prompts/list'):
                    self.assertIn('result', self.request(method, {'_meta': metadata}))

    def test_malformed_request_metadata_is_rejected(self):
        for metadata in (None, [], 'metadata', 1, True, {1: 'invalid key'},
                         {'progressToken': None}, {'progressToken': True},
                         {'progressToken': []}, {'progressToken': {}},
                         {'progressToken': float('nan')},
                         {'progressToken': float('inf')}):
            with self.subTest(metadata=metadata):
                response = self.request('tools/list', {'_meta': metadata})
                self.assertEqual(response['error']['message'], 'INVALID_PARAMS')
                self.assertNotIn('result', response)

    def test_metadata_does_not_enter_tool_arguments_or_result(self):
        client = Mock(wraps=RejectingClient())
        self.server.client = client
        metadata = {'progressToken': 'metadata-never-echo',
                    'arguments': {'force': True}, 'command': 'execute_script'}
        params = {'name': 'test_status', 'arguments': {}, '_meta': metadata}
        response = self.request('tools/call', params)
        self.assertFalse(response['result']['isError'])
        client.call.assert_called_once_with('test_status', {})
        self.assertNotIn('metadata-never-echo', json.dumps(response))
        self.assertEqual(params['_meta'], metadata)  # Input envelope is not mutated.

    def test_metadata_does_not_relax_method_or_command_arguments(self):
        response = self.request('tools/list', {'_meta': {}, 'force': True})
        self.assertEqual(response['error']['message'], 'INVALID_PARAMS')
        response = self.request('tools/call', {'_meta': {}, 'name': 'test_status',
                                'arguments': {}, 'force': True})
        self.assertEqual(response['error']['message'], 'INVALID_PARAMS')
        for arguments in ({'force': True}, {'_meta': {}}):
            response = self.request('tools/call', {'_meta': {}, 'name': 'test_status',
                                    'arguments': arguments})
            self.assertTrue(response['result']['isError'])
        response = self.request('tools/call', {'_meta': {}, 'name': 'execute_script',
                                'arguments': {}})
        self.assertTrue(response['result']['isError'])

    def test_no_live_document_resources_or_templates(self):
        self.assertEqual(self.request('resources/list')['result'], {'resources': []})
        self.assertEqual(self.request('resources/templates/list')['result'], {'resourceTemplates': []})
        self.assertEqual(self.request('prompts/list')['result'], {'prompts': []})
        for method in ['resources/read', 'resources/subscribe', 'prompts/get', 'tasks/list', 'execute_script', 'set_toolset']:
            self.assertEqual(self.request(method)['error']['code'], -32601)

    def test_old_tools_and_extra_arguments_fail(self):
        for name in ['execute_script', 'vwx', 'vwx_batch', 'set_toolset', 'run_menu_command', 'get_document_info']:
            result = self.request('tools/call', {'name': name, 'arguments': {}})['result']
            self.assertTrue(result['isError'])
        result = self.request('tools/call', {'name': 'test_status', 'arguments': {'force': True}})['result']
        self.assertTrue(result['isError'])

    def test_notification_never_calls_tool(self):
        response = self.server.handle({'jsonrpc': '2.0', 'method': 'tools/call',
                                      'params': {'name': 'test_create', 'arguments': {}}})
        self.assertIsNone(response)

    def test_stdio_framing_and_oversized_frame_closes(self):
        for source, expected in [(b'{bad}\n', 1), (b'x' * 65537 + b'\n', 0), (b'{}', 0)]:
            out = io.BytesIO()
            serve(self.server, io.BytesIO(source), out)
            self.assertEqual(len(out.getvalue().splitlines()), expected)
            for line in out.getvalue().splitlines():
                self.assertEqual(loads(line)['error']['code'], -32700)

    def test_real_entrypoint_ignores_legacy_network_and_toolset_environment(self):
        f = Fixture()
        self.addCleanup(f.close)
        config = f.config_file()
        messages = [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
             'params': {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {},
                        '_meta': {'progressToken': 'initialize'}}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized', 'params': {'_meta': {}}},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list',
             'params': {'_meta': {'progressToken': 2}}},
            {'jsonrpc': '2.0', 'id': 3, 'method': 'resources/list', 'params': {'_meta': {}}},
        ]
        repo = Path(__file__).resolve().parents[1]
        env = dict(os.environ, MCP_TRANSPORT='streamable-http', FASTMCP_HOST='0.0.0.0',
                   VWX_TOOLSET='full', VWX_TRANSPORT='tcp', OTEL_EXPORTER_OTLP_ENDPOINT='https://invalid.test')
        run = subprocess.run([sys.executable, '-I', str(repo/'mcp-server/vwx_mcp_server.py'), '--config', str(config)],
                             input=b'\n'.join(dumps(m) for m in messages)+b'\n',
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stderr, b'')
        replies = [loads(line) for line in run.stdout.splitlines()]
        self.assertEqual(len(replies), 3)
        self.assertEqual({t['name'] for t in replies[1]['result']['tools']}, set(COMMANDS))
        self.assertEqual(replies[2]['result'], {'resources': []})
        self.assertEqual(replies[0]['result']['capabilities'], {'tools': {'listChanged': False}})


class SourceBoundaryTests(unittest.TestCase):
    def test_python39_grammar_and_no_execution_or_network_escape(self):
        root = Path(__file__).resolve().parents[1]
        for folder in ['pio_test', 'vwx-plugin', 'mcp-server']:
            for path in (root/folder).glob('*.py'):
                with self.subTest(path=path.name):
                    tree = ast.parse(path.read_text(), feature_version=(3, 9))
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                            self.assertNotIn(node.func.id, ['eval', 'exec', '__import__'])
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                self.assertNotIn(alias.name.split('.')[0], ['socket', 'subprocess', 'requests', 'urllib', 'fastmcp'])
        for removed in ['vwx-plugin/commands.py', 'vwx-plugin/vwx_mcp_bridge.py',
                        'mcp-server/tool_tags.py', 'bridge/deploy_native_bridge.bat',
                        'native/Source/Bridge/VwxBridgePalette.cpp', 'native/VwxBridge2026.vcxproj',
                        'native/VwxBridge.vwr/html/main.js', 'legacy/vwx_mcp_bridge_dialog.py']:
            self.assertFalse((root/removed).exists(), removed)
