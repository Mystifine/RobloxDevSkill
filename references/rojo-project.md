# Rojo project: start one, or convert a Studio game

The blueprint is [assets/PROJECT_STRUCTURE.md](../assets/PROJECT_STRUCTURE.md): layout, Rojo mapping, startup order, packages (MysLib, Nexus, Pulse, SoulStore), toolchain, `AGENTS.md`, MCP and Graphify. Read it first; this file is the procedure. Work on a saved copy of the place, never the published one, and publish nothing.

## 1. Folder

Find where the user keeps projects: the folder holding the most Rojo projects (`default.project.json`), searching two levels under `~/Documents`, `~/Projects`, `~/dev`, `~/source/repos` and `~/Desktop`. If none is found, use `~/Documents`. Create `<that folder>/<GameName>` (PascalCase). It must be new or empty, never an existing project.

## 2. Initialize

1. **Create the files.** Copy the blueprint to `docs/project-structure.md` and create everything it lists:
   - `default.project.json`, `rokit.toml`, `wally.toml` (all four packages at reviewed versions), `selene.toml`;
   - `.gitignore`, `.graphifyignore` (MysLib kept in), `.mcp.json`;
   - `AGENTS.md`, `CLAUDE.md` (`@AGENTS.md`), `README.md`;
   - the `src/` skeleton, with `Server.server.luau` and `Client.client.luau` bootstrapping in an explicit order through MysLib's `Bootstrapper`.
2. **Run the toolchain.** `git init`, then the blueprint's commands (`rokit install`, `wally install`, `selene`, `rojo build`), and build the Graphify graph.
3. **Missing pieces never stop the work.** Install a missing tool when you can. Otherwise use a fallback, and record it in `docs/setup.md` with the step that would fix it:
   - no Graphify: targeted `rg` and bounded reads;
   - no package: a small local module behind the same interface, marked for replacement;
   - no Studio MCP: ask for the place as a `.rbxl` file and read it with Lune (`@lune/roblox`, `deserializePlace`).

## 3. Inventory (Studio MCP, Edit mode, the game open)

1. **Back up first.** The owner saves the place to a file (`File > Save to File`) outside the repository; everything after this works on a copy.
2. **Load [scripts/GameInventory.luau](../scripts/GameInventory.luau)**, then:
   - `Inventory.markdown(Inventory.scripts())` starts `docs/migration.md`: one row per legacy script with what it touches (requires, remotes, DataStores, tags, products, attributes). Fill in each row's new home and status until every row is verified. An asset-id `require` is outside code: drop it ([assets.md](assets.md)).
   - `select(2, Inventory.content())` gives the non-script instance counts per service. Keep them for the switch-over check.
   - `Inventory.export(first, budget)` pages the sources out to `migration/legacy/<DataModel path>.luau`. Rojo does not map that folder. Commit it first so the rewrite can be reviewed against it.
3. **Understand before redesigning.** Read the legacy code feature by feature, and query Graphify on `migration/legacy/`.

## 4. Rebuild into the blueprint

This is a rewrite into systems, not a copy of the scripts:

| Legacy | New home |
|---|---|
| Server Scripts, one domain each | `ServerScriptService/Services/<Domain>Service` with `main()` |
| Round loops, spawning, other infrastructure | `ServerScriptService/Systems/` |
| Config tables, ids, enums | `ReplicatedStorage/Constants/` (server-only ones: `ServerScriptService/Constants/`) |
| Remotes made in Studio or by scripts | declared once in `Constants/Remotes` (Nexus), each handler validating on the server |
| LocalScripts (StarterPlayerScripts, StarterGui, tools) | `ReplicatedStorage/Controllers/<Domain>Controller` with `main()` |
| Shared helpers | MysLib first (query it), else `ReplicatedStorage/Utility/` |
| One script copied into many models (doors, pads, kill bricks) | one service or controller over a CollectionService tag: tag the instances in Studio, delete the copies |
| DataStore code | `PlayerDataService` on SoulStore with the schema and profile, reading the **same store names and keys** (or an explicit migration) so no save is lost |

- **Composition roots only bootstrap,** in an explicit order.
- **Fix the legacy mistakes as you go:** client-trusted values, missing validation, leaks, polling, `wait()`. Log every behaviour change in `docs/migration.md`; gameplay otherwise stays the same.
- **UI:** GUIs built in Studio stay in Studio, and controllers find and drive them. Bind state to views with the project's reactive framework: Pulse in the blueprint (Value, Computed, Effect, Spring, Tween), or React, Fusion or Vide if the game already builds its UI with one.
- **Large games:** migrate one domain at a time, and pass section 6 steps 1-3 before starting the next.

## 5. Map ownership and switch over

- **Map code only.** `default.project.json` maps the blueprint's code folders, the entry scripts and the packages. Declare each service with `$className` and child entries, never map a whole service with `$path`, so Rojo cannot delete its Studio content. A Studio-owned folder inside a mapped tree gets `$ignoreUnknownInstances: true`. Scripts, LocalScripts and ModuleScripts move to Rojo; every other instance stays in Studio.
- **Switch over in the copy.** Delete the legacy scripts, `rojo serve`, connect the plugin. Then confirm that `Inventory.leftovers({ <every Rojo-managed instance> })` is empty and the content counts still match section 3.

## 6. Test the migration

1. **Static:** `selene src` and `rojo build` pass, no require cycles, and the Graphify graph is refreshed and queried.
2. **Inventory:** every `docs/migration.md` row is verified, there are no leftovers, and the content counts match the backup.
3. **Play**, server and client, with a clean console:
   - exercise every feature in the inventory side by side with the backup place: UI flows, combat, purchases with test products, teleports, tags;
   - with two players, a respawn and a rejoin.
4. **Data:** load a legacy-format save from a scratch store and confirm the same values come back. Never use production stores.
5. **Record** the results in `docs/migration.md` and `artifacts/verification/`, and report what you could not verify.
