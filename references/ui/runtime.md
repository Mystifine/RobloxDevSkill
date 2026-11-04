# UI: live state, performance and world-space GUIs

## State

- **`ResetOnSpawn = false` on nearly every GUI container** (ScreenGui, and any BillboardGui or SurfaceGui parented under PlayerGui: HUD, menus, shop, tutorial, offers). Build once at join and keep it across respawns; with the default `true` the whole UI is destroyed and rebuilt on every death, losing open windows, scroll positions, tweens and connections. Only UI that truly belongs to one character (an overhead billboard) lives and dies with it.
- **State lives outside the instances.** Keep one source of truth per fact (a store, a Pulse/signal value or the replicated save), and have the UI render from it and write back through it: never read a TextLabel's text or a Frame's `Visible` to decide logic. Views subscribe, update only when the value changes, and are safe to show, hide and re-show. State means facts (data, the open window, a selection), not every property: a reactive value or effect per instance property costs far more than the write it wraps.
- **Survive respawn, rejoin and teleport:** derive what is open or selected from the store, re-bind to the new character (`CharacterAdded`) instead of rebuilding the UI, and restore on join from the saved or replicated state. Disconnect every listener when a view closes or is destroyed, and keep temporary state (a hover, a draft) out of the save.

## Performance

- Build once, then show/hide; do not recreate frames on every open. Pool list rows and virtualize long lists.
- Update text/images only when the value changes. No per-frame property writes for static UI; drive animation with `TweenService` or one shared loop.
- Avoid stacked full-screen transparent frames, many `UIStroke`/`UIGradient` on large lists, and deep `ClipsDescendants` chains.

## World-space GUIs (BillboardGui, SurfaceGui)

- **BillboardGui defaults: scaled size, world-space placement.** Size with Scale (`UDim2.fromScale`, so it is measured in studs and shrinks with distance like the world), with both `Size` offsets at zero. Position it with `StudsOffsetWorldSpace` (a world-space lift above the adornee, which stays above the head however the camera turns); this world-space property is distinct from a UI dimension's pixel offset. Set `Adornee`, `MaxDistance` and `AlwaysOnTop` deliberately (always-on-top only for pointers that must show through walls), `LightInfluence = 0` for UI, and keep it small and cheap: one per target, not per frame.
- **SurfaceGui:** fix its `Face`, set `SizingMode` and `PixelsPerStud` deliberately (a legible density at the distance it is read), `LightInfluence` and `AlwaysOnTop` on purpose, and keep text large enough to read at that distance.
- **3D UI in front of the camera** (cards in a hand, a held panel): parts parented to the camera, each face a `FixedSize` SurfaceGui (a 512 x 768 canvas, say), moved with `workspace:BulkMoveTo` in a render step bound after the camera's (`Enum.RenderPriority.Camera.Value + 1`). A flat UI component works on them unchanged except its text limits: `MaxTextSize` counts canvas pixels, so it needs larger values. Hit-test with a ray against each part's plane; no physics query is needed.
- **A pointer at (-1, -1) is no pointer:** `UserInputService:GetMouseLocation()` reads -1, -1 in Play while the mouse is outside the game view. A pointer-driven camera took it as the top-left corner and leaned fully that way; treat it as no input and ease back to rest.
- The same rules still apply inside them: bounds and rounded corners, readable text, the project's theme, build once and show or hide, state outside the instances.
