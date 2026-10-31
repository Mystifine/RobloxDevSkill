# Environment (lighting, atmosphere, sky, post-processing, terrain)

The mood of a place: maps built per [modeling.md](modeling.md) get their look here. Match the project's existing Lighting first and change it only on purpose, since it changes every screen and screenshot.

## Lighting

- **Unified Lighting** (fully live): `Lighting.LightingStyle` (`Realistic`, or `Soft` for the classic Roblox look) with `PrioritizeLightingQuality` replaces the deprecated `Technology` property ([Lighting](https://create.roblox.com/docs/reference/engine/classes/Lighting)). Never set `Technology` in new work.
- **Time and sun:** `ClockTime` (or `TimeOfDay`) and `GeographicLatitude`; `Brightness` and `ExposureCompensation`.
- **Fill and reflections:** `Ambient` (areas the sky cannot reach) and `OutdoorAmbient`; `EnvironmentDiffuseScale` and `EnvironmentSpecularScale` (how much the sky lights and reflects on surfaces: PBR materials look flat at 0).
- **Shadows:** `GlobalShadows`, `ShadowSoftness`. Every `PointLight`, `SpotLight` or `SurfaceLight` with `Shadows` on costs on phones: keep shadow casters few and ranges short, and give decorative glows no shadows.

## Atmosphere and sky

- `Atmosphere` in Lighting: `Density` (how much haze), `Offset` (horizon against near), `Color` and `Decay` (near and far tint), `Glare`, `Haze`. A little density gives depth for almost nothing.
- `Sky` (skybox, sun and moon) and `Clouds` (parented to Terrain) set the backdrop. A custom skybox is six image uploads, so the upload gate applies ([assets.md](assets.md)); prefer an existing one.

## Post-processing

- In Lighting an effect shows for every player; in the Camera, for one (a blur behind a menu) ([post-processing](https://create.roblox.com/docs/environment/post-processing-effects)).
- `BloomEffect` (glow on bright surfaces: neon parts and particle `LightEmission` feed it), `ColorCorrectionEffect` (brightness, contrast, saturation, tint; a red tint at low health), `ColorGradingEffect` (`TonemapperPreset` `Default` or `Retro`), `DepthOfFieldEffect`, `SunRaysEffect`, `BlurEffect`.
- Keep them subtle and judge them on a phone: heavy bloom and depth of field cost fill rate and smear small detail. Studio hides some effects below the highest editor quality level.

## Terrain and materials

- Terrain for organic ground: `Terrain:FillBlock`, `FillBall`, `FillCylinder`, `FillWedge` and `ReplaceMaterial`; `ReadVoxels`/`WriteVoxels` for generated terrain (in the serial phase, never desynchronized). Water: `WaterColor`, `WaterTransparency`, `WaterWaveSize`, `WaterWaveSpeed`, `WaterReflectance`.
- Write big generated terrain in chunks and yield between them.
- Custom materials: a `MaterialVariant` under `MaterialService` overrides a base material by name place-wide or per part (`BasePart.MaterialVariant`). Its texture maps are uploads, so keep variants few and send them through the upload gate.

## Check

Look at the place in Studio's device emulator at phone size: at noon and at the darkest time it uses, from the player's camera height, with the project's reference shots beside it.
