# Roblox Project Structure

A setup blueprint for a Rojo-managed Roblox experience: repository layout, runtime boundaries and tooling, not any game's services. Use it to initialize or align a project; replace example names and optional folders as needed. [AGENTS.md](AGENTS.md) stays the canonical source of project-specific rules.

## Repository layout

```text
project/
├── .claude/                       # Optional Claude settings/hooks and skills
├── .codex/config.toml             # Optional project-scoped Codex MCP config
├── .vscode/settings.json          # Editor preferences only
├── artifacts/verification/        # Retained test evidence; not runtime source
├── assets/                        # Editable asset sources and import/build helpers
├── docs/                          # Setup, architecture and behavioral contracts
├── graphify-out/                  # Generated Graphify graph/report (when enabled)
├── Packages/                      # Wally-generated shared dependencies
├── ServerPackages/                # Wally-generated; mounted under ServerScriptService
├── src/                           # Rojo-owned runtime source
│   ├── ReplicatedFirst/LoadingCover.client.luau
│   ├── ReplicatedStorage/
│   │   ├── Constants/             # Shared IDs, enums, configs, remote declarations
│   │   ├── Controllers/           # Client and UI controllers
│   │   ├── States/                # Client state containers, where needed
│   │   └── Utility/               # Client-safe helpers and presentation code
│   ├── ServerScriptService/
│   │   ├── Constants/             # Server-only configs, save schema/profile
│   │   ├── Services/              # Server-authoritative domain services
│   │   ├── Systems/               # Server infrastructure and runtime systems
│   │   └── Server.server.luau     # Server composition root
│   └── StarterPlayer/
│       ├── StarterCharacterScripts/   # Animate/Health only when replacing defaults
│       └── StarterPlayerScripts/Client.client.luau  # Client composition root
├── tests/                         # Specs and fixtures; never runtime code
├── tools/                         # Local build, validation and authoring helpers
├── .env                           # Local secrets; ignored, never committed
├── .graphifyignore                # Graphify scan exclusions (MysLib stays in the graph)
├── .mcp.json                      # Roblox Studio and Blender MCP definitions
├── AGENTS.md                      # Canonical shared agent instructions
├── CLAUDE.md                      # Imports AGENTS.md with `@AGENTS.md`
├── default.project.json           # Rojo DataModel mapping and asset ownership
├── rokit.toml                     # Pinned CLI tools
├── selene.toml                    # Luau lint configuration
├── wally.toml / wally.lock        # Dependency manifest / generated lockfile
└── README.md, .gitignore
```

- `src/`: only authored files Rojo intentionally maps into Roblox. Never edit installed packages or Studio-managed content as source.
- `assets/`: editable sources, exports, manifests and import helpers. Declare ownership in `default.project.json`; don't represent Studio-authored content as if Rojo can recreate it.
- `Packages/`, `ServerPackages/`: generated from `wally.toml`/`wally.lock`; change the manifest and run `wally install`.
- `docs/`: setup, system contracts, controls and verification notes. Link to them from `AGENTS.md` instead of duplicating them.
- `tests/`: test code and isolated fixtures; document how each spec runs.
- `tools/`: repeatable scripts. Anything that publishes or mutates external resources needs explicit invocation and local credentials.
- `artifacts/verification/`: evidence worth keeping. Disposable builds go to the OS temp directory or an ignored cache.
- `graphify-out/`: generated analysis, not code. Keep graph/report if the project uses Graphify; ignore caches.

## Rojo ownership and runtime mapping

`default.project.json` is the source of truth for how files become instances:

| Repository path | Roblox destination | Contents |
| --- | --- | --- |
| `src/ReplicatedFirst/` | `ReplicatedFirst` | Minimal early-loading client code |
| `src/ReplicatedStorage/{Constants,Controllers,States,Utility}/` | same names under `ReplicatedStorage` | Shared non-secret config, client controllers, client state, safe helpers |
| `src/ServerScriptService/{Constants,Services,Systems}/` | same names under `ServerScriptService` | Server settings/schema/store profile, domain services, infrastructure |
| `src/StarterPlayer/StarterPlayerScripts/` | `StarterPlayer.StarterPlayerScripts` | Client entry script |
| `src/StarterPlayer/StarterCharacterScripts/` | `StarterPlayer.StarterCharacterScripts` | Character-lifetime scripts only |
| `Packages/` | `ReplicatedStorage.Packages` | Wally shared dependencies |
| `ServerPackages/` | `ServerScriptService.ServerPackages` | Wally server dependencies |

