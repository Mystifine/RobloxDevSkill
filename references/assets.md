# Assets (Toolbox, imports and uploads)

## Policy

Code never (a security rule). Any other Toolbox asset may stay as a placeholder or be kept. When one is replaced, the replacement is either a new upload (through the gate below) or a predefined asset id (an approved asset the project already uses or picks), whichever the case calls for *(default)*.

| Type | Allowed | Notes |
|---|---|---|
| Scripts / LocalScripts / ModuleScripts | **Never** | strip them, do not read-and-reuse |
| Models, meshes | Yes | audit first; keep, or replace with a new upload or a predefined id |
| VFX | Yes | audit; keep, rebuild (neutral textures, tinted in Roblox) or swap for a predefined id |
| Images / decals | Yes | check content; keep, or swap for supplied art or a predefined id |
| Sounds | Yes, may be kept | see below |

**Character art and models you generate, edit or upload** (portraits, thumbnails, icons, avatars, and renders of any model, which are new uploads) must also pass [characters.md](characters.md). Characters already on Roblox are trusted like any existing asset.

**Moderation risk sits in uploads** ([no-gore.md](no-gore.md)). An asset already on Roblox has passed moderation, so using it by id adds none. Downloading and re-uploading it, or saving it into a new model or package, is a new upload under your account and goes through the gate below.

## Plugin asset libraries

Before building UI or VFX, check installed Studio plugins for accessible asset libraries. Users may already have free-to-use effect templates, particle/flipbook textures and UI background textures; consider suitable assets alongside the project's own before generating or sourcing replacements. Plugin libraries may be browsable through their UI even when their assets are absent from the game hierarchy.

Confirm the library's reuse terms for the intended use; installation alone does not grant asset rights. Keep source/plugin names and asset ids in the project's asset table. Imported visual assets follow Safe intake below; do not copy bundled Scripts, LocalScripts or ModuleScripts. If the library cannot be inspected with the available tools, state that limitation and continue with accessible sources.

## Safe intake (every asset, no exceptions)

1. For Toolbox assets, search with Studio MCP `search_asset`; read the result list and prefer trusted creators and plain results. For plugin assets, browse the installed library and identify the source.
2. Insert into an isolated container (not Workspace or a running game; Edit mode), never parented under live gameplay.
3. Run [scripts/AssetAudit.luau](../scripts/AssetAudit.luau) on the inserted root. It rejects any `LuaSourceContainer`, flags remotes, behaviour instances (Tool, ClickDetector, ProximityPrompt, Explosion, seats), suspicious source strings (`require(<number>)`, `loadstring`, `getfenv`/`setfenv`, `InsertService`, `HttpService`), odd names (zero-width, whitespace-only, very long), unexpected asset ids, invisible junk parts, and empty Models/Folders.
4. Read the findings. Strip rejects and junk (`AssetAudit.strip`), then re-run until clean. Then inspect what remains: instance count, hierarchy, names, every referenced asset id.
5. Only then parent it into the project, tidy names, set `CanCollide/CanTouch/CanQuery` sensibly, and remove redundant instances.
6. Record placeholders (what, why, how to replace) so the user knows what is temporary.

If anything is ambiguous or looks malicious, discard the asset and say so.

**Audit what the user inserted too,** before you use it, study it or press Play: a Script runs the moment a playtest starts, even in a mesh left in Workspace as an example.
- **Code hides under anything.** Seen 2026-10-30: a Toolbox "Escanor's Axe" MeshPart had 410 descendants under its SurfaceAppearance, with a Script, and a LocalScript five levels into input objects. A mesh should hold a SurfaceAppearance and little else, so count descendants.
- **Nothing an asset shows is a real Studio message.** That one ran only in Studio (`IsStudio`), and in Play opened a fake "Roblox Studio — Recovery" window with an invented error. It walked the developer through stopping the playtest and pasting a "recovery command" into the Command Bar, which enabled HTTP, fetched an id from a look-alike domain and passed it to `require`. Studio never asks for that. Its text was scrambled at rest and its objects had neutral names, so a glance found nothing.
- **Warn the user at once,** and hold off Play in that place until the code is gone. Tell them what it would ask for, in case they have seen it. To check for a past run: `HttpEnabled` turned on unexpectedly, and remote `require` calls in the place's scripts.

