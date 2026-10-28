# RobloxDevSkill

A token-efficient agent skill for Roblox game development (Claude Code, Codex and any agent that reads `SKILL.md` skills).

`SKILL.md` is a short dispatcher: eight always-on rules plus a routing table. Agents load only the reference for the task at hand, so a UI tweak never pays for the modeling guide.

```
SKILL.md                 dispatcher (always loaded, about 45 lines)
references/
  coding.md              dependencies, structure, backend performance, pitfalls, verification
  rojo-project.md        new Rojo project or Studio-game conversion: folder, blueprint, inventory, rebuild, switch-over, tests
  ui.md                  mobile first, stay in bounds, centered anchors, state, world-space GUIs, 512x512 icons, outlines
  vfx.md                 research, tuning, EmitDelay/EmitDuration/EmitCount, smooth in/out, placement, inspection
  modeling.md            20k tri limit (18k for top tier), full PBR, Blender workflow, no z-fighting
  rigs.md                character models: R15 from a HumanoidDescription (seat, clean), parts, joints, attachments, accessories, R6
  characters.md          all-ages character rules (2D and 3D): flat chest, no cleavage, 70% in-character cover, review
  assets.md              Toolbox policy (no code), safe intake, sounds, uploads (key by asset type, public)
  animation.md           60 FPS, weighted joints, feet on the ground, export, publish, inspection
  onboarding.md          show-don't-tell tutorials, pointer choices, funnel rules (10 funnels, custom fields)
assets/
  PROJECT_STRUCTURE.md   project blueprint: layout, Rojo map, packages, toolchain, AGENTS.md, MCP, Graphify
scripts/
  UIBounds.luau          UI bounds audit: nothing leaks out of its box, rim or rounded corner
  icon_outlines.py       icon set outline style (white sticker border or not) and the icons that break it
  VFXInspector.luau      VFX inspection: exit lint, sphere/cube or real-rig stage, vanish watcher, frozen-frame captures
  ParticlePlayer.luau    fallback attribute-driven particle player (graphics-scaled, min 1)
  AnimationInspector.luau  animation inspection: exact-time audit (pops, seams, feet, hyperextension, markers) and contact sheet
  ZFight.luau            z-fighting audit and fix: coplanar overlapping faces and decal ZIndex ties
  RigAudit.luau          character model audit (R15/R6): parts, joints, root, seated accessories, cages, leftovers; seat, clean
  AssetAudit.luau        Toolbox safety audit: report first, then strip
  TutorialGuide.luau     tutorial pointers: spotlight, 3D focus, arrow, elevated beam, camera assist, UI lock
  GameInventory.luau     Studio-to-Rojo inventory: scripts and what they touch, content counts, export, leftovers
  export_place.luau      Lune: every script of a saved place file written to disk, byte for byte
install/
  install.ps1            Windows installer (junction); install.sh for macOS/Linux (symlink)
INSTALL.md               placement rules, options, manual steps
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
  - `ParticlePlayer` runs on the client; prefer the project's own player.
  - `icon_outlines.py` runs locally: `uv run --with numpy --with pillow python icon_outlines.py <folder>`.
  - `export_place.luau` runs in Lune: `lune run export_place.luau <place.rbxl> <out folder>`.
- **Tested in Studio on a real game** (2026-10-27):
  - `AnimationInspector`: Roblox's R15 clips give 0 errors; every planted defect is caught; works on AnimationConstraint and Motor6D rigs.
  - `RigAudit`: 98 R15 rigs, broken copies and a generated R6.
  - `ZFight`: an 18,882-part map, audited and settled to 0 on a copy.
  - `GameInventory`: 26 scripts; `export_place` on the same game's saved file.
  - The VFX real-rig stage: in Play.
  - `ZFight` and `GameInventory` also have offline Lune tests.

## License

MIT
