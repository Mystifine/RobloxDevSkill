# Modeling

## Budgets

- Roblox mesh limit is **20,000 triangles per mesh**. Aim well under it for most assets; top-tier hero models may reach about **18,000 triangles max** *(default)*, leaving buffer. Scale detail to the item's importance and typical viewing distance, not every prop to the cap.
- Count triangles on the evaluated mesh (modifiers applied, after triangulation), per mesh object.
- Fewer materials and meshes means fewer draw calls: merge parts that share a material and never move independently.

## Style

*(default)* **Anime ink in full PBR**: a hand-painted look with strong brush lines, on a `SurfaceAppearance` with color, normal, metalness and roughness maps, **each 1024x1024**. The project's existing models come first (SKILL.md rule 2). A style the user names replaces it (realistic, low-poly, voxel, Roblox materials). References always set the proportions, palette and materials (Workflow, step 1), and a reference in another style, a render for instance, still shows the design: it is painted in this one.

Read from seven reference skins the user chose:
- **Painted, not rendered.** Flat, saturated local colors, one per material. Metal is paint too: gold is flat yellow with an ochre shadow, black panel lines and a few white glints. Light and shadow are in the color map, so the look holds under any lighting; metalness stays low (0 to 0.3), since a full 1 washes the paint out under a bright sky. The normal map carries the folds and line work as relief, and roughness separates cloth from metal.
- **Ink on every edge, in smooth curves.** Near-black brush lines that swell slowly and taper, on every rim, hem, seam, panel edge and border between materials: about 0.02 studs, finer on small ornaments. A line follows the form as one curve, never mesh edge by mesh edge: straight segments, fast width changes and lines thresholded from ambient occlusion all read as rough.
- **Folds are the detail.** A fold is a stroke, thick at its pinch and running out to a point, with a soft shadow on one side and a light streak on the other, over a painted shadow shape. They fan out from where cloth gathers: under a belt or hem, at a joint. Capes and coats hang in long verticals; sleeves wrinkle across. Strokes scattered at random read as scratches, and dense fans clump into marks like claw scratches, which on red cloth is also an upload risk ([no-gore.md](no-gore.md)). Start from `kit.DRAPE` or `kit.WRINKLE`, keep them off hair, small pieces and a chest, and with a clean reference place a few creases by hand (`Pieces.ink`).
- **Two or three tones** with soft painted edges: the local color, its shadow tone (same hue, darker), a highlight. Light from above and in front; ink pooled in crevices.
- **Small detail is drawn, not modeled:** muscle, stitching, belt holes, dashes along a seam. Metal stays clean: its detail is panel lines, not scratches.
- **Chunky, angular forms:** fur in spikes, hems torn, armor in faceted plates with crisp rims, cloth with real volume around the limbs. The body is wrapped: no bare rig box shows, including the end of the hand and the sole.
- **Sharpness takes texels, not a bigger number:** a map can be 1024x1024 and still look low-res if one map covers a whole character. Aim for about 100 pixels a stud on a chest: that takes a set per region (`kit.regions`, [rigs.md](rigs.md)), a set for each piece of gear, and no hollow UV islands. One atlas gave 30 to 50.

[scripts/skin_kit.py](../scripts/skin_kit.py) makes this set: `kit.paint` bakes the tones per look, inks every sharp edge, traces the folds, then bakes their relief and each look's roughness and metalness. A hand-painted color map works just as well.

**Art drawn for a model** (a face decal, an emblem, a hand-painted map) is in the same style, or it sits on the skin as a different drawing. Say so in every prompt or brief: "Anime ink: bold near-black brush outlines that swell and taper, heavy on the upper eyelid and every contour, about as thick at 128 px as a skin's ink; flat local colors with one soft shadow tone; no gradients, no thin vector lines, no airbrushing." Lines thin enough to look clean at 512 px vanish on a head a few hundred pixels tall, so judge line weight at 128 px, beside a render of the painted model.

- **Glowing details** stay separate Neon parts, in every style.
- **Realistic PBR,** when asked: the same four maps on clean UVs at consistent texel density, with high-poly detail baked to normals (`kit.bake`), and no light in the color map.
  - **ColorMap is albedo:** each material's own color, with no light or shadow painted in, except a light ambient-occlusion multiply, since `SurfaceAppearance` has no AO slot.
  - **Metalness** is 1 on bare metal only, 0 on paint, cloth, skin, gems and plastic; **roughness** varies with the material and its wear (polished edges, scratches, grime in cavities).
  - **The normal map** carries bevels, panel lines, seams and surface detail. A weak one leaves the surface looking smooth: a median tilt of 2 out of 127 on flat areas read as plastic.
- **Detailed cartoony,** when asked: stylized game art with real detail.
  - Shapes carry it: exaggerated, readable proportions (big heads, hands, claws, horns, tails, weapon heads), a clear big, medium and small shape hierarchy, and a silhouette that reads on a phone.
  - Detail is modeled, not noise: fur clumps, scale plates, armor bevels and trims, cloth folds and torn hems are shapes with bevelled edges and a few loops each.
  - The color map is hand-painted: flat base colors from a small palette (two or three main colors and one accent), a value gradient lighter toward the top, darker cavities and contact areas, light edges on convex rims, and a few strokes for fur, grain and scratches. Saturated, never photographic.
  - Materials stay simple: even roughness, metalness only on real metal, and a normal map only for chunky forms (bevels, plates, carved lines). A color map alone (`MeshPart.TextureID` or `SurfaceAppearance.ColorMap`) is often enough.
