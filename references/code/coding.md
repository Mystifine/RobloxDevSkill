# Coding

## Before writing

1. Map the project: `default.project.json` (what lives where), dependency manifests (`wally.toml`/`pesde.toml`, `rokit.toml`), `Packages/`, `selene.toml`, shared `Utility`/`Constants`/`Services` folders, lint config. Search for an existing helper before writing one (signals, maids, tweens, particle players, networking, data, pooling). A project without a clear structure, or a new one, follows [rojo-project.md](rojo-project.md).
2. Read the dependency's source or docs for any function you will call. Warn the user about: deprecated APIs, missing edge cases (nil, zero, fractional input), hidden per-frame cost, silent overwrites (for example a networking wrapper that keeps only one listener per event, so a second `Connect` replaces the first), and unbounded caches. Report; do not edit `Packages/` unless asked.
3. Match the module pattern in use (`init.luau`, class tables, service/controller split, type exports, `--!strict`).

## Performance (backend first)

- **Loops.** One shared `Heartbeat`/`task` loop per system, not one per object. Disconnect when the set is empty. No `wait()`; use `task.wait/defer/delay/spawn`. Never poll for something an event gives you.
- **Allocation.** Reuse tables (`table.clear`, `table.create`), `RaycastParams`/`OverlapParams`, and `TweenInfo`. Avoid closures and string concatenation in hot paths. A `task.delay`/`task.spawn` per item in a hot path is a new thread each: group items that wake together into one call (an effect player's delay per particle layer, grouped by start time, cut the game's allocation from 2,838 to 868 KB/s with one other fix). Cache `GetService` results and `FindFirstChild` lookups outside loops. Use `Instance.new` then set properties, parent last.
- **Queries.** Avoid `GetDescendants`/`GetChildren` per frame; use `CollectionService` tags or maintained sets. Prefer spatial queries scoped by `OverlapParams`; filter early.
- **Networking.** Server-authoritative (validation: Security, below). Batch and throttle, send deltas, never per-frame replication of what clients can derive. Use `buffer`/packed values for high-frequency payloads. Prefer `UnreliableRemoteEvent` only for cosmetic, loss-tolerant data.
- **Parallel Luau** for heavy pure computation (grids, procedural generation, many raycasts): scripts under different `Actor`s run on separate cores after `task.desynchronize()` or in `ConnectParallel` handlers. They read most properties but write instances only after `task.synchronize()`, cannot `require` while desynchronized, and talk through `Actor:SendMessage` or `SharedTable`. Group actors by logical unit, not one per object ([multithreading](https://create.roblox.com/docs/scripting/multithreading)).
- **Moving many parts:** `workspace:BulkMoveTo(parts, cframes, Enum.BulkMoveMode.FireCFrameChanged)` instead of a CFrame write per part, for parts that move independently. A many-part model that moves as one: weld every part (`WeldConstraint`) to one anchored root and write only the root's CFrame (three 374-part models shaken every frame: 2.93 ms of script a frame with `BulkMoveTo` or `PivotTo`, 0.82 ms welded; a part 21 studs out stayed within 0.00006 studs).
- **Streaming.** With StreamingEnabled, instances beyond the radius are parented to nil on the client, and local-only changes on them can be lost. A model that must arrive whole gets `ModelStreamingMode = Atomic` (wait only on the model); one that must always exist, `Persistent` (wait for `Workspace.PersistentLoaded`); the default is `Nonatomic`. Prefetch with `Player:RequestStreamAroundAsync` before moving a player; `StreamOutBehavior = Opportunistic` is the recommended setting ([streaming](https://create.roblox.com/docs/workspace/streaming)).
- **Memory.** Track every connection/instance/thread with a maid/janitor or the project's equivalent; clean up on player leave, death, unequip and destroy. `Debris:AddItem` is fine for fire-and-forget but cannot be cancelled.
- **Luau.** `--!strict` and typed exports; `@native`/`--!native` only for measured numeric hot paths; `if-then` expressions over closures; integer-keyed arrays.
- **Quality.** Do not lower fidelity, range or features to get a speedup. If a trade is unavoidable, state it and let the user choose. Measure before and after, as [performance.md](performance.md) says (Studio's frame rate swings with the machine's load).

## Security (the client is hostile)

- **Validate every remote argument on the server:** type (`typeof`), range, length, rate and ownership. NaN is a number that fails every comparison, so a check written as a rejection (`if n < 1 or n > 100 then return end`) lets it through, and `math.clamp` returns it unchanged: reject `n ~= n` and `math.abs(n) == math.huge` first, the same for every component of a Vector3 or CFrame. Cap string and table sizes.
- **An Instance argument can be any instance the client can see,** including another player's plot, pet or tool: check that it is the sender's own (an owner attribute or a server-side map), never trust its name or path.
- **Rate-limit per player and action** on the server clock, not with a client cooldown; drop the excess quietly.
- **Judge hits on the server:** distance and line of sight from the server's view of both characters, the weapon's range plus a small latency allowance, and the cooldown on the server clock. Never take a client's damage number, position or target list as given; `Touched` is easy to fake, so damage uses server-side spatial queries.
- **Network ownership:** the server hands an unanchored assembly near a player to that player's client, who can then move it anywhere. Authoritative assemblies (NPCs, projectiles, loot) call `SetNetworkOwner(nil)` on an unanchored part ([gameplay.md](gameplay.md)).

## Data

- Budget DataStore calls, save on `PlayerRemoving` + `BindToClose` + interval, use `UpdateAsync` for read-modify-write, retry with backoff, session-lock, never yield inside critical sections without a guard.
- **Limits** ([Creator Hub](https://create.roblox.com/docs/cloud-services/data-stores/error-codes-and-limits)): store names, keys and scopes up to 50 characters; a value up to 4,194,304 characters of serialized JSON (measure with `HttpService:JSONEncode`); per server about 60 + 40 per player reads and writes a minute (ordered writes 30 + 5); 4 MB of writes per key a minute; queues of 30 per request type whose overflow is dropped (errors 301-306). Check `DataStoreService:GetRequestBudgetForRequestType` before bulk work.
- An `UpdateAsync` transform can run more than once and must not yield; return nil to cancel the write. `BindToClose` gets about 30 seconds for the final saves.
- **A leaderboard that leaves staff out** decides by account (listed user ids and group roles, which also covers players who are offline), never by a testing permission: a console every Studio tester may open would hide them all. Keep saving their stats and filter only what is shown, reading on through the sorted pages (`AdvanceToNextPageAsync`) until the board has its count of eligible rows.
- **Right to erasure:** when a player has their account deleted, Roblox lists the request in a daily inbox message and calls a Right to Erasure Request webhook if one is set. The creator must delete that player's personal data: configure the game's data store deletion templates for keys that carry the user id, and a webhook for anything else (ordered stores, outside services). Key saves by user id so deletion is mechanical ([RTBF and creators](https://create.roblox.com/docs/production/publishing/RTBF-and-creators)).

## Known pitfalls

- **A statement cannot start with a parenthesis after a line ending in a name or a call:** `local a = b` then `(x :: any).y = 1` does not compile ("Ambiguous syntax: this looks like an argument list for a function call"), which `execute_luau` reports only as "Failed to parse command code", while selene and `rojo build` pass it. Cast into a local first, or end the line before with `;`.
- `GetPartBoundsInBox`/`GetPartBoundsInRadius` count a wedge (or any non-block) by its whole bounding box; use `GetPartsInPart` for shape-accurate tests.
- A ray or cast starting inside a part does not hit that part. Thin spherecasts can skip seams, and `Spherecast` results can contain a NaN position on wedge edges: validate `Position` before use.
- `Humanoid.Health` is float32: adding 1 HP vanishes above roughly 16.8M max health. Carry fractional heals yourself.
- A raw RemoteEvent queues server events until its first client listener, but a networking wrapper that connects once and dispatches to registered handlers drops events whose handler is not registered yet: register every handler, then start the transport.
- `WaitForChild` on world content under StreamingEnabled can take longer than its 5 s warning; give it an explicit timeout (`math.huge` to wait silently) or react to `ChildAdded`.
- Code a Studio MCP call requires gets its own module copy, and calls run one at a time: [studio-testing.md](studio-testing.md#studio-mcp-calls).
- `AvatarEditorService:PromptSetFavorite` for an item the account already favorites showed nothing in Studio and never fired `PromptSetFavoriteCompleted`, and every later call errored "PromptSetFavorite can not be called again while currently in progress". The state cannot be read first either: `GetFavoriteAsync` errors "Permission must be obtained with PromptAllowInventoryReadAccess". Prompt once, then offer any reward as a plain claim that does not depend on the favorite.
- With the default Backpack, number keys 1-9 reach `UserInputService.InputBegan` with `gameProcessedEvent` true (the hotbar takes them), so a handler that skips processed input misses every number-key pick. For those keys, skip only while `UserInputService:GetFocusedTextBox()` returns a box.
- **"Players can't join" with nothing in the scripts kicking them:** read the universe before the code (Open Cloud `GET https://apis.roblox.com/cloud/v2/universes/{id}`). An `ageRating` of `AGE_RATING_UNSPECIFIED`, no maturity questionnaire filled in, kept every player out; then check its visibility and the place's own settings.

## Verify

Run the project's linter/formatter/builder (for example `selene`, `stylua`, `rojo build`) and its tests. None of them parses Luau as Roblox does: a module Roblox refuses fails every module that requires it, so read the Play boot output on server and client for "Failed to REQUIRE" and the project's loader warnings. Then test in a Studio Play session: the console is clean, no leaked instances/connections after the feature ends, and behaviour holds for two players and after rejoin. State anything you could not run.

**In Studio:** specs that drive live services, and Play tests with real input (keys, clicks, the camera, moving the character, timing, gamepad and touch), so the client path is tested, not only the remotes: [studio-testing.md](studio-testing.md).
