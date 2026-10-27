# Assets (Toolbox, imports and uploads)

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

## Uploading (Open Cloud)

- **Upload with the asset key.** Projects often keep a separate API key for asset uploads, owned by a dedicated uploader account (for example `ROBLOX_CLOUD_ASSET_API_KEY` beside a main key). Use it for every asset upload, and keep the main key for what the experience owner must own (developer products, game passes, experience settings). With no asset key, ask before uploading with the main one. The content rules (the audit above, [characters.md](characters.md)) apply whichever account uploads. Never print a key or copy it into source, manifests, logs or Studio.
- **Make those uploads public (Open Use).** They belong to a different creator than the experience, so the game can load them only when they are open to everyone. Images, Decals and Meshes start as Open Use unless the uploading account turned on Asset Privacy. Grant anything restricted to everyone with `PATCH https://apis.roblox.com/asset-permissions-api/v1/assets/permissions` (beta; key scope `asset-permissions:write`; `subjectType` `All` with an empty `subjectId`, the ids in `requests`, `action` per the reference schema) or on the asset's Creator Hub permissions. Check `successAssetIds`, confirm each id loads in the experience, and report any that stay private.
