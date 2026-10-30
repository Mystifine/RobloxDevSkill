// Codex usage without spending any: the account's live rate limits from `codex app-server`
// (account/rateLimits/read, no model turn), else the newest snapshot in Codex's session logs.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import readline from 'node:readline';
import { spawn } from 'node:child_process';

const now = () => Math.floor(Date.now() / 1000);
export const maxRuns = () => Number(process.env.CODEX_HANDOFF_MAX_RUNS) || 3;

// One window; a window whose reset has passed is empty again.
function window(raw) {
  const used = Number(raw?.usedPercent ?? raw?.used_percent);
  if (!raw || !Number.isFinite(used)) return null;
  const resetsAt = Number(raw.resetsAt ?? raw.resets_at) || null;
  return { used: resetsAt && resetsAt <= now() ? 0 : used, minutes: Number(raw.windowDurationMins ?? raw.window_minutes) || null, resetsAt };
}
export const normalize = (limits, source, at, allowed = null) => ({ source, at, allowed,
  plan: limits?.planType ?? limits?.plan_type ?? null, primary: window(limits?.primary), secondary: window(limits?.secondary) });

// `command` is [file, args] that starts `codex app-server` on stdio.
export function readLive([command, args], timeoutMs = 15000) {
  return new Promise((resolve) => {
    let child, done = false;
    const finish = (value) => {
      if (done) return;
      done = true; clearTimeout(timer);
      // End of input stops the server; the kill covers a shell that outlives it.
      try { child?.stdin.end(); child?.kill(); } catch { /* already gone */ }
      resolve(value);
    };
    const timer = setTimeout(() => finish(null), timeoutMs);
    try { child = spawn(command, args, { stdio: ['pipe', 'pipe', 'ignore'], windowsHide: true }); }
    catch { finish(null); return; }
    const send = (message) => child.stdin.write(`${JSON.stringify(message)}\n`);
    child.on('error', () => finish(null));
    child.on('close', () => finish(null));
    child.stdin.on('error', () => finish(null));
    readline.createInterface({ input: child.stdout }).on('line', (line) => {
      let message;
      try { message = JSON.parse(line); } catch { return; }
      if (message.id === 1 && !message.error) {
        send({ method: 'initialized' });
        send({ id: 2, method: 'account/rateLimits/read', params: { excludeResetCreditDetails: true } });
      } else if (message.id === 1 || message.id === 2) {
        const result = message.result;
        finish(result ? normalize(result.rateLimitsByLimitId?.codex || result.rateLimits, 'live', Date.now(), result.ordinaryUsageAllowed ?? null) : null);
      }
    });
    send({ id: 1, method: 'initialize', params: { clientInfo: { name: 'roblox-dev-handoff', version: '1' } } });
  });
}

// The newest snapshot Codex logged, read from the end of the newest few session files.
export function readLogged(maxFiles = 6) {
  const files = [];
  const descend = (dir, depth) => {
    if (!fs.existsSync(dir)) return;
    for (const entry of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => b.name.localeCompare(a.name))) {
      if (files.length >= maxFiles) return;
      const full = path.join(dir, entry.name);
      if (entry.isDirectory() && depth < 3) descend(full, depth + 1);
      else if (entry.isFile() && /^rollout-.*\.jsonl$/.test(entry.name)) files.push(full);
    }
  };
  descend(path.join(process.env.CODEX_HOME || path.join(os.homedir(), '.codex'), 'sessions'), 0);
  let best = null;
  for (const file of files) {
    const size = fs.statSync(file).size, length = Math.min(size, 1 << 20), buffer = Buffer.alloc(length);
    const fd = fs.openSync(file, 'r');
    try { fs.readSync(fd, buffer, 0, length, size - length); } finally { fs.closeSync(fd); }
    for (const line of buffer.toString('utf8').split('\n').reverse()) {
      if (!line.includes('"rate_limits"')) continue;
      let entry;
      try { entry = JSON.parse(line); } catch { continue; }
      const limits = entry.payload?.rate_limits, at = Date.parse(entry.timestamp);
      if (!limits || !Number.isFinite(at)) continue;
      if (!best || at > best.at) best = normalize(limits, 'session log', at);
      break;
    }
  }
  return best;
}

