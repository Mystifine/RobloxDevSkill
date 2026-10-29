// Cleanup and the open-handoff listing. Nothing here deletes work that exists only in a handoff:
// a worktree goes only once its main checkout holds every file it changed (or with --discard).
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { appendTable, inside, isMain, liveReservations, loadState, readJson, safeRemove, stateFile, withLock, writeJson } from './state.mjs';
import { briefGoal, selfCommand } from './summarize.mjs';
import { when } from './usage.mjs';

const fail = (message, exitCode) => { const error = new Error(message); error.exitCode = exitCode; throw error; };
const jsonlFiles = (dir) => fs.existsSync(dir) ? fs.readdirSync(dir, { withFileTypes: true, recursive: true })
  .filter((entry) => entry.isFile() && entry.name.endsWith('.jsonl')).map((entry) => path.join(entry.parentPath || entry.path, entry.name)) : [];
// Claude usage from the director sessions' transcripts (and their subagents) since the task's first run.
// Everything those sessions did in the window counts, including unrelated work.
export function claudeUsage(sessions, since) {
  const projects = path.join(process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude'), 'projects');
  const totals = { input: 0, cacheWrite: 0, cacheRead: 0, output: 0, messages: 0 }, seen = new Set();
  for (const project of subdirs(projects)) for (const id of sessions) {
    for (const file of [path.join(project, `${id}.jsonl`), ...jsonlFiles(path.join(project, id))].filter((f) => fs.existsSync(f))) {
      for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
        if (!line.includes('"usage"')) continue;
        let entry; try { entry = JSON.parse(line); } catch { continue; }
        const usage = entry.message?.usage, key = entry.message?.id || entry.requestId;
        if (entry.type !== 'assistant' || !usage || !key || seen.has(key) || Date.parse(entry.timestamp) < since) continue;
        seen.add(key); totals.messages++;
        totals.input += usage.input_tokens || 0; totals.cacheWrite += usage.cache_creation_input_tokens || 0;
        totals.cacheRead += usage.cache_read_input_tokens || 0; totals.output += usage.output_tokens || 0;
      }
    }
  }
  return totals;
}
const subdirs = (dir) => fs.existsSync(dir) ? fs.readdirSync(dir, { withFileTypes: true }).filter((entry) => entry.isDirectory()).map((entry) => path.join(dir, entry.name)) : [];
// A corrupt record must not stop cleanup or the listing.
const record = (file, fallback = null) => { try { return readJson(file, fallback); } catch { return fallback; } };
const key = (dir) => (process.platform === 'win32' ? path.resolve(dir).toLowerCase() : path.resolve(dir));
function runDirs(root) {
  return subdirs(root).flatMap((project) => subdirs(project).filter((dir) => /^\d{8}-\d{6}-/.test(path.basename(dir))).map((dir) => ({
    dir, project, meta: record(path.join(dir, 'meta.json')), invocation: record(path.join(dir, 'invocation.json'), {}) || {}, mtime: fs.statSync(dir).mtimeMs })));
}
const label = (project) => path.basename(project || '?').replace(/-[0-9a-f]{16}$/, '');
const gitOut = (cwd, args, input) => {
  const result = spawnSync('git', ['-C', cwd, ...args], { encoding: 'utf8', input, windowsHide: true, maxBuffer: 64 * 1024 * 1024 });
  return result.status === 0 ? result.stdout : null;
};
const mainOf = (worktree) => {
  const common = gitOut(worktree, ['rev-parse', '--path-format=absolute', '--git-common-dir']);
  return common ? path.dirname(common.trim()) : null;
};
// Files a linked worktree changed that its main checkout doesn't hold with the same content as Git sees it;
// empty means integrated. `git hash-object` applies line-ending and filter rules, so an integration that
// `git apply` wrote with CRLF (core.autocrlf) still matches Codex's LF original.
export function unintegrated(worktree) {
  const main = mainOf(worktree), status = gitOut(worktree, ['status', '--porcelain=v1', '-z', '--untracked-files=all']);
  if (!main || status === null) return ['(not a readable Git worktree)'];
  const files = [], tokens = status.split('\0');
  for (let i = 0; i < tokens.length; i++) {
    if (tokens[i].length < 4) continue;
    files.push(tokens[i].slice(3));
    if (/^[RC]/.test(tokens[i])) i++; // a rename's next token is its old path
  }
  const differ = [], compare = [];
  for (const file of files) {
    const a = path.join(worktree, file), b = path.join(main, file), inA = fs.existsSync(a), inB = fs.existsSync(b);
    if (inA !== inB) differ.push(file);
    else if (inA) {
      const folderA = fs.statSync(a).isDirectory(), folderB = fs.statSync(b).isDirectory();
      if (folderA !== folderB) differ.push(file);
      else if (!folderA) compare.push(file);
    }
  }
  if (compare.length) {
    const hashes = (cwd) => gitOut(cwd, ['hash-object', '--stdin-paths'], `${compare.join('\n')}\n`)?.trim().split('\n') ?? [];
    const [left, right] = [hashes(worktree), hashes(main)];
    compare.forEach((file, i) => { if (!left[i] || left[i] !== right[i]) differ.push(file); });
  }
  return differ;
}
// Through Git, so its metadata goes too; `main` lets a worktree that is already gone be pruned.
export function removeWorktree(worktree, main = mainOf(worktree)) {
  if (fs.existsSync(worktree) && main) gitOut(main, ['worktree', 'remove', '--force', worktree]);
  if (main) gitOut(main, ['worktree', 'prune']);
  return !fs.existsSync(worktree);
}
// Worktrees the wrapper created (`<project>/worktrees/<run>`), with the checkout each came from.
function worktreesOf(runs) {
  const found = new Map();
  for (const run of runs) {
    const cwd = run.invocation.cwd;
    if (cwd && inside(path.join(run.project, 'worktrees'), cwd)) found.set(key(cwd), { worktree: cwd, main: run.invocation.source || null });
  }
  return [...found.values()];
}
function removeImages(root, active, runs, targets) {
  const imageRoot = path.resolve(process.env.CODEX_HOME || path.join(os.homedir(), '.codex'), 'generated_images');
  let removed = 0;
  for (const id of new Set(targets.map((run) => run.meta?.threadId).filter((id) => /^[A-Za-z0-9-]+$/.test(id || '')))) {
    if (active.some((run) => run.thread === id)) continue;
    if (runs.some((run) => run.meta?.threadId === id && !targets.includes(run))) continue;
    const dir = path.join(imageRoot, id);
    if (fs.existsSync(dir) && inside(imageRoot, dir)) { safeRemove(imageRoot, dir); removed++; }
  }
  return removed;
}
const removeRuns = (root, targets) => {
  for (const run of targets) safeRemove(root, run.dir);
  for (const project of new Set(targets.map((run) => run.project))) {
    // LAST_RUN is an earlier wrapper's pointer to its latest run; nothing reads it.
    fs.rmSync(path.join(project, 'LAST_RUN'), { force: true });
    tidy(path.join(project, 'worktrees'));
  }
};
// Removes a folder once it is empty.
const tidy = (dir) => { try { if (fs.readdirSync(dir).length === 0) fs.rmdirSync(dir); } catch { /* absent or in use */ } };
export const describePending = (entry) => [`== ${entry.thread ? `thread ${entry.thread}` : 'not started'} (${label(entry.project)})`,
  `goal: ${entry.goal || '(see brief)'}`, ...(entry.checkpoint ? [`codex progress: ${entry.checkpoint}`] : []), ...(entry.note ? [`note: ${entry.note}`] : []),
  `run dir: ${entry.runDir}`, `${entry.thread ? 'resume' : 'launch'}: ${entry.command}`].join('\n');

