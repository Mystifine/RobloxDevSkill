---
name: roblox-dev
description: Dispatcher for Roblox game development. Use for any Roblox work - Luau scripting, services, modules, networking, DataStores, performance; UI/GUI/HUD, icons, ImageLabels; VFX, particles, ParticleEmitter, skill/ability effects, beams, trails; 3D models, meshes, tris budget, PBR, SurfaceAppearance; Toolbox, free models, asset or sound sourcing and safety audits; Blender-to-Roblox animation, rigging, skinning, .rbxanim. Loads only the reference needed.
---

# Roblox Dev (dispatcher)

Read the rules below, then load **only** the reference your task needs. Do not preload them all.

## Always

1. **Dependencies first.** Before writing code, read the project's manifests and layout (`wally.toml`, `rokit.toml`, `pesde.toml`, `default.project.json`, `Packages/`, `selene.toml`) and its existing utilities. Use what is already there instead of re-implementing it. If a dependency function is deprecated, buggy, slow or easy to misuse, tell the user: name the function, the problem and a safe alternative. Never silently patch a package.
2. **Follow the project's structure.** Put code where the outline says it belongs, one responsibility per module, and match the surrounding naming, comments and idiom. Respect the client/server boundary.
3. **Performance without downgrades.** Prefer backend wins (fewer allocations, events over polling, batched remotes, shared loops, cleanup). Never cut quality or visible features to save time. Measure before and after when a change is claimed as an optimization.
4. **Match the project.** UI, VFX and models follow the existing style, constants and asset tables before inventing new ones.
5. **No Toolbox code, ever.** Models, VFX and images may come from the Toolbox (audited, preferably temporary); Scripts, LocalScripts and ModuleScripts never. Sounds are the exception that may be kept.
6. **Verify, then report faithfully.** Lint, build and test in Studio where possible. Say what you ran, what failed and what you did not verify.
7. **UI is mobile first and stays in bounds; VFX spawns where it belongs.** Design and check the phone first; nothing leaks out of its box, rim or rounded corner; ground effects land on the floor (never at a character's hip, head or in the air). See `references/ui.md` and `references/vfx.md` section 5.

## Route

| Task | Load |
|---|---|
| Luau, modules, services, networking, data, optimization, tests | [references/coding.md](references/coding.md) |
| GUI, HUD, menus, icons, UI tweens | [references/ui.md](references/ui.md) |
| Particles, skill/ability/hit effects, lights, beams, trails | [references/vfx.md](references/vfx.md) |
| 3D models, meshes, textures, Blender asset creation | [references/modeling.md](references/modeling.md) |
| Toolbox, free models, images, sounds, any imported asset | [references/assets.md](references/assets.md) |
| Rigging, skinning, Blender animation, import to Roblox (R15/R6: looks for `animate-roblox-characters` first) | [references/animation.md](references/animation.md) |

A task can span several rows (a skill ability = coding + vfx + animation); load each reference once, when you reach that part.

## Scripts

- [scripts/ParticlePlayer.luau](scripts/ParticlePlayer.luau): fallback attribute-driven particle player. Use the project's own player if it has one.
- [scripts/VFXInspector.luau](scripts/VFXInspector.luau): VFX inspection (lint and repair particle exits, caster-sphere/target-cube stage with multi-angle cameras, vanish watcher, frozen frames for screenshots). Run it on every effect before calling it done; steps in [references/vfx.md](references/vfx.md) section 8.
- [scripts/UIBounds.luau](scripts/UIBounds.luau): UI bounds audit (children and outlines inside their boxes and rounded corners, clear of rims). Run it on every UI at the phone size first; steps in [references/ui.md](references/ui.md).
- [scripts/AssetAudit.luau](scripts/AssetAudit.luau): Toolbox asset safety audit. Run it on every imported asset before keeping anything.

## Handoffs (use if installed; otherwise follow the reference)

`blender-director` (plan), `blender-modeler`, `blender-retopology-uv`, `blender-pbr-materials`, `blender-texture-baking`, `blender-game-optimization`, `blender-asset-qa` (mandatory gate), `blender-export-pipelines`, `blender-character-rigging`, `blender-animation`, `animate-roblox-characters` (R6/R15 animation), `find-skills` (when no skill covers a need).
