// The Codex handoff wrapper against a fake CLI (fake-codex.mjs): no model usage, no live apps.
// From the skill's folder: node --test tests/codex/
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn, spawnSync } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import { fileURLToPath } from 'node:url';
import { alive, loadState, readJson, reserve, release, safeRemove, writeJson } from '../../scripts/codex/state.mjs';
import { limitResetAt, nextStep, summarize } from '../../scripts/codex/summarize.mjs';
import { snapshot, finishSnapshot, git } from '../../scripts/codex/snapshot.mjs';
import { cleanup } from '../../scripts/codex/cleanup.mjs';
import { parse } from '../../scripts/codex/handoff.mjs';
import { bindingReset, normalize, readLogged, room, runCost } from '../../scripts/codex/usage.mjs';

const scripts = fileURLToPath(new URL('../../scripts/codex/', import.meta.url));
const fake = fileURLToPath(new URL('./fake-codex.mjs', import.meta.url));
const now = () => Math.floor(Date.now() / 1000);
function fixture(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'handoff-test-'));
  const root = path.join(dir, 'home'), cwd = path.join(dir, 'repo'), codexHome = path.join(dir, 'codex');
  for (const folder of [root, cwd, codexHome]) fs.mkdirSync(folder);
  const calls = path.join(dir, 'calls.jsonl'), brief = path.join(dir, 'brief.md'), usage = path.join(dir, 'usage.json');
  fs.writeFileSync(brief, 'Perform the fixture task.');
  const env = { ...process.env, CODEX_HANDOFF_HOME: root, CODEX_HOME: codexHome, CODEX_HANDOFF_CLI: fake, CODEX_HANDOFF_MODEL: '',
    CODEX_HANDOFF_EFFORT: '', CODEX_HANDOFF_FALLBACK_MODELS: '', CODEX_HANDOFF_SANDBOX: '', CODEX_HANDOFF_MAX_RUNS: '', CODEX_HANDOFF_SELF: '',
    CLAUDE_CODE_SESSION_ID: '', CLAUDE_CONFIG_DIR: path.join(dir, 'claude'), FAKE_CALLS: calls, FAKE_USAGE_FILE: usage };
  const children = new Set();
  const launch = (args, overrides = {}) => {
    const child = spawn(process.execPath, [path.join(scripts, 'handoff.mjs'), ...args], { env: { ...env, ...overrides }, cwd, windowsHide: true });
    children.add(child);
    let stdout = '', stderr = '';
    child.stdout.on('data', (data) => { stdout += data; }); child.stderr.on('data', (data) => { stderr += data; });
    const done = new Promise((resolve) => child.on('close', (code) => { children.delete(child); resolve({ code, stdout, stderr }); }));
    return { child, done };
  };
  t.after(async () => {
    for (const child of children) { if (process.platform === 'win32') spawnSync('taskkill.exe', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true }); else child.kill('SIGTERM'); }
    await sleep(100);
    safeRemove(os.tmpdir(), dir);
  });
  return { dir, root, cwd, codexHome, brief, calls, env, launch, args: ['--brief', brief, '--cd', cwd],
    setUsage: (value) => fs.writeFileSync(usage, JSON.stringify(value)),
    runs: () => fs.readdirSync(root, { withFileTypes: true }).filter((entry) => entry.isDirectory()).flatMap((project) =>
      fs.readdirSync(path.join(root, project.name)).filter((name) => /^\d{8}-\d{6}-/.test(name)).map((name) => path.join(root, project.name, name))),
    invocations: () => fs.existsSync(calls) ? fs.readFileSync(calls, 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse) : [] };
}
async function until(check, message) {
  const end = Date.now() + 30000;
  while (Date.now() < end) { if (check()) return; await sleep(25); }
  assert.fail(message);
}
function initRepo(cwd) {
  git(cwd, ['init']); fs.writeFileSync(path.join(cwd, 'tracked.txt'), 'initial\n');
  git(cwd, ['add', '.']); git(cwd, ['-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'fixture']);
}
function reportFixture(f, name, eventList, result, { final = 'done', invocation = {}, stderr = '', rawResult } = {}) {
  const project = path.join(f.root, 'project'); fs.mkdirSync(project, { recursive: true });
  const dir = fs.mkdtempSync(path.join(project, `20261025-100000-${name}-`));
  writeJson(path.join(dir, 'invocation.json'), { root: f.root, project, accountKey: 'account', ...invocation });
  fs.writeFileSync(path.join(dir, 'events.jsonl'), eventList.map((event) => JSON.stringify(event)).join('\n'));
  fs.writeFileSync(path.join(dir, 'final.md'), final);
  if (stderr) fs.writeFileSync(path.join(dir, 'stderr.log'), stderr);
  if (rawResult !== undefined) fs.writeFileSync(path.join(dir, 'result.json'), rawResult);
  else if (result) writeJson(path.join(dir, 'result.json'), result);
  return dir;
}
// Splits a printed command the way a POSIX shell would (single quotes only, as the wrapper prints).
const words = (command) => [...command.matchAll(/'((?:[^']|'\\'')*)'|(\S+)/g)].map((m) => m[1] !== undefined ? m[1].replaceAll("'\\''", "'") : m[2]);
const done = { type: 'turn.completed', usage: { input_tokens: 1 } };
const result = { status: 'completed', verification: 'checks passed', reason: '' };

test('invalid/missing arguments fail promptly', () => {
  for (const args of [['--brief'], ['--timeout-min', 'NaN'], ['--brief', 'x', '--check'], ['--kind', 'video'], ['--discard'], ['--usage', '--list']]) {
    assert.throws(() => parse(args), /Missing|timeout|Choose|kind|discard/);
  }
});
test('completion requires a task result, completed turn, and successful infrastructure', async (t) => {
  const f = fixture(t), at = now();
  const reconnect = { type: 'error', message: 'Reconnecting... 2/5 (stream disconnected before completion: IO error)' };
  const capacity = 'Selected model is at capacity. Please try a different model.';
  const cases = [
    ['ok', [done], result, 0], ['missing', [done], null, 4], ['incomplete-stream', [], result, 4],
    ['blocked', [done], { ...result, status: 'blocked', reason: 'cannot finish' }, 4],
    ['sandbox', [{ type: 'item.completed', item: { type: 'command_execution', exit_code: 1, aggregated_output: 'helper_unknown_error: setup refresh had errors' } }, done], result, 4],
    ['recovered-command', [{ type: 'item.completed', item: { type: 'command_execution', exit_code: 1, aggregated_output: 'a recoverable test failed' } }, done], result, 0],
    // Recovered stream reconnects, a byte-order mark and tool noise in stderr are not failures.
    ['reconnects', [reconnect, { ...reconnect, message: 'Falling back from WebSockets to HTTPS transport.' }, done], result, 0],
    ['bom', [done], null, 0, { rawResult: `\uFEFF${JSON.stringify(result)}` }],
    ['tool-noise', [done], result, 0, { stderr: 'Reading additional input from stdin...\nERROR codex_core::tools::router: error=image rate limit, retrying' }],
  ];
  for (const [name, events, taskResult, expected, options] of cases) {
    const report = await summarize(reportFixture(f, name, events, taskResult, options), 0, at, at, f.cwd);
    assert.equal(report.exit, expected, name);
  }
  const busy = await summarize(reportFixture(f, 'capacity', [{ type: 'error', message: capacity }, { type: 'turn.failed', error: { message: capacity } }], null), 1, at, at, f.cwd);
  assert.equal(busy.exit, 71); assert.equal(busy.status, 'CODEX AT CAPACITY');
  const failed = await summarize(reportFixture(f, 'unrecovered', [reconnect, { type: 'turn.failed', error: { message: 'stream disconnected' } }], null, { stderr: 'fatal' }), 1, at, at, f.cwd);
  assert.equal(failed.exit, 1);
});
test('usage limit resets honor stated delays, dates and local clock times', () => {
  const local = (h, m, day = 25) => Math.round(new Date(2026, 9, day, h, m).getTime() / 1000);
  const stated = "You've hit your usage limit. Upgrade to Pro (https://chatgpt.com/explore/pro), visit https://chatgpt.com/settings/usage to purchase more credits or try again at 5:01 PM.";
  assert.equal(limitResetAt(stated, local(14, 0)), local(17, 1));
  assert.equal(limitResetAt(stated, local(17, 30)), local(17, 1, 26));
  assert.equal(limitResetAt('usage limit: try again at 17:01', local(14, 0)), local(17, 1));
  assert.equal(limitResetAt('usage limit: try again in 5 minutes', local(14, 0)), local(14, 5));
  assert.equal(limitResetAt('usage limit: try again on Oct 27th, 2026 9:00 AM.', local(14, 0)), local(9, 0, 27));
  assert.equal(limitResetAt('usage limit reached', local(14, 0)), local(14, 30));
});
test('a mid-run usage limit: code is taken over, image work is resumed by --wait', async (t) => {
  const f = fixture(t), note = "review the sheets, then run verify (user's approval: resume as-is)";
  const code = await f.launch(f.args, { FAKE_SCENARIO: 'limit' }).done;
  assert.equal(code.code, 2, code.stderr); assert.match(code.stdout, /next: take over/);
  assert.deepEqual(loadState(f.root).pending, {});
  // The limit that run reported ("try again in 1 second") is remembered; let it pass so the next run starts.
  await until(() => Object.values(loadState(f.root).limits).every((limit) => limit.until * 1000 < Date.now()), 'the remembered limit never expired');
  const limited = await f.launch([...f.args, '--kind', 'image', '--mcp', 'blender', '--note', note], { FAKE_SCENARIO: 'limit', FAKE_SERVERS: '[{"name":"blender"}]', FAKE_CHECKPOINT: '1' }).done;
  assert.equal(limited.code, 2, limited.stderr);
  assert.match(limited.stdout, /next: images wait for Codex/); assert.match(limited.stdout, /resume after reset: bash /);
  const [entry] = Object.values(loadState(f.root).pending);
  assert.match(entry.checkpoint, /^1 step\(s\) done \(last: phase 1 textures\); next: phase 2 review sheets$/);
  assert.equal(entry.goal, 'Perform the fixture task.');
  const argv = words(entry.command).slice(2), resumed = parse(argv);
  assert.equal(resumed.resume, entry.thread); assert.equal(resumed.note, note); assert.deepEqual(resumed.mcp, ['blender']); assert.equal(resumed.kind, 'image');
  assert.equal(resumed.cd, path.resolve(readJson(path.join(entry.runDir, 'invocation.json')).cwd));
  const waiting = f.launch(['--wait']);
  assert.equal(loadState(f.root).reservations.length, 0);
  const woke = await waiting.done;
  assert.equal(woke.code, 0, woke.stderr);
  assert.ok(woke.stdout.includes(`note: ${note}`) && woke.stdout.includes(`resume: ${entry.command}`) && woke.stdout.includes('codex progress: 1 step(s)'), woke.stdout);
  const again = await f.launch(argv, { FAKE_SERVERS: '[{"name":"blender"}]' }).done;
  assert.equal(again.code, 0, again.stdout + again.stderr);
  const resumedCall = f.invocations().at(-1);
  assert.ok(resumedCall.args.some((arg) => arg.includes('Your last checkpoint is')));
  assert.equal(readJson(path.join(resumedCall.dir, 'checkpoint.json')).next, 'phase 2 review sheets');
  assert.deepEqual(loadState(f.root).pending, {});
  assert.equal((await f.launch(['--wait']).done).code, 1);
});
test('review patches larger than any memory buffer are written to disk', async (t) => {
  const f = fixture(t); initRepo(f.cwd);
  const run = await f.launch(f.args, { FAKE_EDIT_BYTES: String(20 * 1024 * 1024) }).done;
  assert.equal(run.code, 0, run.stdout + run.stderr);
  const dir = f.invocations()[0].dir;
  assert.equal(fs.existsSync(path.join(dir, 'snapshot-error.txt')), false);
  assert.ok(fs.statSync(path.join(dir, 'changes.patch')).size > 20 * 1024 * 1024);
  assert.match(run.stdout, /MB including binary content; for text only: git -C/);
});
test('task cleanup measures director usage from session transcripts since the first run', async (t) => {
  const f = fixture(t), config = path.join(f.dir, 'claude'), start = Date.now() - 60000;
  const runDir = reportFixture(f, 'measured', [done], result);
  writeJson(path.join(runDir, 'invocation.json'), { root: f.root, project: path.join(f.root, 'project'), claudeSession: 'director', startedAt: start });
  writeJson(path.join(runDir, 'meta.json'), { threadId: 'task', usage: { input_tokens: 50, cached_input_tokens: 20, output_tokens: 5 } });
  const message = (id, at, usage) => JSON.stringify({ type: 'assistant', timestamp: new Date(at).toISOString(), message: { id, usage } });
  const usage = { input_tokens: 3, cache_creation_input_tokens: 100, cache_read_input_tokens: 1000, output_tokens: 10 };
  fs.mkdirSync(path.join(config, 'projects', 'p', 'director', 'subagents'), { recursive: true });
  fs.writeFileSync(path.join(config, 'projects', 'p', 'director.jsonl'), [message('old', start - 1000, usage), message('a', start + 1000, usage), message('a', start + 1000, usage), '{"type":"user"}'].join('\n'));
  fs.writeFileSync(path.join(config, 'projects', 'p', 'director', 'subagents', 'agent.jsonl'), message('b', start + 2000, usage));
  const saved = { config: process.env.CLAUDE_CONFIG_DIR, session: process.env.CLAUDE_CODE_SESSION_ID };
  process.env.CLAUDE_CONFIG_DIR = config; delete process.env.CLAUDE_CODE_SESSION_ID;
  t.after(() => { for (const [key, name] of [['config', 'CLAUDE_CONFIG_DIR'], ['session', 'CLAUDE_CODE_SESSION_ID']]) if (saved[key] === undefined) delete process.env[name]; else process.env[name] = saved[key]; });
  await cleanup(f.root, '--thread', 'task');
  const [header, row] = fs.readFileSync(path.join(f.root, 'project', 'usage.tsv'), 'utf8').trim().split('\n').map((line) => line.split('\t'));
  const record = Object.fromEntries(header.map((name, i) => [name, row[i]]));
  assert.deepEqual([record.codex_input, record.claude_input, record.claude_cache_write, record.claude_cache_read, record.claude_output, record.claude_messages],
    ['50', '6', '200', '2000', '20', '2']);
  assert.equal(fs.existsSync(runDir), false);
});
test('simultaneous summaries preserve the longest limit and every ledger row', async (t) => {
  const f = fixture(t), at = now();
  const dirs = Array.from({ length: 12 }, (_, i) => reportFixture(f, `summary-${i}`,
    i < 2 ? [{ type: 'error', message: `usage limit: try again in ${i === 0 ? 60 : 5} minutes` }] : [done], i < 2 ? null : result));
  await Promise.all(dirs.map((dir, i) => new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [path.join(scripts, 'summarize.mjs'), dir, i < 2 ? '1' : '0', String(at), String(at), f.cwd], { env: f.env, stdio: ['ignore', 'ignore', 'pipe'] });
    let stderr = ''; child.stderr.on('data', (data) => { stderr += data; });
    child.on('error', reject); child.on('close', (code) => code === (i < 2 ? 2 : 0) ? resolve() : reject(new Error(`summary ${i} exit ${code}: ${stderr}`)));
  })));
  assert.equal(loadState(f.root).limits.account.until, at + 3600);
  const rows = fs.readFileSync(path.join(f.root, 'project', 'ledger.tsv'), 'utf8').trim().split('\n');
  assert.equal(rows.length, 13); assert.equal(rows.filter((row) => row.startsWith('date\t')).length, 1);
});
test('installer merges safely, is idempotent, and preserves invalid settings', async (t) => {
  const f = fixture(t), config = path.join(f.dir, 'claude'); fs.mkdirSync(config);
  const settings = path.join(config, 'settings.json'), legacy = 'Bash(bash ~/.claude/skills/codex-handoff/scripts/handoff.sh *)';
  fs.writeFileSync(settings, JSON.stringify({ theme: 'dark', permissions: { defaultMode: 'default', allow: ['Bash(git status)', legacy] }, autoMode: { allow: [
    '$defaults', 'Running the roblox-dev Codex handoff wrapper (old wording).', 'My local build rule', 'Running the roblox-dev Codex handoff wrapper (a duplicate).',
  ] } }));
  await Promise.all(Array.from({ length: 6 }, () => new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [path.join(scripts, 'install.mjs')], { env: { ...f.env, CLAUDE_CONFIG_DIR: config }, stdio: ['ignore', 'ignore', 'pipe'] });
    let stderr = ''; child.stderr.on('data', (data) => { stderr += data; });
    child.on('close', (code) => code === 0 ? resolve() : reject(new Error(`install exit ${code}: ${stderr}`)));
  })));
  const first = fs.readFileSync(settings, 'utf8'), parsed = JSON.parse(first);
  assert.equal(parsed.theme, 'dark'); assert.equal(parsed.permissions.defaultMode, 'default');
  assert.deepEqual(parsed.permissions.allow, ['Bash(git status)', legacy, 'Bash(bash ~/.claude/skills/roblox-dev/scripts/codex/handoff.sh *)']);
  assert.equal(parsed.autoMode.allow.length, 3); assert.equal(parsed.autoMode.allow[2], 'My local build rule');
  assert.match(parsed.autoMode.allow[1], /^Running the roblox-dev Codex handoff wrapper \(bash ~\/\.claude\/skills\/roblox-dev\/scripts\/codex\/handoff\.sh \.\.\.\)/);
  assert.equal(spawnSync(process.execPath, [path.join(scripts, 'install.mjs')], { env: { ...f.env, CLAUDE_CONFIG_DIR: config } }).status, 0);
  assert.equal(fs.readFileSync(settings, 'utf8'), first);
  fs.writeFileSync(settings, '{invalid');
  assert.equal(spawnSync(process.execPath, [path.join(scripts, 'install.mjs')], { env: { ...f.env, CLAUDE_CONFIG_DIR: config } }).status, 1);
  assert.equal(fs.readFileSync(settings, 'utf8'), '{invalid');
});
test('snapshot includes pre-existing untracked content without changing the index', (t) => {
  const f = fixture(t); initRepo(f.cwd);
  fs.writeFileSync(path.join(f.cwd, 'tracked.txt'), 'user staged\n'); git(f.cwd, ['add', 'tracked.txt']);
  fs.writeFileSync(path.join(f.cwd, 'tracked.txt'), 'user unstaged\n'); fs.writeFileSync(path.join(f.cwd, 'existing.txt'), 'before\n');
  const index = fs.readFileSync(path.join(f.cwd, '.git', 'index'));
  const before = snapshot(f.cwd, f.root, 'before');
  fs.writeFileSync(path.join(f.cwd, 'existing.txt'), 'after  \n');
  finishSnapshot(f.cwd, f.root, before);
  const patch = fs.readFileSync(path.join(f.root, 'changes.patch'), 'utf8');
  assert.match(patch, /-before\n\+after  \n/); assert.doesNotMatch(patch, /user unstaged/);
  assert.deepEqual(fs.readFileSync(path.join(f.cwd, '.git', 'index')), index);
});
test('same checkout refuses overlap; cancellation targets only the owned process tree', async (t) => {
  const f = fixture(t), childFile = path.join(f.dir, 'child.pid');
  const first = f.launch(f.args, { FAKE_DELAY: '20000', FAKE_CHILD: childFile });
  await until(() => f.invocations().length === 1 && fs.existsSync(childFile), 'first run did not start');
  const second = await f.launch(f.args).done; assert.equal(second.code, 75, second.stderr); assert.equal(f.invocations().length, 1);
  const runDir = f.invocations()[0].dir;
  const cancelled = await f.launch(['--cancel', runDir]).done; assert.equal(cancelled.code, 0, cancelled.stderr);
  const stopped = await first.done; assert.equal(stopped.code, 4, stopped.stderr); assert.match(stopped.stdout, /CANCELLED/);
  assert.equal(alive(Number(fs.readFileSync(childFile, 'utf8'))), false);
  assert.equal(loadState(f.root).reservations.length, 0);
});
test('independent worktrees run concurrently and retain reviewable results', async (t) => {
  const f = fixture(t); initRepo(f.cwd);
  const first = f.launch([...f.args, '--worktree'], { FAKE_DELAY: '1500', FAKE_EDIT: 'output.txt' });
  const second = f.launch([...f.args, '--worktree'], { FAKE_DELAY: '1500', FAKE_EDIT: 'output.txt' });
  await until(() => f.invocations().length === 2, 'both independent workers did not start');
  const calls = f.invocations(); assert.notEqual(calls[0].cwd, calls[1].cwd);
  for (const completed of await Promise.all([first.done, second.done])) assert.equal(completed.code, 0, completed.stderr);
  assert.equal(fs.existsSync(path.join(f.cwd, 'output.txt')), false);
  for (const call of calls) { assert.equal(fs.readFileSync(path.join(call.cwd, 'output.txt'), 'utf8'), 'after\n'); assert.match(fs.readFileSync(path.join(call.dir, 'changes.patch'), 'utf8'), /output.txt/); }
});
test('app resources and resumed threads are exclusive across separate directories', async (t) => {
  const f = fixture(t), other = path.join(f.dir, 'other'); fs.mkdirSync(other);
  for (const [i, option] of [['--resource', 'blender'], ['--resume', 'same-thread']].entries()) {
    const hold = path.join(f.dir, `hold-${i}`);
    const first = f.launch([...f.args, ...option], { FAKE_HOLD: hold });
    const expected = f.invocations().length + 1;
    await until(() => f.invocations().length >= expected, 'resource owner did not start');
    const second = await f.launch(['--brief', f.brief, '--cd', other, ...option]).done;
    fs.writeFileSync(hold, '');
    assert.equal(second.code, 75, second.stderr); assert.equal((await first.done).code, 0);
  }
});
test('successful diagnostic text never triggers model replay; actual model failure falls back; capacity does not', async (t) => {
  const f = fixture(t);
  const good = await f.launch(f.args, { FAKE_SCENARIO: 'mentions-error' }).done;
  assert.equal(good.code, 0, good.stderr); assert.equal(f.invocations().length, 1);
  const fallback = await f.launch(f.args, { FAKE_SCENARIO: 'model-missing' }).done;
  assert.equal(fallback.code, 0, fallback.stderr); assert.equal(f.invocations().length, 3);
  const busy = await f.launch(f.args, { FAKE_SCENARIO: 'capacity' }).done;
  assert.equal(busy.code, 71, busy.stdout); assert.match(busy.stdout, /CODEX AT CAPACITY/); assert.match(busy.stdout, /next: take over/);
  assert.equal(f.invocations().length, 4);
});
test('timeout stops the worker and reports a timeout instead of success', async (t) => {
  const f = fixture(t);
  const timed = await f.launch([...f.args, '--timeout-min', '0.01'], { FAKE_DELAY: '20000' }).done;
  assert.equal(timed.code, 3, timed.stderr); assert.match(timed.stdout, /TIMED OUT/); assert.equal(loadState(f.root).reservations.length, 0);
});
test('cleanup cannot delete active resumes; prune keeps waiting jobs and drops stale bookkeeping', async (t) => {
  const f = fixture(t), runDir = reportFixture(f, 'old', [done], result);
  writeJson(path.join(runDir, 'meta.json'), { threadId: 'thread', usage: {} });
  const token = crypto.randomUUID();
  await reserve(f.root, { token, pid: process.pid, childPid: null, runDir, paths: [], resources: ['thread:thread'], thread: 'thread' });
  await assert.rejects(cleanup(f.root, '--thread', 'thread'), /active/);
  const old = new Date(Date.now() - 10 * 86400000); fs.utimesSync(runDir, old, old);
  await cleanup(f.root, '--prune', '3'); assert.ok(fs.existsSync(runDir));
  await release(f.root, token);
  // A waiting job survives the prune however old; a wait whose run is gone, an idle thread and an expired limit do not.
  const queued = reportFixture(f, 'queued', [], null);
  writeJson(path.join(queued, 'meta.json'), { status: 'QUEUED', threadId: null, usage: {} }); fs.utimesSync(queued, old, old);
  const crashed = reportFixture(f, 'crashed', [], null); fs.utimesSync(crashed, old, old);   // no meta.json, no reservation
  const fresh = reportFixture(f, 'starting', [], null);                                      // just created, not yet reserved
  const probe = reportFixture(f, 'probe', [], null); writeJson(path.join(probe, 'meta.json'), { status: 'READY', threadId: 'probe-thread', usage: {} });
  fs.writeFileSync(path.join(f.root, 'project', 'LAST_RUN'), `${probe}\n`);                  // an earlier wrapper's pointer
  const state = loadState(f.root);
  state.pending = { [queued]: { runDir: queued, until: now(), command: 'x' }, gone: { runDir: path.join(f.root, 'project', 'missing'), until: now(), command: 'y' } };
  state.threads = { idle: { cwd: f.cwd, updated: Date.now() - 40 * 86400000 }, recent: { cwd: f.cwd, updated: Date.now() } };
  state.limits = { expired: { until: now() - 60 } };
  writeJson(path.join(f.root, 'state.json'), state);
  await cleanup(f.root, '--prune', '3');
  const after = loadState(f.root);
  assert.ok(fs.existsSync(queued)); assert.deepEqual(Object.keys(after.pending), [queued]);
  assert.deepEqual(Object.keys(after.threads), ['recent']); assert.deepEqual(after.limits, {});
  assert.equal(fs.existsSync(runDir), false); assert.equal(fs.existsSync(crashed), false); assert.ok(fs.existsSync(fresh));
  assert.equal(fs.existsSync(probe), false); assert.equal(fs.existsSync(path.join(f.root, 'project', 'LAST_RUN')), false);
});
test('overlapping additional writable roots are rejected', async (t) => {
  const f = fixture(t), nested = path.join(f.cwd, 'nested'); fs.mkdirSync(nested);
  await reserve(f.root, { token: 'a', pid: process.pid, runDir: f.root, paths: [f.cwd], resources: [] });
  await assert.rejects(reserve(f.root, { token: 'b', pid: process.pid, runDir: f.root, paths: [nested], resources: [] }), /busy/);
  await release(f.root, 'a');
});
test('MCP is disabled with a valid inert transport by default and enabled servers are locked', async (t) => {
  const f = fixture(t), servers = JSON.stringify([{ name: 'blender' }, { name: 'host-tool' }]);
  const plain = await f.launch(f.args, { FAKE_SERVERS: servers }).done;
  assert.equal(plain.code, 0, plain.stderr);
  const args = f.invocations()[0].args;
  assert.ok(args.includes('mcp_servers.blender={command="__codex_handoff_disabled__",enabled=false}'));
  assert.ok(args.includes('mcp_servers.host-tool={command="__codex_handoff_disabled__",enabled=false}'));
  const hold = path.join(f.dir, 'hold');
  const first = f.launch([...f.args, '--mcp', 'blender'], { FAKE_SERVERS: servers, FAKE_HOLD: hold });
  await until(() => f.invocations().length === 2, 'MCP owner did not start');
  assert.ok(f.invocations()[1].args.includes('mcp_servers.blender.enabled=true'));
  const other = path.join(f.dir, 'other'); fs.mkdirSync(other);
  const second = await f.launch(['--brief', f.brief, '--cd', other, '--resource', 'blender'], { FAKE_SERVERS: servers }).done;
  fs.writeFileSync(hold, '');
  assert.equal(second.code, 75, second.stderr); assert.equal((await first.done).code, 0);
});
test('readiness probes cache by configuration and model, and leave no run directory', async (t) => {
  const f = fixture(t);
  assert.equal((await f.launch(['--check', '--cd', f.cwd]).done).code, 0);
  const cached = await f.launch(['--check', '--cd', f.cwd]).done;
  assert.equal(cached.code, 0); assert.match(cached.stdout, /cached model probe/); assert.match(cached.stdout, /open handoffs: none/);
  assert.equal(f.invocations().length, 1);
  assert.equal((await f.launch(['--check', '--cd', f.cwd, '--model', 'different-model']).done).code, 0);
  assert.equal(f.invocations().length, 2);
  assert.deepEqual(f.runs(), []);
});
test('dirty source worktrees and known resume-directory mismatches are refused', async (t) => {
  const f = fixture(t); initRepo(f.cwd); fs.writeFileSync(path.join(f.cwd, 'uncommitted.txt'), 'user work');
  const worktree = await f.launch([...f.args, '--worktree']).done;
  assert.equal(worktree.code, 64, worktree.stderr); assert.equal(f.invocations().length, 0); assert.deepEqual(f.runs(), []);
  const first = await f.launch(f.args).done; assert.equal(first.code, 0, first.stderr);
  const thread = Object.keys(loadState(f.root).threads)[0], other = path.join(f.dir, 'other'); fs.mkdirSync(other);
  const resume = await f.launch(['--brief', f.brief, '--cd', other, '--resume', thread]).done;
  assert.equal(resume.code, 64, resume.stderr); assert.equal(f.invocations().length, 1);
});
test('resume preserves sandbox choice and uses portable writable-root overrides', async (t) => {
  const f = fixture(t), extra = path.join(f.dir, 'extra writable'); fs.mkdirSync(extra);
  const resumed = await f.launch([...f.args, '--resume', 'external-thread', '--sandbox', 'workspace-write', '--add-dir', extra]).done;
  assert.equal(resumed.code, 0, resumed.stderr);
  const args = f.invocations()[0].args;
  assert.ok(args.includes('sandbox_mode="workspace-write"'));
  const config = args.find((arg) => arg.startsWith('sandbox_workspace_write.writable_roots='));
  const roots = JSON.parse(config.slice(config.indexOf('=') + 1));
  assert.ok(roots.includes(extra.replaceAll('\\', '/')));
  assert.ok(roots.every((root) => !root.includes('\\')));
});

