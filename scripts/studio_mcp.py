"""Command-line client for Roblox Studio's own MCP server (StudioMCP), over stdio. Two uses:
  - Studio access when the agent has no Studio MCP tool (the server ships with Studio, so Codex's or Studio's MCP setup
    is not needed in the agent).
  - Fewer tokens with or without one: a .luau file whose first line is `--@use RigSkin, RigAudit` gets those scripts
    from this folder inlined (loadstring in Edit, a temporary ModuleScript in Play; no HTTP, so it works with the
    place's HttpEnabled off), so their source never passes through the conversation.

  python studio_mcp.py list                                  the server's tools and their input schemas
  python studio_mcp.py luau FILE [--datamodel Edit|Server|Client]
  python studio_mcp.py play FILE                             starts Play, runs FILE on the server, stops Play
  python studio_mcp.py call TOOL ['{"json": "args"}' | @args.json] [--image out.png]
  python studio_mcp.py save INSTANCE OUT.rbxm                one instance (a dotted path from game, such as
                                                             ServerStorage.Clips.Walk) as an .rbxm file, ready to upload
  options: --studio NAME (a part of the place name, when several Studios are open; or STUDIO_ID), --timeout SECONDS
           --output FILE (text blocks as UTF-8, no BOM; avoids PowerShell redirect encoding)

The server: STUDIO_MCP (its command line), else %LOCALAPPDATA%\\Roblox\\mcp.bat on Windows. studio_id is filled in
(the server finds Studio a second or two after it starts, so it is polled), datamodel_type defaults to Edit, images
from screen_capture are written to --image. Each run starts its own server process (about 2 s).

Calls run in Studio one at a time and block it until they yield. A reply can be lost while the code still runs (seen
"Target is not reachable" came back after a dressing script had run): read the state again before
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
        # A Studio window can list with no name (null): match ids first, and prefer a named window when none is asked for.
        def name(s):
            return s.get('name') or ''
        if want:
            match = [s for s in studios if s['id'] == want] or [s for s in studios if want.lower() in name(s).lower()]
            if not match:
                sys.exit('no Studio matches ' + want + ': ' + ', '.join(name(s) or s['id'] for s in studios))
            return match[0]['id']
        pick = next((s for s in studios if name(s)), studios[0])
        if len(studios) > 1:
            print('several Studios open, using ' + (name(pick) or pick['id']) + ' (--studio to choose)', file=sys.stderr)
        return pick['id']

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
    (nothing left behind); in Play, where loadstring is off, through a temporary ModuleScript that is
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


def show(result, image, output=None):
    if output:
        # Keep the same text as stdout, without shell-dependent redirection encoding.
        with open(output, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(c['text'] for c in result.get('content', []) if c.get('type') == 'text'))
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


def play(s, studio, a):
    """FILE on the Play server, between a start and a stop of Play. Stopping discards what the run changed; the place's own scripts run,
    so audit what was inserted first (references/safety/assets.md)."""
    with open(a.target, encoding='utf-8-sig') as f:  # a BOM hides the --@use line from Studio
        source = f.read()
    try:
        # Inside the try: a Studio slow to start Play may have started it by the time this call gives up.
        s.call('start_stop_play', {'is_start': True, 'studio_id': studio}, a.timeout)
        for _ in range(120):
            state = s.call('get_studio_state', {'studio_id': studio}, 30)
            if 'Server' in ' '.join(c.get('text', '') for c in state.get('content', [])):
                break
            time.sleep(1)
        else:
            sys.exit('Play did not start in 2 minutes')
        time.sleep(3)  # the place's own startup
        args = {'code': inline_uses(source, 'Server'), 'datamodel_type': 'Server', 'studio_id': studio}
        return show(s.call('execute_luau', args, a.timeout), a.image, a.output)
    finally:
        s.call('start_stop_play', {'is_start': False, 'studio_id': studio}, a.timeout)


SAVE = '''local item: Instance = game
for name in string.gmatch(__PATH__, "[^%.]+") do
	item = assert(item:FindFirstChild(name), "no " .. name .. " under " .. item:GetFullName())
end
local data = buffer.tostring(game:GetService("SerializationService"):SerializeInstancesAsync({ item }))
if __AT__ < 0 then
	return tostring(#data)
end
local piece = string.sub(data, __AT__ + 1, __AT__ + __CHUNK__)
local alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
local out = table.create(math.ceil(#piece / 3) * 4)
for i = 1, #piece, 3 do
	local a, b, c = string.byte(piece, i, i + 2)
	local n = a * 65536 + (b or 0) * 256 + (c or 0)
	for j = 3, 0, -1 do
		local index = bit32.band(bit32.rshift(n, j * 6), 63) + 1
		table.insert(out, string.sub(alphabet, index, index))
	end
	if not b then
		out[#out], out[#out - 1] = "=", "="
	elseif not c then
		out[#out] = "="
	end
end
return table.concat(out)'''


def text_of(result):
    """A tool result's text, a returned string unquoted."""
    text = '\n'.join(c['text'] for c in result.get('content', []) if c.get('type') == 'text').strip()
    if result.get('isError'):
        raise RuntimeError(text[-2000:])
    return json.loads(text) if text.startswith('"') else text


