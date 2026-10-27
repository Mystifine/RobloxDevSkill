# RobloxDevSkill

A token-efficient agent skill for Roblox game development (Claude Code, Codex and any agent that reads `SKILL.md` skills).

`SKILL.md` is a short dispatcher: six always-on rules plus a routing table. Agents load only the reference for the task at hand, so a UI tweak never pays for the modeling guide.

```
SKILL.md                 dispatcher (always loaded, ~50 lines)
references/
  coding.md              dependencies, structure, backend performance, pitfalls, verification
  ui.md                  centered anchors, matching project style, 512x512 icons, placeholders
  vfx.md                 research, property tuning, EmitDelay/EmitDuration/EmitCount, smooth in/out, inspection
  modeling.md            20k tri limit (18k for top tier), full PBR, Blender workflow
  assets.md              Toolbox policy (no code), safe intake, sounds
  animation.md           60 FPS, weighted joints, clean curves, export and verify
scripts/
  ParticlePlayer.luau    fallback attribute-driven particle player (graphics-scaled, min 1)
  VFXInspector.luau      VFX inspection: exit lint, sphere/cube stage, vanish watcher, frozen-frame captures
  AssetAudit.luau        Toolbox safety audit: report first, then strip
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

All are plain Luau modules. `AssetAudit` runs in Studio (Edit) on an inserted asset; `VFXInspector` lints in Edit and photographs in Play (see `references/vfx.md` section 7); `ParticlePlayer` runs on the client and mirrors the `EmitDelay` / `EmitCount` / `EmitDuration` attribute contract documented in `references/vfx.md`. Prefer the project's own particle player when it has one.

## License

MIT