Declare important service classes and Studio-preserved roots explicitly. Use `$ignoreUnknownInstances` only for subtrees Studio owns, never to hide missing mappings, and record the exceptions in `AGENTS.md`. Keep server-only modules, save data, secrets and authoritative logic out of `ReplicatedStorage`: everything replicated is visible and untrusted, whatever its folder name.

## Source architecture

- **Shared/client:** `Constants/` holds replicated config, enums, remote declarations and asset IDs (no secrets or authoritative state). `Controllers/` coordinates input, presentation, UI and reactions to server updates (split UI subcontrollers into a child folder when numerous). `States/` exists only when a distinct state abstraction helps; never mirror the whole save as editable client state. `Utility/` holds cohesive client-safe helpers. `ReplicatedFirst/` holds only code that must run before replicated content.
- **Server:** a `Services/` module owns validation, mutation, persistence coordination and lifecycle for one domain and exposes only needed APIs. `Systems/` is for cross-cutting infrastructure, not a second service folder. `Constants/` holds server-only config, schemas and store profiles. Use a folder with `init.luau` for cohesive submodules, a single file otherwise; no speculative empty layers.

### Composition roots and startup

1. `Server.server.luau` requires the system and service bootstrappers; `Client.client.luau` requires the controller bootstrapper.
2. Initialize foundational systems, then save infrastructure, then services that register save-dependent work.
3. Keep dependency order explicit in bootstrappers, never from filesystem or child enumeration order. Start dependent controllers intentionally.
4. Composition roots assemble modules; they contain no feature behavior.

