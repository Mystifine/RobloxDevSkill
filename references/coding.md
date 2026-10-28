# Coding

## Before writing

1. Map the project: `default.project.json` (what lives where), dependency manifests, `Packages/`, shared `Utility`/`Constants`/`Services` folders, lint config. Search for an existing helper before writing one (signals, maids, tweens, particle players, networking, data, pooling). A project without a clear structure, or a new one, follows [rojo-project.md](rojo-project.md).
2. Read the dependency's source or docs for any function you will call. Warn the user about: deprecated APIs, missing edge cases (nil, zero, fractional input), hidden per-frame cost, silent overwrites (for example a networking wrapper that keeps only one listener per event, so a second `Connect` replaces the first), and unbounded caches. Report; do not edit `Packages/` unless asked.
3. Match the module pattern in use (`init.luau`, class tables, service/controller split, type exports, `--!strict`).

## Performance (backend first)

- **Loops.** One shared `Heartbeat`/`task` loop per system, not one per object. Disconnect when the set is empty. No `wait()`; use `task.wait/defer/delay/spawn`. Never poll for something an event gives you.
- **Allocation.** Reuse tables (`table.clear`, `table.create`), `RaycastParams`/`OverlapParams`, and `TweenInfo`. Avoid closures and string concatenation in hot paths. Cache `GetService` results and `FindFirstChild` lookups outside loops. Use `Instance.new` then set properties, parent last.
- **Queries.** Avoid `GetDescendants`/`GetChildren` per frame; use `CollectionService` tags or maintained sets. Prefer spatial queries scoped by `OverlapParams`; filter early.
- **Networking.** Server-authoritative; validate every remote argument (type, range, rate, ownership). Batch and throttle, send deltas, never per-frame replication of what clients can derive. Use `buffer`/packed values for high-frequency payloads. Prefer `UnreliableRemoteEvent` only for cosmetic, loss-tolerant data.
- **Data.** Budget DataStore calls, save on `PlayerRemoving` + `BindToClose` + interval, use `UpdateAsync` for read-modify-write, retry with backoff, session-lock, never yield inside critical sections without a guard.
- **Memory.** Track every connection/instance/thread with a maid/janitor or the project's equivalent; clean up on player leave, death, unequip and destroy. `Debris:AddItem` is fine for fire-and-forget but cannot be cancelled.
- **Luau.** `--!strict` and typed exports; `@native`/`--!native` only for measured numeric hot paths; `if-then` expressions over closures; integer-keyed arrays.
- **Quality.** Do not lower fidelity, range or features to get a speedup. If a trade is unavoidable, state it and let the user choose. Profile (MicroProfiler, Script Profiler, `os.clock`) before and after.

## Known pitfalls

- `GetPartBoundsInBox`/`GetPartBoundsInRadius` count a wedge (or any non-block) by its whole bounding box; use `GetPartsInPart` for shape-accurate tests.
- A ray or cast starting inside a part does not hit that part. Thin spherecasts can skip seams, and `Spherecast` results can contain a NaN position on wedge edges: validate `Position` before use.
- `Humanoid.Health` is float32: adding 1 HP vanishes above roughly 16.8M max health. Carry fractional heals yourself.
- Anything a Studio MCP `execute_luau` call requires has its own module cache; to test live services run them from a temporary Script and remove it afterwards.
- Studio MCP calls run one at a time, so a long call blocks every other. Start long work from a temporary Script and poll an attribute it writes.

## Verify

Run the project's linter/formatter/builder (for example `selene`, `stylua`, `rojo build`) and its tests. Then test in a Studio Play session: the console is clean, no leaked instances/connections after the feature ends, and behaviour holds for two players and after rejoin. State anything you could not run.

**Specs in Studio:** drive live services from a temporary Script (a spec as its child ModuleScript) that writes its result to an attribute you poll; an Edit-mode `execute_luau` keeps a stale require cache after edits, so run specs in Play. Never let a test write live or the owner's saves (use a scratch/QA profile and restore what it changed), and delete every temporary Script, ModuleScript and server you started.
