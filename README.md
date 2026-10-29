# RobloxDevSkill

A token-efficient agent skill for Roblox game development (Claude Code, Codex and any agent that reads `SKILL.md` skills).

`SKILL.md` is a short dispatcher: nine always-on rules plus a routing table. Agents load only the reference for the task at hand, so a UI tweak never pays for the modeling guide. Everything in it is a default: a project's own `AGENTS.md`, `CLAUDE.md` and docs, and the user's instructions, take precedence over every rule, the safety and content rules included. Rules marked *(default)* are house conventions; the unmarked ones guard against Roblox limits, moderation or bugs, so the agent names the risk once and then follows the instruction. The project blueprint (`assets/PROJECT_STRUCTURE.md`: packages, Graphify) is the author's own setup.

```
SKILL.md                 dispatcher (always loaded, about 50 lines)
references/
  coding.md              dependencies, structure, backend performance, security, data limits and erasure, pitfalls, verification
  gameplay.md            physics movers, network ownership, NPC pathfinding, playing animations in game
  rojo-project.md        new Rojo project or Studio-game conversion: folder, blueprint, inventory, rebuild, switch-over, parity tests
  ui.md                  mobile first, in bounds (UIStroke), safe areas, centered anchors, Studio previews, state, world-space GUIs, icons
  vfx.md                 research, tuning, EmitDelay/EmitDuration/EmitCount, smooth in/out, placement, inspection
  modeling.md            20k tri limit (18k for top tier), full PBR, Blender workflow, no z-fighting
  environment.md         Unified Lighting, atmosphere, sky, post-processing, terrain, custom materials
  rigs.md                character models: R15 from a HumanoidDescription (seat, clean), parts, joints, attachments, accessories, R6
  characters.md          all-ages character rules (2D and 3D): flat chest, no cleavage, 70% in-character cover, review
  no-gore.md             blood and gore: strict uploads (false-positive margin, neutral textures), trusted existing assets, stylized play
  assets.md              Toolbox policy (no code), safe intake, sounds, the upload gate, uploads (key by asset type, public)
  animation.md           60 FPS, weighted joints, feet on the ground, export, publish, inspection
  onboarding.md          show-don't-tell tutorials, pointer choices, funnel rules (10 funnels, custom fields)
  game-design.md         fantasy, direction, simple vs deep, loops, progression, retention, social, review
  game-economy.md        currencies, pacing (PacingSim), odds, monetization, paid random items, live ops
assets/
  PROJECT_STRUCTURE.md   project blueprint: layout, Rojo map, packages, toolchain, AGENTS.md, MCP, Graphify
  GAME_DESIGN_PLAN.md    game design plan template, written to the project's docs/game-design.md
scripts/
  UIBounds.luau          UI bounds audit: nothing leaks out of its box, rim or rounded corner
  icon_outlines.py       icon set outline style (white sticker border or not) and the icons that break it
  VFXInspector.luau      VFX inspection: exit lint, sphere/cube or real-rig stage, vanish watcher, frozen-frame captures
  ParticlePlayer.luau    fallback attribute-driven particle player (scaled by quality and measured frame rate, min 1)
  AnimationInspector.luau  animation inspection: exact-time audit (pops, seams, feet, hyperextension, markers) and contact sheet
  ZFight.luau            z-fighting audit and fix: coplanar overlapping faces and decal ZIndex ties
  RigAudit.luau          character model audit (R15/R6): parts, joints, root, seated accessories, cages, leftovers; seat, clean
  AssetAudit.luau        Toolbox safety audit: report first, then strip
  TutorialGuide.luau     tutorial pointers: spotlight, 3D focus, arrow, elevated beam, camera assist, UI lock
  GameInventory.luau     Studio-to-Rojo inventory: scripts and what they touch, content counts, export, leftovers
  export_place.luau      Lune: every script of a saved place file written to disk, byte for byte
  UIParity.luau          port vs original: per-window fingerprints of every visible text and image, scroll sweeps
  PacingSim.luau         pacing model (Lune): milestone times for casual and optimizing players, odds tables
tests/
  run.luau               Lune specs for the pure-Luau scripts (PacingSim)
install/
  install.ps1            Windows installer (junction); install.sh for macOS/Linux (symlink)
INSTALL.md               placement rules, options, manual steps
rokit.toml, selene.toml  pinned Lune and Selene, lint settings
.github/workflows/       CI: the specs and Selene on every push and pull request
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

## Companion skills

It hands off to Blender and animation skills when they are installed (`blender-director`, `blender-asset-qa`, `blender-game-optimization`, `blender-export-pipelines`, `blender-character-rigging`, `animate-roblox-characters`, `find-skills`, and others named in `SKILL.md`). Without them it falls back to the rules in each reference.

## Using the scripts

- **Loading:** the `.luau` files are plain Studio modules. Load one through a local static server and `loadstring` (Edit or server), or as a temporary ModuleScript (client), as `SKILL.md` describes.
- **Where they run:**
  - `UIBounds`, `AssetAudit`, `ZFight`, `RigAudit`, `AnimationInspector` and `GameInventory` run in Edit.
  - `VFXInspector` lints in Edit and photographs in Play (`references/vfx.md` section 8).
  - `ParticlePlayer` and `UIParity` run on the client (Play); prefer the project's own particle player.
  - `icon_outlines.py` runs locally: `uv run --with numpy --with pillow python icon_outlines.py <folder>`.
  - `export_place.luau` runs in Lune: `lune run export_place.luau <place.rbxl> <out folder>`.
  - `PacingSim.luau` runs in Lune (or any Luau VM, Studio included): copy it beside a model, `lune run model.luau` (`references/game-economy.md`).
- **Tested in Studio on a real game** (2026-10-27 unless noted):
  - `AnimationInspector`: Roblox's R15 clips give 0 errors; every planted defect is caught; works on AnimationConstraint and Motor6D rigs.
  - `RigAudit`: 98 R15 rigs, broken copies and a generated R6.
  - `ZFight`: an 18,882-part map, audited and settled to 0 on a copy.
  - `GameInventory`: 26 scripts; `export_place` on the same game's saved file.
  - `UIParity` (2026-10-28): in Play, a fixture covering every option, clipping rule and sweep case (39 checks), its visibility verdicts matching the engine's own hit test. An earlier version matched that game's Rojo port to the original at five viewport sizes (HUD, 8 windows, every scroll position) and caught a 3 px nudge.
  - `UIBounds` (2026-10-28): 50 runs on a game's unit card under its HUD scale (10 sizes from 360x800 to 1280x720 in both orientations, five contents; outer and inner strokes, rims, rounded corners). They found UIBounds ignoring `UIScale` (false findings below a scale of 1, missed leaks above it); with outlines and corners scaled, the same runs come out clean. `Center` strokes, `BorderOffset` and `ScaledSize` thickness are type-checked but not yet exercised in Studio.
  - The VFX real-rig stage: in Play.
  - `ZFight` and `GameInventory` were also tested offline in Lune while they were written.
- **Also checked** (2026-10-28): every Studio script type-checks clean under both Luau type solvers (luau-lsp with Roblox's definitions; strict mode, except `ZFight`, which is nonstrict) and passes Selene with no warnings; `export_place` re-exported that game's saved file and matched the earlier export, apart from one edit made after the file was saved; `icon_outlines.py` measured generated icons of known border widths; both installers ran local, global, update and Claude-link installs.
- **Tested in Lune** (2026-10-28): `PacingSim`, 1,694 spec checks. Cost ladders match brute force; the chance arithmetic matches its closed forms; simulated timings (sessions, offline earnings, time-away rules, a second currency, all three player policies, saving for a buy) match hand-worked cases; bad models are reported (NaN costs, a buy that never gets dearer, duplicate milestones, unknown policies, sessions longer than a day); over 4,000 runs of a 1-in-600 roll, `simulateMany`'s p10, median and p90 land within 3% of theory. It type-checks clean in strict mode under both Luau type solvers (luau-lsp, standard platform) and passes Selene with no warnings.
- **Changed, not yet re-run in Studio** (2026-10-28): ParticlePlayer's frame-rate scaling. It type-checks clean under both solvers against that day's Roblox definitions, and Selene passes.

## Checks

From this folder, with [Rokit](https://github.com/rojo-rbx/rokit):

```sh
rokit install
lune run tests/run.luau     # specs for the pure-Luau scripts
selene scripts tests        # lint, std = roblox
luau-lsp analyze --platform=roblox --definitions=@roblox=<globalTypes.d.luau> <the Studio scripts>   # strict types; again with --flag:LuauSolverV2=true
```

`export_place.luau` is a Lune script: type-check it with Lune's own definitions. The Studio scripts are proven in Studio (above); the specs cannot stand in for the engine's layout or physics.

## License

MIT
