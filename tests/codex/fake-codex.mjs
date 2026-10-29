// A stand-in for the Codex CLI: no model, no network. FAKE_* environment variables pick the scenario.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import readline from 'node:readline';
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

const args = process.argv.slice(2), env = process.env;
const emit = (event) => console.log(JSON.stringify(event));
if (args.includes('--version')) { console.log('codex-fake 1'); process.exit(0); }
if (args[0] === 'login') process.exit(0);
if (args[0] === 'mcp') { console.log(env.FAKE_SERVERS || '[]'); process.exit(0); }
if (args[0] === 'debug') { emit({ models: ['fallback-a', 'fallback-b', 'fallback-c'].map((slug) => ({ slug, visibility: 'list' })) }); process.exit(0); }
if (args[0] === 'app-server') {
  // Usage comes from FAKE_USAGE_FILE: {"primary": %, "secondary": %, "reset": epoch seconds, "allowed": bool}; no file means not logged in.
  if (env.FAKE_APP_LOG) fs.appendFileSync(env.FAKE_APP_LOG, `${process.pid}\n`);
  readline.createInterface({ input: process.stdin }).on('line', (line) => {
    const message = JSON.parse(line);
    if (message.id === 1) emit({ id: 1, result: { userAgent: 'codex-fake' } });
    if (message.id !== 2) return;
    if (!env.FAKE_USAGE_FILE || !fs.existsSync(env.FAKE_USAGE_FILE)) { emit({ id: 2, error: { code: -32000, message: 'not logged in' } }); return; }
    const usage = JSON.parse(fs.readFileSync(env.FAKE_USAGE_FILE, 'utf8')), reset = usage.reset ?? Math.floor(Date.now() / 1000) + 3600;
    emit({ id: 2, result: { ordinaryUsageAllowed: usage.allowed ?? true, rateLimits: { planType: 'plus',
      primary: { usedPercent: usage.primary, windowDurationMins: 300, resetsAt: reset },
      secondary: { usedPercent: usage.secondary ?? 0, windowDurationMins: 10080, resetsAt: reset + 86400 } } } });
  });
  process.stdin.on('end', () => process.exit(0));
} else {
  const final = args[args.indexOf('-o') + 1], dir = path.dirname(final), scenario = env.FAKE_SCENARIO || 'ok';
  fs.appendFileSync(env.FAKE_CALLS, `${JSON.stringify({ args, cwd: process.cwd(), dir, pid: process.pid })}\n`);
  const thread = args[1] === 'resume' ? args[2] : crypto.randomUUID();
  emit({ type: 'thread.started', thread_id: thread });
  if (env.FAKE_CHILD) {
    const child = spawn(process.execPath, ['-e', 'setInterval(()=>{},1000)'], { stdio: 'ignore' });
    fs.writeFileSync(env.FAKE_CHILD, String(child.pid));
  }
  await sleep(Number(env.FAKE_DELAY || 0));
  if (env.FAKE_HOLD) while (!fs.existsSync(env.FAKE_HOLD)) await sleep(25);
  if (env.FAKE_CHECKPOINT) fs.writeFileSync(path.join(dir, 'checkpoint.json'), JSON.stringify({ done: ['phase 1 textures'], next: 'phase 2 review sheets' }));
  if (env.FAKE_EDIT_BYTES) fs.writeFileSync(path.join(process.cwd(), 'large.bin'), crypto.randomBytes(Number(env.FAKE_EDIT_BYTES)));
  if (env.FAKE_IMAGES) {
    const images = path.join(env.CODEX_HOME, 'generated_images', thread);
    fs.mkdirSync(images, { recursive: true });
    fs.writeFileSync(path.join(images, 'ig_1.png'), 'not really a png');
  }
  if (scenario === 'limit') { emit({ type: 'error', message: "You've hit your usage limit. Try again in 1 second." }); process.exit(1); }
  if (scenario === 'capacity') {
    emit({ type: 'error', message: 'Selected model is at capacity. Please try a different model.' });
    emit({ type: 'turn.failed', error: { message: 'Selected model is at capacity. Please try a different model.' } });
    process.exit(1);
  }
  if (scenario === 'model-missing' && !args.includes('fallback-a')) { emit({ type: 'error', message: 'model_not_found' }); process.exit(1); }
  const probe = args.some((arg) => arg.includes('the two letters "OK"'));
  if (env.FAKE_EDIT) fs.writeFileSync(path.join(process.cwd(), env.FAKE_EDIT), 'after\n');
  if (scenario === 'sandbox') emit({ type: 'item.completed', item: { type: 'command_execution', exit_code: 1, aggregated_output: 'helper_unknown_error: setup refresh had errors' } });
  if (scenario === 'reconnect') for (const n of [2, 3]) emit({ type: 'error', message: `Reconnecting... ${n}/5 (stream disconnected before completion: IO error)` });
  if (scenario === 'fail') { emit({ type: 'turn.failed', error: { message: 'tool crashed' } }); process.exit(1); }
  emit({ type: 'item.completed', item: { type: 'agent_message', text: scenario === 'mentions-error' ? 'Implemented model_not_found handling' : 'done' } });
  emit({ type: 'turn.completed', usage: { input_tokens: 10, cached_input_tokens: 2, output_tokens: 3 } });
  fs.writeFileSync(final, probe ? 'OK' : 'Work finished.');
  if (!probe && scenario !== 'missing-result') {
    const result = JSON.stringify({ status: scenario === 'blocked' ? 'blocked' : 'completed', verification: 'fixture check passed', reason: scenario === 'blocked' ? 'tool unavailable' : '' });
    fs.writeFileSync(path.join(dir, 'result.json'), scenario === 'bom' ? `﻿${result}` : result);
  }
  if (env.FAKE_USAGE_AFTER) fs.writeFileSync(env.FAKE_USAGE_FILE, env.FAKE_USAGE_AFTER);
}
