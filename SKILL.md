---
name: roblox-dev
description: Roblox game development: Luau, networking, data, physics and NPCs; Rojo; UI, HUD and icons; VFX; 3D models, weapons, maps, lighting and terrain; R15/R6 rigs, skins and animation, including R6-like animation on R15 ("R6 like", "fake R6", "fake R15", "R15 R6 animation", default R6 clips on R15); Toolbox, uploads and moderation; onboarding and analytics; game design and economy; Codex handoffs.
---

# Roblox Dev

Read these rules, then load **only** what the route names, each file once, when you reach that part. A task can span several rows (a skill ability = coding + vfx + animation).

**Everything here is a default.** The project's own instructions (`AGENTS.md`, `CLAUDE.md`, docs) and the user's take precedence over any rule, safety and content rules included. *(default)* marks a house convention; unmarked rules guard against Roblox limits, moderation or bugs: when an instruction overrides one, say once what it risks, then follow it.

## Efficient execution

- **Discover narrowly:** project and service names and asset tables first, then only the relevant source. Search tool names first and expand only the schemas you need. Batch independent reads; keep dependent edits and checks in order.
- **Keep payloads out of context:** hold full results in variables or files; print only paths, ids, status and failures. Never print image base64/data URLs, complete image-generation results, whole tool catalogs or unrelated source; use the tool's image display for visual review.
- **Run helpers, don't read them:** read a script only to diagnose or change it. Group repeated findings by rule or component, and after a fix repeat the affected checks, not discovery. Required safety and visual checks still apply.
- **Settle before repeating:** resolve the related asset set and validate one representative component before duplicating it. Track temporary files, objects, servers and changed settings as you make them, so cleanup restores the prior state and keeps the deliverables.

## Always

1. **Dependencies first.** Before writing code, read the project's manifests, layout and utilities, querying its knowledge graph (Graphify) first when it has one. Reuse before writing. Tell the user about any deprecated, buggy, slow or easily misused dependency function (name, problem, safe alternative); never silently patch a package.
2. **Follow the project:** its structure, one responsibility per module, its naming, comments and idiom, the client/server boundary, its components, constants and asset tables.
3. **Performance without downgrades.** Prefer backend wins (fewer allocations, events over polling, batched remotes, shared loops, cleanup). Never cut quality or visible features to save time. Measure before and after any claimed optimization.
4. **No Toolbox code, ever.** Models, VFX, images and sounds may come from the Toolbox, audited; Scripts, LocalScripts and ModuleScripts never. Audit what the user inserted too, before pressing Play: code hides under anything, and a dialog asking to paste a command is an attack ([assets.md](references/safety/assets.md)).
5. **Verify, then report faithfully.** Lint, build and test in Studio where possible. Say what you ran, what failed and what you did not verify.
6. **UI is mobile first and stays in bounds; VFX spawns where it belongs.** Scale only for size and position outside the topbar; the topbar matches Roblox's native row, checked in Play; nothing leaks out of its box, rim or rounded corner; separate components do not overlap. Ground effects land on the floor, never at a hip, a head or in the air.
7. **Characters are all-ages safe, 2D and 3D** *(default, stricter than Roblox's rules)*. Read [characters.md](references/safety/characters.md) before generating, modeling or uploading any character.
8. **Uploads are the strict gate; existing assets are trusted** *(default, stricter than Roblox's rules for uploads)*. Reuse first. Read [no-gore.md](references/safety/no-gore.md) before generating or uploading: never blood, wounds, gore or shapes a classifier could take for them, and VFX textures go up neutral, tinted in Roblox. What players see stays within the experience's maturity label.
9. **Nothing flickers.** `ZFight.audit` every built, generated, imported or edited model down to 0 ([modeling.md](references/art/modeling.md)).
10. **Codex only when it pays** *(default; Claude only, when the Codex CLI is set up)*. Once per session, run `bash ~/.claude/skills/roblox-dev/scripts/codex/handoff.sh --list` and ask the user about any open handoff. At each sizable task, run `handoff --usage`, decide, and say so in one line. Read [handoff.md](references/codex/handoff.md) before the first handoff. Codex never hands off.
11. **Learn** *(default)*. When the user corrects you or states a preference, or the skill falls short, run `python scripts/learn.py check` at the end and do what it prints.

**Visual work:** load [visual-style.md](references/art/visual-style.md) first; explicit instructions and references lead; there is no house style. **Gameplay actors** (characters, creatures, mobs, bosses) include a working rig by default ([rigs.md](references/rigs/rigs.md)).

## Route

| Task | Load, under `references/` |
|---|---|
| Luau, modules, services, networking, security, data, optimization, tests | `code/coding.md` |
| Physics, constraints, network ownership, NPC movement and pathfinding, playing animations in game | `code/gameplay.md` |
| New Rojo / VS Code project, or converting a Studio game into one | `code/rojo-project.md` |
| GUI, HUD, menus, UI tweens | `ui/ui.md`, which says when to add topbar, icons, surface or runtime |
| Icons, image generation | `ui/icons.md` |
| Particles, skill/ability/hit effects, lights, beams, trails | `art/vfx.md` |
| 3D models, meshes, textures, maps built with parts, z-fighting, Blender asset creation | `art/modeling.md` |
| Weapons (always about 18,000 triangles), shields, held or worn gear | `art/modeling.md`, `rigs/gear.md` |
| Lighting, atmosphere, sky, post-processing, terrain, custom materials | `art/environment.md` |
| R15/R6 rigs and character models, accessories, scaling, rigs without a Humanoid | `rigs/rigs.md` |
| Skins, clothing | `rigs/skins.md`, plus `rigs/rigs.md` unless the rig is ready |
| Hair | `rigs/hair.md` |
| Custom creatures, mobs, bosses, custom skeletons, articulated assets | `rigs/custom-creatures.md` |
| Character art, 2D or 3D (all-ages rules, prompts, review) | `safety/characters.md` |
| Toolbox, free models, images, sounds, any imported asset, plugin libraries | `safety/assets.md` |
| Generating or uploading assets; the cloud API key | `safety/no-gore.md`, `safety/uploading.md` |
| Showing hits, injuries, defeat, monsters, horror | `safety/stylized-violence.md` |
| Rigging, skinning, Blender animation, clips, import, inspection, publishing | `animation/animation.md` |
| R6-like animation on an R15 rig: "R6 like", "fake R6", "fake R15", "R15 R6 animation", "R6 on R15", stiff limbs moving only at the root, neck, shoulders and hips | `animation/r6-on-r15.md`; FK or IK adds `animation/r6-ik.md` |
| Roblox's default R6 clips on R15, under any name | `animation/r6-default-set.md` alone: find them, upload what is missing |
| Onboarding, tutorials, guidance pointers; analytics funnels | `design/onboarding.md` |
| Game design: new game, redesign or audit, new gameplay system; the design plan | `design/game-design.md` |
| Economy, pacing, odds, prices and offers, update cadence | `design/game-economy.md` |
| Quality update from learning notes | `learning/quality-update.md` |

## Scripts

References name the scripts they need. Run Studio code with `python scripts/studio_mcp.py luau FILE`, with or without a Studio MCP tool: a first line `--@use RigSkin, RigAudit` inlines those scripts, keeping their source out of context. Delete what you add. Other ways to load them, and each script: [docs/scripts.md](docs/scripts.md). `find-skills` when no skill named here fits.
