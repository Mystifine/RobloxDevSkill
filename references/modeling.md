# Modeling

## Budgets

- Roblox mesh limit is **20,000 triangles per mesh**. Aim well under it for most assets; top-tier hero models may reach about **18,000 triangles max** *(default)*, leaving buffer. Scale detail to the item's importance and typical viewing distance, not every prop to the cap.
- **Weapons always sit at the top of that range: about 18,000 triangles, and high quality** *(default)*. Anything a character wields (swords, axes, spears, staffs, bows, guns), however small or common, is seen up close in the hand, so the scaling above does not lower it. The count is the whole weapon's, on its evaluated mesh.
  - **Check it:** `kit.weapon_budget(pieces)` must return `{}` at the clay stage and before export: 17,000 to 19,000 triangles with modifiers applied, and no mesh over the limit. In Studio, `RigSkin.audit` warns (`budget`) on a held weapon outside that band, wherever it came from.
  - **Spend it on form you can see:** a bevel on every hard edge, curves with no visible facets, a blade's real grind and fuller, a grip's wraps, the shaping of a guard and pommel, rivets, engraving and panel lines, a gun's machined parts. Never reach the count by subdividing flat faces or with hidden or interior geometry. If the detail runs out first, the design needs more detail.
  - **High quality means it holds up filling the screen:** crisp shading, its own materials and map, and every rule below (folds, z-fighting, normals, UVs). Review it close up and in the hand, not only at gameplay distance.
  - Optimization never takes a weapon under the band. A weapon that already exists (the project's, or from the Toolbox) keeps its mesh: state its count rather than calling it on budget. An explicit request for something else, such as a deliberately low-poly look, wins.
- Count triangles on the evaluated mesh (modifiers applied, after triangulation), per mesh object.
- Fewer materials and meshes means fewer draw calls: merge parts that share a material and never move independently.

## Style

Resolve appearance through [visual-style.md](visual-style.md). Load only relevant recipes from its table; there is no default stud, anime, cartoon or realistic treatment. Model-bound faces, decals, emblems and gear inherit the model's selected appearance.

## Materials and textures

Choose the material workflow separately from the art style and rigging. Follow explicit user requirements; otherwise use the approach that achieves the intended look under project lighting at gameplay distance.

| Intended surface treatment | Starting approach |
|---|---|
| Simple flat-color or blocky surfaces | Native colors/materials or a palette texture |
| Painted cartoon or retro surfaces | Painted color texture; additional maps where useful |
| Detailed stylized surfaces | PBR where relief or material separation improves the result |
| Realistic surfaces | PBR with physically consistent material values |

- **No universal full-PBR requirement.** Generate and apply maps that contribute to the result. A normal map provides relief; roughness/metalness control surface response; emission supports glowing regions. Do not manufacture detail or upload unused maps merely to complete a set. A helper producing four maps does not make all four mandatory.
- **No fixed resolution or atlas count.** Choose map sizes and visible texel density from projected screen coverage, viewing distance, repetition, target devices and the project's budgets. Use shared atlases where compatible; split a region only when needed for clarity or independent movement/materials. Check current [texture specifications](https://create.roblox.com/docs/art/modeling/texture-specifications) and asset-specific limits instead of treating 1024 as a universal cap or default. Adjust helper `size` parameters accordingly.
- **PBR does not imply realism.** Painted color and stylized roughness/relief are valid when the reference calls for them. For realistic albedo, avoid baked directional light; see the selected recipe for how painted shading is handled.
- **Glow:** choose separate Neon geometry, supported SurfaceAppearance emissive maps, or effect components according to the design, target workflow and needed control. Do not require extra Neon meshes for every glowing mark. Check current [PBR map support](https://create.roblox.com/docs/art/modeling/surface-appearance) when exporting; older helpers may export only color/normal/metal/rough.
- **Verify the surface:** check UVs and assigned maps after export/import, then inspect under neutral and project lighting. A map's presence or resolution alone does not establish correct color, relief or readability. Native-material assets need no UVs unless another chosen feature uses textures.

## Workflow

Choose modeling techniques for the selected forms and deformation needs. Poly-model structured shapes; sculpt organic detail when useful, then retopologize for the target budget and movement. A high-poly bake source can combine modeled bevels and sculpted detail. Do not impose a construction method as an art style.

1. **Resolve the brief before detailed modeling:** intended use and completion scope, visual direction, movement/deformation, material approach and budget. Gameplay characters, creatures, mobs and bosses include a working rig by default unless explicitly static or a modeling-only stage; follow [rigs.md](rigs.md), including its custom-creature route, before deciding topology and piece boundaries. Static props and whole-object movement need no skeleton; mechanical articulation may need joints without organic skinning. Inspect the selected references; infer unseen sides consistently and disclose consequential guesses. Ask for more views only when a material ambiguity remains. Then:
   - **Check the view first:** a turnaround is often turned a little, so a tail seen on one side, or one arm wider than the other, may be the model's rotation and not asymmetry. Compare the arms' widths and where the centre line sits before building either side differently.
   - **List its defining features:** the shapes someone would name it by (a crest's outline, how a helmet frames the face, the shape of a tube's segments, where the head sits against the shoulders).
   - **Measure its proportions** from the image in pixels (head to torso, widths, the head's height above the shoulders) and build to those numbers, not by eye.
   - **Write down its palette and materials:** distinguish material colors from lighting highlights in a rendered reference, and identify bare metal, paint, cloth, skin, gems or glow and their wear. Compare under project lighting before compensating for a washed-out result; do not automatically warm or saturate every palette. Match the selected source's line weight, stroke density, shading and value contrast.
2. **Blockout:** establish the silhouette and proportion hierarchy using shaped volumes, mirrored where symmetric. Plan joint pivots, bend topology and rigid attachments now for articulated assets. Separate pieces where construction, materials or movement justify them (armor, belts, horns, hair, weapons). Primitive shapes are a starting point; leave them unchanged only when the chosen design calls for that simplicity.
3. **Clay check:** gray renders beside the reference (`python scripts/ref_sheet.py OUT.png REFERENCE RENDER ...` scales each to one height), with the triangle count. Fix shapes here, before UVs and textures; a Codex build stops here for review ([codex-handoff.md](codex-handoff.md), 4).
   - Render the reference's own view (its camera angle and lens) as well as the front and side, both scaled to the same height, side by side.
   - Go through the feature list and the measured proportions one at a time. Texturing waits until each one matches.
   - A glance at thumbnails is not a check: one passed a slanted crest built as a rounded column, with the head a stud too high.
4. **Prepare deformation and UVs:** for rigged assets, bind/weight the model and check representative poses before expensive final bakes. For textured surfaces, place seams where they hide and straighten islands where strokes run; choose atlas layout and density through Materials and textures. Skip UV work for surfaces using only native colors/materials.
5. **Texture:** use the selected techniques and contributing maps, following Materials and textures and any applicable style recipe. Bake high-poly relief where useful; do not add wear, ink, studs or photographic detail absent from the selected direction.
6. **Finish:** optimize, QA and export. Verify rigged assets with representative motion after import into Studio ([rigs.md](rigs.md)); a rest-pose mesh inspection does not satisfy the rig requirement. Rig-only delivery needs no full animation set or AI.

**Running Blender:** `python scripts/find_blender.py` prints a Blender to run, from the PATH, a running copy or the usual install folders. Builds run headless: `blender -b --factory-startup -P build.py -- args`. Close stdin when calling a CLI from a script. To work in an open Blender with no Blender tool loaded, its MCP add-on answers on 127.0.0.1:9876: send one JSON message `{"type": "execute_code", "params": {"code": "<python>"}}` over a socket, and build in a scene of your own, never clearing the user's. Objects in a scene that isn't active keep a stale `matrix_world`, so use `location` there.

Blender skills when installed: `blender-director` (plan) -> `blender-modeler` / `blender-hardsurface-modeling` -> `blender-retopology-uv` (UVs) -> the selected look's skills (`blender-pbr-materials`; anime ink adds `hand-painted-style` / `anime-style`, realistic bakes add `blender-texture-baking`) -> `blender-game-optimization` -> `blender-asset-qa` -> `blender-export-pipelines`. Rigged assets add `blender-character-rigging` before final bakes and `blender-animation` for diagnostic motion or requested clips. Organic detail adds `blender-sculpting`. Search (`find-skills`) for unusual assets such as creatures, vehicles or vegetation.

Rules:
- **Every MeshPart has `DoubleSided = true`, always.** Set it when the mesh enters the place; `RigSkin` does on what it touches and `RigSkin.audit` reports any it finds off.
- Match shading to the chosen forms. For crisp plates, marking edges past about 40 degrees sharp (`kit.sharpen`) can avoid inflated-looking rims; do not apply that threshold to every organic or deliberately faceted asset.
- Real-world scale, applied transforms, sensible origin/pivot, clear naming.
- No hidden or interior faces that never render (a side a joint can swing into view does render: [rigs.md](rigs.md), Skins); no coplanar overlaps (z-fighting); consistent normals; no n-gons left unintended.
- Gameplay actors follow [rigs.md](rigs.md): compatible R15/R6 characters can use standard skins; custom anatomy uses its own skeleton. Character art also follows [characters.md](characters.md), renders included.
- Every model, texture and decal you make is an upload: no blood or gore in it, and weapons, claws and tools carry no blood, though wear, rust and grime are fine ([no-gore.md](no-gore.md)).
- Run `blender-asset-qa` before calling a model done. Verify triangle count, UVs, normals and materials after export.
- After import in Studio: set `CollisionFidelity` (`Box`/`Hull` for most; precise only when needed), `CanCollide/CanTouch/CanQuery` off for decor, `Anchored` as appropriate, `RenderFidelity` as fits, and confirm textures applied. Remove leftover empty Models or Folders.

## No z-fighting (flicker)

Two visible faces that look the same way, lie in the same plane and overlap flicker in game (z-fighting), and so do two decals or textures sharing a face and a ZIndex. Only exact coincidence fights: a 0.002-stud gap was clean at 1500 studs, so 0.03 is a safe separation.

- **Build so faces never coincide.** Lay plates, trims, paths and overlays at least 0.03 studs in front of what they sit on, or butt them edge to edge instead of overlapping. Never stack two plates at the same height. Delete duplicate parts. Give every decal or texture on a face its own ZIndex.
- **Check actively** whenever a model is built, generated, imported or edited, in Edit mode with [scripts/ZFight.luau](../scripts/ZFight.luau). `return select(2, ZFight.audit(model))` must report 0.
  - The report sorts pairs as `flicker` (two different surfaces: plainly visible), `shimmer` (one textured surface, tiled from two origins) and `hidden` (one smooth surface). Fix all three.
  - `ZFight.settle(model)` fixes what it finds: it grows the thinner part 0.03 studs out on the fighting side, so nothing else moves, and renumbers tied decals. Audit again afterwards. On a real 18,882-part map, the audit took 0.8 s and the settle 2 s, with no part changed by more than 0.13 studs.
- **ZFight reads Parts, not MeshParts or unions,** and its report counts those it skipped, so its 0 says nothing about a skin or other mesh. For meshes, in Blender: blender-asset-qa compares separate pieces, and `rr.folds(objects)` must return `{}`. It measures a mesh overlapping itself where it can be seen (0.002 studs² or more), which QA skips (it ignores triangles that share a vertex), and both exports refuse one. A buckle's crossing outline folded its cap into a filled hollow that flickered, with QA and ZFight at 0; `kit.prism` now refuses such an outline.
  - A generated map runs settle as its builder's last step, and the fix goes back into the builder or source.
  - It analyses Parts, wedges and cylinders. MeshParts, unions and terrain are not analysed: offset those by hand and look at them in Studio.
- **Blender meshes:** `blender-asset-qa` catches coplanar overlaps inside a mesh before export.

## Report

State the selected visual direction, final triangle count per mesh, material/texture counts and resolutions, and any simplification or consequential reference inference. For actors, state the rig type, deformation/motion checks and Studio verification result. Distinguish static, rigged, animated and gameplay-integrated delivery; disclose missing verification rather than claiming an animation-ready result from properties alone.
