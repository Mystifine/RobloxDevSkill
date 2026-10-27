# RobloxDevSkill

A token-efficient agent skill for Roblox game development (Claude Code, Codex and any agent that reads `SKILL.md` skills).

`SKILL.md` is a short dispatcher: six always-on rules plus a routing table. Agents load only the reference for the task at hand, so a UI tweak never pays for the modeling guide.

```
SKILL.md                 dispatcher (always loaded, ~50 lines)
references/
  coding.md              dependencies, structure, backend performance, pitfalls, verification
  ui.md                  centered anchors, matching project style, 512x512 icons, placeholders
  vfx.md                 research, property tuning, EmitDelay/EmitDuration/EmitCount, smooth in/out
  modeling.md            20k tri limit (18k for top tier), full PBR, Blender workflow
  assets.md              Toolbox policy (no code), safe intake, sounds
  animation.md           60 FPS, weighted joints, clean curves, export and verify
scripts/
  ParticlePlayer.luau    fallback attribute-driven particle player (graphics-scaled, min 1)
  AssetAudit.luau        Toolbox safety audit: report first, then strip
```

## Install

Claude Code (project or user skills folder) or any agent skills directory:

```powershell
git clone https://github.com/Mystifine/RobloxDevSkill.git "$HOME\.agents\skills\roblox-dev"
```

The folder name should match the skill name, `roblox-dev`. For Claude Code, link it into `~\.claude\skills\roblox-dev` (a directory junction or a copy).

## Companion skills

It hands off to Blender and animation skills when they are installed (`blender-director`, `blender-asset-qa`, `blender-game-optimization`, `blender-export-pipelines`, `blender-character-rigging`, `animate-roblox-characters`, `find-skills`, and others named in `SKILL.md`). Without them it falls back to the rules in each reference.

## Using the scripts

Both are plain Luau modules. `AssetAudit` runs in Studio (Edit) on an inserted asset; `ParticlePlayer` runs on the client and mirrors the `EmitDelay` / `EmitCount` / `EmitDuration` attribute contract documented in `references/vfx.md`. Prefer the project's own particle player when it has one.

## License

MIT