// `--clean THREAD|RUN_DIR` after acceptance or takeover, or `--prune DAYS` (every launch and check).
export async function cleanup(root, mode, arg, claudeTokens, { discard = false } = {}) {
  const byDir = mode === '--thread' && path.isAbsolute(arg || '');
  if (!((mode === '--thread' && (byDir || /^[A-Za-z0-9-]+$/.test(arg || ''))) || (mode === '--prune' && Number(arg) > 0))) fail('cleanup: use --clean THREAD|RUN_DIR or --prune DAYS', 64);
  if (claudeTokens !== undefined && (!Number.isFinite(Number(claudeTokens)) || Number(claudeTokens) < 0)) fail('Invalid Claude token count', 64);
  return withLock(root, () => {
    const state = loadState(root), active = liveReservations(state), runs = runDirs(root);
    const busy = new Set(active.map((run) => key(run.runDir)));
    if (mode === '--prune') return prune(root, state, active, busy, runs, Number(arg));
    // A run directory stands for its whole task when it has a thread.
    let thread = byDir ? null : arg, targets;
    if (byDir) {
      const run = runs.find((candidate) => key(candidate.dir) === key(arg));
      if (!run || !inside(root, arg)) fail('--clean needs a thread id or a run directory under the handoff home', 64);
      thread = run.meta?.threadId || null;
      if (!thread) targets = [run];
    }
    targets ||= runs.filter((run) => run.meta?.threadId === thread || run.invocation.resume === thread);
    if (targets.some((run) => busy.has(key(run.dir))) || (thread && active.some((run) => run.thread === thread))) fail(`${thread ? `Thread ${thread}` : 'That run'} is active; cancel or wait before cleaning`, 75);
    // All or nothing: a worktree holding work that isn't in its main checkout stops the whole clean.
    const worktrees = worktreesOf(targets), blocked = [];
    if (!discard) for (const { worktree } of worktrees) {
      const left = fs.existsSync(worktree) ? unintegrated(worktree) : [];
      if (left.length) blocked.push(`${worktree}: ${left.slice(0, 6).join(', ')}${left.length > 6 ? `, ${left.length - 6} more` : ''}`);
    }
    if (blocked.length) fail(`clean refused, nothing removed: a worktree holds work its main checkout doesn't have:\n  ${blocked.join('\n  ')}\nIntegrate it (the run's changes.patch), or rerun with --discard to drop it.`, 4);
    if (thread) {
      for (const project of new Set(targets.filter((run) => run.meta).map((run) => run.project))) {
        const subset = targets.filter((run) => run.project === project && run.meta), sum = (name) => subset.reduce((n, run) => n + (run.meta.usage?.[name] || 0), 0);
        const since = Math.min(...subset.map((run) => run.invocation.startedAt || Infinity));
        const sessions = new Set([...subset.map((run) => run.invocation.claudeSession), process.env.CLAUDE_CODE_SESSION_ID].filter(Boolean));
        const claude = Number.isFinite(since) && sessions.size ? claudeUsage(sessions, since) : null;
        const file = path.join(project, 'usage.tsv');
        // A retry after a partial cleanup does not double-count the same task.
        const recorded = fs.existsSync(file) && fs.readFileSync(file, 'utf8').split('\n').some((line) => line.split('\t')[1] === thread);
        if (!recorded) appendTable(file, 'date\tthread\truns\tcodex_input\tcodex_cached\tcodex_output\tclaude_input\tclaude_cache_write\tclaude_cache_read\tclaude_output\tclaude_messages\tclaude_manual\tfirst_run',
          [new Date().toISOString(), thread, subset.length, sum('input_tokens'), sum('cached_input_tokens'), sum('output_tokens'),
            ...(claude ? [claude.input, claude.cacheWrite, claude.cacheRead, claude.output, claude.messages] : ['', '', '', '', '']),
            claudeTokens ?? '', path.basename(subset[0].dir)].join('\t'));
        console.log(`handoff usage: codex ${sum('input_tokens')} in (${sum('cached_input_tokens')} cached), ${sum('output_tokens')} out; ` + (claude
          ? `claude ${claude.input} in, ${claude.cacheWrite} cache write, ${claude.cacheRead} cache read, ${claude.output} out over ${claude.messages} message(s) since ${new Date(since).toISOString()} (all director activity in that window)`
          : 'claude not measured (no recorded session)'));
      }
      delete state.threads?.[thread];
    }
    const removedTrees = worktrees.filter(({ worktree, main }) => removeWorktree(worktree, main || undefined)).length;
    for (const { worktree } of worktrees) tidy(path.dirname(worktree));
    const dirs = new Set(targets.map((run) => key(run.dir)));
    for (const [name, entry] of Object.entries(state.pending)) if ((thread && entry.thread === thread) || dirs.has(key(entry.runDir))) delete state.pending[name];
    const removedImages = removeImages(root, active, runs, targets);
    removeRuns(root, targets);
    writeJson(stateFile(root), state);
    console.log(`handoff cleanup: removed ${targets.length} run dir(s), ${removedImages} image-original folder(s), ${removedTrees} of ${worktrees.length} worktree(s)`);
    return 0;
  });
}
// Runs, waits and bookkeeping older than `days`; never active runs, waiting jobs or unintegrated worktrees.
function prune(root, state, active, busy, runs, days) {
  const cutoff = Date.now() - days * 86400000, waiting = new Set(Object.values(state.pending).map((entry) => key(entry.runDir)));
  // A run without meta.json that holds no reservation crashed; it ages out like a finished one.
  // A passed readiness probe holds nothing worth keeping, whatever its age.
  const targets = runs.filter((run) => !busy.has(key(run.dir)) && !waiting.has(key(run.dir)) && (run.mtime < cutoff || run.meta?.status === 'READY'));
  const removedImages = removeImages(root, active, runs, targets);
  removeRuns(root, targets);
  const remaining = new Set(runs.filter((run) => !targets.includes(run)).map((run) => key(run.invocation.cwd || run.dir)));
  let removedTrees = 0;
  for (const project of subdirs(root)) for (const worktree of subdirs(path.join(project, 'worktrees'))) {
    if (remaining.has(key(worktree)) || fs.statSync(worktree).mtimeMs >= cutoff || unintegrated(worktree).length) continue;
    if (removeWorktree(worktree)) removedTrees++;
  }
  for (const project of subdirs(root)) {
    tidy(path.join(project, 'worktrees'));
    fs.rmSync(path.join(project, 'LAST_RUN'), { force: true });
  }
  // Stale bookkeeping: waits whose run is gone, threads idle for 30 days, expired limits.
  let stale = 0;
  for (const [name, entry] of Object.entries(state.pending)) if (!fs.existsSync(entry.runDir)) { delete state.pending[name]; stale++; }
  for (const [id, thread] of Object.entries(state.threads || {})) if ((thread.updated || 0) < Date.now() - 30 * 86400000) { delete state.threads[id]; stale++; }
  for (const [account, limit] of Object.entries(state.limits)) if ((limit.until || 0) * 1000 < Date.now()) { delete state.limits[account]; stale++; }
  if (stale) writeJson(stateFile(root), state);
  if (targets.length || removedImages || removedTrees) console.log(`handoff cleanup: pruned ${targets.length} run dir(s), ${removedImages} image-original folder(s), ${removedTrees} worktree(s) (passed probes, or older than ${days} day(s))`);
  return 0;
}

