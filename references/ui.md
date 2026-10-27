# UI

## Match first

Read the project's existing UI controllers/components, theme or style constants (colors, fonts, corner radius, stroke, padding, tween styles), and its image-asset table. New UI reuses those; do not introduce a second visual language unless the user asks for one. Reuse existing components before building new ones.

## Layout rules

- **Center anchor.** Set `AnchorPoint = (0.5, 0.5)` and position by the element's center, so tweens of `Size`, `Rotation` and `Position` (pop-ins, scale-ups, shakes) grow from the middle. Use another anchor only when asked or when an edge must stay pinned (for example a bar that fills from the left).
- Scale-based `Size`/`Position` with `UIAspectRatioConstraint`, `UISizeConstraint`, `UITextSizeConstraint` and `UIScale` for device scaling. Lay out with `UIListLayout`/`UIGridLayout`/`UIPadding` rather than hand-placed offsets.
- `ScreenGui`: `ResetOnSpawn = false` for persistent HUD, `ZIndexBehavior = Sibling`, set `IgnoreGuiInset` deliberately. Respect safe areas on phones.
- Verify at phone, tablet and desktop sizes (Studio device emulator). With the emulator on, mouse input becomes touch; check buttons are at least about 44 px.

## Performance

- Build once, then show/hide; do not recreate frames on every open. Pool list rows and virtualize long lists.
- Update text/images only when the value changes. No per-frame property writes for static UI; drive animation with `TweenService` or one shared loop.
- Avoid stacked full-screen transparent frames, many `UIStroke`/`UIGradient` on large lists, and deep `ClipsDescendants` chains. Disconnect listeners when a view closes.

## Icons and images

- Generate icons as **512x512, 1:1 (square), transparent-background PNG** by default (smaller memory on clients). If a generator cannot output transparency, remove the background and confirm the alpha channel before upload. Use a different size or aspect only for non-icon art (banners, hero art), with the user's agreement.
- All image ids live in the project's image-asset table (or one new constants module), never inline in controllers, so a replacement is a one-line change.
- When an image is needed and not supplied: look in the Toolbox if available (audit per [assets.md](assets.md)), otherwise use a temporary placeholder and mark it (comment or attribute `Placeholder = true`). Tell the user which ids are placeholders; images are normally supplied later to upload and swap in.
- Preload important images (`ContentProvider:PreloadAsync`) before showing a screen that depends on them.
