# RobloxDevSkill

A token-efficient agent skill for Roblox game development (Claude Code, Codex and any agent that reads `SKILL.md` skills).

`SKILL.md` is a short dispatcher: ten always-on rules, shared visual-style precedence and a routing table. Agents load only the reference for the task at hand, so a UI tweak never pays for the modeling guide. Everything in it is a default: a project's own `AGENTS.md`, `CLAUDE.md` and docs, and the user's instructions, take precedence over every rule, the safety and content rules included. Rules marked *(default)* are house conventions; the unmarked ones guard against Roblox limits, moderation or bugs, so the agent names the risk once and then follows the instruction. The project blueprint (`assets/PROJECT_STRUCTURE.md`: packages, Graphify) is the author's own setup.

```
SKILL.md                 dispatcher: request/reference -> matching project theme -> asset-specific fallback
.mcp.json                repository-only Studio/Blender MCP access (excluded by installers)
references/
  coding.md              dependencies, structure, backend performance, security, data limits and erasure, pitfalls, verification
  gameplay.md            physics movers, network ownership, NPC pathfinding, playing animations in game
  rojo-project.md        new Rojo project or Studio-game conversion: folder, blueprint, inventory, rebuild, switch-over, parity tests
  ui.md                  simulator-cartoon UI/icon fallback, mobile first, in bounds (UIStroke), safe areas, centered anchors, Studio previews, state, world-space GUIs
  vfx.md                 research, tuning, EmitDelay/EmitDuration/EmitCount, smooth in/out, placement, inspection
  modeling.md            stud-style model / anime-ink skin fallbacks, 1024x1024 maps, 20k tri limit (18k for top tier), DoubleSided always, box modeling, clay check, no z-fighting
  environment.md         Unified Lighting, atmosphere, sky, post-processing, terrain, custom materials
  rigs.md                character models: R15 from a HumanoidDescription (seat, clean), parts, joints, attachments, accessories, R6, no Humanoid by default (AnimationController), skins (custom art on a standard rig: welded or skinned)
  characters.md          all-ages character rules (2D and 3D): modest covered chest, no cleavage, 70% in-character cover, a straight layer past the hips, prompts, review
  no-gore.md             blood and gore: strict uploads (false-positive margin, neutral textures), trusted existing assets, stylized play
  assets.md              Toolbox policy (no code), safe intake, sounds, the upload gate, uploads (the cloud API key, owner-owned)
  animation.md           60 FPS, weighted joints, feet on the ground, export, publish, inspection
  onboarding.md          show-don't-tell tutorials, pointer choices, funnel rules (10 funnels, custom fields, a post-tutorial funnel per feature)
  game-design.md         fantasy, direction, simple vs deep, loops, progression, retention, social, review
  game-economy.md        currencies, pacing (PacingSim), odds, monetization, paid random items, live ops
  codex-handoff.md       Claude only: open handoffs, Codex usage and room, briefs, review, takeover, cleanup
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
  RigAudit.luau          character model audit (R15/R6, with or without a Humanoid): parts, joints, root, seated accessories, cages, leftovers; seat, clean, controller (the Humanoid swapped for an AnimationController)
  RigSkin.luau           skins: dump a rig for Blender, dress it around its visible body (welded pieces or a skinned mesh, body colors, a face decal; any pose), equip weapons and shields on Motor6Ds, audit the skin
  roblox_rig.py          Blender side of skins: the rig's body as seen in game (solid, colored, a rounded head) and its armature, rigid weights, Roblox-ready exports
  skin_kit.py            Blender: R6/R15 skin layout, armor shapes (closed wraps, squircle domes, prisms, lettering), hair (volume, cap, blade locks, bangs, layers, spikes), '<Part>__<Look>' pieces, clay-check renders, the checks for sides a wrap leaves bare and for hair, PBR stage (merge, atlas, baked SurfaceAppearance maps)
  skin_ink.py            inks a baked paint layer in smooth tapered strokes, with Pillow (called by skin_kit.paint)
  studio_mcp.py          command-line client for Studio's own MCP server: runs .luau files with the skill's scripts inlined (--@use), any tool, captures
  upload_asset.py        Open Cloud upload to the experience's owner, waiting for moderation
  AssetAudit.luau        Toolbox safety audit: report first, then strip
  TutorialGuide.luau     tutorial pointers: spotlight, 3D focus, arrow, elevated beam, camera assist, UI lock
  GameInventory.luau     Studio-to-Rojo inventory: scripts and what they touch, content counts, export, leftovers
  export_place.luau      Lune: every script of a saved place file written to disk, byte for byte
  UIParity.luau          port vs original: per-window fingerprints of every visible text and image, scroll sweeps
  PacingSim.luau         pacing model (Lune): milestone times for casual and optimizing players, odds tables
  codex/                 Codex handoff wrapper (Node): handoff.sh entry, usage, state, summaries, cleanup, installer
tests/
  run.luau               Lune specs for the pure-Luau scripts (PacingSim)
  codex/                 Node tests for the handoff wrapper against a fake Codex CLI
  python/                MCP UTF-8 output/error handling and installer exclusion regressions (standard library)
  blender/               isolated Blender geometry and material/bake regressions
  studio/                engine regressions for animation inspection, capture-sheet redraw, a held weapon's fit in the hand and rigs without a Humanoid
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

## Codex handoff (Claude Code, optional)

When it is cheaper than doing the task in Claude (the brief, review and fix rounds counted) and the account has room, Claude decides and reviews while the local [Codex CLI](https://github.com/openai/codex) does the execution on its own quota: decided code, bulk edits, Studio and Blender work, and image generation. The wrapper reads the account's live usage before every launch (no model turn), refuses or queues runs that would not fit, takes failed code back to Claude (images stay with Codex), lists open handoffs for the user to settle, and cleans up after each task. Rules: `references/codex-handoff.md`. It merges the earlier CodexHandoffSkill.

One-time setup (Git Bash on Windows):

```sh
npm install -g @openai/codex && codex login
node ~/.claude/skills/roblox-dev/scripts/codex/install.mjs      # Claude permission rules for the wrapper (merged, idempotent)
bash ~/.claude/skills/roblox-dev/scripts/codex/handoff.sh --check
```

Configure the MCP servers Codex needs (Roblox Studio, Blender) once in Codex (`codex mcp list`); Claude's are not shared. Runs default to `--sandbox danger-full-access` (`CODEX_HANDOFF_SANDBOX` to change it). State lives in `~/.claude/codex-handoffs` (`CODEX_HANDOFF_HOME`).

## Companion skills

The bundled [animate-r15-like-r6](skills/animate-r15-like-r6/SKILL.md) companion covers stiff R6-style motion on real R15 rigs: six moving joints, nine locked joints, smooth locomotion, compact jump/fall arcs, and validation. The dispatcher routes matching requests to it; it ships with the existing install.

It hands off to Blender and animation skills when they are installed (`blender-director`, `blender-asset-qa`, `blender-game-optimization`, `blender-export-pipelines`, `blender-character-rigging`, `animate-roblox-characters`, `find-skills`, and others named in `SKILL.md`). Without them it falls back to the rules in each reference.

## Repository MCP access

The tracked `.mcp.json` enables Roblox Studio and Blender MCP while developing this repository in a client that reads project MCP files. It copies the existing Windows setup: Studio's `%LOCALAPPDATA%\Roblox\mcp.bat` through `cmd`, and Blender through `uvx --python 3.11 mcp-for-blender`. Studio needs its MCP server enabled; Blender needs its MCP add-on running. Adapt the Studio command for other operating systems. The config contains no credentials.

The installers exclude `.mcp.json` from skill copies and global updates. Developer junctions/symlinks to the full repository still expose it; see [INSTALL.md](INSTALL.md).

## Using the scripts

- **Loading:** the `.luau` files are plain Studio modules. Run them with `studio_mcp.py` (a `--@use` line inlines them through `loadstring`, Edit or server), load one through a local static server and `loadstring`, or use a temporary ModuleScript (client), as `SKILL.md` describes.
- **Where they run:**
  - `UIBounds`, `AssetAudit`, `ZFight`, `RigAudit`, `AnimationInspector` and `GameInventory` run in Edit.
  - `RigSkin` runs in Edit, or on a game's server to dress characters; `roblox_rig.py` and `skin_kit.py` run inside Blender (`import roblox_rig, skin_kit`; tested on 5.1).
  - `studio_mcp.py`, `upload_asset.py` and `find_blender.py` run locally with Python 3 (standard library only), `ref_sheet.py` with Pillow; `studio_mcp.py` starts Studio's MCP server (`STUDIO_MCP`, or `mcp.bat` on Windows).
  - `VFXInspector` lints in Edit and photographs in Play (`references/vfx.md` section 8).
  - `ParticlePlayer` and `UIParity` run on the client (Play); prefer the project's own particle player.
  - `icon_outlines.py` runs locally: `uv run --with numpy --with pillow python icon_outlines.py <folder>`.
  - `export_place.luau` runs in Lune: `lune run export_place.luau <place.rbxl> <out folder>`.
  - `PacingSim.luau` runs in Lune (or any Luau VM, Studio included): copy it beside a model, `lune run model.luau` (`references/game-economy.md`).
  - `scripts/codex/` runs locally with Node 20+ through `handoff.sh` (Git Bash on Windows), from Claude Code (`references/codex-handoff.md`).
- **Tested in Studio on a real game**:
  - `AnimationInspector`: Roblox's R15 clips give 0 errors; every planted defect is caught; works on AnimationConstraint and Motor6D rigs.
  - `RigAudit`: 98 R15 rigs, broken copies and a generated R6.
  - `ZFight`: an 18,882-part map, audited and settled to 0 on a copy.
  - `GameInventory`: 26 scripts; `export_place` on the same game's saved file.
  - `UIParity`: in Play, a fixture covering every option, clipping rule and sweep case (39 checks), its visibility verdicts matching the engine's own hit test. An earlier version matched that game's Rojo port to the original at five viewport sizes (HUD, 8 windows, every scroll position) and caught a 3 px nudge.
  - `UIBounds`: 50 runs on a game's unit card under its HUD scale (10 sizes from 360x800 to 1280x720 in both orientations, five contents; outer and inner strokes, rims, rounded corners). They found UIBounds ignoring `UIScale` (false findings below a scale of 1, missed leaks above it); with outlines and corners scaled, the same runs come out clean. `Center` strokes, `BorderOffset` and `ScaledSize` thickness are type-checked but not yet exercised in Studio.
  - The VFX real-rig stage: in Play.
  - `ZFight` and `GameInventory` were also tested offline in Lune while they were written.
- **Also checked**: every Studio script type-checks clean under both Luau type solvers (luau-lsp with Roblox's definitions; strict mode, except `ZFight`, which is nonstrict) and passes Selene with no warnings; `export_place` re-exported that game's saved file and matched the earlier export, apart from one edit made after the file was saved; `icon_outlines.py` measured generated icons of known border widths; both installers ran local, global, update and Claude-link installs.
- **Tested in Lune**: `PacingSim`, 1,694 spec checks. Cost ladders match brute force; the chance arithmetic matches its closed forms; simulated timings (sessions, offline earnings, time-away rules, a second currency, all three player policies, saving for a buy) match hand-worked cases; bad models are reported (NaN costs, a buy that never gets dearer, duplicate milestones, unknown policies, sessions longer than a day); over 4,000 runs of a 1-in-600 roll, `simulateMany`'s p10, median and p90 land within 3% of theory. It type-checks clean in strict mode under both Luau type solvers (luau-lsp, standard platform) and passes Selene with no warnings.
- **Codex handoff**: 30 Node tests against a fake CLI (CodexHandoffSkill's 20, carried over, plus the usage gate, room under parallel launches, queueing, the take-over line, misclassified failures, cleanup and the listing); the last 8 full runs on Windows (Node 26) passed in a row, after one installer write race was fixed with a retried write. Live with Codex CLI 0.162.1: the usage read (about 1.6 s, no model turn), the listing of 13 runs left by the old wrapper, a code handoff in a worktree (completed in 1m45s; reviewed, its spec rerun, integrated with `git apply`, then cleaned with its run and worktree removed) and an image handoff (completed in 3m20s; checked at 512 px with icon_outlines clean; cleaning removed Codex's image copy). The live runs found two faults the fake missed, both fixed and now tested: the entry points did nothing when reached through the install's junctions, and a worktree that `git apply` integrated with CRLF line endings was refused. A skill test the same day (two Blender character runs, two image runs) found four more, all fixed and now tested (32 tests): a recovered WebSocket-to-HTTPS fallback, logged as an error item, marked finished runs FAILED; `--add-dir` locked a shared output folder against a parallel run; one median cost for every run said 4% where a Blender build took 36%, so cost and room are now per kind (upper quartile); and delivered rebuild scripts kept their intermediates in the run directory, which `--clean` now refuses to delete. The next image run, with 5 recovered reconnects, completed as COMPLETED.
- **Skins**: `RigSkin` and `roblox_rig.py` on one character (a 16-piece R15 skin, a 7-piece R6 skin and a skinned R15 mesh, built in Blender around dumped rigs), worn by copies of a Rig Builder R6 and R15 (Motor6D) and a player's avatar R15 (AnimationConstraint, cages, a hat).
  - In Edit: `RigSkin.audit` and RigAudit give 0 errors, and AnimationInspector gives the same findings on every dressed rig as on the bare one.
  - In Play: every copy stands, walks to a `MoveTo` target with a stock walk clip, and its pieces and bones drift 0.0000 studs from their parts. Copies dressed mid-walk match the copies dressed at rest exactly. On death every piece stays on its limb.
  - The tests found three faults, all fixed:
    - Roblox's importer drops an object's own transform, so pieces exported with their origins at their centres all landed at the file origin. Exports now use the scene origin, and the new `astray` rule catches a misplaced piece.
    - Death breaks every Weld and WeldConstraint in the character, so pieces fell out of the world. They are now held by RigidConstraints, which survive.
    - Blender's `matrix_world` lags a script's location changes, which baked pieces at the origin. The exports now update the view layer first.
  - `RigSkin` type-checks clean in strict mode under both Luau type solvers and passes Selene with no warnings.
  - A second character, built from a user's reference: R6 and R15 skins fitted to a generated R6 and R15 (whose R15 stands 0.19 studs taller than a Rig Builder one). The first attempt passed every audit and Play check yet did not look like the reference, so the clay check now renders the reference's own view and goes through a list of measured features. The second attempt was built around the visible body (colored to the painted skin's median tone, a face decal on the rig's head, nothing hidden): 0 findings from both audits, all 16 Play checks passed (walk, `MoveTo`, death). AnimationInspector audits no longer leave an empty `__AnimInspect` folder in the place.
  - A third character from a user's concept sheet (an armored stand): an 18-piece R6 and a 34-piece R15 skin (about 15,000 triangles each) on a generated R6 and R15, built headless in Blender and uploaded to the experience's group. Both audits 0 errors, AnimationInspector matching the bare rigs, and in Play a walk and a death with 0 studs of drift. It found five faults, all fixed and re-tested on fresh rigs in Studio:
    - The generated R15 had a dynamic head (FaceControls), which garbled the face decal (magnified, offset, the mouth as a dark line). `face` now puts it on a classic head piece and hides that head: 0.000 studs and 0.00° from a head posed mid-turn, and audits 0 findings.
    - A Studio call's reply was lost while its dressing still ran; dressing again left 52 orphaned `SkinWeld_` attachments. `apply` and `bind` now remove them, and the audit's `stale` rule reports them (35 and 18 found after deleting a Skin folder, 0 after dressing again).
    - The importer leaves every MeshPart gray Plastic; `looks` styles pieces by name (34 and 18 styled).
    - `roblox_rig.build`'s replica boxes were wound inward, which blender-asset-qa reported as inside-out parts and as z-fighting between the skin and the body. They are wound outward now (0 inside-out parts).
    - Uploads went first to the key's user, whom neither the group-owned experience nor the Studio account could load; `assets.md` now has the owner check, its failure signs, what to try first (the same user key uploading to the group, which worked), the observed `Approved` state, and `upload_asset.py`.
  - The session's own Blender builder, rebuilt on `skin_kit.py`, gave the same pieces and vertex positions as the uploaded skins. `studio_mcp.py` (no Studio MCP tool was connected) listed the tools, ran inlined `--@use` audits in Edit and on the Play server and client (loadstring is off in Play, so there a temporary ModuleScript, none left behind), captured, started and stopped Play, and exited non-zero on a tool error. `upload_asset.py` was checked dry and against the API with an invalid key (401), then made 14 live uploads (below), all approved.
  - Two more stands, built with the skill's scripts only (`studio_mcp.py`, `skin_kit.py`, `roblox_rig.py`, `upload_asset.py`, RigSkin): a 15-piece R6 and 27-piece R15 skin from a user's concept sheet (Roblox materials through `looks`), and an original stand in full PBR (one `<Part>__Skin` per body part plus Neon gems: 11 pieces on R6, 24 on R15, about 15,000 triangles each, four 1024 maps per rig). Both: QA clean (UV check on for PBR), both audits 0 findings, the R15's dynamic head given its face piece automatically, AnimationInspector matching the bare rigs, and in Play a walk and a death with 0 studs of drift. The concept image went to Codex by rule 10 (an image run, about 5% of the 5-hour window, in parallel with the rigs and the bake setup). Found and fixed:
    - The importer dropped the FBX's embedded textures: the maps are uploaded as images and given to a SurfaceAppearance in Studio.
    - A game Script cannot set or read a SurfaceAppearance's maps ("lacking capability Plugin") but can clone one, maps and all: `looks` now clones Instance values (6 of 6 PBR pieces textured, none doubled on dressing again).
    - The bake stage (`skin_kit.merge`, `unwrap`, `bake`, `preview`, `render(pbr=True)`) bakes an R6 skin in about 45 s on CPU. Rebuilt on it, the original stand gave the same pieces and triangles and passed QA again; the maps are not byte-identical between runs, since island packing varies.
  - A dragon and a demon skin (R6 and R15, uploaded): QA, both audits and AnimationInspector all passed, but in game the dragon's scale sleeves and leggings showed bare limbs on every step, on the sides facing the torso and the other leg. The skill taught this: `wrap`'s example passed `open_side=a['inner']`, rigs.md said "limb wraps open toward the torso", modeling.md said "no hidden or interior faces", and no clay view or front or side walk sheet shows those sides.
    - Now `wrap(tuck=...)` closes them, `gaps` measures them, `render(apart=...)` shows them, and rigs.md makes closed the default. Clipping into the neighbour is accepted, since the limb is moving whenever that side shows; flicker at rest is not.
    - On the skin as uploaded, `gaps` reports every limb on both rigs (4 parts on R6, 12 on R15) on its inner side. Rebuilt closed in a scratch copy of the dragon's build, with scales on those sides and the skirt closed, the limbs clear; what remains is the sleeveless tunic's top corners, which that design leaves open. The rebuild adds 13% and 14% triangles (23,964 to 26,964 on R6, 24,732 to 28,132 on R15). On the demon, whose feather sleeves are one-sided by design, `open_sides` clears the arms and leaves the rest reported.
    - blender-asset-qa then gave no new errors. It found two flicker faults in the first `tuck`, both fixed and tested: with `thick == gap` the wall's back lay on the plane the limb shares with its neighbour, and an R6 arm's ring ended level with the torso's underside.
    - Not yet re-run in Studio: the uploaded skins are unchanged, and `tuck` has been checked in Blender only.
- **Changed, not yet re-run in Studio**: ParticlePlayer's frame-rate scaling. It type-checks clean under both solvers against Roblox's definitions, and Selene passes.

- **An armored character from a user's turnaround, with the memory and project history left out** (the Crimson Knight): a 6-piece R6 and 15-piece R15 skin with a rapier, four 1024 sets per rig. Blender QA, both audits, AnimationInspector matching the bare rigs, and in Play a walk with 0 studs of drift. The run found these, all now in the skill:
  - Nothing told Codex what a face's style was: `codex-handoff.md` asked for no style, the wrapper's image prompt named only the moderation references, and `rigs.md` gave faces neither a style nor a layout. Image briefs now need a `## Style` section, the wrapper refuses one without it, and its prompt makes the section binding.
  - A project had to write its own surfaces, region dressing, batch uploads, Play test and z-fight positions. `kit.Form` and its strips and plates, `Hair.shell`, `kit.coplanar`, `kit.pokes`, `RigSkin.surface`, `surfaces`, `preload`, `playtest`, `upload_asset.py --manifest`, `studio_mcp.py play`, `ref_sheet.py` and `find_blender.py` do that. Ported onto them, the character's meshes kept the same triangle counts.
  - `PreloadAsync` on an id string reported Failure for maps that displayed correctly; the same maps through an ImageLabel or Decal report Success, a SurfaceAppearance reports nothing, and a bad id still fails.
  - `kit.paint` lit from the front only, so a white back read gray; it now lights the back alike. Fold lines were black and clumped into marks like claw scratches; they now take a deep tone of their look, with sparse starting specs.
  - A generated R15's upper leg box runs above its joint, which made a tabard too tall; `layout` now gives `hip`.
  - `kit.render` framed from the ground up and cropped a weapon; it now frames what is there.
