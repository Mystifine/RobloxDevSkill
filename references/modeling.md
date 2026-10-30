# Modeling

## Budgets

- Roblox mesh limit is **20,000 triangles per mesh**. Aim well under it for most assets; top-tier hero models may reach about **18,000 triangles max** *(default)*, leaving buffer. Scale detail to the item's importance and typical viewing distance, not every prop to the cap.
- Count triangles on the evaluated mesh (modifiers applied, after triangulation), per mesh object.
- Fewer materials and meshes means fewer draw calls: merge parts that share a material and never move independently.

## Style

*(default)* **Detailed cartoony**: stylized game art with real detail. The project's existing models come first (SKILL.md rule 2), and a style the user names replaces this one (realistic, low-poly, voxel, anime).

- **Shapes carry it:** exaggerated, readable proportions (big heads, hands, claws, horns, tails, weapon heads), a clear big, medium and small shape hierarchy, and a silhouette that reads on a phone.
- **Detail is modeled, not noise:** fur clumps, scale plates, armor bevels and trims, cloth folds and torn hems are shapes with bevelled edges and a few loops each.
- **The color map is hand-painted:** flat base colors from a small palette (two or three main colors and one accent), a value gradient lighter toward the top, darker cavities and contact areas, light edges on convex rims, and a few strokes for fur, grain and scratches. Saturated, never photographic.
- **Materials stay simple:** even roughness, metalness only on real metal, and a normal map only for chunky forms (bevels, plates, carved lines). A color map alone (`MeshPart.TextureID` or `SurfaceAppearance.ColorMap`) is often enough.
- **Low-poly** (flat-shaded facets, colors from a palette texture) is a variant for when it is asked for.
- **Realistic,** when asked: full PBR (color, normal, metalness and roughness maps in a `SurfaceAppearance`) on clean UVs at consistent texel density, with high-poly detail baked to normals.

Roblox caps texture maps at 1024x1024: paint or bake at 1024 (512 for small props) and spend the texels on what is seen.

## Workflow

**Poly-model, don't sculpt** *(default)*. Roblox asset modelers mostly box-model in Blender, then paint the texture or color it from a palette; sculpting and high-to-low bakes are for a sculpted or realistic look the user asks for.

1. **Reference:** the user's art or the brief's design; for a character, front and side views to model against. With one view, ask for more, or say which parts are guessed. Then, before modeling:
   - **List its defining features:** the shapes someone would name it by (a crest's outline, how a helmet frames the face, the shape of a tube's segments, where the head sits against the shoulders).
   - **Measure its proportions** from the image in pixels (head to torso, widths, the head's height above the shoulders) and build to those numbers, not by eye.
   - **Write down its look when it has one of its own** (ink outlines, hatching, cel shading, a palette): line weight, stroke density, value contrast and colors. Texture to that, not to the default style.
2. **Blockout:** each part is one continuous mesh shaped from a cube or cylinder (extrude, loop cuts, inset, bevel, proportional editing), mirrored where it is symmetric. Separate pieces only where the object really has them (armor plates, belts, horns, hair locks, weapons), and shape those too. Never assemble a body from untouched primitives, a cylinder per limb and a box for the torso: three monsters built that way read as crude (seen 2026-10-29).
3. **Clay check:** gray renders beside the reference, with the triangle count. Fix shapes here, before UVs and textures; a Codex build stops here for review ([codex-handoff.md](codex-handoff.md), 4).
   - Render the reference's own view (its camera angle and lens) as well as the front and side, both scaled to the same height, side by side.
   - Go through the feature list and the measured proportions one at a time. Texturing waits until each one matches.
   - A glance at thumbnails is not a check: one passed a slanted crest built as a rounded column, with the head a stud too high (2026-10-29).
4. **UVs:** few islands, seams where they hide, islands straightened where strokes run; one texture set per model where it fits.
5. **Texture:** bake ambient occlusion and an edge mask from the mesh, and combine them with the base colors, the gradient and painted strokes into the color map. Roughness and metalness are flat values or simple masks.
6. **Finish:** optimize, QA and export.

Blender skills when installed: `blender-director` (plan) -> `blender-modeler` / `blender-hardsurface-modeling` -> `blender-retopology-uv` (UVs) -> `blender-texture-baking` with `hand-painted-style`, `stylized-style` or `lowpoly-style` -> `blender-game-optimization` -> `blender-asset-qa` -> `blender-export-pipelines`. The realistic look adds `blender-sculpting` and `blender-pbr-materials`. Search for further skills (`find-skills`) when the asset type is unusual (creatures, vehicles, vegetation).

Rules:
- Real-world scale, applied transforms, sensible origin/pivot, clear naming.
- No hidden or interior faces that never render; no coplanar overlaps (z-fighting); consistent normals; no n-gons left unintended.
- Character models (R15/R6 rigs, NPCs) follow [rigs.md](rigs.md), where a custom character is a skin on a standard rig; any that could read as female also follow [characters.md](characters.md), renders included.
- Every model, texture and decal you make is an upload: no blood or gore in it, and weapons, claws and tools carry no blood, though wear, rust and grime are fine ([no-gore.md](no-gore.md)).
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
