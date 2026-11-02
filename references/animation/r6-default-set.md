# Roblox's default R6 set on R15

23 R15 KeyframeSequences recreating every clip of the R6 `Animate` script, built on classic R15 proportions (`BodyTypeScale` and `ProportionScale` 0: HipHeight 2, the same leg length as R6). One upload-ready `.rbxm` per clip, saved by Studio, in [assets/r6-on-r15/clips/](../../assets/r6-on-r15/clips/). `R6OnR15.DEFAULTS` lists their source ids.

## When someone asks for them

For any request like "default R6 animations for R15", run this and use its ids. Do not rebuild, re-verify or inspect the clips first.

```sh
python scripts/publish_r6_clips.py --studio "PLACE NAME" [--env-file .env] [--manifest r6_clips.json]
```

1. **It finds the owner.** An animation plays only in experiences owned by its creator, so it reads the open place's owner (`--group ID` or `--user ID` to set it).
2. **It queries each clip by name,** through Studio's MCP server: `search_asset` with an exact-phrase query, type `Animation`, in that owner's scope. The tool's schema leaves `Animation` out, but the server takes it, so the script calls the server directly.
3. **A match is the right animation.** The name and creator are enough: never download, compare or re-check it. Only a clip under that exact name with that creator counts, since a user's inventory also holds other creators' animations.
4. **It uploads only what is missing,** through Open Cloud with the project's key ([uploading.md](../safety/uploading.md)), one at a time, stopping at the first not approved. Studio cannot publish an animation by script (`AssetService:CreateAssetAsync` has no animation type).
5. **Wire the ids it prints:** `R6OnR15.wire(animate, ids)`, below.

**The name is hard-coded, and is how these clips are recognized:** `RDSkill R6onR15 v1 <clip>`, such as `RDSkill R6onR15 v1 walk`. Never upload them under another name or rename them on Roblox: the next run would upload duplicates. `v1` changes only when the clips' data does (`--set`), so an old name always means the old data. A set rebuilt for other proportions takes its own `--set` word.

| Situation | What happens |
|---|---|
| No key, clips missing | exit 4: it prints what it found and what is missing. Ask the user for the project's key; never search other projects for one |
| Studio not open | Open Cloud cannot list private animations by name (`itemconfiguration`'s listing needs a browser cookie: do not use it). Only `--manifest` then says what exists, so tell the user a rerun could upload duplicates, or open Studio |
| Not approved | exit 2 with the state: stop and report; never resend. A rerun picks up after the clips already there |
| Reading the plan first | `--dry-run` searches for real and sends nothing |

## What is in the set

| Group | Clips |
|---|---|
| Locomotion | `idle` (weight 9), `idle2` (weight 1), `walk` (also the run: R6 has no run clip), `jump`, `fall`, `climb`, `sit` |
| Tools | `toolnone`, `toolslash` (only the right arm and torso, so a walk keeps playing beneath), `toollunge` (full body) |
| Emotes | `wave`, `point`, `laugh`, `cheer`, `dance1`, `dance2`, `dance3`, each dance with `b` and `c` variants |

- **The motion comes from R6's own clips,** sampled from the engine at 60 FPS, then thinned to the keys the curve needs, so nothing about Roblox's easing or partly keyed joints is guessed. Linear interpolation is correct here: it is what the sources hold. Loops close on their first pose, which removes the seam a few R6 clips have.
- **Proportions:** a clip fits the rig it was built on. On another R15 the turns are identical and joint positions differ by up to about 0.13 studs on the far-sliding clips (`climb`, `cheer`). Rebuild for an exact fit. `R6OnR15.map(character)` reads a player's real avatar in Play; a default `HumanoidDescription` (HipHeight 2.19) is not the same body as a game's classic R15 (HipHeight 2).
- **In a game:** `R6OnR15.wire(animate, ids)` on a copy of the R15 `Animate` in StarterCharacterScripts, in Edit. R6's own `Animate` cannot run on R15, since it waits for `Torso`.
- **Tempo:** R15's `Animate` is tuned to its own clips, which plays R6's walk about 13% fast and its climb 2.4 times too fast. `wire` retunes its source to R6's `speed / 14.5` and `speed / 12`, and reports any line it cannot find in a customized script; `R6Tempo = false` leaves the source alone. Swimming uses the walk and idle, as R6 does.
- **Inherited quirks:** the audit finds what the originals do. R6's walk sinks a foot 0.16 studs, its dances slide feet, `sit` and `toollunge` lift both feet. A finding the R6 source also has is fidelity, not a bug; compare `AnimationInspector.audit` on both. To clean a contact, rework that clip with `plant` and `settle`, and say that it no longer matches the original.

## Rebuilding

Only for another rig's proportions, or to change the data:

```lua
R6OnR15.defaults(R6OnR15.map(rig), folder)  -- Edit only; a few seconds
```

Save each sequence from Studio (`SerializationService:SerializeInstancesAsync`) as `assets/r6-on-r15/clips/<clip>.rbxm` with no attributes, since Roblox warns that files edited elsewhere may not upload.
