---
name: roblox-dev
description: Dispatcher for Roblox game development. Use for any Roblox work - Luau scripting, services, modules, networking, DataStores, performance; Rojo/VS Code project setup and converting a Studio game into a Rojo project; UI/GUI/HUD, icons, ImageLabels; character art and portraits (all-ages safety); VFX, particles, ParticleEmitter, skill/ability effects, beams, trails; 3D models, meshes, tris budget, PBR, SurfaceAppearance, building maps with parts, z-fighting and flicker; Toolbox, free models, asset or sound sourcing, uploads and safety audits; Blender-to-Roblox animation, rigging, skinning, .rbxanim; onboarding/tutorial guidance and AnalyticsService funnels. Loads only the reference needed.
---

# Roblox Dev (dispatcher)

Read the rules below, then load **only** the reference your task needs. Do not preload them all.

## Always

1. **Dependencies first.** Before writing code, read the project's manifests and layout (`default.project.json`, `wally.toml`/`pesde.toml`, `rokit.toml`, `Packages/`, `selene.toml`) and its existing utilities, querying its knowledge graph (Graphify) first when it has one. Reuse what exists instead of re-implementing it. Tell the user about any dependency function that is deprecated, buggy, slow or easy to misuse (name, problem, safe alternative); never silently patch a package.
2. **Follow and match the project.** Code goes where its structure says, one responsibility per module, in the surrounding naming, comments and idiom, respecting the client/server boundary. UI, VFX and models reuse its style, constants and asset tables before inventing new ones.
3. **Performance without downgrades.** Prefer backend wins (fewer allocations, events over polling, batched remotes, shared loops, cleanup). Never cut quality or visible features to save time. Measure before and after when a change is claimed as an optimization.
4. **No Toolbox code, ever.** Models, VFX and images may come from the Toolbox (audited, preferably temporary); Scripts, LocalScripts and ModuleScripts never. Sounds are the exception that may be kept.
5. **Verify, then report faithfully.** Lint, build and test in Studio where possible. Say what you ran, what failed and what you did not verify.
6. **UI is mobile first and stays in bounds; VFX spawns where it belongs.** Design and check the phone first; nothing leaks out of its box, rim or rounded corner; ground effects land on the floor (never at a character's hip, head or in the air). See `references/ui.md` and `references/vfx.md` section 5.
7. **Characters are all-ages safe, 2D and 3D.** Female designs are fine with a flat chest, no cleavage, and in-character armor or clothing over the chest and at least 70% of the torso, the chest piece unlike the skin. Read `references/characters.md` before generating, modeling or uploading any character.
8. **Nothing flickers.** No two visible faces may overlap in the same plane, and no two decals may share a face and a ZIndex. Run `ZFight.audit` on every built, generated, imported or edited model and settle it to 0 (`references/modeling.md`).

## Route

| Task | Load |
|---|---|
| Luau, modules, services, networking, data, optimization, tests | [references/coding.md](references/coding.md) |
| New Rojo / VS Code project, or converting a Studio game into one | [references/rojo-project.md](references/rojo-project.md) |
| GUI, HUD, menus, icons, image generation, UI tweens | [references/ui.md](references/ui.md) |
| Particles, skill/ability/hit effects, lights, beams, trails | [references/vfx.md](references/vfx.md) |
| 3D models, meshes, textures, building with parts (maps), z-fighting, Blender asset creation | [references/modeling.md](references/modeling.md) |
| Character art or models, 2D or 3D (all-ages rules, prompts, review) | [references/characters.md](references/characters.md) |
| Toolbox, free models, images, sounds, any imported asset; uploads and API keys | [references/assets.md](references/assets.md) |
| Rigging, skinning, Blender animation, import, inspection, publishing (R15/R6: `animate-roblox-characters` first) | [references/animation.md](references/animation.md) |
| Onboarding, tutorials, guidance pointers, analytics funnels | [references/onboarding.md](references/onboarding.md) |

A task can span several rows (a skill ability = coding + vfx + animation); load each reference once, when you reach that part.

## Scripts

Load a Luau script into Studio with `loadstring(game:GetService("HttpService"):GetAsync(url, true))()`, served by a local static server on this folder (`python -m http.server 8394 --bind 127.0.0.1 --directory <skill>/scripts`; allow HTTP requests in Game Settings if Studio refuses). The client has no `loadstring`, so there use a temporary ModuleScript. Delete what you add when done.

- [UIBounds](scripts/UIBounds.luau): mandatory bounds audit, phone size first (ui.md). [icon_outlines.py](scripts/icon_outlines.py): an icon set's outline style and the icons that break it (ui.md; Python with numpy and Pillow).
- [VFXInspector](scripts/VFXInspector.luau): mandatory effect check (vfx.md section 8). [ParticlePlayer](scripts/ParticlePlayer.luau): fallback particle player; use the project's own first.
- [AnimationInspector](scripts/AnimationInspector.luau): mandatory clip audit and contact sheet (animation.md section 4).
- [ZFight](scripts/ZFight.luau): mandatory z-fighting audit and fix for every build (modeling.md).
- [AssetAudit](scripts/AssetAudit.luau): mandatory audit of every imported asset (assets.md).
- [TutorialGuide](scripts/TutorialGuide.luau): tutorial pointers and UI lock (onboarding.md).
- [GameInventory](scripts/GameInventory.luau): scripts, dependencies and Studio content of a game being converted (rojo-project.md).

Blender and animation skill chains: modeling.md, animation.md; `find-skills` when nothing fits.
