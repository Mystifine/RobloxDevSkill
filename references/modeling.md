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
- Characters that could read as female follow [characters.md](characters.md), renders included.
- Run `blender-asset-qa` before calling a model done. Verify triangle count, UVs, normals and materials after export.
- After import in Studio: set `CollisionFidelity` (`Box`/`Hull` for most; precise only when needed), `CanCollide/CanTouch/CanQuery` off for decor, `Anchored` as appropriate, `RenderFidelity` as fits, and confirm textures applied. Remove leftover empty Models or Folders.

## Report

State the final triangle count per mesh, material/texture counts and resolutions, and any simplification you made.
