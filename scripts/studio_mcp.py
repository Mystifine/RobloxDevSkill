"""Command-line client for Roblox Studio's own MCP server (StudioMCP), over stdio. Two uses:
  - Studio access when the agent has no Studio MCP tool (the server ships with Studio, so Codex's or Studio's MCP setup
    is not needed in the agent).
  - Fewer tokens with or without one: a .luau file whose first line is `--@use RigSkin, RigAudit` gets those scripts
    from this folder inlined (loadstring in Edit, a temporary ModuleScript in Play; no HTTP, so it works with the
    place's HttpEnabled off), so their source never passes through the conversation.

  python studio_mcp.py list                                  the server's tools and their input schemas
  python studio_mcp.py luau FILE [--datamodel Edit|Server|Client]
  python studio_mcp.py call TOOL ['{"json": "args"}' | @args.json] [--image out.png]
  options: --studio NAME (a part of the place name, when several Studios are open; or STUDIO_ID), --timeout SECONDS

The server: STUDIO_MCP (its command line), else %LOCALAPPDATA%\\Roblox\\mcp.bat on Windows. studio_id is filled in
(the server finds Studio a second or two after it starts, so it is polled), datamodel_type defaults to Edit, images
from screen_capture are written to --image. Each run starts its own server process (about 2 s).

Calls run in Studio one at a time and block it until they yield. A reply can be lost while the code still runs (seen
2026-10-30: "Target is not reachable" came back after a dressing script had run): read the state again before
re-running, and write scripts that can run twice. Exit code 1 on a tool error."""
import argparse
import base64
import json
import os
import queue
import shlex
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATAMODEL_TOOLS = {'execute_luau', 'search_game_tree', 'inspect_instance', 'multi_edit', 'script_read', 'script_grep'}


def server_command():
    if os.environ.get('STUDIO_MCP'):
        return shlex.split(os.environ['STUDIO_MCP'], posix=os.name != 'nt')
    bat = os.path.expandvars(r'%LOCALAPPDATA%\Roblox\mcp.bat')
    if os.name == 'nt' and os.path.exists(bat):
        return ['cmd.exe', '/c', bat]
    sys.exit('Studio MCP server not found: set STUDIO_MCP to the command that starts it (as in your Studio MCP setup)')