test('usage is read live without a model turn, falls back to the session log, and stops the app server', async (t) => {
  const f = fixture(t), appLog = path.join(f.dir, 'app.log');
  f.setUsage({ primary: 40, secondary: 5 });
  const live = await f.launch(['--usage'], { FAKE_APP_LOG: appLog }).done;
  assert.equal(live.code, 0, live.stderr);
  assert.match(live.stdout, /codex usage \(live, plus plan\): 5h window 40% used, resets .*; weekly 5% used/);
  assert.match(live.stdout, /room: 3 more runs now \(cap 3\)/);
  assert.deepEqual(f.invocations(), []);
  const pid = Number(fs.readFileSync(appLog, 'utf8').trim());
  await until(() => !alive(pid), 'the app server outlived the usage read');
  fs.rmSync(path.join(f.dir, 'usage.json'));
  const day = path.join(f.codexHome, 'sessions', '2026', '10', '29'); fs.mkdirSync(day, { recursive: true });
  const at = new Date().toISOString(), reset = now() + 7200;
  fs.writeFileSync(path.join(day, 'rollout-2026-10-29T01-00-00-x.jsonl'), [
    JSON.stringify({ timestamp: at, type: 'event_msg', payload: { type: 'token_count', rate_limits: { primary: { used_percent: 55, window_minutes: 300, resets_at: reset }, secondary: { used_percent: 9, window_minutes: 10080, resets_at: reset + 86400 } } } }),
    JSON.stringify({ timestamp: at, type: 'event_msg', payload: { type: 'token_count', rate_limits: null } })].join('\n'));
  const logged = await f.launch(['--usage']).done;
  assert.match(logged.stdout, /codex usage \(session log of .*\): 5h window 55% used/);
  assert.match(logged.stdout, /room: 3 more runs now/);
  const saved = process.env.CODEX_HOME; process.env.CODEX_HOME = f.codexHome;
  t.after(() => { if (saved === undefined) delete process.env.CODEX_HOME; else process.env.CODEX_HOME = saved; });
  assert.equal(readLogged().primary.used, 55);
});
test('room counts the measured run cost, active runs, resets and the cap', () => {
  assert.deepEqual(runCost([]), { primary: { value: 10, measured: 0 }, secondary: { value: 2, measured: 0 } });
  const cost = runCost([{ primary: 4, secondary: 1 }, { primary: 6, secondary: 1 }, { primary: 8, secondary: 2 }, { primary: 30, secondary: 9, overlap: true }, { primary: null, secondary: 1 }]);
  assert.deepEqual(cost, { primary: { value: 6, measured: 3 }, secondary: { value: 1, measured: 4 } });
  const later = now() + 3600;
  const usage = (primary, secondary = 0, allowed = true) => normalize({ primary: { usedPercent: primary, resetsAt: later }, secondary: { usedPercent: secondary, resetsAt: later + 86400 } }, 'live', Date.now(), allowed);
  assert.equal(room(usage(70), 0, cost, 9), 5);      // 30% left at 6% a run
  assert.equal(room(usage(70), 2, cost, 9), 3);      // two runs already active
  assert.equal(room(usage(10, 98), 0, cost, 9), 2);  // the week binds
  assert.equal(room(usage(10), 0, cost, 3), 3);      // the cap binds
  assert.equal(room(usage(10, 0, false), 0, cost), 0);
  assert.equal(room(null, 1, cost, 3), 2);           // unknown usage: the cap alone
  assert.equal(normalize({ primary: { usedPercent: 99, resetsAt: now() - 5 } }, 'live', Date.now()).primary.used, 0);
  assert.equal(bindingReset(usage(97), 0, cost), later);
  assert.ok(Math.abs(bindingReset(usage(10), 3, cost) - now()) <= 1);
});
test('a launch without room is refused before it starts; image work is queued and --wait releases it', async (t) => {
  const f = fixture(t);
  f.setUsage({ primary: 95, reset: now() + 3 });
  const refused = await f.launch(f.args).done;
  assert.equal(refused.code, 2, refused.stdout); assert.match(refused.stderr, /no room for another Codex run[\s\S]*next: take over/);
  assert.deepEqual(f.invocations(), []); assert.deepEqual(f.runs(), []);
  const queued = await f.launch([...f.args, '--kind', 'image', '--note', 'icons for the shop']).done;
  assert.equal(queued.code, 2, queued.stderr); assert.match(queued.stdout, /QUEUED/); assert.match(queued.stdout, /--wait/);
  const [entry] = Object.values(loadState(f.root).pending);
  assert.equal(entry.thread, null); assert.match(entry.command, /--kind image/);
  const listed = await f.launch(['--list']).done;
  assert.match(listed.stdout, /0 running, 1 waiting/); assert.match(listed.stdout, /waiting .* queued, due/);
  f.setUsage({ primary: 10 });
  const woke = await f.launch(['--wait']).done;
  assert.equal(woke.code, 0, woke.stderr); assert.match(woke.stdout, /note: icons for the shop/); assert.ok(woke.stdout.includes(`launch: ${entry.command}`));
  const started = await f.launch(words(entry.command).slice(2)).done;
  assert.equal(started.code, 0, started.stdout + started.stderr);
  assert.deepEqual(loadState(f.root).pending, {});
  assert.equal(fs.existsSync(entry.runDir), false);
  assert.ok(f.invocations()[0].args.some((arg) => arg.includes('at most 5 reference images')));
});
test('parallel launches never overshoot the room', async (t) => {
  const f = fixture(t), hold = path.join(f.dir, 'hold');
  f.setUsage({ primary: 75 });   // 25% left at the default 10% a run: room for two
  const launches = ['a', 'b', 'c'].map((name) => { const dir = path.join(f.dir, name); fs.mkdirSync(dir); return f.launch(['--brief', f.brief, '--cd', dir], { FAKE_HOLD: hold }); });
  await until(() => f.invocations().length >= 2, 'two runs did not start');
  const refused = await Promise.race(launches.map((launch) => launch.done));
  assert.equal(refused.code, 2, refused.stderr); assert.match(refused.stderr, /no room/);
  fs.writeFileSync(hold, '');
  const codes = (await Promise.all(launches.map((launch) => launch.done))).map((outcome) => outcome.code).sort();
  assert.deepEqual(codes, [0, 0, 2]); assert.equal(f.invocations().length, 2);
});
test('a run measures its share of the usage windows', async (t) => {
  const f = fixture(t);
  f.setUsage({ primary: 10, secondary: 2 });
  const measured = await f.launch(f.args, { FAKE_USAGE_AFTER: JSON.stringify({ primary: 18, secondary: 3 }) }).done;
  assert.equal(measured.code, 0, measured.stderr);
  assert.match(measured.stdout, /codex usage: 5h window 10% -> 18%, weekly 2% -> 3%/);
  const sample = loadState(f.root).samples.at(-1);
  assert.deepEqual([sample.primary, sample.secondary, sample.overlap, sample.kind], [8, 1, false, 'code']);
});
test('the summary tells Claude to take over code and to keep images with Codex', async (t) => {
  const f = fixture(t), at = now(), failed = [{ type: 'thread.started', thread_id: 'thread-a' }, { type: 'turn.failed', error: { message: 'tool crashed' } }];
  const text = async (name, events, options, exit = 1) => (await summarize(reportFixture(f, name, events, null, options), exit, at, at, f.cwd)).text;
  assert.match(await text('code', failed), /^next: take over: finish the brief yourself/m);
  assert.match(await text('image', failed, { invocation: { kind: 'image' } }), /^next: images stay with Codex/m);
  assert.match(await text('completed', [done], { rawResult: JSON.stringify(result) }, 0), /^next: review against the brief/m);
  // A run that generated images is image work even when launched as code.
  const saved = process.env.CODEX_HOME; process.env.CODEX_HOME = f.codexHome;
  t.after(() => { if (saved === undefined) delete process.env.CODEX_HOME; else process.env.CODEX_HOME = saved; });
  fs.mkdirSync(path.join(f.codexHome, 'generated_images', 'thread-b'), { recursive: true });
  fs.writeFileSync(path.join(f.codexHome, 'generated_images', 'thread-b', 'ig_1.png'), 'png');
  assert.match(await text('generated', [{ type: 'thread.started', thread_id: 'thread-b' }, { type: 'turn.failed', error: { message: 'x' } }]), /^next: images stay with Codex/m);
  assert.match(nextStep('CODEX USAGE LIMIT', true), /--wait/);
  assert.match(nextStep('NEEDS REVIEW', false), /finish whatever is missing yourself/);
  assert.equal(nextStep('READY', false), '');
});
test('clean removes runs, image originals and integrated worktrees, and refuses work that is not integrated', async (t) => {
  const f = fixture(t); initRepo(f.cwd);
  const first = await f.launch([...f.args, '--worktree'], { FAKE_EDIT: 'output.txt', FAKE_IMAGES: '1' }).done;
  assert.equal(first.code, 0, first.stderr);
  const call = f.invocations()[0], thread = Object.keys(loadState(f.root).threads)[0];
  const images = path.join(f.codexHome, 'generated_images', thread);
  assert.ok(fs.existsSync(images)); assert.match(first.stdout, /next: review against the brief/);
  const refused = await f.launch(['--clean', thread]).done;
  assert.equal(refused.code, 4, refused.stdout); assert.match(refused.stderr, /clean refused, nothing removed[\s\S]*output\.txt/);
  assert.ok(fs.existsSync(call.cwd) && fs.existsSync(call.dir) && fs.existsSync(images));
  // Integrated as `git apply` writes it under core.autocrlf: CRLF on disk, the same content to Git.
  git(f.cwd, ['config', 'core.autocrlf', 'true']);
  fs.writeFileSync(path.join(f.cwd, 'output.txt'), 'after\r\n');
  const cleaned = await f.launch(['--clean', thread]).done;
  assert.equal(cleaned.code, 0, cleaned.stderr); assert.match(cleaned.stdout, /removed 1 run dir\(s\), 1 image-original folder\(s\), 1 of 1 worktree\(s\)/);
  assert.ok(!fs.existsSync(call.cwd) && !fs.existsSync(call.dir) && !fs.existsSync(images));
  assert.doesNotMatch(git(f.cwd, ['worktree', 'list']), /worktrees/);
  fs.rmSync(path.join(f.cwd, 'output.txt'));
  const second = await f.launch([...f.args, '--worktree'], { FAKE_EDIT: 'other.txt' }).done;
  assert.equal(second.code, 0, second.stderr);
  const discarded = await f.launch(['--clean', f.invocations()[1].dir, '--discard']).done;
  assert.equal(discarded.code, 0, discarded.stderr);
  assert.ok(!fs.existsSync(f.invocations()[1].cwd)); assert.deepEqual(f.runs(), []);
});
test('--check lists every open handoff with the command for each choice', async (t) => {
  const f = fixture(t), hold = path.join(f.dir, 'hold'), busyDir = path.join(f.dir, 'busy'); fs.mkdirSync(busyDir);
  f.setUsage({ primary: 10 });
  assert.equal((await f.launch(f.args, { FAKE_SCENARIO: 'fail' }).done).code, 1);
  const running = f.launch(['--brief', f.brief, '--cd', busyDir], { FAKE_HOLD: hold });
  await until(() => f.invocations().length === 2, 'the held run did not start');
  f.setUsage({ primary: 99 });
  assert.equal((await f.launch([...f.args, '--kind', 'image']).done).code, 2);
  const check = await f.launch(['--check', '--cd', f.cwd]).done;
  fs.writeFileSync(hold, '');
  assert.equal(check.code, 0, check.stderr);
  assert.match(check.stdout, /open handoffs: 1 running, 1 waiting, 1 finished but not cleaned, 0 leftover worktree\(s\)\. Ask the user/);
  for (const pattern of [/running .* code /, /  stop: bash .* --cancel "/, /waiting .* queued, due /, /  launch: bash /, /finished .* FAILED /, /  when done: bash .* --clean /]) assert.match(check.stdout, pattern);
  assert.match(check.stdout, /room: 0 more runs now/);
  assert.equal((await running.done).code, 0);
});
test('the entry points run when the skill is reached through a junction or symlink, as installs are', (t) => {
  const f = fixture(t), link = path.join(f.dir, 'linked-scripts');
  fs.symlinkSync(scripts, link, 'junction');
  try {
    const help = spawnSync(process.execPath, [path.join(link, 'handoff.mjs'), '--help'], { encoding: 'utf8', env: f.env });
    assert.equal(help.status, 0, help.stderr); assert.match(help.stdout, /^Usage: handoff\.sh/);
    const list = spawnSync(process.execPath, [path.join(link, 'handoff.mjs'), '--list'], { encoding: 'utf8', env: f.env });
    assert.equal(list.status, 0, list.stderr); assert.match(list.stdout, /open handoffs: none/);
  } finally {
    // Unlink only the link, never what it points at.
    try { fs.unlinkSync(link); } catch { fs.rmdirSync(link); }
  }
});
test('prompts carry the skill rules; image runs also carry the image rules', async (t) => {
  const f = fixture(t);
  assert.equal((await f.launch(f.args).done).code, 0);
  assert.equal((await f.launch([...f.args, '--kind', 'image']).done).code, 0);
  const [plain, image] = f.invocations().map((call) => call.args[1]);
  assert.match(plain, /roblox-dev skill at .*: its SKILL\.md rules/); assert.doesNotMatch(plain, /reference images/);
  assert.match(image, /at most 5 reference images[\s\S]*characters\.md[\s\S]*no-gore\.md/);
  assert.match(plain, /without a byte-order mark/);
});
