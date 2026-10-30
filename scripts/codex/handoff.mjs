import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn, spawnSync } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import { fileURLToPath } from 'node:url';
import { activeRuns, alive, atomicWrite, canonical, inside, isMain, liveReservations, loadState, release, reserve,
  readJson, safeRemove, stateFile, updateReservation, withLock, writeJson } from './state.mjs';
import { checkout, finishSnapshot, git, snapshot } from './snapshot.mjs';
import { queueRun, summarize } from './summarize.mjs';
import { cleanup, describePending, openHandoffs, removeWorktree } from './cleanup.mjs';
import { bindingReset, describeUsage, readLive, readLogged, room, runCost, runCosts, when } from './usage.mjs';

const HELP = `Usage: handoff.sh --brief FILE --cd DIR [--kind code|image] [--queue] [--resume THREAD] [--worktree]
  --check [--probe]             CLI, login, MCP, model (probe cached 12 h), usage and every open handoff
  --usage / --list              Codex usage and room now (no model turn) / open handoffs only
  --image FILE / --add-dir DIR  repeatable references / shared writable roots (not locked)
  --mcp NAME / --resource NAME  repeatable MCP opt-in / exclusive app lock
  --sandbox MODE                danger-full-access (default), workspace-write, read-only
  --model MODEL / --effort LEVEL / --timeout-min N / --name SLUG
  --note TEXT                   director's next steps, replayed with a waiting job
  --wait                        block until a waiting job has room, then print its command
  --cancel RUN_DIR              stop a running handoff's process tree
  --clean THREAD|RUN_DIR [--discard] [--claude-tokens N]
                                after acceptance or takeover: log usage; delete its runs, image
                                originals and integrated worktree (--discard: any worktree, and
                                delivered files that still name the run directory)
  --ignore-limit                launch despite low usage or a remembered limit
Exit: 0 ok, 1 failed, 2 usage limit/no room/queued, 3 timeout, 4 blocked/needs review,
      64 arguments, 69 missing CLI, 70 login, 71 no usable model/at capacity, 75 busy`;