class Server:
    def __init__(self):
        self.p = subprocess.Popen(server_command(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.q, self.next_id = queue.Queue(), 0
        threading.Thread(target=self._read, daemon=True).start()
        self.request('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {},
                                    'clientInfo': {'name': 'roblox-dev studio_mcp.py', 'version': '1'}}, 60)
        self._send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})

    def _read(self):
        for line in self.p.stdout:
            self.q.put(line)
        self.q.put(None)

    def _send(self, msg):
        self.p.stdin.write((json.dumps(msg) + '\n').encode()); self.p.stdin.flush()

    def request(self, method, params, timeout):
        self.next_id += 1; rid = self.next_id
        self._send({'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params})
        end = time.time() + timeout
        while True:
            try:
                line = self.q.get(timeout=max(end - time.time(), 0.01))
            except queue.Empty:
                sys.exit(f'{method}: no reply in {timeout:.0f} s (the code may still be running in Studio)')
            if line is None:
                sys.exit('the Studio MCP server exited')
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if msg.get('id') == rid:
                if 'error' in msg:
                    sys.exit(f'{method}: {json.dumps(msg["error"])}')
                return msg['result']

    def call(self, tool, args, timeout):
        return self.request('tools/call', {'name': tool, 'arguments': args}, timeout)

    def studio(self, want):
        for _ in range(20):
            res = self.call('list_roblox_studios', {}, 60)
            studios = json.loads(res['content'][0]['text']).get('studios', [])
            if studios:
                break
            time.sleep(0.5)
        else:
            sys.exit('no Roblox Studio found: is Studio open with its MCP server enabled?')
        if want:
            match = [s for s in studios if s['id'] == want or want.lower() in s['name'].lower()]
            if not match:
                sys.exit('no Studio matches ' + want + ': ' + ', '.join(s['name'] for s in studios))
            return match[0]['id']
        if len(studios) > 1:
            print('several Studios open, using ' + studios[0]['name'] + ' (--studio to choose)', file=sys.stderr)
        return studios[0]['id']

    def close(self):
        try:
            self.p.stdin.close()
        except OSError:
            pass
        self.p.kill()


USE_MODULE = '''local function __use(name: string, source: string): any
	local m = Instance.new("ModuleScript")
	m.Name, m.Source = name, source
	m.Parent = if game:GetService("RunService"):IsServer() then game:GetService("ServerStorage")
		else game:GetService("Players").LocalPlayer:WaitForChild("PlayerGui")
	local ok, result = pcall(require, m)
	m:Destroy()
	if not ok then error(result, 0) end
	return result
end
'''


def inline_uses(src, datamodel='Edit'):
    """`--@use A, B` on the first line: each name's .luau in this folder becomes a local. In Edit through loadstring
    (nothing left behind); in Play, where loadstring is off (seen 2026-10-30), through a temporary ModuleScript that is
    required and destroyed."""
    first = src.split('\n', 1)[0]
    if not first.startswith('--@use'):
        return src
    pre = [] if datamodel == 'Edit' else [USE_MODULE]
    for name in [n.strip() for n in first[6:].split(',') if n.strip()]:
        body = open(os.path.join(HERE, name + '.luau'), encoding='utf-8').read()
        eq = '=' * 3
        while f']{eq}]' in body:
            eq += '='
        text = f'[{eq}[{body}]{eq}]'
        pre.append(f'local {name} = assert(loadstring({text}, "{name}"))()' if datamodel == 'Edit' else f'local {name} = __use("{name}", {text})')
    return '\n'.join(pre) + '\n' + src


def show(result, image):
    for c in result.get('content', []):
        if c.get('type') == 'text':
            print(c['text'])
        elif c.get('type') == 'image':
            path = image or 'capture.png'
            with open(path, 'wb') as f:
                f.write(base64.b64decode(c['data']))
            print('image saved:', os.path.abspath(path))
        else:
            print(json.dumps(c)[:2000])
    return 1 if result.get('isError') else 0


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    ap.add_argument('command', choices=['list', 'luau', 'call'])
    ap.add_argument('target', nargs='?', help='luau: the .luau file; call: the tool name')
    ap.add_argument('args', nargs='?', default='{}', help='call: JSON arguments or @file.json')
    ap.add_argument('--datamodel', default='Edit', choices=['Edit', 'Server', 'Client'])
    ap.add_argument('--image', help='where to write an image result (screen_capture)')
    ap.add_argument('--studio', default=os.environ.get('STUDIO_ID'), help='place name part or studio id')
    ap.add_argument('--timeout', type=float, default=float(os.environ.get('STUDIO_MCP_TIMEOUT', 300)))
    a = ap.parse_args()
    s = Server()
    try:
        if a.command == 'list':
            for t in s.request('tools/list', {}, 60)['tools']:
                print('==', t['name'], '\n', t.get('description', '').strip(), '\n', json.dumps(t.get('inputSchema')))
            return 0
        if not a.target:
            ap.error(a.command + ' needs a target')
        if a.command == 'luau':
            tool = 'execute_luau'
            args = {'code': inline_uses(open(a.target, encoding='utf-8').read(), a.datamodel), 'datamodel_type': a.datamodel}
        else:
            tool = a.target
            args = json.load(open(a.args[1:], encoding='utf-8')) if a.args.startswith('@') else json.loads(a.args)
            if tool in DATAMODEL_TOOLS:
                args.setdefault('datamodel_type', a.datamodel)
        if tool != 'list_roblox_studios':
            args.setdefault('studio_id', s.studio(a.studio))
        return show(s.call(tool, args, a.timeout), a.image)
    finally:
        s.close()


if __name__ == '__main__':
    sys.exit(main())