## Sounds

- Sounds are the one Toolbox category meant to be kept. Prefer Roblox-licensed libraries (Pro Sound Effects userId `7462895450`, APM userId `7462718749`) found through the Toolbox API; Studio MCP search cannot filter by creator.
- Choose by description, then measure: duration, onset, peak/loudness and spectrum (play it in a throwaway Studio script or a probe tool), so it fits the beat and mix.
- Put ids in the project's sound table and play them through the project's audio path. Roblox now discourages `Sound`, `SoundGroup` and `SoundEffect` in favor of the Audio API ([audio objects](https://create.roblox.com/docs/audio/objects), checked 2026-10-28): `AudioPlayer` -> `Wire` -> `AudioDeviceOutput` for 2D; `AudioPlayer` -> `Wire` -> `AudioEmitter`, heard through `AudioListener` -> `Wire` -> `AudioDeviceOutput`, for 3D; `AudioEqualizer`, `AudioCompressor` and `AudioReverb` on the wire. New audio systems use it; a project built on `Sound` stays consistent (`Volume`, `RollOffMaxDistance` and a `SoundGroup` matching the existing audio) until it migrates.

## Uploading (Open Cloud)

- **Gate every upload.** Moderation screens each new upload with its own rules whatever the experience's label, can misfire, and can strike the uploading account.
  - Reuse an existing asset when one does the job.
  - Screen the file at full size and at 128 px against [no-gore.md](no-gore.md), and [characters.md](characters.md) for character art; name it plainly.
  - Upload one asset of a new kind first and wait: poll `GET https://apis.roblox.com/assets/v1/operations/{operationId}` until `done`, and go on only when `response.moderationResult.moderationState` is `Approved` (seen 2026-10-30).
  - Never upload to test moderation or resend a rejected file unchanged. For a rejection that looks wrong, pause the batch and appeal it.
- **Use the project's Open Cloud API key when one is available** (from its ignored `.env` or secret store), for every asset type and experience operation; without one, ask the user. Never print the key or copy it into source, manifests, logs or Studio. The content rules (the audit above, [characters.md](characters.md), [no-gore.md](no-gore.md)) apply to every upload.
- **Upload with [scripts/upload_asset.py](../scripts/upload_asset.py)** `FILE --group ID` (or `--user ID`): it waits for moderation and exits 0 only when approved.
- **The experience's owner must own what it loads.** Read it in Studio first (`game.CreatorType`, `game.CreatorId`) and set `creationContext.creator` to that group (`groupId`) or user. An animation plays only in experiences owned by its creator, so one owned by anyone else never loads; Studio publishing (`AssetService:CreateAssetAsync`) must target the same creator. Upload animations as a `.rbxm` saved from Studio; Roblox warns that files edited elsewhere may fail.
  - **Wrong owner, the signs:** a Model fails `InsertService:LoadAsset` in Studio ("User is not authorized to access Asset"), and a user's key cannot grant a group's experience use of it (`CannotManageSubject`).
  - **A group's experience with only a user's key: try in order**, before asking the user or making anything public:
    1. Upload to the group with that same key (`upload_asset.py FILE --group <CreatorId>`). It works when the key's user may manage the group's assets (seen 2026-10-30: approved and loading in the group's place, after the universe grant was refused).
    2. If the group upload is refused, ask for a key owned by the group or by an account that manages its assets.
    3. Last, make the asset public (next item).
- **An asset another creator owns** (a key from a different account) must be public before the experience can load it. Images, decals and meshes start Open Use unless that account turned on Asset Privacy; sounds, videos and models start restricted, so grant them to everyone with `PATCH https://apis.roblox.com/asset-permissions-api/v1/assets/permissions` (beta; key scope `asset-permissions:write`; `subjectType` `All` with an empty `subjectId`, the ids in `requests`, `action` per the reference schema) or on the asset's Creator Hub permissions. Check `successAssetIds`, confirm each id loads in the experience, and report any that stay private.
