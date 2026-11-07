# Assets (Toolbox, imports and uploads)

## Policy

Code never (a security rule). Any other Toolbox asset may stay as a placeholder or be kept. When one is replaced, the replacement is either a new upload (through [the gate](uploading.md)) or a predefined asset id (an approved asset the project already uses or picks), whichever the case calls for *(default)*.

| Type | Allowed | Notes |
|---|---|---|
| Scripts / LocalScripts / ModuleScripts | **Never** | strip them, do not read-and-reuse |
| Models, meshes | Yes | audit first; keep, or replace with a new upload or a predefined id |
| VFX | Yes | audit; keep, rebuild (neutral textures, tinted in Roblox) or swap for a predefined id |
| Images / decals | Yes | check content; keep, or swap for supplied art or a predefined id |
| Sounds | Yes, may be kept | see below |

**Character art and models you generate, edit or upload** (portraits, thumbnails, icons, avatars, and renders of any model, which are new uploads) must also pass [characters.md](characters.md). Characters already on Roblox are trusted like any existing asset.

**Moderation risk sits in uploads** ([no-gore.md](no-gore.md)). An asset already on Roblox has passed moderation, so using it by id adds none. Downloading and re-uploading it, or saving it into a new model or package, is a new upload under your account and goes through [the gate](uploading.md).

## Plugin asset libraries

Before building UI or VFX, check installed Studio plugins for accessible libraries: effect templates/meshes (slash arcs, rings, cones), particle/flipbook textures and UI backgrounds. Search for assets compatible with the style already resolved by [visual-style.md](../art/visual-style.md); a library's look never overrides references or a matching project theme. Catalogs may be visible only in the plugin UI, outside the game hierarchy.

For UI reuse, availability or ownership does not establish a style match. Apply the [icon consistency check and fallback workflow](../ui/icons.md) to the related group before keeping library or Toolbox icons, including artwork embedded in buttons.

**Check them before generating any image** (a VFX texture or flipbook, an icon, a UI background or frame). Generation is the costly path (a Codex image run, a review at full size and an upload through moderation), and a plugin may already ship the common ones: sparks, glows, smoke, gradients, panel frames.
1. **List them.** On Windows, Studio keeps installed plugins at `%LOCALAPPDATA%\Roblox\<userId>\InstalledPlugins\<pluginAssetId>\<version>\Plugin.rbxm` and local ones in `%LOCALAPPDATA%\Roblox\Plugins`; each `Plugin.rbxm`'s root instance names its plugin. Effect, particle and UI libraries are the candidates.
2. **Read what is on disk.** Lune's `roblox.deserializeModel` opens a `Plugin.rbxm`. Read image ids from the Content properties (`ImageContent`, `TextureContent`, `ColorMapContent`): Lune 0.11 fails on `Image`, `Texture`, `TextureID` and `ColorMap` ("missing default value"). Most bundled images are the plugin's own interface, so preview a candidate before using it. A `settings.json` beside the versions can list the user's saved items with their ids (VFX Studio keeps saved effects there).
3. **Ask when only its window shows it.** A library that loads its catalog online shows it only in the plugin's window: ask the user to look there before you generate, since a question costs less than a run.

Confirm the library's reuse terms for the intended use; installation alone does not grant asset rights. Keep source/plugin names and asset ids in the project's asset table. Imported visual assets follow Safe intake below; do not copy bundled Scripts, LocalScripts or ModuleScripts. If neither you nor the user can inspect a library, say so and continue with accessible sources.

## Safe intake (every asset, no exceptions)

1. For Toolbox assets, search with Studio MCP `search_asset`; read the result list and prefer trusted creators and plain results. For plugin assets, browse the installed library and identify the source.
2. Insert into an isolated container (not Workspace or a running game; Edit mode), never parented under live gameplay.
3. Run [scripts/AssetAudit.luau](../../scripts/AssetAudit.luau) on the inserted root. It rejects any `LuaSourceContainer`, flags remotes, behaviour instances (Tool, ClickDetector, ProximityPrompt, Explosion, seats), suspicious source strings (`require(<number>)`, `loadstring`, `getfenv`/`setfenv`, `InsertService`, `HttpService`), odd names (zero-width, whitespace-only, very long), unexpected asset ids, invisible junk parts, and empty Models/Folders.
4. Read the findings. Strip rejects and junk (`AssetAudit.strip`), then re-run until clean. Then inspect what remains: instance count, hierarchy, names, every referenced asset id.
5. Only then parent it into the project, tidy names, set `CanCollide/CanTouch/CanQuery` sensibly, and remove redundant instances.
6. Record placeholders (what, why, how to replace) so the user knows what is temporary.

If anything is ambiguous or looks malicious, discard the asset and say so.

**Audit what the user inserted too,** before you use it, study it or press Play: a Script runs the moment a playtest starts, even in a mesh left in Workspace as an example.
- **Code hides under anything.** A Toolbox "Escanor's Axe" MeshPart had 410 descendants under its SurfaceAppearance, with a Script, and a LocalScript five levels into input objects. A mesh should hold a SurfaceAppearance and little else, so count descendants.
- **Nothing an asset shows is a real Studio message.** That one ran only in Studio (`IsStudio`), and in Play opened a fake "Roblox Studio — Recovery" window with an invented error. It walked the developer through stopping the playtest and pasting a "recovery command" into the Command Bar, which enabled HTTP, fetched an id from a look-alike domain and passed it to `require`. Studio never asks for that. Its text was scrambled at rest and its objects had neutral names, so a glance found nothing.
- **Warn the user at once,** and hold off Play in that place until the code is gone. Tell them what it would ask for, in case they have seen it. To check for a past run: `HttpEnabled` turned on unexpectedly, and remote `require` calls in the place's scripts.

## Sounds

- Sounds are the one Toolbox category meant to be kept, and any public one may be used. Finding, measuring and playing them: [audio.md](../art/audio.md).

