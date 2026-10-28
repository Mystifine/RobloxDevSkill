# Modeling

## Budgets

- Roblox mesh limit is **20,000 triangles per mesh**. Aim well under it for most assets; top-tier hero models may reach about **18,000 triangles max**, leaving buffer. Scale detail to the item's importance and typical viewing distance, not every prop to the cap.
- Count triangles on the evaluated mesh (modifiers applied, after triangulation), per mesh object.
- Fewer materials and meshes means fewer draw calls: merge parts that share a material and never move independently.

## Quality target

Default to highly detailed, **full PBR**: color, normal, metalness and roughness maps (`SurfaceAppearance`) on clean, non-overlapping UVs with consistent texel density. Bake high-poly detail to normals. Roblox caps texture maps at 1024x1024, so bake at 1024 and spend the texel budget on what is visible. Use a different style (stylized, flat color, hand-painted) only when the user or the project says so.

## Workflow

Use Blender skills when installed: `blender-director` (plan) -> `blender-modeler` / `blender-hardsurface-modeling` / `blender-sculpting` -> `blender-retopology-uv` -> `blender-texture-baking` + `blender-pbr-materials` -> `blender-game-optimization` -> `blender-asset-qa` -> `blender-export-pipelines`. Search for further relevant skills (`find-skills`) when the asset type is unusual (creatures, vehicles, vegetation).

Rules:
- Real-world scale, applied transforms, sensible origin/pivot, clear naming.
- No hidden or interior faces that never render; no coplanar overlaps (z-fighting); consistent normals; no n-gons left unintended.
- Character models (R15/R6 rigs, NPCs) follow [rigs.md](rigs.md); any that could read as female also follow [characters.md](characters.md), renders included.
- Run `blender-asset-qa` before calling a model done. Verify triangle count, UVs, normals and materials after export.
- After import in Studio: set `CollisionFidelity` (`Box`/`Hull` for most; precise only when needed), `CanCollide/CanTouch/CanQuery` off for decor, `Anchored` as appropriate, `RenderFidelity` as fits, and confirm textures applied. Remove leftover empty Models or Folders.

## No z-fighting (flicker)

Two visible faces that look the same way, lie in the same plane and overlap flicker in game (z-fighting), and so do two decals or textures sharing a face and a ZIndex. Only exact coincidence fights: a 0.002-stud gap was clean at 1500 studs, so 0.03 is a safe separation.

- **Build so faces never coincide.** Lay plates, trims, paths and overlays at least 0.03 studs in front of what they sit on, or butt them edge to edge instead of overlapping. Never stack two plates at the same height. Delete duplicate parts. Give every decal or texture on a face its own ZIndex.
- **Check actively** whenever a model is built, generated, imported or edited, in Edit mode with [scripts/ZFight.luau](../scripts/ZFight.luau). `return select(2, ZFight.audit(model))` must report 0.
  - The report sorts pairs as `flicker` (two different surfaces: plainly visible), `shimmer` (one textured surface, tiled from two origins) and `hidden` (one smooth surface). Fix all three.
  - `ZFight.settle(model)` fixes what it finds: it grows the thinner part 0.03 studs out on the fighting side, so nothing else moves, and renumbers tied decals. Audit again afterwards. On a real 18,882-part map, the audit took 0.8 s and the settle 2 s, with no part changed by more than 0.13 studs.
  - A generated map runs settle as its builder's last step, and the fix goes back into the builder or source.
  - It analyses Parts, wedges and cylinders. MeshParts, unions and terrain are not analysed: offset those by hand and look at them in Studio.
- **Blender meshes:** `blender-asset-qa` catches coplanar overlaps inside a mesh before export.

## Report

State the final triangle count per mesh, material/texture counts and resolutions, and any simplification you made.
