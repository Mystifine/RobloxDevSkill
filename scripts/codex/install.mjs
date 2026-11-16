// Merges the Claude Code permission rules that let the handoff wrapper run without a prompt; --uninstall takes them out
// again (the skill's uninstallers run it). Idempotent; keeps every other setting and rule; leaves invalid JSON untouched;
// never changes the permission mode.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { atomicWrite, withLock } from './state.mjs';

const wrapper = 'bash ~/.claude/skills/roblox-dev/scripts/codex/handoff.sh';
const permission = `Bash(${wrapper} *)`;
const autoModeRule = `Running the roblox-dev Codex handoff wrapper (${wrapper} ...) to read Codex usage and to launch, queue, resume, list, check, cancel or clean local Codex CLI runs, including with --sandbox danger-full-access.`;
const configDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');
const settingsPath = path.join(configDir, 'settings.json');
const uninstall = process.argv.includes('--uninstall');
const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
// One current auto-mode rule for this wrapper, recognised by its opening words whatever its wording.
const ours = (rule) => typeof rule === 'string' && rule.startsWith('Running the roblox-dev Codex handoff wrapper');
function child(parent, key, label, initial) {
  if (parent[key] === undefined) parent[key] = initial;
  const value = parent[key];
  if (Array.isArray(initial) ? !Array.isArray(value) || value.some((entry) => typeof entry !== 'string') : !isObject(value)) {
    throw new Error(`${label} must be ${Array.isArray(initial) ? 'an array of strings' : 'a JSON object'}.`);
  }
  return value;
}
function read() {
  let settings = {}, mode = 0o600;
  try {
    settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
    mode = fs.statSync(settingsPath).mode;
  } catch (error) {
    if (error instanceof SyntaxError) throw new Error(`Cannot parse ${settingsPath}; it was left unchanged. Fix the JSON and rerun.`);
    if (error.code !== 'ENOENT') throw error;
  }
  if (!isObject(settings)) throw new Error(`${settingsPath} must contain a JSON object.`);
  return { settings, mode };
}
function add() {
  const { settings, mode } = read();
  const allow = child(child(settings, 'permissions', 'settings.permissions', {}), 'allow', 'settings.permissions.allow', []);
  const auto = child(child(settings, 'autoMode', 'settings.autoMode', {}), 'allow', 'settings.autoMode.allow', ['$defaults']);
  let changed = false;
  if (!allow.includes(permission)) { allow.push(permission); changed = true; }
  // An older wording is replaced where it stood, duplicates dropped.
  const index = auto.findIndex(ours);
  if (index < 0) { auto.push(autoModeRule); changed = true; }
  else if (auto[index] !== autoModeRule || auto.filter(ours).length > 1) {
    const merged = auto.map((rule, i) => (i === index ? autoModeRule : rule)).filter((rule, i) => i === index || !ours(rule));
    auto.splice(0, auto.length, ...merged);
    changed = true;
  }
  // Atomic, and retried while Windows briefly holds the file (antivirus, indexer).
  if (changed) atomicWrite(settingsPath, `${JSON.stringify(settings, null, 2)}\n`, mode);
  console.log(changed ? `Installed the Codex handoff permissions in ${settingsPath}.` : `The Codex handoff permissions are already in ${settingsPath}.`);
  console.log('The Claude Code permission mode was not changed. Handoffs default to --sandbox danger-full-access; override with --sandbox or CODEX_HANDOFF_SANDBOX.');
}
function remove() {
  const { settings, mode } = read();
  let changed = false;
  const allow = settings.permissions?.allow;
  if (Array.isArray(allow) && allow.includes(permission)) {
    settings.permissions.allow = allow.filter((rule) => rule !== permission);
    changed = true;
  }
  const auto = settings.autoMode?.allow;
  if (Array.isArray(auto) && auto.some(ours)) {
    settings.autoMode.allow = auto.filter((rule) => !ours(rule));
    changed = true;
  }
  if (changed) atomicWrite(settingsPath, `${JSON.stringify(settings, null, 2)}\n`, mode);
  console.log(changed ? `Removed the Codex handoff permissions from ${settingsPath}.` : `No Codex handoff permissions in ${settingsPath}.`);
}
async function main() {
  if (uninstall && !fs.existsSync(settingsPath)) {
    console.log(`No ${settingsPath}: no Codex handoff permissions to remove.`);
    return;
  }
  fs.mkdirSync(configDir, { recursive: true });
  return withLock(configDir, uninstall ? remove : add);
}
main().catch((error) => {
  console.error(`codex handoff ${uninstall ? 'uninstall' : 'install'}: ${error.message}`);
  process.exitCode = 1;
});
