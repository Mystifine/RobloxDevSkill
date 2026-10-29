// A successful CLI turn is not proof that the delegated task completed.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { appendTable, atomicWrite, isMain, loadState, readJson, stateFile, withLock, writeJson } from './state.mjs';

// The wrapper as Claude calls it (handoff.sh exports its own path), so printed commands match the permission rule.
export const selfCommand = () => `bash ${process.env.CODEX_HANDOFF_SELF || '~/.claude/skills/roblox-dev/scripts/codex/handoff.sh'}`;
const quote = (value) => /^[A-Za-z0-9_.,:/=@+~-]+$/.test(value) ? value : `'${value.replaceAll("'", "'\\''")}'`;
// A complete, runnable command, so a timer's output can continue the job after /clear.
export function resumeCommand(invocation, runDir, threadId, brief = path.join(runDir, 'brief.md')) {
  const args = ['--brief', brief, ...(threadId ? ['--resume', threadId] : []), '--cd', invocation.cwd];
  const repeat = { mcp: '--mcp', resource: '--resource', addDir: '--add-dir', ...(threadId ? {} : { image: '--image' }) };
  for (const [key, flag] of Object.entries(repeat)) for (const value of invocation[key] || []) args.push(flag, value);
  if (invocation.kind === 'image') args.push('--kind', 'image');
  for (const [key, flag] of [['sandbox', '--sandbox'], ['model', '--model'], ['effort', '--effort'], ['name', '--name'], ['note', '--note']]) if (invocation[key]) args.push(flag, invocation[key]);
  if (invocation.queue) args.push('--queue');
  // Only a queued launch still has to create its worktree.
  if (invocation.worktree && !threadId) args.push('--worktree');
  if (invocation.timeoutMin && invocation.timeoutMin !== 180) args.push('--timeout-min', invocation.timeoutMin);
  return [selfCommand(), ...args.map((arg) => quote(String(arg)))].join(' ');
}
export function briefGoal(text) {
  const lines = text.split(/\r?\n/), start = lines.findIndex((line) => /^##\s*Goal\b/i.test(line));
  const end = lines.findIndex((line, i) => start >= 0 && i > start && /^#/.test(line));
  const body = start < 0 ? lines : lines.slice(start + 1, end < 0 ? undefined : end);
  return body.join(' ').replace(/\s+/g, ' ').trim().slice(0, 240);
}

// Codex states a reset as a delay, a date, or a bare local clock time ("try again at 5:01 PM.").
export function limitResetAt(message, end) {
  const units = { second: 1, minute: 60, hour: 3600, day: 86400 };
  let wait = 0;
  for (const [, n, unit] of message.matchAll(/(\d+)\s*(second|minute|hour|day)s?/gi)) wait += Number(n) * units[unit.toLowerCase()];
  if (wait) return end + wait;
  const at = message.match(/(?:try again|resets?)\s+(?:at|on)\s+(.+)/i)?.[1].replace(/(\d)(?:st|nd|rd|th)\b/gi, '$1').replace(/[.\s]+$/, '');
  const parsed = at ? Date.parse(at) : NaN;
  if (parsed > end * 1000) return Math.round(parsed / 1000);
  const clock = Number.isNaN(parsed) && at?.match(/\b(\d{1,2}):(\d{2})\s*(?:([ap])\.?m\b\.?)?/i);
  if (clock) {
    const [hour, minute] = [Number(clock[1]), Number(clock[2])];
    const hours = clock[3] ? (hour % 12) + (clock[3].toLowerCase() === 'p' ? 12 : 0) : hour;
    if (hours < 24 && minute < 60 && (!clock[3] || (hour >= 1 && hour <= 12))) {
      const reset = new Date(end * 1000);
      reset.setHours(hours, minute, 0, 0);
      if (reset.getTime() <= end * 1000) reset.setDate(reset.getDate() + 1);
      return Math.round(reset.getTime() / 1000);
    }
  }
  return end + 1800;
}

// The default after a run: Claude takes over unfinished code; images stay with Codex, since Claude cannot generate them.
export function nextStep(status, image, thread) {
  if (status === 'READY') return '';
  if (status === 'COMPLETED') return `next: review against the brief (the patch, the evidence, the project's checks); accept, or brief concrete fixes and run the follow-up; then --clean ${thread || '<thread>'}`;
  if (status === 'CANCELLED') return 'next: cancelled; carry on as decided (code: take over yourself; images: relaunch with Codex)';
  if (!image) return status === 'NEEDS REVIEW'
    ? 'next: review; completion is unconfirmed, so finish whatever is missing yourself'
    : 'next: take over: finish the brief yourself from the checkout (the patch shows what Codex changed) and its checkpoint; relaunch only if the user asks';
  if (status === 'NEEDS REVIEW') return 'next: review the images; send anything missing back to Codex with the follow-up';
  if (status === 'CODEX USAGE LIMIT') return `next: images wait for Codex: start "${selfCommand()} --wait" in the background (it prints the resume at the reset) and tell the user; do any non-image remainder yourself`;
  return 'next: images stay with Codex: fix the cause and run the follow-up (moderation: reword the prompt per references/characters.md and no-gore.md; at most 5 reference images; capacity: retry in a few minutes); do any non-image remainder yourself';
}

const TRANSIENT = /^(Reconnecting\.\.\. \d+\/\d+|Falling back from WebSockets)/i;
const NOISE = /^Reading additional input from stdin/;
// `extra.usageAfter` is a live usage read after the run; `extra.overlap` says another run shared the account.
export async function summarize(runDir, codexExit, start, end, cwd = '', extra = {}) {
  const read = (name) => { try { return fs.readFileSync(path.join(runDir, name), 'utf8'); } catch (e) { if (e.code === 'ENOENT') return ''; throw e; } };
  const invocation = readJson(path.join(runDir, 'invocation.json'), {});
  const root = invocation.root || path.dirname(path.dirname(runDir));
  const project = invocation.project || path.dirname(runDir);
  let threadId = invocation.resume || null, turnFailed = '', completed = false, reconnects = 0;
  const usage = { input_tokens: 0, cached_input_tokens: 0, output_tokens: 0 }, errors = [], files = new Set(), mcp = new Map();
  let commands = 0, nonZero = 0, toolText = '';
  for (const line of read('events.jsonl').split('\n')) {
    if (!line.trim()) continue;
    let event;
    try { event = JSON.parse(line); } catch { errors.push('Malformed event log'); continue; }
    if (event.type === 'thread.started') threadId = event.thread_id;
    if (event.type === 'turn.completed') { completed = true; for (const key of Object.keys(usage)) usage[key] += event.usage?.[key] || 0; }
    if (event.type === 'turn.failed') turnFailed = event.error?.message || 'turn failed';
    // Stream reconnects that Codex recovers from are not failures; a turn that never finishes still fails.
    if (event.type === 'error') { if (TRANSIENT.test(event.message || '')) reconnects++; else errors.push(event.message || 'CLI error'); }
    if (event.type !== 'item.completed') continue;
    const item = event.item || {};
    if (item.type === 'command_execution') {
      commands++; if (item.exit_code != null && item.exit_code !== 0) nonZero++;
      // Scan failed tools, not successful grep output containing quoted diagnostics.
      if (item.exit_code !== 0) toolText += `\n${item.aggregated_output || ''}`;
    } else if (item.type === 'file_change' && item.status !== 'failed') {
      for (const change of item.changes || []) files.add(change.path);
    } else if (item.type === 'mcp_tool_call') {
      const key = `${item.server}.${item.tool}${item.status === 'failed' ? ' (failed)' : ''}`;
      mcp.set(key, (mcp.get(key) || 0) + 1);
      if (item.status === 'failed') toolText += `\n${JSON.stringify(item.error || item.result || '')}`;
    } else if (item.type === 'error') errors.push(item.message || 'tool error');
  }
  const final = read('final.md').trim(), stderr = read('stderr.log').split('\n').filter((line) => !NOISE.test(line)).join('\n');
  if (turnFailed) errors.push(turnFailed);
  // stderr also logs tool errors Codex recovered from, so it only explains a run that did not finish.
  const finished = completed && Number(codexExit) === 0;
  const errorText = [...errors, finished ? '' : stderr].join('\n');
  const limitHit = errorText.match(/[^\n]*(?:usage limit|rate limit|quota)[^\n]*/i)?.[0];
  const capacityHit = /at capacity/i.test(errorText);
  const modelHit = /model_not_found|model is not supported|model .{0,60}does not exist|access to (the )?model/i.test(errorText);
  const infrastructureFailure = /helper_unknown_error|setup refresh had errors|requires approval,? but approval policy is never/i.test(`${errorText}\n${toolText}`);
  let result;
  try { result = readJson(path.join(runDir, 'result.json')); } catch { errors.push('Invalid result.json'); }
  const validResult = result && ['completed', 'blocked', 'failed'].includes(result.status) && typeof result.verification === 'string' && result.verification.trim() && typeof result.reason === 'string';
  let status, exit;
  if ([124, 137].includes(Number(codexExit))) [status, exit] = ['TIMED OUT', 3];
  else if (Number(codexExit) === 130) [status, exit] = ['CANCELLED', 4];
  else if (limitHit) [status, exit] = ['CODEX USAGE LIMIT', 2];
  else if (capacityHit) [status, exit] = ['CODEX AT CAPACITY', 71];
  else if (modelHit) [status, exit] = ['NO USABLE MODEL', 71];
  else if (infrastructureFailure || (validResult && result.status === 'blocked')) [status, exit] = ['BLOCKED', 4];
  else if (Number(codexExit) !== 0 || turnFailed || errors.length || (validResult && result.status === 'failed')) [status, exit] = ['FAILED', 1];
  else if (read('snapshot-error.txt')) [status, exit] = ['NEEDS REVIEW', 4];
  else if (invocation.probe && completed && final === 'OK') [status, exit] = ['READY', 0];
  else if (!invocation.probe && completed && final && validResult && result.status === 'completed' && !result.reason.trim()) [status, exit] = ['COMPLETED', 0];
  else [status, exit] = ['NEEDS REVIEW', 4];
  const limitUntil = limitHit ? limitResetAt(limitHit, end) : undefined;
  const images = [];
  if (threadId && /^[A-Za-z0-9-]+$/.test(threadId)) {
    const imageDir = path.join(process.env.CODEX_HOME || path.join(os.homedir(), '.codex'), 'generated_images', threadId);
    if (fs.existsSync(imageDir)) for (const file of fs.readdirSync(imageDir)) {
      const image = path.join(imageDir, file);
      if (fs.statSync(image).mtimeMs >= (start - 5) * 1000) images.push(image);
    }
  }
  // A run that generated images is image work even if the launch didn't say so.
  const imageWork = invocation.kind === 'image' || images.length > 0;
  const seconds = Math.max(0, end - start), out = [`Codex handoff: ${status} (codex exit ${codexExit}) in ${Math.floor(seconds / 60)}m${seconds % 60}s`];
  const next = invocation.probe ? '' : nextStep(status, imageWork, threadId);
  if (next) out.push(next);
  let checkpoint = '';
  try {
    const saved = readJson(path.join(runDir, 'checkpoint.json'));
    if (saved) checkpoint = `${Array.isArray(saved.done) ? saved.done.length : 0} step(s) done${Array.isArray(saved.done) && saved.done.length ? ` (last: ${String(saved.done.at(-1)).slice(0, 160)})` : ''}; next: ${String(saved.next || '?').slice(0, 240)}`;
  } catch { checkpoint = 'checkpoint.json is invalid'; }
  const resumable = { ...invocation, cwd: invocation.cwd || cwd };
  // Only work that must wait for Codex (images, or a launch with --queue) is kept for --wait; Claude takes over the rest.
  const pending = limitHit && !invocation.probe && (imageWork || invocation.queue) ? resumeCommand(resumable, runDir, threadId) : '';
  if (threadId) out.push(`thread: ${threadId}`, ...(invocation.probe ? [] : [`follow-up: ${resumeCommand(resumable, runDir, threadId, '<follow-up brief>')}`]));
  out.push(`run dir: ${runDir}`, `working directory: ${cwd}`);
  if (read('model.txt').trim()) out.push(`model: ${read('model.txt').trim()}`);
  out.push(`codex tokens: ${usage.input_tokens} in (${usage.cached_input_tokens} cached), ${usage.output_tokens} out`);
  const before = invocation.usageBefore, after = extra.usageAfter;
  // A share of a window is measured only between two live reads of the same window.
  const delta = (key) => {
    const a = before?.[key], b = after?.[key];
    return before?.source === 'live' && after?.source === 'live' && a && b && b.used >= a.used && Math.abs((b.resetsAt || 0) - (a.resetsAt || 0)) <= 120 ? b.used - a.used : null;
  };
  if (after) out.push(`codex usage: 5h window ${before?.primary?.used ?? '?'}% -> ${after.primary?.used ?? '?'}%, weekly ${before?.secondary?.used ?? '?'}% -> ${after.secondary?.used ?? '?'}%${extra.overlap ? ' (shared with other runs)' : ''}`);
  if (commands) out.push(`commands: ${commands} run, ${nonZero} non-zero exits`);
  if (reconnects) out.push(`network: ${reconnects} stream reconnect(s)${finished ? ', recovered' : ''}`);
  const capped = (title, entries, max = 20) => {
    if (entries.length) out.push(`${title}:`, ...entries.slice(0, max).map((entry) => `  ${entry}`), ...(entries.length > max ? [`  ... ${entries.length - max} more`] : []));
  };
  const changes = read('git-changes.txt').trim();
  if (changes) {
    capped('checkout changes during run (includes concurrent external edits)', changes.split('\n'), 40);
    const patch = path.join(runDir, 'changes.patch'), mb = fs.existsSync(patch) ? fs.statSync(patch).size / 1e6 : 0, trees = readJson(path.join(runDir, 'trees.json'), {});
    out.push(`review patch: ${patch}${mb > 2 ? ` (${mb.toFixed(1)} MB including binary content; for text only: git -C "${cwd}" diff ${trees.before} ${trees.after} -- <paths>)` : ''}`);
  }
  else capped('tool-reported file changes', [...files]);
  if (read('snapshot-error.txt')) out.push(`snapshot failed: ${read('snapshot-error.txt')}`);
  if (!invocation.probe && !validResult) out.push('result.json missing or invalid; completion is unconfirmed.');
  if (checkpoint) out.push(`checkpoint: ${checkpoint}`);
  if (validResult) out.push(`verification: ${result.verification}`, ...(result.reason ? [`remaining work: ${result.reason}`] : []));
  if (mcp.size) out.push(`mcp calls: ${[...mcp].map(([key, count]) => `${key} x${count}`).join(', ')}`);
  capped('generated image originals', images);
  capped('review media', fs.readdirSync(runDir).filter((file) => /\.(png|jpe?g|gif|webp)$/i.test(file)).map((file) => path.join(runDir, file)));
  capped('errors', [...new Set(errors)]);
  if (exit !== 0 && stderr.trim()) capped('stderr tail', stderr.trim().split('\n').slice(-8));
  if (limitUntil) out.push(`usage limit: blocked until ${new Date(limitUntil * 1000).toISOString()}`);
  if (pending) out.push(`resume after reset: ${pending}`, `timer: ${selfCommand()} --wait (in the background; prints this resume once Codex has room)`);
  out.push('--- Codex final report ---', final ? final.slice(0, 6000) : '(none)');
  const text = out.join('\n');
  await withLock(root, () => {
    const state = loadState(root);
    if (threadId) { state.threads ||= {}; state.threads[threadId] = { cwd, project, updated: Date.now() }; }
    if (limitUntil) {
      const key = invocation.accountKey || 'legacy';
      if (limitUntil > (state.limits[key]?.until || 0)) state.limits[key] = { until: limitUntil, message: limitHit };
    }
    if (!invocation.probe && (delta('primary') !== null || delta('secondary') !== null)) {
      state.samples = [...state.samples, { at: end, kind: imageWork ? 'image' : 'code', seconds, primary: delta('primary'), secondary: delta('secondary'), overlap: !!extra.overlap }].slice(-40);
    }
    // Success NEVER clears another run's active usage limit.
    // A later run of the same job supersedes its pending resume, whatever the outcome.
    for (const [key, entry] of Object.entries(state.pending)) {
      if ((threadId && entry.thread === threadId) || (!entry.thread && invocation.brief && path.resolve(invocation.brief) === path.resolve(entry.runDir, 'brief.md'))) delete state.pending[key];
    }
    if (pending) state.pending[threadId || runDir] = { account: invocation.accountKey || 'legacy', until: limitUntil, thread: threadId, runDir, project,
      goal: briefGoal(read('brief.md')), note: invocation.note || '', checkpoint, command: pending };
    writeJson(stateFile(root), state);
    writeJson(path.join(runDir, 'meta.json'), { status, codexExit, threadId, seconds, usage, files: [...files], images, errors, result });
    atomicWrite(path.join(runDir, 'summary.txt'), text + '\n');
    appendTable(path.join(project, 'ledger.tsv'), 'date\tstatus\tseconds\tinput_tokens\tcached_input_tokens\toutput_tokens\tthread\trun',
      [new Date(end * 1000).toISOString(), status, seconds, usage.input_tokens, usage.cached_input_tokens, usage.output_tokens, threadId || '', path.basename(runDir)].join('\t'));
  });
  return { text, exit, status, threadId };
}

// A launch that found no room and must wait for Codex: kept as a not-started job that --wait prints when room returns.
export async function queueRun(runDir, invocation, until, reason) {
  const command = resumeCommand(invocation, runDir, null);
  const text = [`Codex handoff: QUEUED (no room for another Codex run)`,
    `next: start "${selfCommand()} --wait" in the background (it prints this launch once Codex has room) and tell the user when it should start`,
    `run dir: ${runDir}`, reason, `queued launch: ${command}`].join('\n');
  await withLock(invocation.root, () => {
    const state = loadState(invocation.root);
    // Re-queuing the same brief replaces its earlier entry.
    for (const [key, entry] of Object.entries(state.pending)) if (!entry.thread && invocation.brief && path.resolve(invocation.brief) === path.resolve(entry.runDir, 'brief.md')) delete state.pending[key];
    state.pending[runDir] = { account: invocation.accountKey || 'legacy', until, thread: null, runDir, project: invocation.project,
      goal: briefGoal(fs.readFileSync(path.join(runDir, 'brief.md'), 'utf8')), note: invocation.note || '', checkpoint: '', command };
    writeJson(stateFile(invocation.root), state);
    writeJson(path.join(runDir, 'meta.json'), { status: 'QUEUED', threadId: null, usage: {} });
    atomicWrite(path.join(runDir, 'summary.txt'), text + '\n');
  });
  return text;
}
if (isMain(import.meta.url)) {
  const [dir, code, start, end, cwd] = process.argv.slice(2);
  summarize(dir, Number(code), Number(start), Number(end), cwd).then((report) => { console.log(report.text); process.exitCode = report.exit; })
    .catch((error) => { console.error(error.message); process.exitCode = error.exitCode || 1; });
}
