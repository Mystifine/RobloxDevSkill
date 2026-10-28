# Rojo project: start one, or convert a Studio game

The blueprint is [assets/PROJECT_STRUCTURE.md](../assets/PROJECT_STRUCTURE.md): layout, Rojo mapping, startup order, packages (MysLib, Nexus, Pulse, SoulStore), toolchain, `AGENTS.md`, MCP and Graphify. Read it first; this file is the procedure. Work on saved copies of the place, never the published one or the owner's open session, and publish nothing.

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

1. **Back up first.** The owner saves the place to a file (`File > Save to File`) outside the repository. Copy it twice: a **working copy** for the switch-over and a **reference copy** left untouched, to play beside the port. Open each in its own Studio window.
2. **Load [scripts/GameInventory.luau](../scripts/GameInventory.luau)**, then:
   - `Inventory.markdown(Inventory.scripts())` starts `docs/migration.md`: one row per legacy script with what it touches.
     - It records requires, remote calls (even on remotes made at runtime), DataStores (a computed store name is shown as its expression), tags, products and attributes.
     - Fill in each row's new home and status until every row is verified.
     - An asset-id `require` is outside code: drop it ([assets.md](assets.md)).
   - `select(2, Inventory.content())` gives the non-script instance counts per service. Keep them for the switch-over check.
3. **Export the legacy code from the backup file**, not through Studio: `lune run <skill>/scripts/export_place.luau <backup.rbxl> migration/legacy`.
   - It writes every script byte for byte (a 26-script, 1 MB game took 1.3 s).
   - Rojo does not map `migration/legacy/`. Commit it first, so the rewrite can be reviewed against it.
4. **Understand before redesigning.** Read the legacy code feature by feature, and query Graphify on `migration/legacy/`.

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

- **Order of work.** Domains with their own scripts and state migrate one at a time, each passing section 6 steps 1-3 before the next. A monolith whose systems share one session table cannot be split that way: list which domain owns each field, move each domain with its fields, and prove parity offline (configs equal to the old ones, the new save load equal to the old `load()`) before the switch-over.
- **Composition roots only bootstrap,** in an explicit order. Client handlers register before the transport starts, so no early server event is dropped.
- **One teardown per player.** The data service takes the final save, then releases each domain in reverse start order. A service with its own `PlayerRemoving` races that order (seen: a plot freed before its units were cleared, their loops still running).
- **An unpublished copy has no DataStores:** with `game.PlaceId == 0` every DataStoreService call throws, and a save library may retry forever. Give the save layer a session-memory mode for that case so the copy stays playable; real saves are tested as in section 6.
- **Fix the legacy mistakes as you go:** client-trusted values, missing validation, leaks, polling, `wait()`. Log every behaviour change in `docs/migration.md`; gameplay otherwise stays the same.
- **UI:** with a reactive UI framework in the project, rebuild the Studio GUIs as reactive components in code. The blueprint installs Pulse; React, Fusion or Vide also count.
  - **Components:** a component function builds its instances. Framework values (Pulse `Value`, `Computed`) hold state: data, the open window, the selected tab. A component's effect (one, or a few) reads them and writes its instances. Never give each instance property its own value or effect: a port that did allocated 17x the original's Lua memory per second on an idle HUD. Reuse a shared components module for buttons and panels.
  - **GUIs built in code** by the legacy scripts: port the builder calls as they are, under the same lifetime and state rules, then convert screen by screen, each checked for parity.
  - **Match the original** layout, sizes, colors, fonts and images: pass the parity and UIBounds checks (section 6), then delete the Studio GUI.
  - **Without a reactive framework,** the GUIs stay in Studio, and controllers find and drive them.

## 5. Map ownership and switch over

- **Map code only.** `default.project.json` maps the blueprint's code folders, the entry scripts and the packages. Declare each service with `$className` and child entries, never map a whole service with `$path`, so Rojo cannot delete its Studio content. A Studio-owned folder inside a mapped tree gets `$ignoreUnknownInstances: true`. Scripts, LocalScripts and ModuleScripts move to Rojo; every other instance stays in Studio, except GUIs rebuilt as components.
- **Switch over in the working copy.** Delete the legacy scripts, `rojo serve`, connect the plugin (or write the `rojo build` output into the copy with Lune's `@lune/roblox`). Then confirm that `Inventory.leftovers({ <every Rojo-managed instance> })` is empty and the content counts still match section 3, apart from the GUIs rebuilt as components.

## 6. Test the migration

1. **Static:** `selene src` and `rojo build` pass, no require cycles, and the Graphify graph is refreshed and queried.
2. **Inventory:** every `docs/migration.md` row is verified, there are no leftovers, and the content counts match the backup (apart from rebuilt GUIs).
3. **Play** the working copy beside the reference copy, server and client, with a clean console:
   - **UI parity**, the same fresh player in both, at the same viewport: phone landscape (844x390) first, then portrait (390x844) if the game allows it, tablet (1024x768) and desktop (1280x720). Set it with Studio's device emulator or by resizing the Studio window (a screen too short for a size: use one of the same aspect ratio). [scripts/UIParity.luau](../scripts/UIParity.luau): `fingerprint()` gives one line per window (count and hash of its texts and images with their pixel rectangles); open each window the same way in both, `sweep(frame)` each scrolling page, and read `Detail` only where a line differs. Pass `Ignore` for decorations placed at random and `Moving` for animated ones. Then UIBounds ([ui.md](ui.md)): the same findings as the original, or fewer.
   - **Every feature with real input** (clicks, keys, walking: [coding.md](coding.md) Verify): each inventory row, UI flows, purchases with test products, teleports, tags, cutscenes and their skip; then two players, a respawn and a rejoin.
   - **Client cost** beside the original on the same screen: Lua allocation and heap ([coding.md](coding.md) Performance). The port costs no more without a reason.
4. **Data:** a legacy-format save loads with the same values: offline through the real save library over a fake DataStoreService (Lune), or in a private published test place on scratch stores. Never production stores or the owner's saves.
5. **Record** the results in `docs/migration.md` and `artifacts/verification/`, and report what you could not verify.