const age = (ms) => { const minutes = Math.max(0, Math.round((Date.now() - ms) / 60000)); return minutes >= 60 ? `${Math.floor(minutes / 60)}h${String(minutes % 60).padStart(2, '0')}m` : `${minutes}m`; };
const clip = (text, max = 110) => text.length <= max ? text : `${text.slice(0, max).replace(/\s+\S*$/, '')}...`;
const goalOf = (dir) => { try { return clip(briefGoal(fs.readFileSync(path.join(dir, 'brief.md'), 'utf8'))) || '(empty brief)'; } catch { return '(no brief)'; } };
const dated = (dir) => path.basename(dir).replace(/^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})\d{2}-.*$/, '$1-$2-$3 $4:$5 UTC');
// Every handoff still open, with the command for each choice, so Claude can ask the user what to do.
export async function openHandoffs(root) {
  return withLock(root, () => {
    const state = loadState(root), live = liveReservations(state).filter((run) => run.paths.length), runs = runDirs(root);
    const waiting = Object.values(state.pending).filter((entry) => fs.existsSync(entry.runDir));
    const busy = new Set(live.map((run) => key(run.runDir))), waitingDirs = new Set(waiting.map((entry) => key(entry.runDir)));
    const waitingThreads = new Set(waiting.map((entry) => entry.thread).filter(Boolean));
    const kindOf = (run) => (run.invocation.kind === 'image' || run.meta?.images?.length ? 'image' : 'code');
    const running = [], held = [], finished = [], leftovers = [];
    for (const reservation of live) {
      const run = runs.find((candidate) => key(candidate.dir) === key(reservation.runDir)) || { dir: reservation.runDir, invocation: {} };
      running.push(`running   ${label(run.project)}  ${kindOf(run)}  ${age(run.invocation.startedAt || Date.now())}  ${goalOf(run.dir)}`,
        `  run dir: ${run.dir}`, `  stop: ${selfCommand()} --cancel "${run.dir}"`);
    }
    for (const entry of waiting) held.push(`waiting   ${label(entry.project)}  ${entry.thread ? 'paused' : 'queued'}, due ${when(entry.until)}  ${clip(entry.goal || '(see brief)')}`,
      `  ${entry.thread ? 'resume' : 'launch'}: ${entry.command}`, `  drop: ${selfCommand()} --clean ${entry.thread || `"${entry.runDir}"`}`);
    // Finished or crashed but not cleaned: the latest run of each task that is neither running nor waiting.
    const latest = new Map();
    for (const run of runs) {
      if (busy.has(key(run.dir)) || waitingDirs.has(key(run.dir)) || ['READY', 'QUEUED'].includes(run.meta?.status)) continue;
      const thread = run.meta?.threadId || run.invocation.resume;
      if (thread && (waitingThreads.has(thread) || live.some((reservation) => reservation.thread === thread))) continue;
      const id = thread || run.dir;
      if (!latest.has(id) || path.basename(run.dir) > path.basename(latest.get(id).dir)) latest.set(id, run);
    }
    for (const [id, run] of latest) finished.push(`finished  ${label(run.project)}  ${run.meta?.status || 'CRASHED (no result)'}  ${dated(run.dir)}  ${kindOf(run)}  ${goalOf(run.dir)}`,
      `  summary: ${run.meta ? path.join(run.dir, 'summary.txt') : `(none) ${run.dir}`}`, `  when done: ${selfCommand()} --clean ${run.meta?.threadId || `"${id === run.dir ? run.dir : id}"`}`);
    const owned = new Set(runs.map((run) => key(run.invocation.cwd || run.dir)));
    for (const project of subdirs(root)) for (const worktree of subdirs(path.join(project, 'worktrees'))) {
      if (owned.has(key(worktree))) continue;
      const left = unintegrated(worktree), main = mainOf(worktree);
      leftovers.push(`worktree  ${label(project)}  ${left.length ? `${left.length} file(s) not in the main checkout` : 'integrated'}  ${worktree}`,
        main ? `  remove: git -C "${main}" worktree remove --force "${worktree}"` : '  remove: not a Git worktree any more; delete the folder');
    }
    const count = (lines, per) => lines.length / per;
    const total = count(running, 3) + count(held, 3) + count(finished, 3) + count(leftovers, 2);
    if (!total) return 'open handoffs: none';
    return [`open handoffs: ${count(running, 3)} running, ${count(held, 3)} waiting, ${count(finished, 3)} finished but not cleaned, ${count(leftovers, 2)} leftover worktree(s). Ask the user what to do with each before starting new handoffs.`,
      ...running, ...held, ...finished, ...leftovers].join('\n');
  });
}
if (isMain(import.meta.url)) {
  const [root, mode, arg, flag, value] = process.argv.slice(2);
  cleanup(path.resolve(root), mode, arg, flag === '--claude-tokens' ? value : undefined).then((code) => { process.exitCode = code; })
    .catch((error) => { console.error(error.message); process.exitCode = error.exitCode || 1; });
}
