# Hand-painted and detailed cartoon art

Apply only characteristics selected by the [visual-style dispatcher](../visual-style.md).

- Establish a clear large, medium and small shape hierarchy and a silhouette readable at gameplay distance. Exaggerate heads, hands, claws, horns, tails or weapon heads only to match the chosen direction.
- Model forms that establish volume: fur clumps, scale plates, armor bevels and trims, cloth folds or torn hems. Use texture detail for smaller marks; procedural noise is not a substitute for designed forms.
- A limited palette, lighter upper surfaces, dark cavities/contact areas, light convex edges and a few directed strokes can give readable painted shading. Match the reference's saturation, gradient strength and brushwork rather than requiring all of them.
- Keep roughness broad and coherent where the surface should read simply; vary it where material separation matters. Normals can reinforce bevels, carved lines or plates. A painted color map alone may be sufficient; detailed stylized assets can benefit from PBR.
- Painted lighting is an intentional artistic choice here. Compare under project lighting so baked shadows and engine shading do not muddy the result. Avoid injecting painted shadows into a treatment that calls for clean albedo.

For tapered anime contours, also consult [anime-ink.md](anime-ink.md) when relevant. Choose maps and resolution through [modeling.md](../modeling.md#materials-and-textures).