Give each bootstrapped module one `main()` (or the project's equivalent). Make asynchronous startup explicit per module, never a way to hide ordering dependencies.

## Player data and SoulStore pattern

A reusable server/client boundary:

```text
src/ReplicatedStorage/Constants/Remotes.luau                  # Data snapshot/update remote declarations
src/ReplicatedStorage/Controllers/PlayerDataController.luau   # Client read/observe API
src/ServerScriptService/Constants/PlayerDataSchema.luau       # Defaults, reconcile shape, migrations
src/ServerScriptService/Constants/DataStoreProfile.luau       # Store names and environment selection
src/ServerScriptService/Services/PlayerDataService.luau       # SoulStore lifecycle and server API
```

- The server-only schema declares the default save; keep shared UI config out unless genuinely persistent. The server-only profile isolates production and development store names; client input never selects or resets a production store.
- SoulStore is a Wally **server dependency**, required only through `ServerScriptService.ServerPackages`. Follow its pinned API; never copy package code.
- `PlayerDataService` loads one session per player, reconciles from a fresh schema copy, registers save/removal, and exposes a small API. It is not a feature service. It initializes before save-dependent services, which register through a loaded-player lifecycle instead of assuming data during `PlayerAdded`.
- Writes are server-authoritative and validated; clients never send arbitrary save paths or values.
- `PlayerDataController` owns the client cache: initial snapshot by request, then server-pushed changes. It queues updates arriving before the snapshot and cleans up subscriptions on teardown. UI reads and subscribes; it never mutates the save.
- Declare remote names and payloads in one shared place; the server owns handlers and validation.
- Keep migrations explicit and server-side, with tests/fixtures for defaults, reconciliation and migrations that don't touch production DataStores.

## Wally packages

The repository owns the manifest and lockfile; package folders are install outputs. Include every package below, pinned to reviewed versions (no angle-bracket placeholders in an installable manifest):

```toml
[package]
name = "owner/project-name"
version = "0.1.0"
registry = "https://github.com/UpliftGames/wally-index"
realm = "shared"

[dependencies]
myslib = "mystifine/myslib@<reviewed-version>"
nexus = "mystifine/nexus@<reviewed-version>"
pulse = "mystifine/pulse@<reviewed-version>"

[server-dependencies]
soulstore = "mystifine/soulstore@<reviewed-version>"
```

`[dependencies]` install to `ReplicatedStorage.Packages`; `[server-dependencies]` to `ServerPackages`, server code only. Commit `wally.toml` and `wally.lock`, run `wally install` after manifest changes or on a fresh checkout, never edit package internals, and require packages through the Rojo-mounted folders.

## Toolchain and linting

Pin tools in `rokit.toml` and commit them:

```toml
[tools]
rojo = "rojo-rbx/rojo@<pinned-version>"
selene = "Kampfkarren/selene@<pinned-version>"
wally = "UpliftGames/wally@<pinned-version>"
```

`selene.toml` uses `std = "roblox"`. Check changes with:

```powershell
rokit install
wally install
selene <changed-luau-files>
rojo build default.project.json -o "$env:TEMP/project-check.rbxlx"
rojo serve default.project.json   # sync with Studio
```

A Rojo build validates mapped source; it does not recreate Studio-owned content.

## Asset generation guidelines

- **Icons:** Generate at 512 × 512 pixels (1:1) with a transparent background unless otherwise specified. Match the established visual style and tone of the project.
- **Models:** Keep each generated model at or below 20,000 triangles. For higher-tier models, target around 18,000 triangles maximum to leave performance headroom.

## Agent instruction files

- **`AGENTS.md`** is the one canonical brief: purpose, ownership, architecture, security rules, verification, MCP discovery and Graphify usage (sections below). Link to `docs/` for details and volatile numbers rather than copying them.
- **`CLAUDE.md`** imports it with a line containing only `@AGENTS.md`. Claude Code expands `@path` imports into context at session start; a plain Markdown link such as `[AGENTS.md](AGENTS.md)` is **not** loaded. Add only short Claude-specific notes beneath the import, never a second copy of the rules.
- `.claude/` holds optional Claude settings, hooks and skills; `.codex/config.toml` holds Codex configuration such as MCP servers. Neither replaces `AGENTS.md`.
- Add other agent files only when a tool requires them, keep them short and point back to `AGENTS.md`. Never check in instructions that disagree about ownership, startup or verification.

## MCP configuration

MCP files configure tools, not runtime architecture.

- **Discover every session:** check Roblox Studio MCP and Blender MCP in available agent tools, client configs and installed launchers/add-ons. Absence from `.mcp.json` proves nothing.
- **Merge, don't invent:** add working entries for both to `.mcp.json` and, where Codex needs its own format, `.codex/config.toml`, keeping names aligned. Preserve unrelated servers and owner settings, avoid duplicates, prefer portable commands, and never invent paths, endpoints or credentials. Secrets come from ignored env files or a secret store, never MCP config.
- **Check connectivity read-only** (Studio DataModel, Blender scene); configuration alone proves nothing. Use connected tools for Studio verification and Blender asset work within Rojo ownership.
- Document prerequisites, launch commands and connectivity results in `docs/`. When something is missing, report the exact limitation and next setup step, then continue independent work. Never claim an unavailable integration was used.

## Graphify

Graphify is optional repository knowledge tooling, never a runtime or package dependency. Checking for it and using it when available is required. Give `AGENTS.md` a concise section named `Graphify and efficient project exploration` with the discovered entrypoint, verified query/update commands (or a docs link), graph location, refresh rules, delegation rule and fallback; listing it as available is not enough. Carry these rules:

- At the start of every task, discover a Graphify skill, MCP tool or CLI, then run a focused, bounded query for the task's feature or symbols before broad exploration. Do this even for docs- or config-only tasks.
- MysLib is part of every query's scope. Before writing a helper (timers, debris, hitboxes, attribute modifiers, bootstrapping and the like), query for it, for example `graphify query "MysLib <capability>"`, and reuse what exists instead of re-implementing it.
- Read only the source excerpts needed to verify results; current source is authoritative over a stale graph. Never dump the full graph or report into context. Reuse findings within the task.
- With no usable graph, build it with the documented command, then query. Refresh after source or architecture changes or stale results, using incremental updates when supported; don't reindex an unaffected graph.
- When one agent delegates work to others (possibly in parallel worktrees, with the graph tracked), delegates query but don't refresh. The directing agent refreshes once in the main checkout after integrating accepted work.
- `.graphifyignore` (gitignore syntax) excludes build outputs, caches, binaries, secrets and package installs, **except MysLib**: its sources stay in the graph so queries surface its APIs. The other packages stay out:

  ```gitignore
  Packages/*
  !Packages/_Index/
  Packages/_Index/*
  !Packages/_Index/mystifine_myslib@*/
  ServerPackages/
  ```

  After adding or upgrading MysLib, refresh the graph and confirm a MysLib query returns its modules. `graphify-out/` (`graph.json`, HTML, `GRAPH_REPORT.md`) holds no source.
- If Graphify is unavailable or fails, report what was checked once and continue with targeted `rg` plus bounded reads. Never claim a query or update that didn't succeed, or measured token savings without evidence.

## Initialize a new checkout

1. Discover and configure Roblox Studio and Blender MCP and run read-only connection checks; discover Graphify and run its documented workflow. Carry both into `AGENTS.md`, and create `CLAUDE.md` with `@AGENTS.md`.
2. Run the toolchain commands above.
3. Before adding gameplay modules, make the Rojo map, package realms, entry scripts and bootstrap order match this document. If the experience persists player data, add the schema/profile, SoulStore-backed `PlayerDataService`, `PlayerDataController` and their remotes as one foundation.
4. Keep `.env` and local credentials out of version control. Commit `wally.lock`, tool pins, project mappings and canonical instructions so others can reproduce the setup.
