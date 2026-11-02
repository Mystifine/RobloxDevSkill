# Low-poly and palette-driven art

Use only when the [visual-style dispatcher](../visual-style.md) selects deliberate geometric simplification. A low triangle budget alone does not require flat shading, pixel textures or a retro effect.

- Spend geometry on the silhouette and defining changes of plane. Preserve intentional facets; smooth or mark sharp edges according to the reference rather than applying one angle threshold everywhere.
- A palette texture or native colors/materials can supply clean color blocks. Place UVs safely within swatches to avoid filtering into adjacent colors; test at game distance and through mip levels.
- Choose texture filtering, resolution and dithering from the intended treatment. Low-poly does not automatically mean pixel art or PS1 distortion.
- Low-poly assets may use painted textures or PBR when that achieves the selected surface response. Remove detail that vanishes at the intended distance before increasing texture or geometry budgets.
- If the asset deforms, retain enough joint topology for its pose range. Deliberate angular art still needs a functional rig when it is a gameplay actor.

Materials: [modeling.md](../modeling.md#materials-and-textures). Rigging: [rigs.md](../../rigs/rigs.md).
