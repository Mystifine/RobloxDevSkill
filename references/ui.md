# UI

Everything here applies to every GUI container, **ScreenGui, BillboardGui and SurfaceGui** alike (bounds, touch size, state, performance), not only ScreenGui; the BillboardGui and SurfaceGui specifics are under World-space GUIs.

## Match first

Read the project's existing UI controllers/components, theme or style constants (colors, fonts, corner radius, stroke, padding, tween styles), and its image-asset table. New UI reuses those; do not introduce a second visual language unless the user asks for one. Reuse existing components before building new ones.

## Mobile first

Roblox is a phone platform: **design, build and verify for the phone first**, then scale up to tablet and desktop, unless the user says otherwise. The smallest case is the case.

- Start from the phone's landscape size (about 844 x 390) and its safe area; add layout for larger screens with constraints, not the reverse. Reserve the thumbstick and jump/action zones; never put a control under them.
- Touch first: every button at least 44 px in both directions (after the device scale), no hover-only information, no tiny close buttons, text no smaller than about 11 px after scaling.
- Verify at phone, then tablet, then desktop; with the Studio device emulator on, mouse input becomes touch. A layout that only works on desktop is unfinished.
- Unless the project says portrait is unsupported, check both orientations; if it is unsupported, say so and do not add portrait layouts.

## Stay in bounds

Nothing leaks out of its box unless the design says so. **A stroke is drawn outside its frame**, so an element's outline adds its thickness on every side: a bar 1 px inside a rim still touches the rim once its own outline is counted.

- Children stay inside the parent with their outlines, keep **at least 2 px clear** of any border, rim or outline band, and stay clear of **rounded corners** (a child near a corner of a `UICorner` parent can poke out of the arc).
- Size content from the container's inner edge (rim inset plus stroke thickness), with a margin, not from its outer edge.
- A deliberate overlap (a badge breaking a card's corner, a glow, a shine sweep) is marked with the boolean attribute `AllowBleed` and a comment that says why.
- Check with [scripts/UIBounds.luau](../scripts/UIBounds.luau) on the mounted UI at the phone size first: `UIBounds.audit(frame)` reports `outside-parent`, `on-border`, `corner` and `outside-root` with pixel amounts. Fix the layout, not the audit.

## Layout rules

- **Center anchor.** Set `AnchorPoint = (0.5, 0.5)` and position by the element's center, so tweens of `Size`, `Rotation` and `Position` (pop-ins, scale-ups, shakes) grow from the middle. Use another anchor only when asked or when an edge must stay pinned (for example a bar that fills from the left).
- Scale-based `Size`/`Position` with `UIAspectRatioConstraint`, `UISizeConstraint`, `UITextSizeConstraint` and `UIScale` for device scaling. Lay out with `UIListLayout`/`UIGridLayout`/`UIPadding` rather than hand-placed offsets.
- `ScreenGui`: `ZIndexBehavior = Sibling`, set `IgnoreGuiInset` deliberately. Respect safe areas on phones. `ResetOnSpawn` is covered under State.

## State

- **`ResetOnSpawn = false` on nearly every GUI container** (ScreenGui, and any BillboardGui or SurfaceGui parented under PlayerGui: HUD, menus, shop, tutorial, offers). Build once at join and keep it across respawns; with the default `true` the whole UI is destroyed and rebuilt on every death, losing open windows, scroll positions, tweens and connections. Only UI that truly belongs to one character (an overhead billboard) lives and dies with it.
- **State lives outside the instances.** Keep one source of truth per fact (a store, a Pulse/signal value or the replicated save), and have the UI render from it and write back through it: never read a TextLabel's text or a Frame's `Visible` to decide logic. Views subscribe, update only when the value changes, and are safe to show, hide and re-show.
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

- Generate icons as **512x512, 1:1 (square), transparent-background PNG** by default (smaller memory on clients). If a generator cannot output transparency, remove the background and confirm the alpha channel before upload. Use a different size or aspect only for non-icon art (banners, hero art), with the user's agreement.
- **Outlines match the set.** Before generating, measure the siblings' edge with [scripts/icon_outlines.py](../scripts/icon_outlines.py): a viewer shows transparency as white, which hides a white sticker border. Give every new or edited icon the same edge (a dark ink line, a white sticker border of the same width, or none). An edit never adds or drops a border, and a brief states the measured style, never one remembered.
- **Character art** follows [characters.md](characters.md): put its garment line in the prompt and review at full size before upload.
- **Uploads** use the project's asset key and must end public: [assets.md](assets.md), Uploading.
- All image ids live in the project's image-asset table (or one new constants module), never inline in controllers, so a replacement is a one-line change.
- When an image is needed and not supplied: look in the Toolbox if available (audit per [assets.md](assets.md)), otherwise use a temporary placeholder and mark it (comment or attribute `Placeholder = true`). Tell the user which ids are placeholders; images are normally supplied later to upload and swap in.
- Preload important images (`ContentProvider:PreloadAsync`) before showing a screen that depends on them.
