# RobloxDevSkill

A token-efficient agent skill for Roblox game development (Claude Code, Codex and any agent that reads `SKILL.md` skills).

`SKILL.md` is a short dispatcher: eleven always-on rules, shared visual-style routing, asset-readiness decisions and a routing table. Agents load only the references for the task at hand, so a UI tweak never pays for the modeling guide. [docs/developing.md](docs/developing.md) holds the limits that keep it that way. Visual direction follows instructions/references, then comparable project assets, then a suitable inferred treatment; there is no fixed house style. Gameplay actors include a tested rig by default unless explicitly static or a modeling-only stage; rigging alone does not add a full animation set or AI. Materials, maps and resolution adapt to the intended result rather than requiring full PBR. Everything in it is a default: a project's own `AGENTS.md`, `CLAUDE.md` and docs, and the user's instructions, take precedence over every rule, the safety and content rules included. Rules marked *(default)* are house conventions; the unmarked ones guard against Roblox limits, moderation or bugs, so the agent names the risk once and then follows the instruction. The project blueprint (`assets/templates/PROJECT_STRUCTURE.md`: packages, Graphify) is the author's own setup.

```
SKILL.md                 dispatcher: always-on rules and the route table, read on every task
references/              read only when the route names them; each file serves one kind of task
  code/                  coding, gameplay (physics, NPCs, playing animations), rojo-project
  ui/                    ui (the workflow), topbar, icons, surface (fades and shine), runtime (state, world-space GUIs)
  art/                   visual-style, modeling, environment, vfx, cutscenes (cinematic cameras, timelines), audio (sound, music, mixing), video (watching references and recordings),
                         styles/ (stud, anime-ink, hand-painted, realistic, low-poly, simulator-cartoon)
  rigs/                  rigs (R15, R6, no Humanoid, audits), custom-creatures, skins, hair, gear
  animation/             animation (clips, export, inspection), r6-on-r15, r6-ik, r6-default-set
  safety/                characters (all-ages), no-gore (uploads), stylized-violence (what players see), assets (Toolbox intake), uploading
  design/                game-design, game-economy, onboarding (tutorials), analytics (funnels, custom events, the 10 funnel slots, releases and reviews), journeys
  codex/                 handoff (Claude only)
  learning/              learning (notes kept on the maintainer's machine), quality-update (turning them into skill changes)
scripts/                 run, not read: Studio audits and helpers, Blender kits, upload tools, the Codex wrapper, learning notes
assets/
  templates/             PROJECT_STRUCTURE (project blueprint), GAME_DESIGN_PLAN (written to a project's docs/game-design.md)
  r6-on-r15/clips/       Roblox's 23 default R6 animations as R15 KeyframeSequences, ready to upload
docs/
  scripts.md             what each script does, where it runs, how to load it, what it was tested on
  checks.md              the record of what was tested and found
  developing.md          how to change the skill without growing it: budgets, rules, measuring
tests/                   Lune, Python, Node, Blender and Studio regressions (docs/checks.md has the commands)
install/, INSTALL.md     placement rules, installers
rokit.toml, selene.toml  pinned Lune and Selene, lint settings
.github/workflows/       CI: the specs and Selene on every push and pull request
.mcp.json                repository-only Studio and Blender MCP access (excluded by installers)
```

## Install

The skill installs to `~/.agents/skills/roblox-dev`. If `~/.claude` exists, Claude gets a link to that copy (never a second copy); if only `~/.claude` exists, it installs there. Add `-Local` / `--local` to install into the current project instead.

```powershell
irm https://raw.githubusercontent.com/Mystifine/RobloxDevSkill/main/install/install.ps1 -OutFile install.ps1; ./install.ps1
```

```sh
curl -fsSLO https://raw.githubusercontent.com/Mystifine/RobloxDevSkill/main/install/install.sh && sh install.sh
```

Full rules, options and manual steps: [INSTALL.md](INSTALL.md).

## Codex handoff (Claude Code, optional)

When it is cheaper than doing the task in Claude (the brief, review and fix rounds counted) and the account has room, Claude decides and reviews while the local [Codex CLI](https://github.com/openai/codex) does the execution on its own quota: decided code, bulk edits, Studio and Blender work, and image generation. The wrapper reads the account's live usage before every launch (no model turn), refuses or queues runs that would not fit, takes failed code back to Claude (images stay with Codex), lists open handoffs for the user to settle, and cleans up after each task. Rules: `references/codex/handoff.md`. It merges the earlier CodexHandoffSkill.

One-time setup (Git Bash on Windows):

```sh
npm install -g @openai/codex && codex login
node ~/.claude/skills/roblox-dev/scripts/codex/install.mjs      # Claude permission rules for the wrapper (merged, idempotent)
bash ~/.claude/skills/roblox-dev/scripts/codex/handoff.sh --check
```

Configure the MCP servers Codex needs (Roblox Studio, Blender) once in Codex (`codex mcp list`); Claude's are not shared. Runs default to `--sandbox danger-full-access` (`CODEX_HANDOFF_SANDBOX` to change it). State lives in `~/.claude/codex-handoffs` (`CODEX_HANDOFF_HOME`).

## Learning notes

The skill can keep notes for its maintainer on what using it teaches: what was asked and attached, what came out, the reaction, and what the skill should change. Nothing is sent anywhere. Notes are off until you turn them on, so anyone else who installs the skill writes nothing:

```sh
python scripts/learn.py on     # off stops new notes and keeps the ones there
```

- **Taking notes:** when a task teaches the skill something, the agent writes a note in the [format](references/learning/learning.md) and [scripts/learn.py](scripts/learn.py) files it under `~/.roblox-dev/learning/notes` (`ROBLOX_DEV_LEARNING_HOME`). That is outside the skill's folder, which installs replace, and outside the system's temp folder, which gets cleaned.
- **Using them:** now and then, ask the agent for a quality update. It reads the notes, proposes changes, applies what you approve under the [developing rules](docs/developing.md), and archives what it dealt with. The process is in [quality-update.md](references/learning/quality-update.md).

## Related skills

The [R6-like references](references/animation/r6-on-r15.md) cover R6-like animation on real R15 rigs, also called "R6 like", "fake R6", "fake R15" or "R15 R6 animation": six moving joints, nine locked joints, FK and IK that behave like R6's in Studio and Blender, Roblox's default R6 clips rebuilt for R15, smooth locomotion, compact jump/fall arcs, and validation. The dispatcher routes matching requests to them.

The skill hands off to Blender and animation skills when they are installed, loading only those a task needs (`blender-director`, `blender-asset-qa`, `blender-game-optimization`, `blender-export-pipelines`, `blender-character-rigging`, `animate-roblox-characters`, `find-skills`, and others named in the references). Without them it falls back to the rules in each reference.

## Repository MCP access

The tracked `.mcp.json` enables Roblox Studio and Blender MCP while developing this repository in a client that reads project MCP files. It copies the existing Windows setup: Studio's `%LOCALAPPDATA%\Roblox\mcp.bat` through `cmd`, and Blender through `uvx --python 3.11 mcp-for-blender`. Studio needs its MCP server enabled; Blender needs its MCP add-on running. Adapt the Studio command for other operating systems. The config contains no credentials.

The installers exclude `.mcp.json` from skill copies and global updates. Developer junctions/symlinks to the full repository still expose it; see [INSTALL.md](INSTALL.md).

## License

MIT
