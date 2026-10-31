# UI

Everything here applies to **ScreenGui, BillboardGui and SurfaceGui** alike; the world-space specifics are under World-space GUIs.

## Match first

Apply [SKILL.md's visual style precedence](../SKILL.md#visual-style-precedence). Inspect reference layouts and comparable project UI, controllers, theme tokens (colors, fonts, corners, strokes, spacing, tweens) and image tables. Reuse components compatible with the chosen design.

Before building UI, check installed plugins' asset libraries for reusable imagery, including background textures ([assets.md, Plugin asset libraries](assets.md#plugin-asset-libraries)).

## Style

**Simulator cartoon fallback.** The reference HUD (`StarterGui.SimulatorReferenceHUD`, `SimulatorReferenceTopbar` and `SimulatorReferenceStatus`, when available) uses:

- Rounded, saturated plates with dark plum outlines (`#301C30`), soft vertical gradients and diagonal shine stripes contained by the rounded face.
- Bold rounded lettering, such as FredokaOne: white or pale text with a strong dark outline. Keep captions, values and newly needed labels as editable native text, rather than baking them into button images; choose wording for the requested feature.
- Large, glossy cartoon icons, distinct functional colors, compact status cards and a restrained rainbow progression strip. Notification badges may overlap their own card; independent components still need clearance (below).

## Mobile first

Roblox is a phone platform: **design, build and verify for the phone first**, then scale up to tablet and desktop, unless the user says otherwise. The smallest case is the case.

- Start from the phone's landscape size (about 844 x 390) and its safe area; add layout for larger screens with constraints, not the reverse. Reserve the thumbstick and jump/action zones; never put a control under them.
- Touch first: every button at least 44 px in both directions (after the device scale), no hover-only information, no tiny close buttons, text no smaller than about 11 px a line after scaling (`TextScaled` text wraps by itself when its box is tall enough, so `TextBounds.Y` can hold two lines).
- Verify at phone, then tablet, then desktop; with the Studio device emulator on, mouse input becomes touch. A layout that only works on desktop is unfinished.
- Unless the project says portrait is unsupported, check both orientations; if it is unsupported, say so and do not add portrait layouts.

## Stay in bounds

Nothing leaks out of its box unless the design says so. **A border stroke's band sits where its settings put it** ([UIStroke](https://create.roblox.com/docs/reference/engine/classes/UIStroke)):
- `BorderStrokePosition.Outer` (the default) draws it entirely outside the frame, so an element's outline adds its thickness on every side: a bar 1 px inside a rim still touches the rim once its own outline is counted. `Center` puts half outside, `Inner` none (the band then eats into the content area). `BorderOffset` moves it on (a scale of the frame's shorter side plus pixels).
- `StrokeSizingMode.ScaledSize` makes `Thickness` a share of the frame's shorter side (0.1 on a 200 x 300 frame is 20 px), so the outline grows with the device scale; `FixedSize` keeps pixels.
- An object may carry several border strokes (give each its own `ZIndex`); the widest sets the reach. On text objects only `ApplyStrokeMode.Border` outlines the box; the default `Contextual` outlines the glyphs.
- A `UIScale` scales the strokes, `BorderOffset` pixels and `UICorner` radii under it along with the elements.

