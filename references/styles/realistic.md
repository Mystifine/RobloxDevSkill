# Realistic surfaces

Use when the [visual-style dispatcher](../visual-style.md) calls for physically consistent surface response. PBR can also support other styles; it is not a realism switch.

- **ColorMap is albedo:** the material's own color, without painted directional light, glints or cast shadows. Roblox's SurfaceAppearance has no dedicated AO slot; if AO is multiplied into albedo, keep it restrained and check that it does not double-darken cavities.
- **Metalness:** bare metal is metallic; paint, cloth, skin, gems and plastic are dielectric. Layered, worn or mixed surfaces can vary across the map. Do not make painted metal metallic just because metal lies underneath it.
- **Roughness:** distinguish materials and meaningful wear. Curvature can guide polished edges and AO can guide cavity grime, but do not apply generic wear that the reference does not show.
- **Normals:** bake bevels, panel lines, seams and surface relief from a high-poly source when useful. Judge strength under neutral and project lighting; a technically present but imperceptible map does not establish the intended form. Normals cannot repair a missing silhouette.
- Use clean UVs at consistent visible texel density. `kit.bake` in `scripts/skin_kit.py` can produce the color/normal/metal/rough set; a separate high-to-low bake can transfer detailed sculpted geometry. Use only maps that contribute and select resolution for the asset's screen coverage.

See [modeling.md](../modeling.md#materials-and-textures) for adaptive map selection and supported texture requirements.