def luau(s, studio, code, timeout=300, datamodel='Edit'):
    """Runs code (with its --@use line) and returns the text it returned; raises on a Studio error."""
    args = {'code': inline_uses(code, datamodel), 'datamodel_type': datamodel, 'studio_id': studio}
    return text_of(s.call('execute_luau', args, timeout))


def save(s, studio, path, out, timeout=300, chunk=60000):
    """The instance at `path` (dots from game) serialized by Studio (SerializationService, as an upload expects) into `out`."""
    def run(at):
        code = SAVE.replace('__PATH__', json.dumps(path)).replace('__AT__', str(at)).replace('__CHUNK__', str(chunk))
        return luau(s, studio, code, timeout)
    total, raw = int(run(-1)), bytearray()
    while len(raw) < total:
        raw += base64.b64decode(run(len(raw)))
    with open(out, 'wb') as f:
        f.write(bytes(raw))
    return total


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    ap.add_argument('command', choices=['list', 'luau', 'play', 'call', 'save'])
    ap.add_argument('target', nargs='?', help='luau, play: the .luau file; call: the tool name')
    ap.add_argument('args', nargs='?', default='{}', help='call: JSON arguments or @file.json; save: the .rbxm to write')
    ap.add_argument('--datamodel', default='Edit', choices=['Edit', 'Server', 'Client'])
    ap.add_argument('--image', help='where to write an image result (screen_capture)')
    ap.add_argument('--output', help='write response text as UTF-8 without a BOM (use instead of shell redirection)')
    ap.add_argument('--studio', default=os.environ.get('STUDIO_ID'), help='place name part or studio id')
    ap.add_argument('--timeout', type=float, default=float(os.environ.get('STUDIO_MCP_TIMEOUT', 300)))
    a = ap.parse_args()
    s = Server()
    try:
        if a.command == 'list':
            result = s.request('tools/list', {}, 60)
            if a.output:
                with open(a.output, 'w', encoding='utf-8', newline='\n') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
            for t in result['tools']:
                print('==', t['name'], '\n', t.get('description', '').strip(), '\n', json.dumps(t.get('inputSchema')))
            return 0
        if not a.target:
            ap.error(a.command + ' needs a target')
        if a.command == 'play':
            return play(s, s.studio(a.studio), a)
        if a.command == 'save':
            size = save(s, s.studio(a.studio), a.target, a.args, a.timeout)
            print(f'saved {a.target}: {size} bytes to {os.path.abspath(a.args)}')
            return 0
        if a.command == 'luau':
            tool = 'execute_luau'
            args = {'code': inline_uses(open(a.target, encoding='utf-8-sig').read(), a.datamodel), 'datamodel_type': a.datamodel}
        else:
            tool = a.target
            args = json.load(open(a.args[1:], encoding='utf-8')) if a.args.startswith('@') else json.loads(a.args)
            if tool in DATAMODEL_TOOLS:
                args.setdefault('datamodel_type', a.datamodel)
            if tool == 'screen_capture':
                args.setdefault('capture_id', 'ScreenCapture_1')
        if tool != 'list_roblox_studios':
            args.setdefault('studio_id', s.studio(a.studio))
        return show(s.call(tool, args, a.timeout), a.image, a.output)
    finally:
        s.close()


if __name__ == '__main__':
    sys.exit(main())