- **Low-poly** (flat-shaded facets, colors from a palette texture), when asked.
- **Roblox materials,** when asked: no textures or UVs; one piece per material, each styled by `Color` and `Material` (a skin's `looks`, [rigs.md](rigs.md)), glow as Neon.

Roblox caps texture maps at 1024x1024, and every map is made at that size by default: spend the texels on what is seen.

## Workflow

**Poly-model, don't sculpt** *(default)*. Roblox asset modelers mostly box-model in Blender. The high-poly for the bakes is that model with its bevels, subdivision and modeled detail; sculpt only organic detail the references show that box modeling cannot reach (wrinkles, muscle, fur).

1. **Reference:** the user's art or the brief's design; for a character, front and side views to model against. With one view, ask for more, or say which parts are guessed. Then, before modeling:
   - **Check the view first:** a turnaround is often turned a little, so a tail seen on one side, or one arm wider than the other, may be the model's rotation and not asymmetry. Compare the arms' widths and where the centre line sits before building either side differently.
   - **List its defining features:** the shapes someone would name it by (a crest's outline, how a helmet frames the face, the shape of a tube's segments, where the head sits against the shoulders).
   - **Measure its proportions** from the image in pixels (head to torso, widths, the head's height above the shoulders) and build to those numbers, not by eye.
   - **Write down its palette and materials:** colors from the lit sides of its forms (a pale color sampled from a render washes out under a bright Roblox sky: push it warmer and more saturated, and judge it in the place), and which parts are bare metal, paint, cloth, skin, gems or glow, and how worn. Match its drawing (ink outlines, hatching, cel shading) only in a style the user asked for: then note line weight, stroke density and value contrast, and texture to those.
2. **Blockout:** each part is one continuous mesh shaped from a cube or cylinder (extrude, loop cuts, inset, bevel, proportional editing), mirrored where it is symmetric. Separate pieces only where the object really has them (armor plates, belts, horns, hair locks, weapons), and shape those too. Never assemble a body from untouched primitives, a cylinder per limb and a box for the torso: three monsters built that way read as crude.
3. **Clay check:** gray renders beside the reference (`python scripts/ref_sheet.py OUT.png REFERENCE RENDER ...` scales each to one height), with the triangle count. Fix shapes here, before UVs and textures; a Codex build stops here for review ([codex-handoff.md](codex-handoff.md), 4).
   - Render the reference's own view (its camera angle and lens) as well as the front and side, both scaled to the same height, side by side.
   - Go through the feature list and the measured proportions one at a time. Texturing waits until each one matches.
   - A glance at thumbnails is not a check: one passed a slanted crest built as a rounded column, with the head a stud too high.
4. **UVs:** few islands, seams where they hide, islands straightened where strokes run; one texture set per model where it fits.
5. **Texture:** the default paints each look, inks its edges and folds, and exports the four maps (Style, above). Realistic PBR instead bakes normal, ambient occlusion and curvature (the edge mask) from the high-poly, builds each material's albedo, metalness and roughness on them (edge wear on curvature, grime in the AO), multiplies a little AO into the albedo, and exports the four maps.
6. **Finish:** optimize, QA and export.

**Running Blender:** `python scripts/find_blender.py` prints a Blender to run, from the PATH, a running copy or the usual install folders. Builds run headless: `blender -b --factory-startup -P build.py -- args`. Close stdin when calling a CLI from a script. To work in an open Blender with no Blender tool loaded, its MCP add-on answers on 127.0.0.1:9876: send one JSON message `{"type": "execute_code", "params": {"code": "<python>"}}` over a socket, and build in a scene of your own, never clearing the user's. Objects in a scene that isn't active keep a stale `matrix_world`, so use `location` there.

Blender skills when installed: `blender-director` (plan) -> `blender-modeler` / `blender-hardsurface-modeling` -> `blender-retopology-uv` (UVs) -> `hand-painted-style`, `anime-style` and `blender-pbr-materials` (realistic: `blender-texture-baking`) -> `blender-game-optimization` -> `blender-asset-qa` -> `blender-export-pipelines`. Organic detail adds `blender-sculpting`. Search for further skills (`find-skills`) when the asset type is unusual (creatures, vehicles, vegetation).

Rules:
- **Every MeshPart has `DoubleSided = true`, always.** Set it when the mesh enters the place; `RigSkin` does on what it touches and `RigSkin.audit` reports any it finds off.
- Crisp rims: mark edges past about 40 degrees sharp (`kit.sharpen`). Smooth shading across a plate's rim makes the whole plate look inflated.
- Real-world scale, applied transforms, sensible origin/pivot, clear naming.
- No hidden or interior faces that never render (a side a joint can swing into view does render: [rigs.md](rigs.md), Skins); no coplanar overlaps (z-fighting); consistent normals; no n-gons left unintended.
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
- **ZFight reads Parts, not MeshParts or unions,** and its report counts those it skipped, so its 0 says nothing about a skin or other mesh. For meshes, in Blender: blender-asset-qa compares separate pieces, and `rr.folds(objects)` must return `{}`. It measures a mesh overlapping itself where it can be seen (0.002 studs² or more), which QA skips (it ignores triangles that share a vertex), and both exports refuse one. A buckle's crossing outline folded its cap into a filled hollow that flickered, with QA and ZFight at 0; `kit.prism` now refuses such an outline.
  - A generated map runs settle as its builder's last step, and the fix goes back into the builder or source.
  - It analyses Parts, wedges and cylinders. MeshParts, unions and terrain are not analysed: offset those by hand and look at them in Studio.
- **Blender meshes:** `blender-asset-qa` catches coplanar overlaps inside a mesh before export.

## Report

State the final triangle count per mesh, material/texture counts and resolutions, and any simplification you made.