const fail = (message, exitCode = 64) => { const error = new Error(message); error.exitCode = exitCode; throw error; };
const hash = (value) => crypto.createHash('sha256').update(value).digest('hex').slice(0, 16);
const winpath = (value) => {
  if (process.platform === 'win32' && /^\/[a-z](?:\/|$)/i.test(value)) return `${value[1]}:${value.slice(2) || '/'}`;
  return value;
};
const stamp = () => new Date().toISOString().replace(/[-:]/g, '').replace('T', '-').slice(0, 15);
// The skill this wrapper ships in; Codex is pointed at its rules.
const skillRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
export function parse(argv) {
  const o = { cd: process.cwd(), kind: 'code', sandbox: process.env.CODEX_HANDOFF_SANDBOX || 'danger-full-access',
    model: process.env.CODEX_HANDOFF_MODEL || '', effort: process.env.CODEX_HANDOFF_EFFORT || '',
    timeoutMin: 180, image: [], addDir: [], mcp: [], resource: [] };
  const flags = { '--check': 'check', '--probe': 'probe', '--usage': 'usage', '--list': 'list', '--wait': 'wait', '--worktree': 'worktree',
    '--queue': 'queue', '--discard': 'discard', '--ignore-limit': 'ignoreLimit', '--help': 'help', '-h': 'help' };
  const values = { '--brief': 'brief', '--cd': 'cd', '--resume': 'resume', '--kind': 'kind', '--image': 'image', '--add-dir': 'addDir',
    '--sandbox': 'sandbox', '--model': 'model', '--effort': 'effort', '--timeout-min': 'timeoutMin', '--name': 'name',
    '--cancel': 'cancel', '--clean': 'clean', '--claude-tokens': 'claudeTokens', '--mcp': 'mcp', '--resource': 'resource', '--note': 'note' };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (flags[arg]) o[flags[arg]] = true;
    else if (values[arg]) {
      const value = argv[++i];
      if (!value || value.startsWith('--')) fail(`Missing value for ${arg}`);
      const key = values[arg];
      if (Array.isArray(o[key])) o[key].push(value); else o[key] = value;
    } else fail(`Unknown argument: ${arg}`);
  }
  if (!['read-only', 'workspace-write', 'danger-full-access'].includes(o.sandbox)) fail('Invalid sandbox mode');
  if (!['code', 'image'].includes(o.kind)) fail('--kind must be code or image');
  o.timeoutMin = Number(o.timeoutMin);
  if (!Number.isFinite(o.timeoutMin) || o.timeoutMin <= 0 || o.timeoutMin > 1440) fail('--timeout-min must be > 0 and <= 1440');
  if (o.claudeTokens !== undefined && (!Number.isFinite(Number(o.claudeTokens)) || Number(o.claudeTokens) < 0)) fail('Invalid --claude-tokens');
  if ([o.check, o.usage, o.list, o.wait, o.cancel, o.clean, o.brief].filter(Boolean).length > 1) fail('Choose one of --brief, --check, --usage, --list, --wait, --cancel, --clean');
  if (o.discard && !o.clean) fail('--discard goes with --clean');
  if (o.note && o.note.length > 1500) fail('--note must be at most 1500 characters; point to a file for more');
  if (o.worktree && o.resume) fail('Resume with --cd pointing to the original worktree');
  for (const key of ['cd', 'brief', 'cancel']) if (o[key]) o[key] = path.resolve(winpath(o[key]));
  // --clean takes a thread id or a run directory.
  if (o.clean && /[\\/]/.test(o.clean)) o.clean = path.resolve(winpath(o.clean));
  for (const key of ['image', 'addDir']) o[key] = o[key].map((p) => path.resolve(winpath(p)));
  for (const name of [...o.mcp, ...o.resource]) if (!/^[A-Za-z0-9_.:-]+$/.test(name)) fail(`Invalid resource/server name: ${name}`);
  return o;
}
function cliCommand(args) {
  const explicit = process.env.CODEX_HANDOFF_CLI;
  if (explicit) return /\.m?js$/i.test(explicit) ? [process.execPath, [explicit, ...args]] : [explicit, args];
  if (process.platform === 'win32') {
    if (!process.env.CODEX_HANDOFF_BASH) fail('On Windows launch handoff.sh from Git Bash', 69);
    // Arguments are positional data, never interpolated shell code.
    return [process.env.CODEX_HANDOFF_BASH, ['-c', 'exec codex "$@"', 'handoff-codex', ...args]];
  }
  return ['codex', args];
}
function cliSync(args, cwd) {
  const [command, argv] = cliCommand(args);
  return spawnSync(command, argv, { cwd, encoding: 'utf8', timeout: 30000, windowsHide: true });
}
function configFiles(cwd) {
  const files = [path.join(process.env.CODEX_HOME || path.join(os.homedir(), '.codex'), 'config.toml')];
  const parents = [];
  for (let dir = cwd;; dir = path.dirname(dir)) { parents.push(dir); if (dir === path.dirname(dir)) break; }
  files.push(...parents.reverse().map((dir) => path.join(dir, '.codex', 'config.toml')));
  return [...new Set(files)].filter((file) => fs.existsSync(file));
}
export function configInfo(cwd, model, effort) {
  const files = configFiles(cwd), text = files.map((file) => fs.readFileSync(file, 'utf8')), servers = new Set();
  for (const content of text) for (const match of content.matchAll(/^\s*\[mcp_servers\.(?:"([A-Za-z0-9_-]+)"|'([A-Za-z0-9_-]+)'|([A-Za-z0-9_-]+))\]\s*(?:#.*)?$/gm)) servers.add(match[1] || match[2] || match[3]);
  const home = process.env.CODEX_HOME || path.join(os.homedir(), '.codex');
  return { servers: [...servers], accountKey: hash(path.resolve(home)), configKey: hash(JSON.stringify([files, text, model, effort,
    process.env.CODEX_HANDOFF_CLI || 'codex', process.env.CODEX_HANDOFF_FALLBACK_MODELS || ''])) };
}
// Live limits first (no model turn); the newest session-log snapshot when the account can't be read.
const readUsage = async () => (await readLive(cliCommand(['app-server']))) || readLogged();
async function usageReport(root, usage) {
  usage ??= await readUsage();
  let state;
  await withLock(root, () => { state = loadState(root); });
  return { usage, ...describeUsage(usage, activeRuns(state).length, runCosts(state.samples)) };
}
// Why another run of this kind can't start now, or null. Runs only under the state lock, so parallel launches can't overshoot.
function noRoom(state, usage, account, kind) {
  const cost = runCost(state.samples, kind), active = activeRuns(state).length;
  if (room(usage, active, cost) < 1) return { until: bindingReset(usage, active, cost), text: describeUsage(usage, active, runCosts(state.samples)).text };
  // Without a live read, a limit an earlier run reported still holds.
  const remembered = usage?.source === 'live' ? 0 : state.limits[account]?.until || 0;
  return remembered * 1000 > Date.now() ? { until: remembered, text: `Codex reported a usage limit until ${when(remembered)}` } : null;
}
function killTree(child) {
  if (!child?.pid || child.exitCode !== null) return;
  if (process.platform === 'win32') {
    const result = spawnSync('taskkill.exe', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true, encoding: 'utf8' });
    if (result.status !== 0 && alive(child.pid)) throw new Error(`Could not stop child ${child.pid}: ${result.stderr}`);
  } else {
    try { process.kill(-child.pid, 'SIGKILL'); } catch (error) { if (error.code !== 'ESRCH') throw error; }
  }
}
async function execute(root, runDir, token, args, cwd, timeoutMin) {
  const [command, argv] = cliCommand(args);
  const events = fs.openSync(path.join(runDir, 'events.jsonl'), 'w'), stderr = fs.openSync(path.join(runDir, 'stderr.log'), 'w');
  let child, timer, poll, reason = '', spawnError;
  const stop = (why) => { if (!reason) reason = why; try { killTree(child); } catch (error) { console.error(error.message); } };
  const interrupt = () => stop('cancelled');
  process.on('SIGINT', interrupt); process.on('SIGTERM', interrupt);
  try {
    child = spawn(command, argv, { cwd, stdio: ['ignore', events, stderr], windowsHide: true, detached: process.platform !== 'win32' });
    child.on('error', (error) => { spawnError = error; });
    const closed = new Promise((resolve) => child.on('close', (code) => resolve(code ?? 1)));
    await updateReservation(root, token, { childPid: child.pid });
    timer = setTimeout(() => stop('timeout'), timeoutMin * 60000);
    poll = setInterval(() => { if (fs.existsSync(path.join(runDir, 'cancel.json'))) stop('cancelled'); }, 200);
    const code = await closed;
    if (spawnError) fs.appendFileSync(path.join(runDir, 'stderr.log'), `${spawnError.message}\n`);
    return { code: reason === 'timeout' ? 124 : reason === 'cancelled' ? 130 : code, reason };
  } finally {
    clearTimeout(timer); clearInterval(poll);
    process.off('SIGINT', interrupt); process.off('SIGTERM', interrupt);
    fs.closeSync(events); fs.closeSync(stderr);
    await updateReservation(root, token, { childPid: null });
  }
}
function modelMissing(dir) {
  const events = fs.readFileSync(path.join(dir, 'events.jsonl'), 'utf8').split('\n').filter(Boolean).map((line) => {
    try { return JSON.parse(line); } catch { return {}; }
  });
  // Never replay a completed task or one that has begun tools/mutations.
  if (events.some((event) => event.type === 'turn.completed' ||
    ['command_execution', 'file_change', 'mcp_tool_call'].includes(event.item?.type))) return false;
  const diagnostics = events.filter((event) => ['error', 'turn.failed'].includes(event.type))
    .map((event) => event.message || event.error?.message || '').join('\n');
  return /model_not_found|model is not supported|model .{0,60}does not exist|access to (the )?model/i.test(
    diagnostics + '\n' + fs.readFileSync(path.join(dir, 'stderr.log'), 'utf8'));
}
async function withFallback(root, runDir, token, args, cwd, options, info) {
  let cached;
  await withLock(root, () => { cached = loadState(root).models[info.configKey]; });
  let model = options.model || (cached?.at > Date.now() - 86400000 ? cached.model : '');
  const tried = new Set();
  for (let attempt = 0; attempt < 4; attempt++) {
    for (const file of ['final.md', 'result.json']) fs.rmSync(path.join(runDir, file), { force: true });
    const result = await execute(root, runDir, token, [...args, ...(model ? ['-m', model] : [])], cwd, options.timeoutMin);
    atomicWrite(path.join(runDir, 'model.txt'), model || 'Codex config');
    if (!modelMissing(runDir) || result.reason) {
      if (model && result.code === 0) await withLock(root, () => {
        const state = loadState(root); state.models[info.configKey] = { model, at: Date.now() }; writeJson(stateFile(root), state);
      });
      return result;
    }
    for (const file of ['events.jsonl', 'stderr.log']) fs.copyFileSync(path.join(runDir, file), path.join(runDir, `attempt-${attempt + 1}-${file}`));
    tried.add(model);
    let candidates = process.env.CODEX_HANDOFF_FALLBACK_MODELS ? process.env.CODEX_HANDOFF_FALLBACK_MODELS.split(',').map((s) => s.trim()).filter(Boolean) : undefined;
    if (!candidates) {
      const catalog = cliSync(['debug', 'models']);
      try { candidates = JSON.parse(catalog.stdout).models.filter((m) => m.visibility === 'list').sort((a, b) => (a.priority ?? 99) - (b.priority ?? 99)).map((m) => m.slug); }
      catch { candidates = []; }
    }
    const next = candidates.find((m) => !tried.has(m));
    if (!next || attempt === 3) return result;
    fs.appendFileSync(path.join(runDir, 'fallback.txt'), `Model ${model || 'configured default'} unavailable; retrying ${next}\n`);
    model = next;
  }
}
// Holds no reservation, so other handoffs run normally while it waits; checks the account at most every 2 minutes.
async function waitForRoom(root) {
  let nextRead = 0;
  for (;;) {
    let entries;
    await withLock(root, () => { entries = Object.values(loadState(root).pending).filter((entry) => fs.existsSync(entry.runDir)); });
    if (!entries.length) fail('No waiting handoffs are recorded', 1);
    const due = entries.filter((entry) => entry.until * 1000 <= Date.now()).sort((a, b) => a.until - b.until);
    if (due.length && Date.now() >= nextRead) {
      const report = await usageReport(root);
      // Each waiting job needs room for its own kind; the costliest one due sets how many may start.
      const kinds = due.map((entry) => readJson(path.join(entry.runDir, 'invocation.json'))?.kind === 'image' ? 'image' : 'code');
      const free = Math.min(...kinds.map((kind) => report.room[kind]));
      if (free >= 1) {
        const ready = due.slice(0, free);
        console.log(['handoff: Codex has room again. This context survives /clear.',
          'Authorized: run each command unchanged; it repeats its original brief and scope. Anything new or outward still needs the user.',
          ...ready.map(describePending), report.text,
          ...(entries.length > ready.length ? [`${entries.length - ready.length} more waiting: start --wait again after launching these.`] : [])].join('\n'));
        return 0;
      }
      nextRead = Date.now() + 120000;
    }
    const soonest = Math.min(...entries.map((entry) => entry.until * 1000));
    await sleep(Math.min(60000, Math.max(1000, (due.length ? nextRead : soonest) - Date.now() + 1000)));
  }
}
async function cancel(root, dir) {
  await withLock(root, () => {
    if (!inside(root, dir)) fail('--cancel must name a run directory under the handoff home');
    const reservation = liveReservations(loadState(root)).find((r) => path.resolve(r.runDir) === dir);
    if (!reservation) fail('No active handoff owns that run directory', 75);
    if (!alive(reservation.pid)) fail('Supervisor exited but its child may still run; inspect the recorded child PID before stopping it manually', 75);
    writeJson(path.join(dir, 'cancel.json'), { requested: Date.now() });
    console.log(`handoff: cancellation requested for ${dir}`);
  });
}
// A launch without room: Claude takes over code; images and --queue wait as a queued job.
async function refuse(root, options, ctx, refusal) {
  if (options.kind !== 'image' && !options.queue) {
    fail(`no room for another Codex run\n${refusal.text}\nnext: take over: do this work yourself (or relaunch with --queue to wait for room)`, 2);
  }
  const runDir = fs.mkdtempSync(path.join(ctx.project, `${stamp()}-${(options.name || path.parse(options.brief).name).replace(/[^A-Za-z0-9._-]/g, '-').slice(0, 48)}-`));
  fs.copyFileSync(options.brief, path.join(runDir, 'brief.md'));
  const invocation = { root, project: ctx.project, cwd: ctx.source, accountKey: ctx.info.accountKey, kind: options.kind, queue: options.queue,
    worktree: options.worktree, brief: options.brief, resume: options.resume || null, mcp: options.mcp, resource: options.resource,
    addDir: options.addDir, image: options.image, sandbox: options.sandbox, model: options.model, effort: options.effort,
    timeoutMin: options.timeoutMin, name: options.name, note: options.note, startedAt: Date.now() };
  writeJson(path.join(runDir, 'invocation.json'), invocation);
  console.log(await queueRun(runDir, invocation, refusal.until, refusal.text));
  removeQueued(root, options.brief);
  return 2;
}
// A job launched from a queued directory no longer needs it.
function removeQueued(root, brief) {
  const dir = path.dirname(brief);
  if (inside(root, dir) && readJson(path.join(dir, 'meta.json'))?.status === 'QUEUED') safeRemove(root, dir);
}
async function run(root, options, ctx) {
  const { info, project } = ctx;
  let cwd = ctx.source;
  // The gate reads usage before anything is created; the reservation re-checks it under the lock.
  const usage = options.check ? null : await readUsage();
  if (!options.check && !options.ignoreLimit) {
    let refusal;
    await withLock(root, () => { refusal = noRoom(loadState(root), usage, info.accountKey, options.kind); });
    if (refusal) return refuse(root, options, ctx, refusal);
  }
  const name = (options.name || (options.check ? 'probe' : path.parse(options.brief).name)).replace(/[^A-Za-z0-9._-]/g, '-').slice(0, 48);
  const runDir = fs.mkdtempSync(path.join(project, `${stamp()}-${name}-`)), token = crypto.randomUUID();
  let claimed = false, worktree = null, before;
  try {
    if (options.worktree) {
      if (!checkout(cwd)) fail('--worktree requires a Git repository');
      const target = path.join(project, 'worktrees', path.basename(runDir));
      await withLock(root, () => {
        if (liveReservations(loadState(root)).some((run) => run.paths.some((dir) => dir === cwd || inside(dir, cwd) || inside(cwd, dir)))) fail('Source checkout is active; wait before creating a worktree', 75);
        if (git(cwd, ['status', '--porcelain', '--untracked-files=normal'])) fail('--worktree starts from HEAD and requires a clean source checkout; use a prepared worktree with --cd for uncommitted inputs');
        git(cwd, ['worktree', 'add', '--detach', target, 'HEAD']);
        worktree = target;
      });
      cwd = canonical(worktree);
    }
    const resources = [...new Set([...options.resource, ...options.mcp].map((n) => `app:${n.toLowerCase()}`).concat(options.resume ? [`thread:${options.resume}`] : [], options.check ? [`probe:${info.configKey}`] : []))];
    // Only the checkout is exclusive. --add-dir roots are shared output folders (each run writes its own files), so two
    // runs delivering to one folder can run together (seen 2026-10-29: locking Downloads refused a parallel launch).
    const paths = options.check ? [] : [cwd];
    const admit = options.check || options.ignoreLimit ? undefined : (state) => {
      const refusal = noRoom(state, usage, info.accountKey, options.kind);
      if (refusal) throw Object.assign(new Error(refusal.text), { exitCode: 2, refusal });
    };
    await reserve(root, { token, pid: process.pid, childPid: null, runDir, paths, resources, thread: options.resume || null }, admit);
    claimed = true;
    writeJson(path.join(runDir, 'invocation.json'), { root, project, cwd, source: ctx.source, ...info, sandbox: options.check ? 'read-only' : options.sandbox, probe: !!options.check, resume: options.resume || null, mcp: options.mcp,
      // Everything resumeCommand needs to rebuild this launch.
      kind: options.kind, queue: !!options.queue, brief: options.brief, resource: options.resource, addDir: options.addDir, image: options.image, model: options.model,
      effort: options.effort, timeoutMin: options.timeoutMin, name: options.name, note: options.note, usageBefore: usage,
      claudeSession: process.env.CLAUDE_CODE_SESSION_ID || null, startedAt: Date.now() });
    // A resume continues from the thread's latest checkpoint, so a limit or timeout loses at most one phase.
    const checkpoint = path.join(runDir, 'checkpoint.json');
    if (options.resume) {
      const previous = fs.readdirSync(project).filter((entry) => /^\d{8}-\d{6}-/.test(entry)).sort().reverse()
        .map((entry) => path.join(project, entry)).find((dir) => dir !== runDir && fs.existsSync(path.join(dir, 'checkpoint.json')) &&
          readJson(path.join(dir, 'meta.json'))?.threadId === options.resume);
      if (previous) fs.copyFileSync(path.join(previous, 'checkpoint.json'), checkpoint);
    }
    if (!options.check) {
      fs.copyFileSync(options.brief, path.join(runDir, 'brief.md'));
      if (checkout(cwd)) { before = snapshot(cwd, runDir, 'before'); atomicWrite(path.join(runDir, 'base.txt'), before); }
    }
    const lessons = path.join(project, 'LESSONS.md');
    const roblox = fs.existsSync(path.join(skillRoot, 'SKILL.md')) ? ` For Roblox work the roblox-dev skill at ${skillRoot} applies: its SKILL.md rules and the references the brief names.` : '';
    const images = options.kind === 'image' ? ` Image task: use the built-in image generator with at most 5 reference images per generation; save finals and any originals where the brief says, copying originals (never moving or editing them), and record each exact prompt; write prompts per ${path.join(skillRoot, 'references', 'characters.md')} and ${path.join(skillRoot, 'references', 'no-gore.md')}; if moderation blocks a prompt, reword it once within the brief's design, then report blocked.` : '';
    const prompt = options.check ? 'Reply with exactly the two letters "OK", without punctuation. Do not use tools.' :
      `Read ${path.join(runDir, 'brief.md')} and carry out the brief. Follow project AGENTS.md.${roblox}${fs.existsSync(lessons) ? ` Read standing lessons at ${lessons}.` : ''}${images} ` +
      `The working directory is ${cwd}. Keep scratch and review media in ${runDir}; it is deleted at cleanup, so anything a deliverable still needs afterwards (files your delivered scripts read or write, sources) goes beside the deliverables, never in it, and no deliverable names its path. ` +
      (fs.existsSync(checkpoint) ? `Your last checkpoint is ${checkpoint}; continue from it. ` : '') +
      `After each phase in the brief (or each major milestone), overwrite ${checkpoint} with JSON {"done":["finished and verified steps"],"next":"the next step","notes":"state a resume needs"}. ` +
      `Finish with a report under 250 words and write ${path.join(runDir, 'result.json')} as UTF-8 JSON without a byte-order mark: ` +
      '{"status":"completed|blocked|failed","verification":"checks run and results","reason":"remaining work or empty"}. ' +
      'Use completed only when every requirement and required verification is satisfied. A tool/sandbox failure that prevents finishing means blocked. Do not change setup, permissions, or sandbox to get around a failure.';
    const configs = ['-c', 'approval_policy="never"'];
    for (const server of info.servers) {
      const enabled = !options.check && options.mcp.includes(server);
      if (enabled) configs.push('-c', `mcp_servers.${server}.enabled=true`, '-c', `mcp_servers.${server}.default_tools_approval_mode="approve"`);
      // Replace the entire disabled table with a valid inert transport. Some
      // inventory entries are injected by the host rather than config.toml;
      // overriding only enabled would create an invalid transport for those.
      else configs.push('-c', `mcp_servers.${server}={command="__codex_handoff_disabled__",enabled=false}`);
    }
    if (options.effort) configs.push('-c', `model_reasoning_effort=${JSON.stringify(options.effort)}`);
    const writable = [runDir, ...options.addDir];
    // Forward slashes avoid JSON/TOML backslash escape drift through Windows shims.
    const configRoots = writable.map((dir) => dir.replaceAll('\\', '/'));
    const args = options.resume ? ['exec', 'resume', options.resume, prompt, '-c', `sandbox_mode=${JSON.stringify(options.sandbox)}`, '-c', `sandbox_workspace_write.writable_roots=${JSON.stringify(configRoots)}`] :
      ['exec', prompt, '-C', cwd, '-s', options.check ? 'read-only' : options.sandbox, ...writable.flatMap((dir) => ['--add-dir', dir])];
    args.push(...configs, '--skip-git-repo-check', '--json', '-o', path.join(runDir, 'final.md'));
    for (const image of options.image) args.push(`--image=${image}`);
    const start = Math.floor(Date.now() / 1000);
    console.log(`handoff: started\nrun dir: ${runDir}\nworking directory: ${cwd}`);
    const outcome = await withFallback(root, runDir, token, args, cwd, { ...options, timeoutMin: options.check ? 3 : options.timeoutMin }, info);
    if (before) {
      try { finishSnapshot(cwd, runDir, before); }
      catch (error) { atomicWrite(path.join(runDir, 'snapshot-error.txt'), error.message); }
    }
    const end = Math.floor(Date.now() / 1000);
    let usageAfter = null, overlapped = false;
    if (!options.check) {
      usageAfter = await readLive(cliCommand(['app-server']));
      await withLock(root, () => { overlapped = !!loadState(root).reservations.find((r) => r.token === token)?.overlap; });
    }
    const report = await summarize(runDir, outcome.code, start, end, cwd, { usageAfter, overlap: overlapped });
    console.log(report.text);
    if (report.exit === 0) for (const file of ['events.jsonl', 'stderr.log']) fs.rmSync(path.join(runDir, file), { force: true });
    if (options.check && report.exit === 0) {
      await withLock(root, () => { const state = loadState(root); state.probes[info.configKey] = { at: Date.now() }; writeJson(stateFile(root), state); });
      // A passed probe leaves nothing worth keeping.
      safeRemove(project, runDir);
    }
    if (!options.check) removeQueued(root, options.brief);
    return report.exit;
  } catch (error) {
    if (!claimed) {
      // Nothing ran: leave no run directory or worktree behind.
      if (worktree) removeWorktree(worktree, true);
      if (fs.existsSync(runDir)) safeRemove(project, runDir);
      if (error.refusal) return refuse(root, options, ctx, error.refusal);
    }
    throw error;
  } finally {
    if (claimed) await release(root, token);
  }
}
export async function main(argv = process.argv.slice(2)) {
  const options = parse(argv);
  if (options.help) { console.log(HELP); return 0; }
  if (Number(process.versions.node.split('.')[0]) < 20) fail('Node 20 or newer is required', 69);
  const root = path.resolve(winpath(process.env.CODEX_HANDOFF_HOME || path.join(os.homedir(), '.claude', 'codex-handoffs')));
  if (options.cancel) { await cancel(root, options.cancel); return 0; }
  if (options.clean) return cleanup(root, '--thread', options.clean, options.claudeTokens, { discard: options.discard });
  if (options.list) { console.log(await openHandoffs(root)); return 0; }
  if (options.wait) return waitForRoom(root);
  if (options.usage) { console.log((await usageReport(root)).text); return 0; }
  if (!options.check && !options.brief) fail(HELP);
  if (!fs.existsSync(options.cd) || !fs.statSync(options.cd).isDirectory()) fail('--cd directory does not exist');
  if (!options.check && (!fs.existsSync(options.brief) || !fs.statSync(options.brief).isFile())) fail('Brief file does not exist');
  for (const image of options.image) if (!fs.existsSync(image) || !fs.statSync(image).isFile()) fail(`Image does not exist: ${image}`);
  for (const dir of options.addDir) if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) fail(`Writable directory does not exist: ${dir}`);
  const version = cliSync(['--version']);
  if (version.error || version.status !== 0) fail('Codex CLI unavailable; install @openai/codex and put it on PATH', 69);
  if (cliSync(['login', 'status']).status !== 0) fail('Codex is not logged in; run codex login', 70);
  const source = canonical(checkout(options.cd) || options.cd);
  if (path.resolve(root) === path.resolve(source) || inside(source, root)) fail('CODEX_HANDOFF_HOME must be outside the working checkout to keep snapshots and scratch separate');
  const info = configInfo(source, options.model, options.effort);
  // Ask Codex for its effective server inventory: inline TOML, inherited config,
  // and disabled entries must not silently escape opt-in and resource locking.
  const inventory = cliSync(['mcp', 'list', '--json'], source);
  let enabled = [];
  try {
    if (inventory.status !== 0) throw new Error('inventory command failed');
    const servers = JSON.parse(inventory.stdout);
    if (!Array.isArray(servers) || servers.some((server) => typeof server.name !== 'string')) throw new Error('invalid inventory');
    info.servers = servers.map((server) => server.name);
    enabled = servers.filter((server) => server.enabled !== false).map((server) => server.name);
    if (info.servers.some((name) => !/^[A-Za-z0-9_-]+$/.test(name))) fail('MCP names must use letters, digits, underscores, or hyphens for CLI overrides');
  } catch (error) { if (error.exitCode) throw error; fail('Cannot discover effective MCP servers with codex mcp list --json; check the Codex configuration', 69); }
  info.configKey = hash(info.configKey + version.stdout.trim());
  if (options.resume) await withLock(root, () => {
    const saved = loadState(root).threads?.[options.resume];
    if (saved && saved.cwd !== source) fail(`Resume must use its original working directory: ${saved.cwd}`);
  });
  for (const name of options.mcp) if (!info.servers.includes(name)) fail(`MCP server ${name} not found in Codex configs; configure it once before launch`);
  const common = checkout(source) ? canonical(path.resolve(source, git(source, ['rev-parse', '--git-common-dir']))) : source;
  const project = path.join(root, `${path.basename(common.endsWith(`${path.sep}.git`) ? path.dirname(common) : common)}-${hash(common)}`);
  await cleanup(root, '--prune', '3');
  fs.mkdirSync(project, { recursive: true });
  const ctx = { source, info, project };
  if (!options.check) return run(root, options, ctx);
  console.log(`mcp servers (enable per run with --mcp): ${enabled.join(', ') || 'none'}`);
  let cached, code = 0;
  if (!options.probe) await withLock(root, () => { cached = loadState(root).probes[info.configKey]; });
  if (cached?.at > Date.now() - 43200000) console.log(`handoff: Codex ready (${version.stdout.trim()}, cached model probe)`);
  else code = await run(root, options, ctx);
  console.log((await usageReport(root)).text);
  console.log(await openHandoffs(root));
  return code;
}
if (isMain(import.meta.url)) {
  main().then((code) => { process.exitCode = code; }).catch((error) => { console.error(`handoff: ${error.message}`); process.exitCode = error.exitCode || 1; });
}
