# Visual style dispatcher

Use for visual decisions across models, textures, UI, icons, VFX and environments. Resolve the direction here, then load only useful recipes and the domain's implementation guide. Do not load the entire style library. There is no fixed house style; references may combine characteristics from several styles.

Before substantial asset production, briefly resolve intended use and completion scope, visual direction, movement/deformation needs, and material/budget choices. State reasonable assumptions and continue; ask only when unresolved information would materially change the result or cause substantial rework. A small edit needs only the decisions it changes.

## Resolve direction

Fill unspecified choices in this order:

1. **Request and references:** explicit instructions win where they differ from an image. Inspect supplied images and linked references; identify what each contributes. Match visible proportions, silhouette, palette, materials, shading, linework, layout and typography where relevant. A palette reference does not prescribe anatomy; a front view does not establish the back.
2. **Project:** inspect comparable assets, theme tokens and configuration in the available scope. Match the relevant family and reuse compatible work. Unrelated project assets do not override a supplied reference.
3. **Inference:** when neither gives direction, choose a coherent treatment suited to purpose, genre, viewing distance and target platform. Briefly state the assumption and proceed. Ask only when an unresolved choice would materially change the result or require substantial rework.

Report inaccessible references and use available evidence without claiming to have matched them. With one view, infer unseen construction and surfaces consistently; disclose consequential guesses. Request another view only when it is needed to resolve a material ambiguity.

Describe concrete characteristics rather than requiring a preset name: realistic proportions with painted shadows and exaggerated armor is a valid direction. Model-bound faces, emblems, textures and gear inherit the model's treatment; UI imagery follows its own component family. Coordinate the domains without assuming identical rendering techniques.

## Select techniques

**Style recipes provide techniques for achieving a selected appearance. They must not introduce characteristics absent from the user's request, references or relevant project assets.** An inferred direction may use a recipe, but do not adopt its example palette, ornaments or outlines automatically.

| Relevant characteristics | Optional recipe |
|---|---|
| Chunky toy forms, deliberate stud relief | [styles/stud.md](styles/stud.md) |
| Tapered ink contours and painted anime shading | [styles/anime-ink.md](styles/anime-ink.md) |
| Painted color/value hierarchy and detailed cartoon forms | [styles/hand-painted.md](styles/hand-painted.md) |
| Physically consistent surfaces and realistic light response | [styles/realistic.md](styles/realistic.md) |
| Faceted geometry, palette textures, deliberate simplification | [styles/low-poly.md](styles/low-poly.md) |
| Rounded, glossy simulator UI and cartoon icons | [styles/simulator-cartoon.md](styles/simulator-cartoon.md) |

These are examples, not an exhaustive taxonomy. For another style, work directly from its observed characteristics and the relevant domain guide. For a mixed direction, load only the recipes whose techniques contribute, and apply only those techniques.

Keep decisions separate:

- **Appearance:** shape, palette, shading, linework and presentation.
- **Function:** static, moves as a whole, articulated, or organically deforming; this determines rigging needs, not the art style.
- **Implementation:** native materials, painted textures or PBR; maps, resolution, topology and budgets depend on the result and platform. Stylized art can use PBR; low-poly art can too. See [modeling.md, Materials and textures](modeling.md#materials-and-textures).

## Compare the result

State the selected source and key characteristics briefly in the work brief. Compare the output with the reference's view and at the actual gameplay distance or UI size. Check silhouette/proportions, palette/value hierarchy, surface response and line weight where applicable. Fix observable mismatches rather than adding generic polish. Domain checks still apply: a good style match does not prove a usable rig or a responsive UI.