- Children stay inside the parent with their outlines, keep **at least 2 px clear** of any border, rim or outline band, and stay clear of **rounded corners** (a child near a corner of a `UICorner` parent can poke out of the arc).
- Size content from the container's inner edge (rim inset plus stroke thickness), with a margin, not from its outer edge.
- Children of a `UIListLayout` or `UIGridLayout` box sit flush with its edge, so their outer outlines poke past it: draw those strokes `Inner`, or pad the box by the stroke.
- A fill inside a rounded track is never narrower than its two rounded ends (`UDim2.new(share, 2 * radius * (1 - share), 1, 0)`), or its corners poke out of the track's.
- A deliberate overlap (a badge breaking a card's corner, a glow, a shine sweep, a sunburst its parent clips) is marked with the boolean attribute `AllowBleed` and a comment that says why.
- **Separate components stay separate.** Independent buttons, cards, panels and HUD groups must not intersect, clip, or cover each other's text, icons or outlines unless the user or design explicitly specifies that overlap. Measure their visible footprints, including outer strokes and decorations, and keep at least 4 px of visible clearance by default. This applies across different containers and ScreenGuis, not just siblings. A badge's intentional overlap with its own card does not permit that card to collide with another component; `AllowBleed` is not a waiver for unrelated collisions.
- Check with [scripts/UIBounds.luau](../scripts/UIBounds.luau) on the mounted UI at the phone size first: `UIBounds.audit(frame)` reports `outside-parent`, `on-border`, `corner` and `outside-root` with pixel amounts. Fix the layout, not the audit.

## Layout rules

- **Center anchor** *(default)*. Set `AnchorPoint = (0.5, 0.5)` and position by the element's center, so tweens of `Size`, `Rotation` and `Position` (pop-ins, scale-ups, shakes) grow from the middle. Use another anchor only when asked or when an edge must stay pinned (for example a bar that fills from the left).
- Scale-based `Size`/`Position` with `UIAspectRatioConstraint`, `UISizeConstraint`, `UITextSizeConstraint` and `UIScale` for device scaling. Lay out with `UIListLayout`/`UIGridLayout`/`UIPadding` rather than hand-placed offsets.
- `ScreenGui`: `ZIndexBehavior = Sibling`, and the safe area chosen per ScreenGui with `ScreenInsets`: `CoreUISafeInsets` keeps buttons and text clear of notches, rounded corners and Roblox's own top-bar buttons; `DeviceSafeInsets` clears only the device's cutouts; `TopbarSafeInsets` lays UI into the top bar beside Roblox's buttons; `None` is the whole screen (like `IgnoreGuiInset = true`) for full-bleed backgrounds and overlays. `ClipToDeviceSafeArea` and `SafeAreaCompatibility` decide what happens at the cut edges. Never put a control in a `None` ScreenGui on a phone. Where a project's windows already live in one, they stay (the project wins), and each window keeps clear of the top bar itself: it fits and centres in the screen below `GuiService:GetGuiInset()`. `ResetOnSpawn` is covered under State.

## Topbar controls

- A button or frame intended for the topbar belongs **inside the available topbar rectangle**, not at a percentage of the full-screen HUD height. Prefer a separate `ScreenGui` with `ScreenInsets = TopbarSafeInsets`, `ResetOnSpawn = false` and `SafeAreaCompatibility = None`. Its origin and available size follow the engine's dynamic [topbar safe area](https://create.roblox.com/docs/reference/engine/enums/ScreenInsets), including notches and Roblox's experience controls.
- **Match native CoreGui control height unless explicitly specified otherwise.** A custom topbar button or frame must have the same rendered height as Roblox's adjacent native controls at the current device/UI scale, including outer strokes; match their vertical centre too. Measure the native control's visible plate, not its glyph or the full `TopbarInset.Height`. Merely fitting the inset, or copying an oversized project button, is insufficient. Use the inset for placement and CoreGui control height for sizing; preserve aspect ratio and scale the inner icon proportionally. Never size from viewport height or a body-HUD scale. A separate transparent touch target may meet the 44 px minimum where space permits, without enlarging the visible plate or overlapping nearby controls.
- `TopbarSafeInsets` already applies the topbar position offset: do not apply it twice. If an existing custom layout must position the control in another coordinate space, convert the full `GuiService.TopbarInset` rectangle into that space, including its `Min` offset, and update when `TopbarInset` changes. A fixed desktop topbar height or negative Y offset is not a device-independent solution.
- Place body cards and status panels below the topbar in a `CoreUISafeInsets` container, or explicitly reserve the topbar rectangle in their existing layout. Leave the required visible gap between the topbar control's outermost edge and the first body component. Changing ZIndex, hiding overflow with clipping, or marking an accidental collision `AllowBleed` does not fix the layout.

## Preview and measure in Studio

- **Mount a preview in CoreGui** (Edit): Studio shows it and never saves it with the place. `screen_capture` leaves CoreGui out, so move the preview into StarterGui only for a capture, then delete it, along with anything the code made on the way (sounds, groups).
- **Lay out against the device,** not the Studio window: a frame of the device's size holding the HUD at its own `UIScale`. `GuiService:GetGuiInset()` reads 0 in Edit, so a preview passes the top bar's height in.
- **Measure at each size,** once open tweens settle (Edit can run them late): UIBounds, the smallest text per line, every button's size, the distance to the top bar and the screen edges. Then the content extremes: the longest name and text, the lowest and highest values, optional parts hidden or shown.
- **Check topbar and component separation together:** phone landscape and portrait when supported, tablet, and desktop. Compare the custom component's rendered height and vertical alignment against native CoreGui controls; then confirm its complete visible footprint fits the actual topbar rectangle, clears Roblox's controls, and stays separated from the first body card. Compare independent component rectangles in screen coordinates, including those in separate ScreenGuis: an in-root UIBounds pass alone does not check every such collision. Edit mode can report zero insets; use a clearly identified temporary inset preview for layout checks and verify engine-provided insets in Play when possible. Do not save preview-only inset overrides into the delivered UI.
- **An unpublished place (PlaceId 0) may load none of the game's own images** (every one returned `AssetFetchStatus.Failure`). Judge art in the published place; images missing from such a preview are not a layout fault.
- **Keep Studio in the foreground for captures:** in the background it stops rendering 3D, so the world and every ViewportFrame come out blank while the GUI still draws. That is the environment, not a code fault.
- **Engine gotchas:** `TextFits` checks text against its own label only (a label wider than its parent still passes; UIBounds catches the leak); children of a `UIGridLayout` ignore `Rotation` (rotate a frame inside each cell); under a `UIScale`, `AbsoluteSize` is scaled, so lay out in logical points (`AbsoluteSize / scale`).

## State

- **`ResetOnSpawn = false` on nearly every GUI container** (ScreenGui, and any BillboardGui or SurfaceGui parented under PlayerGui: HUD, menus, shop, tutorial, offers). Build once at join and keep it across respawns; with the default `true` the whole UI is destroyed and rebuilt on every death, losing open windows, scroll positions, tweens and connections. Only UI that truly belongs to one character (an overhead billboard) lives and dies with it.
- **State lives outside the instances.** Keep one source of truth per fact (a store, a Pulse/signal value or the replicated save), and have the UI render from it and write back through it: never read a TextLabel's text or a Frame's `Visible` to decide logic. Views subscribe, update only when the value changes, and are safe to show, hide and re-show. State means facts (data, the open window, a selection), not every property: a reactive value or effect per instance property costs far more than the write it wraps.
- **Survive respawn, rejoin and teleport:** derive what is open or selected from the store, re-bind to the new character (`CharacterAdded`) instead of rebuilding the UI, and restore on join from the saved or replicated state. Disconnect every listener when a view closes or is destroyed, and keep temporary state (a hover, a draft) out of the save.

## World-space GUIs (BillboardGui, SurfaceGui)
- **BillboardGui defaults: scaled size, studs offset.** Size with Scale (`UDim2.fromScale`, so it is measured in studs and shrinks with distance like the world) and offset with `StudsOffsetWorldSpace` (a world-space lift above the adornee, which stays above the head however the camera turns). Use pixel `Size` offsets, `StudsOffset` or `ExtentsOffset` only when the design asks (a tag that must stay a fixed on-screen size, for example). Set `Adornee`, `MaxDistance` and `AlwaysOnTop` deliberately (always-on-top only for pointers that must show through walls), `LightInfluence = 0` for UI, and keep it small and cheap: one per target, not per frame.
- **SurfaceGui:** fix its `Face`, set `SizingMode` and `PixelsPerStud` deliberately (a legible density at the distance it is read), `LightInfluence` and `AlwaysOnTop` on purpose, and keep text large enough to read at that distance.
- The same rules still apply inside them: bounds and rounded corners, readable text, the project's theme, build once and show or hide, state outside the instances.

## Performance

- Build once, then show/hide; do not recreate frames on every open. Pool list rows and virtualize long lists.
- Update text/images only when the value changes. No per-frame property writes for static UI; drive animation with `TweenService` or one shared loop.
- Avoid stacked full-screen transparent frames, many `UIStroke`/`UIGradient` on large lists, and deep `ClipsDescendants` chains.

## Icons and images

- **Fallback imagery:** match the simulator HUD with readable silhouettes, saturated colors, two or three clean shade planes, small glossy highlights and consistent deep plum/navy outlines; no extra sticker border. UI labels stay native text, except artwork intrinsic to an icon, such as a calendar's number.
- **Reuse before generating:** search matching project images, then compatible plugin libraries and Toolbox art ([assets.md](assets.md)). Source availability never changes the selected style. Generate missing art when possible; otherwise mark a temporary placeholder (`Placeholder = true`) and report what is missing and how to replace it with supplied art, a new upload or a predefined asset id.
- Generate icons as **512x512, 1:1 (square), transparent-background PNG** *(default)* (smaller memory on clients); downscale a generator's larger square output with premultiplied-alpha LANCZOS. If a generator cannot output transparency, remove the background and confirm the alpha channel before upload. Use a different size or aspect only for non-icon art (banners, hero art), with the user's agreement.
- **Outlines match the set.** Before generating, measure the siblings' edge with [scripts/icon_outlines.py](../scripts/icon_outlines.py): a viewer shows transparency as white, which hides a white sticker border. Give every new or edited icon the same edge (a dark ink line, a white sticker border of the same width, or none). An edit never adds or drops a border, and a brief states the measured style, never one remembered.
- **Character art** follows [characters.md](characters.md): put its garment line in the prompt and review at full size before upload.
- **Damage, health and defeat icons** are uploads and follow [no-gore.md](no-gore.md): a burst or star for damage, a heart for health, a cartoon skull or KO stars for defeats; never blood drops, splatter or wounds.
- **Uploads** use the project's cloud API key and must load in the experience: [assets.md](assets.md), Uploading.
- All image ids live in the project's image-asset table (or one new constants module), never inline in controllers, so a replacement is a one-line change.
- Preload important images (`ContentProvider:PreloadAsync`) before showing a screen that depends on them.
