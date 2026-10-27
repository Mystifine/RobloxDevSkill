# Assets (Toolbox and imports)

## Policy

| Type | Allowed | Notes |
|---|---|---|
| Scripts / LocalScripts / ModuleScripts | **Never** | strip them, do not read-and-reuse |
| Models, meshes | Yes, temporary preferred | audit first; plan to replace with our own |
| VFX | Yes, temporary preferred | audit; rebuild our own versions later |
| Images / decals | Yes, temporary preferred | check content; swap when the user supplies final art |
| Sounds | Yes, may be kept | see below |

**Character art and models** (portraits, thumbnails, icons, avatars) must also pass [characters.md](characters.md) before use or upload.

## Safe intake (every asset, no exceptions)

1. Search with Studio MCP `search_asset`; read the result list and prefer trusted creators and plain results.
2. Insert into an isolated container (not Workspace or a running game; Edit mode), never parented under live gameplay.
3. Run [scripts/AssetAudit.luau](../scripts/AssetAudit.luau) on the inserted root. It rejects any `LuaSourceContainer`, flags remotes, behaviour instances (Tool, ClickDetector, ProximityPrompt, Explosion, seats), suspicious source strings (`require(<number>)`, `loadstring`, `getfenv`/`setfenv`, `InsertService`, `HttpService`), odd names (zero-width, whitespace-only, very long), unexpected asset ids, invisible junk parts, and empty Models/Folders.
4. Read the findings. Strip rejects and junk (`AssetAudit.strip`), then re-run until clean. Then inspect what remains: instance count, hierarchy, names, every referenced asset id.
5. Only then parent it into the project, tidy names, set `CanCollide/CanTouch/CanQuery` sensibly, and remove redundant instances.
6. Record placeholders (what, why, how to replace) so the user knows what is temporary.

If anything is ambiguous or looks malicious, discard the asset and say so.

## Sounds

- Sounds are the one Toolbox category meant to be kept. Prefer Roblox-licensed libraries (Pro Sound Effects userId `7462895450`, APM userId `7462718749`) found through the Toolbox API; Studio MCP search cannot filter by creator.
- Choose by description, then measure: duration, onset, peak/loudness and spectrum (play it in a throwaway Studio script or a probe tool), so it fits the beat and mix.
- Put ids in the project's sound table; set `Volume`, `RollOffMaxDistance` and a `SoundGroup` to match existing audio.
