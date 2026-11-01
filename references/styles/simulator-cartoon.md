# Simulator cartoon UI and imagery

Use only when selected by the [visual-style dispatcher](../visual-style.md). These are techniques from a reference family, not defaults for all Roblox interfaces.

Techniques to apply when supported by the user's reference:

- Rounded, saturated plates with dark outlines, soft vertical gradients and diagonal shine contained by rounded faces.
- Bold rounded lettering such as FredokaOne, pale text with strong dark outlines, glossy cartoon icons, functional colors, compact status cards and restrained progression accents.
- Notification badges may deliberately overlap their own card. Independent components still need clearance; see [ui.md](../ui.md).

Match the actual reference's palette, corners, line weight and decoration. For icons, readable silhouettes, two or three shade planes and small glossy highlights can fit this family; add a sticker border only when the set has one. Preserve editable native UI labels except text intrinsic to artwork, such as a calendar's number. Measure sibling outlines with `scripts/icon_outlines.py` before making replacements.

The [UI implementation and verification rules](../ui.md) apply regardless of style.
