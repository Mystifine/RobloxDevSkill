"""MCP output must survive Windows shell encoding and preserve tool failures."""
import base64
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import studio_mcp


class PlayTests(unittest.TestCase):
    def test_play_runs_on_the_server_and_always_stops(self):
        class Fake:
            def __init__(self):
                self.calls = []

            def call(self, tool, args, timeout):
                self.calls.append(tool if tool != 'start_stop_play' else f'play {args["is_start"]}')
                if tool == 'get_studio_state':
                    return {'content': [{'type': 'text', 'text': 'Available DataModels: Client, Server'}]}
                if tool == 'execute_luau':
                    self.server = args
                    raise RuntimeError('lost')
                return {'content': []}

        fake = Fake()
        with tempfile.TemporaryDirectory() as tmp, patch.object(studio_mcp.time, 'sleep'):
            script = Path(tmp) / 't.luau'
            script.write_text('return 1')
            args = type('A', (), {'target': str(script), 'timeout': 5, 'image': None, 'output': None})
            with self.assertRaises(RuntimeError):
                studio_mcp.play(fake, 'id', args)
        self.assertEqual(fake.calls, ['play True', 'get_studio_state', 'execute_luau', 'play False'])
        self.assertEqual(fake.server['datamodel_type'], 'Server')

    def test_play_stops_even_when_starting_it_times_out(self):
        class Slow:
            calls = []

            def call(self, tool, args, timeout):
                self.calls.append(args['is_start'])
                if args['is_start']:
                    sys.exit('no reply')
                return {'content': []}

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / 't.luau'
            script.write_text('return 1')
            args = type('A', (), {'target': str(script), 'timeout': 5, 'image': None, 'output': None})
            with self.assertRaises(SystemExit):
                studio_mcp.play(Slow(), 'id', args)
        self.assertEqual(Slow.calls, [True, False])


class OutputTests(unittest.TestCase):
    def test_unicode_text_and_image_have_separate_outputs(self):
        payload = json.dumps({'name': '竜の娘', 'motion': '▂▇█'}, ensure_ascii=False)
        result = {'content': [{'type': 'text', 'text': payload},
                              {'type': 'image', 'data': base64.b64encode(b'image bytes').decode()}]}
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            output, image = Path(tmp) / '結果.json', Path(tmp) / 'capture.png'
            self.assertEqual(studio_mcp.show(result, str(image), str(output)), 0)
            raw = output.read_bytes()
            self.assertFalse(raw.startswith(b'\xef\xbb\xbf'))
            self.assertEqual(json.loads(raw.decode('utf-8')), json.loads(payload))
            self.assertEqual(image.read_bytes(), b'image bytes')

    def test_error_text_is_saved_and_failure_status_is_preserved(self):
        result = {'isError': True, 'content': [{'type': 'text', 'text': '失敗'},
                                              {'type': 'text', 'text': 'second line'}]}
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            output = Path(tmp) / 'error.txt'
            self.assertEqual(studio_mcp.show(result, None, str(output)), 1)
            self.assertEqual(output.read_bytes(), '失敗\nsecond line'.encode())

    def test_cli_writes_raw_response_text_and_closes_server(self):
        class Stdout(io.StringIO):
            def reconfigure(self, **_):
                pass

        result = {'content': [{'type': 'text', 'text': '{"ok":true,"name":"竜"}'}]}
        with tempfile.TemporaryDirectory() as tmp, patch.object(studio_mcp, 'Server') as constructor:
            output = Path(tmp) / 'result.json'
            server = constructor.return_value
            server.studio.return_value = 'test-studio'
            server.call.return_value = result
            argv = ['studio_mcp.py', 'call', 'get_studio_state', '--output', str(output)]
            with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(Stdout()):
                self.assertEqual(studio_mcp.main(), 0)
            self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['name'], '竜')
            server.close.assert_called_once()

    def test_list_output_is_machine_readable(self):
        class Stdout(io.StringIO):
            def reconfigure(self, **_):
                pass

        result = {'tools': [{'name': 'execute_luau', 'inputSchema': {'type': 'object'}}]}
        with tempfile.TemporaryDirectory() as tmp, patch.object(studio_mcp, 'Server') as constructor:
            output = Path(tmp) / 'tools.json'
            constructor.return_value.request.return_value = result
            with patch.object(sys, 'argv', ['studio_mcp.py', 'list', '--output', str(output)]), contextlib.redirect_stdout(Stdout()):
                self.assertEqual(studio_mcp.main(), 0)
            self.assertEqual(json.loads(output.read_text(encoding='utf-8')), result)


if __name__ == '__main__':
    unittest.main()