// A run's share of each window: the upper quartile of the last 20 runs of its kind measured alone, since one code
// run can be a 2% fix and the next a 36% Blender build (seen 2026-10-29, where a median said 4%); until 3 exist,
// a cautious default or the costliest measured, whichever is larger. Without a kind, every kind counts.
export function runCost(samples = [], kind) {
  const quartile = (key, fallback) => {
    const values = samples.filter((sample) => !sample.overlap && (!kind || sample.kind === kind) && Number.isFinite(sample[key])).slice(-20)
      .map((sample) => sample[key]).sort((a, b) => a - b);
    return { value: values.length >= 3 ? Math.max(1, values[Math.ceil(values.length * 3 / 4) - 1]) : Math.max(fallback, ...values), measured: values.length };
  };
  return { primary: quartile('primary', 10), secondary: quartile('secondary', 2) };
}
export const runCosts = (samples) => ({ code: runCost(samples, 'code'), image: runCost(samples, 'image') });
const fits = (w, per) => w ? Math.floor((100 - w.used) / per) : Infinity;
// How many more runs fit now; unknown usage is limited by the cap alone.
export function room(usage, active, cost, cap = maxRuns()) {
  if (usage?.allowed === false) return 0;
  return Math.max(0, Math.min(fits(usage?.primary, cost.primary.value), fits(usage?.secondary, cost.secondary.value), cap) - active);
}
// When room returns: the reset of each window that is too full, else now (a run ending frees it; --wait polls).
export function bindingReset(usage, active, cost) {
  const resets = [];
  for (const [w, per] of [[usage?.primary, cost.primary.value], [usage?.secondary, cost.secondary.value]]) if (w && fits(w, per) - active < 1) resets.push(w.resetsAt);
  if (usage?.allowed === false) resets.push(usage.primary?.resetsAt);
  return Math.max(now(), ...resets.filter(Boolean));
}
const pad = (n) => String(n).padStart(2, '0');
export function when(seconds) {
  if (!seconds) return 'unknown';
  const d = new Date(seconds * 1000), left = Math.max(0, seconds - now());
  const span = left >= 86400 ? `${Math.floor(left / 86400)}d${Math.floor((left % 86400) / 3600)}h` : `${Math.floor(left / 3600)}h${pad(Math.floor((left % 3600) / 60))}m`;
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())} (in ${span})`;
}
// `costs` is runCosts(samples): room is reported per kind.
export function describeUsage(usage, active, costs, cap = maxRuns()) {
  const free = { code: room(usage, active, costs.code, cap), image: room(usage, active, costs.image, cap) };
  const show = (name, w) => w ? `${name} ${w.used}% used, resets ${when(w.resetsAt)}` : `${name} unknown`;
  const measured = (cost, kind) => cost.primary.measured >= 3 ? `upper quartile of ${cost.primary.measured} ${kind} runs measured alone` : `a default or the costliest so far; ${cost.primary.measured} of 3 ${kind} runs measured alone`;
  const runs = (n, kind) => `${n} more ${kind} run${n === 1 ? '' : 's'}`;
  const lines = [usage
    ? `codex usage (${usage.source}${usage.source === 'live' ? '' : ` of ${new Date(usage.at).toISOString()}`}${usage.plan ? `, ${usage.plan} plan` : ''}): ${show('5h window', usage.primary)}; ${show('weekly', usage.secondary)}${usage.allowed === false ? '; ordinary usage NOT allowed now' : ''}`
    : 'codex usage: unknown (no live read, no session log); only the cap limits launches',
  `a code run costs about ${costs.code.primary.value}% of the 5h window and ${costs.code.secondary.value}% of the week (${measured(costs.code, 'code')}); ` +
    `an image run about ${costs.image.primary.value}% and ${costs.image.secondary.value}% (${measured(costs.image, 'image')})`,
  `active runs: ${active}; room: ${runs(free.code, 'code')} and ${runs(free.image, 'image')} now (cap ${cap})`];
  return { text: lines.join('\n'), room: free };
}