- **The Style section, proven live:** the same face, briefed from `modeling.md`'s wording with a render of the painted model attached, came back with bold brows and lids and a nose and mouth that hold at 128 px, where the first brief's nearly vanished. The first wording, "generate again when it drifts", had no limit and no measure, so Codex spent four generations on tonal noise and reported failed over a good result; the prompt now caps it at two more and says noise is not drift. Rerun on the same brief, it completed in 2m58s.
- **Fast mode, proven live:** Codex ignores an invalid `service_tier` without an error, so exit codes prove nothing. A trace showed `response.completed` reporting `priority` on the main response with `service_tier="priority"` and `default` without it, and the same prompt took 22 to 25 s against 36 to 45 s.

## Checks

From this folder, with [Rokit](https://github.com/rojo-rbx/rokit):

```sh
rokit install
lune run tests/run.luau     # specs for the pure-Luau scripts
selene scripts tests        # lint, std = roblox
node --test tests/codex/handoff.test.mjs   # the Codex handoff wrapper (Node 20+, Git), against a fake CLI
python -m unittest discover -s tests/python -v
blender -b --factory-startup --python-exit-code 1 -P tests/blender/skin_kit_test.py
python scripts/studio_mcp.py luau tests/studio/AnimationInspector.spec.luau --studio "PLACE NAME" --output animation-results.json
python scripts/studio_mcp.py luau tests/studio/RigSkin.spec.luau --studio "PLACE NAME" --output rigskin-results.json
python scripts/studio_mcp.py luau tests/studio/RigAudit.spec.luau --studio "PLACE NAME" --output rigaudit-results.json
luau-lsp analyze --platform=roblox --definitions=@roblox=<globalTypes.d.luau> <the Studio scripts>   # strict types; again with --flag:LuauSolverV2=true
```

`export_place.luau` is a Lune script: type-check it with Lune's own definitions. The Studio scripts are proven in Studio (above); the specs cannot stand in for the engine's layout or physics.

The Studio specs run in Edit mode with temporary generated R6/R15 rigs, clips and meshes, then clean them up. Use `studio_mcp.py --output FILE` for UTF-8 text/JSON files; PowerShell redirection can write UTF-16 despite the process's stdout encoding. Python regressions run in CI; Blender and Studio require those applications locally.

These regressions passed: four Python tests, four Blender 5.1.2 tests (including a real four-map bake), and 13 Studio checks repeated twice. Touching ornaments retain closed, separate topology; invalid bake inputs leave materials and scene settings unchanged. Stock R6/R15 walks infer locomotion, idle stays stationary, and deliberate planted slide/sink defects remain detectable. Stock clip/grid findings are retained. Consecutive colored capture sheets were also inspected without caller-added waits. Selene, 1,694 PacingSim checks, all 32 handoff tests and skill validation passed. After `tuck`, `gaps` and `apart` were added the same day, 15 Blender tests and 11 Python tests (1 skipped) passed.

Held weapons, after a user's screenshot of a sword whose guard and blade cut into the hand: `skin_kit.grip_fit` and `fist` in Blender, and in Studio `RigSkin.equip` seating the handle inside the fist and `RigSkin.audit` measuring the fit from the weapon's and the skin's meshes. All 32 Blender tests (12 of them new) and 18 Studio checks (`RigSkin.spec.luau`, on generated R6 and R15 rigs, run twice) passed: a sword built to the fist and one with a knuckle bow pass, and a guard or pommel in the hand, a short handle, a weapon facing backward, an unseated handle and a glove that enlarges the fist are each caught. On the uploaded HeroSkins gear, Blender and Studio agree: the sword's guard starts 0.01 studs ahead of the grip, and the halberd's handle ends 0.64 behind it, inside a 0.67 fist; once seated, the halberd's ring also enters the fist 0.42 ahead and 0.39 behind. Side and below captures of re-seated copies show the handle inside the fist and the guard where the audit puts it. A pommel at exactly the handle limit read as over it in Studio only (float rounding), so both checks allow 0.001. Selene is clean and the editor's Luau diagnostics show none; `luau-lsp` was not installed for a command-line run.

Hair, after the user found the skill's hair poor: 48 anime hair meshes from a user's `HAIRS` model (40 accessories and 8 distinct hair-on-head models; about 90 older and high-poly hairs viewed beside them) were read from Studio's local cache, since EditableMesh refuses meshes the user does not own (the cache holds mesh versions 1 to 7; a v7 core mesh is a 4-byte length and a Draco stream). Each was placed on the classic head by the legacy hat weld or its saved head offset and measured in Blender: crown rise, standoff, bulge, coverage by region, lock shape, hem and fringe. The skill's DragonGirl and DemonGirl hair, measured the same way, rose 0.14 over the head (references: at least 0.2, median 0.42) and sat 0.06 to 0.07 off the scalp (references' 10th percentile 0.105), every bang ending within 0.04 of one height. On the 46 references `hair_check` reports only design exceptions (9 crops at the nape, 2 headband fringes, a ponytail and a crop at the back), and on both monster hairs rise, standoff and fringe. Two hairs built with `kit.Hair` (long with bangs, spiky) were rendered beside references: the first builds passed `hair_check` yet read as noodles and a sea urchin, which set the lock profile (full width until near the tip), the bangs' roots (on the crown) and the spikes' sweep (up and back), and is why rigs.md asks for close-up renders as well. The docstring example builds a manifold hair of about 2,500 triangles that passes on generated R6 and R15. All 37 Blender tests (5 new) passed.

Rigs without a Humanoid, after a user asked for Humanoid-less R6 and R15 as the default build. On generated R6 and R15 rigs whose Humanoid was swapped for an AnimationController (the Animator moved over):
- **In Play:** with the root anchored, a stock walk played on the server moved every joint (6 on R6, 15 on R15; R15's AnimationConstraints come with `IsKinematic` on), and the parts stayed within 0.0001 studs of their joints. The client saw the server's track (legs swinging about 100°). Unanchored and unheld, the rigs sank 2.01 (R6) and 1.96 (R15) studs, since only the root, head and torso collide; held by AlignPosition and AlignOrientation, they stayed within 0.0001 studs.
- **Clothing and looks:** a layered jacket from the Creator Store, worn through `AddAccessory` before the swap, wrapped and bent mid-walk exactly as on a Humanoid copy. Classic Shirt and Pants stopped showing on R6 and R15, and BodyColors stopped recoloring parts.
- **The dynamic head:** it rendered untinted white, though its Color and TextureID were unchanged. Of the fixes tried (removing FaceControls, clearing the texture, a tinted SurfaceAppearance, an Overlay SurfaceAppearance), only the last two matched the Humanoid copy. Overlay was chosen because it shows the part's Color only where the texture is transparent, so it should follow later color changes and leave colored features alone, where a tint multiplies everything (reasoned, not tested).
- **The Humanoid changes nothing on parenting:** dump's rest-pose `rootHeight` is 3.192 on a blank R15 straight from the generator (HipHeight 2.192 plus half the root), and 3 on R6.

`RigAudit.controller` encodes this, and the new audit rules (`standing`, `clothing`, `untinted`) check it.
- **New spec:** `RigAudit.spec.luau` passed 22 checks twice. They cover the swap, `RootHeight`, the anchored root, `RigSkin.dump` reading the converted rig, a 0-error audit, an idempotent rerun, a stock walk auditing the same in AnimationInspector with and without the Humanoid, the head's Overlay, and each new rule caught and cleared.
- **In Play, dressed:** a dressed R6 and R15 (a skin piece through `apply`, a sword through `equip`), converted and walking, kept the piece 0 studs and the sword 0.00003 studs from their joints, and both audits gave 0 findings.
- **Existing checks:** AnimationInspector's 13 and RigSkin's 18 Studio checks still pass, Selene is clean, and the editor's Luau diagnostics show none for the four changed scripts.
- **Not run:** walking a converted NPC along a path by CFrame (gameplay.md), and conversion inside a running game script, which the earlier SurfaceAppearance finding says lacks the capability for the Overlay map.

Folded meshes, after a user's screenshot of a flickering belt buckle on a skin: a crescent outline whose inner arc ran past the outer circle crossed itself, so its cap folded over itself (on R15, 19 flipped triangles, 24 overlapping pairs and four times the crescent's area, a filled hollow). Every audit passed it: blender-asset-qa skips triangles that share a vertex, and ZFight does not read MeshParts, so its 0 said nothing about a skin. The bevel was not the cause: the outline folded with `b=0`, while sharp-tipped crescents and the HeroSkins pendant did not. Now `kit.prism` refuses a crossing outline, `rr.folds` measures a mesh's visible overlap with itself, both exports refuse 0.002 studs² or more, and `ZFight.audit` counts the MeshParts and unions it skipped. The limit comes from measuring 14 shipped assets and the original buckle: buried creases (up to 72 pairs) do not count, and visible overlap was 0.212 on the buckle, 0.017 to 0.028 on DemonGirl's and DragonGirl's legs and feet, and at most 0.00065 elsewhere. The DragonGirl hit was a real defect, a black wedge in a toe claw. All Blender tests (7 new) and the Python tests passed, Selene is clean, the 23 `prism` calls in the HeroSkins designs still build, and in Studio `ZFight.audit` reported 8 MeshParts unread on a dressed R6, 32 on an R15 and no note on plain Parts.

## Developing the skill

### Skill optimization

The goal: fewer tokens each time the skill is used, with every detail kept. Keep the values and thresholds, names and APIs, the order of steps, the failure signs and their fixes, and the evidence behind a rule. Repetition and misplaced text go; knowledge stays.

**What a task pays for:**
- `SKILL.md`: every task. It holds only the always-on rules (a line or two each), the route table and the scripts list.
- **A reference:** every task routed to it, for the whole file. Each line should serve most of those tasks.
- **A script:** only when it is read or run.
- **`README.md` and `INSTALL.md`:** never. They are for people and for developing the skill, so test records, history and this section live here, not in the references.

Measure with `wc -c SKILL.md references/*.md` (characters / 4 is close enough to tokens). `SKILL.md` was about 2,300 tokens, and the references ranged from 800 (environment.md) to 5,700 (game-design.md).

**Rules:**
1. **Measure before and after.** Give the counts in the commit: `SKILL.md`, each reference changed, and what a typical route loads (`SKILL.md` plus its reference).
2. **One home per fact.** Each rule, value or process lives in the reference that owns its task. Anywhere else links to it (`[rigs.md](references/rigs.md), Skins`) instead of restating it. A rule in `SKILL.md` keeps a one-line form there and its details in the reference, never the same text twice.
3. **Route narrowly.**
   - One reference per task family. Split a file when its routes mostly need only a part of it, giving each part its own route row. Merge two files that always load together.
   - Within a file, what every task needs comes first; rare cases, edge cases and background come last.
   - Point to another reference only for the case that needs it ("when X, read Y"), never a general "see also".
4. **Cut words, not facts.** Drop restatements, hedges, filler and examples that only repeat the rule; prefer short list items to paragraphs. Keep every number, name, API, step order, failure signature and fix.
5. **Evidence in one sentence, with no date.** An observation that justifies a rule stays in the reference as a plain statement. The story of how it was found goes in the commit or here, undated too. `tests/python/test_no_dates.py` fails on a date in a note.
6. **Scripts carry their own detail.** When a script enforces a rule, the reference says what to run and what its findings mean. The script's header documents its options and checks.
7. **Nothing that loads by itself.** Keep `CLAUDE.md`, `AGENTS.md` and similar files out of the skill folder: an agent may load them whenever it reads a file there, and every use would pay.
8. **Check that nothing was lost.** Read the diff line by line: every removed fact must still exist in its home, or be a true duplicate. Then run the checks above and one real task with the skill loaded.

## License

MIT
