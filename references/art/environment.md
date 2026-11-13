# Environment (lighting, atmosphere, sky, post-processing, terrain)

The mood of a place: maps built per [modeling.md](modeling.md) get their look here. Resolve the requested atmosphere and surface treatment through [visual-style.md](visual-style.md). Preserve compatible project Lighting and change it only on purpose, since it changes every screen and screenshot; an isolated asset request does not imply restyling the whole place.

## Lighting

- **Unified Lighting** (fully live): `Lighting.LightingStyle` (`Realistic`, or `Soft` for the classic Roblox look) with `PrioritizeLightingQuality` replaces the deprecated `Technology` property ([Lighting](https://create.roblox.com/docs/reference/engine/classes/Lighting)). Never set `Technology` in new work.
- **Time and sun:** `ClockTime` (or `TimeOfDay`) and `GeographicLatitude`; `Brightness` and `ExposureCompensation`.
- **Fill and reflections:** `Ambient` (areas the sky cannot reach) and `OutdoorAmbient`; `EnvironmentDiffuseScale` and `EnvironmentSpecularScale` (how much the sky lights and reflects on surfaces: PBR materials look flat at 0).
- **Shadows:** `GlobalShadows`, `ShadowSoftness`. Every `PointLight`, `SpotLight` or `SurfaceLight` with `Shadows` on costs on phones: keep shadow casters few and ranges short, and give decorative glows no shadows.
- **A roofed set:** with the sun blocked and Bloom on, `PointLight`s at brightness 2.2 to 5 blew pale bodies to white, and 0.5 to 1 read correctly. Scaled up, `Wood`'s grain became stripes across a mesh, where `SmoothPlastic` read as a clean dark silhouette.
- **A glint across flat SmoothPlastic under a low sun** (about 17° up): a `SurfaceAppearance` with a white `RoughnessMap` (fully rough) removed it, where `EnvironmentSpecularScale` 0, SunRays off and a SurfaceAppearance with no roughness map left it.

- **Judge every colour under the lighting the running game applies,** not Edit's: read any script that changes Lighting at start (an exposure lift, a saturation grade, a bloom threshold) first. Under +0.8 exposure, sunlit Plastic showed about 1.8 times its colour (wood 120,80,50 read salmon, a violet roof lilac) and Neon about four times, so its channels clipped and hues moved (orange 255,120,30 showed yellow until its green fell near 70; violet 150,60,240 showed pink until its red was under 100).
- **Preview that runtime look in Edit to iterate:** apply the game's start-up deltas, capture, then restore them, never saving the place while they are on; it matched Play but for a stronger bloom on Neon, so confirm once in Play.
- **Keep a building's PointLights small under a lift:** a portal light of range 16 and brightness 1.4 with a sign light of range 18 turned a slate front lilac and bleached its banners; range 10 at 0.8, the sign light gone, kept the wall's colour.

## Atmosphere and sky

- `Atmosphere` in Lighting: `Density` (how much haze), `Offset` (horizon against near), `Color` and `Decay` (near and far tint), `Glare`, `Haze`. A little density gives depth for almost nothing.
- `Sky` (skybox, sun and moon) and `Clouds` (parented to Terrain) set the backdrop. A custom skybox is six image uploads, so the upload gate applies ([assets.md](../safety/assets.md)); prefer an existing one.
- **Rendering a custom skybox:** `SkyboxFt` shows the -Z view, `SkyboxBk` +Z, `SkyboxLf` +X and `SkyboxRt` -X (checked against the engine's sun disc; the first guess had Lf and Rt swapped). The Up and Dn faces' rotation is unknown, so paint the panorama the same in every direction beyond about 30° above and below the horizon: it showed no seam.
- **Keep Atmosphere thin over a skybox painted below the horizon:** `Density` 0.1 with `Haze` 0.6 replaced a painted cloud sea with a flat fill; `Density` 0.03 with `Haze` 0 showed it.

## Post-processing

- In Lighting an effect shows for every player; in the Camera, for one (a blur behind a menu) ([post-processing](https://create.roblox.com/docs/environment/post-processing-effects)).
- `BloomEffect` (glow on bright surfaces: neon parts and particle `LightEmission` feed it), `ColorCorrectionEffect` (brightness, contrast, saturation, tint; a red tint at low health), `ColorGradingEffect` (`TonemapperPreset` `Default` or `Retro`), `DepthOfFieldEffect`, `SunRaysEffect`, `BlurEffect`.
- **A grade cannot add a hue the picture lacks:** `TintColor` multiplies each channel, so gold or red over a blue or teal sky gave navy, teal or olive at every strength tried. Drain first: `Saturation` -0.4 to -0.7, a little `Brightness`, then the tint, turned the same sky gold. Too much drain turned fire cream, so shots with fire drain less.
- Keep them subtle and judge them on a phone: heavy bloom and depth of field cost fill rate and smear small detail. Studio hides some effects below the highest editor quality level.

## Terrain and materials

- Terrain for organic ground: `Terrain:FillBlock`, `FillBall`, `FillCylinder`, `FillWedge` and `ReplaceMaterial`; `ReadVoxels`/`WriteVoxels` for generated terrain (in the serial phase, never desynchronized). Water: `WaterColor`, `WaterTransparency`, `WaterWaveSize`, `WaterWaveSpeed`, `WaterReflectance`.
- Write big generated terrain in chunks and yield between them.
- Custom materials: a `MaterialVariant` under `MaterialService` overrides a base material by name place-wide or per part (`BasePart.MaterialVariant`). Its texture maps are uploads, so keep variants few and send them through the upload gate.

## Check

Look at the place in Studio's device emulator at phone size: at noon and at the darkest time it uses, from the player's camera height, with the project's reference shots beside it.
