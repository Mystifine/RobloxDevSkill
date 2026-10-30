# Codex handoff (Claude only)

When a handoff pays (section 2), Claude decides, briefs and accepts, and Codex executes on its own quota, so Claude's tokens go to design and review. **If you are Codex, ignore this file: you never hand off.** Needs the Codex CLI, logged in (`codex login`), plus Git, Node 20+ and Bash (Git Bash on Windows); one-time setup in the README, "Codex handoff".

`handoff` below means `bash ~/.claude/skills/roblox-dev/scripts/codex/handoff.sh` (a project-local install: `bash .claude/skills/roblox-dev/scripts/codex/handoff.sh`). Call it exactly that way, with `--cd` rather than a `cd` prefix, so its permission rule matches. Run `--brief` and `--wait` in the background (`run_in_background: true`); their completion notifies you, so never poll.

## 1. Start: check, then settle open handoffs

Run `handoff --check` before the first handoff of a session. It checks the CLI, login and MCP servers, probes the model (cached 12 h), reads usage and **lists every open handoff**: running, waiting (paused by a limit or queued for room), finished but not cleaned, and leftover worktrees, each with its commands. If anything is listed, **ask the user what to do with each** (AskUserQuestion, up to four per call; group many similar ones) before starting new work, then act on the answers:

| Listed | Choices (the listing prints each command) |
|---|---|
| running | let it run; or stop it (`--cancel`), then take over or drop it |
| waiting | keep waiting (`--wait` in the background); launch now (`--ignore-limit`); take over; drop (`--clean`) |
| finished | review and accept, then `--clean`; take over; drop (`--clean`, with `--discard` for unintegrated worktree work) |
| leftover worktree | integrate its work, then remove it; or remove it |

`handoff --list` prints the same list without the checks and without calling Codex; SKILL.md runs it at the start of every session that uses this skill.

## 2. Whether to hand off

Decide at the start of each sizable task, not once per session. Hand off only when all three hold; otherwise do the task yourself:
1. **Decided:** a spec Codex can finish without asking (on ambiguity it blocks or guesses).
2. **Cheaper than doing it yourself, overhead included.** The handoff costs orienting enough to brief (reading what Codex will change), the brief itself, waiting (minutes per run: a code run took 1m45s, an image run 3m20s, seen 2026-10-29), the review (the summary, every critical changed line, visuals at full size), usually one fix round for visual work, and the whole task again if it fails and you take over. It pays when your own execution would be long: many files or long scripts to write and read, a long build-and-verify loop whose renders and logs would fill your context, bulk mechanical edits, images. It does not pay for a tight loop that needs your judgment at every step (each step's brief and review cost what doing it does).
3. **Room:** `handoff --usage` (section 3) shows room for its kind now. Without room, do code yourself; queue images.

| Usually pays | Stays with Claude |
|---|---|
| Building a decided spec: features, systems, UI screens, refactors and ports across many files | Design, trade-offs, creative direction, talking with the user, acceptance |
| Bulk and mechanical edits; config and data tables; docs, specs and tests | Small edits, where a brief and a review cost as much |
| Images: icons, textures, thumbnails, concept sheets (`--kind image`) | Critical code: DataStores and saves, ProcessReceipt and purchases, remote validation, migrations (or hand it off with explicit invariants and review every changed line) |
| Blender models, rigs and animation; Studio map building, VFX tuning and inspector runs; long verification loops | Anything that needs the user mid-task |

## 3. Usage before every batch

`handoff --usage` reads the account's live limits without a model turn (about 2 s): the 5-hour and weekly windows (percent used, reset times), whether usage is allowed, the active runs, what a code run and an image run each cost, and **room: how many more runs of each kind fit now**. A kind's cost is the upper quartile of its recent runs measured alone, so one Blender build (36% of the 5-hour window) keeps the code estimate honest where a median of all runs said 4% (seen 2026-10-29); until three runs of a kind exist, it is a cautious default or the costliest so far. Launch at most that many and do the rest yourself. A launch without room is refused before anything starts (exit 2): code stays with you, while image work (`--kind image`, or any launch with `--queue`) is queued for `--wait`. Launches sent together can't overshoot, because the room is checked again under a lock. `CODEX_HANDOFF_MAX_RUNS` caps parallel runs (default 3).

## 4. Brief

Orient only enough to decide, then write the brief to a unique file in your scratch folder (omit empty sections):

```markdown
# Task
## Goal
## Context        <working dir; paths, references, decisions; skill references by path>
## Requirements   <observable behavior; exact spec or creative payload>
## Deliverables   <paths, formats, sizes, names>
## Constraints    <allowed edits; what to preserve; outward actions authorized, or "none";
                   if ambiguity changes the decided design, report blocked; else choose conservatively and note it>
## Verification   <commands, invariants, this skill's mandatory checks with their output as evidence;
                   visual work: a labeled contact sheet <= 1600 px>
## Phases         <work over about 45 minutes or several deliverables: numbered, independently verifiable>
```

- **Point, don't paste.** Codex reads the project's AGENTS.md, the project's handoff `LESSONS.md` and this skill (the wrapper names its folder), so cite references by path (`references/ui.md`) and name the mandatory checks that apply: UIBounds for UI, VFXInspector for effects, AnimationInspector for animations, ZFight for models and maps, RigAudit for characters, AssetAudit for Toolbox imports.
- **Studio:** name the place and say Codex may run Play tests and temporary fixtures in it (it cannot ask; one run stopped to confirm its target), and pass `--mcp Roblox_Studio`. While a handoff holds Studio, don't drive it yourself. Blender likewise (`--mcp blender`).
- **Critical code:** write the invariants and test cases into the brief.
- **UI:** a spec, not a vibe: colors, fonts, sizes, strokes, spacing and a wireframe per screen size; selected, empty, loading, error, disabled and long-text states; mock data. For a new style, give a small working style kit first; later screens reuse it. Require UIBounds clean at every screen size and a contact sheet of the key states; check one phone view at full size yourself, in the longest-text state.
- **3D models: two runs, with a clay review between.** Run 1 builds the blockout to the reference and stops: gray renders from the front, side and three-quarter beside the reference, and the triangle count. Review them at full size (silhouette, proportions, style, `references/characters.md` for characters), brief shape fixes as a follow-up on the same thread until it passes, then run the follow-up for UVs, textures, QA, export and renders. Box cuirasses and primitive bodies went through bakes and renders unchecked in one run, at 36% of the 5-hour window (seen 2026-10-29); at the clay stage they cost a follow-up.
- **Rebuildable deliverables:** the wrapper tells Codex to keep anything a deliverable needs after the run (intermediate files its delivered scripts read) beside the deliverables, never in the run directory, which cleanup deletes.
- **Images:** the exact prompt, size (icons: 512x512 transparent PNG, `references/ui.md`), palette, framing, an example to match (`--image`), and where finals and originals go. `--kind image` adds the image rules to Codex's prompt: at most 5 reference images per generation; originals copied, never edited; prompts per `references/characters.md` and `references/no-gore.md`; a moderation block reworded once within the design, then reported.
- **Outward actions** (publishing, uploading, commit or push, purchases, deleting user files) only with the user's explicit authorization, written into the brief.
- Reuse approved briefs from the project's handoff `templates/`.

## 5. Launch

`handoff --brief "<brief>" --cd "<checkout>" [--kind image] --note "<note>"`, in the background. The note (at most 1500 characters) is the context that survives `/clear`: review criteria, next steps, the scope the user authorized.

- **Parallel:** one run per checkout. `--worktree` gives each run a detached worktree from a clean HEAD (without uncommitted or ignored files such as `Packages/`); or pass prepared worktrees with `--cd`.
- **Apps:** `--mcp <server>` enables only that server and locks it across handoffs; callers sharing one app also pass the same `--resource <name>`.
- **Sandbox:** the default `danger-full-access` is unsandboxed (the Windows sandbox failed under concurrent runs). Honor `CODEX_HANDOFF_SANDBOX` or `--sandbox`; never widen it.
- **Shared output folders:** `--add-dir DIR` adds a writable root but locks nothing, so runs delivering to one folder (Downloads, a project's `assets/`) start together; give each run its own file names in it. Only `--cd` is exclusive.
- **Other:** `--image FILE` (repeatable), `--timeout-min N` (180), `--name SLUG`; `--model` and `--effort` only when the user asks; `--cancel "<run dir>"` stops a run's process tree.

## 6. When a run ends

The summary's second line, `next:`, says what to do; follow it.

- **COMPLETED** (a finished turn and a result.json claiming every requirement) still needs your acceptance. Review in proportion: the summary lists the changed files; read every line of critical code and new logic in `changes.patch`, sample mechanical edits and let the checks cover them, run the project's checks, and compare visuals with the payload at full size where it matters (Codex saying it looked is not evidence). For a fix round, brief the concrete defects with expected values and run the summary's `follow-up:` command; the same defect twice, fix it yourself.
- **Anything else: take over** *(default)*. Finish the brief yourself from the checkout (the patch shows what Codex changed) and its checkpoint; relaunch only if the user asks.
- **Images are the exception:** Claude cannot generate them, so they stay with Codex. Fix the cause (reword a blocked prompt, at most 5 references) and run the follow-up; after a capacity error, retry in a few minutes; after a usage limit, start `handoff --wait` in the background and tell the user when it resumes (its output carries the resume command, even after `/clear`). Do any non-image remainder yourself.

## 7. Finish and clean up

Clean each handoff as soon as it is settled (accepted, taken over or dropped): `handoff --clean <thread>` (or `"<run dir>"` for a run without a thread). It logs the task's Codex and Claude usage to the project's `usage.tsv` (the Claude figure counts all session activity since the first run), then deletes its run directories, Codex's copies of generated images (keep the ones you need in the project first) and its worktree. A worktree holding changes its main checkout doesn't have stops the clean with nothing removed: integrate them first, or add `--discard`. So does a delivered file that still names the run directory (a rebuild script keeping its intermediates there): move what it needs beside the deliverables and fix the path, or add `--discard`. Also delete the brief and any other scratch you made for the task. Every launch and check prunes runs older than 3 days (never running or waiting jobs, never work that exists only in a worktree), and a passed probe leaves nothing behind.

After integrating all accepted work, run the project's end-of-task steps once in the main checkout. Save a reusable approved brief in the project's `templates/`, and add a one-line `LESSONS.md` rule for a demonstrated mistake. Tell the user what changed, how it was verified and what remains.

Files live in `~/.claude/codex-handoffs` (`CODEX_HANDOFF_HOME`), one folder per project: `templates/`, `LESSONS.md`, `ledger.tsv`, `usage.tsv`, run directories and `worktrees/`. Exit codes: 0 ok; 1 failed; 2 usage limit, no room or queued; 3 timeout; 4 blocked, cancelled, needs review or a refused clean; 64 arguments; 69 CLI or config; 70 login; 71 no usable model or at capacity; 75 busy. On a failure read only the summary and the relevant log tail.
