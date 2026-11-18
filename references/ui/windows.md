# UI: windows, modals and sheets

For a window, modal or sheet, beside [ui.md](ui.md).

- **Side menus leave while a window is open** *(default)*: a spring per side slides each cluster off-screen from its layout position and hides it once fully out, then springs it back on close.
- **A modal's shade covers every layer drawn above the window,** the top bar row and any HUD ScreenGui with a higher `DisplayOrder` included: a shade inside the windows' ScreenGui (`CoreUISafeInsets`, `DisplayOrder` 10) left the HUD's top bar row (a `TopbarSafeInsets` ScreenGui at `DisplayOrder` 50) bright behind a dark sheet. Strips round the safe area in a ScreenGui above them all (`DisplayOrder` 51, `ScreenInsets` `None`), shown with the sheet and closing it on a tap, fixed it without moving the sheet's own layers.
- **A sheet that holds a whole feature** (an upgrade, a commitment, a detail page) **is sized against the screen,** not the window it opens from *(default)*: a layer on the window's full-screen frame (`Sibling` `ZIndex` above the window) filling about 95% of a phone and 78% of a desktop, two columns in landscape and one upright. As a modal inside a landscape window's body, a portrait sheet got about 530 x 570 px at 1080p and 8 px text on a 760 x 354 phone; as a screen layer, 1485 x 627 px and 722 x 307 px, its smallest text 12 px and buttons at least 44 px.
- **A fold or collapse control sits on its panel's edge,** or is left out *(default)*: an arrow beside a column of menu tiles, at mid-height and apart from them, read as a random floating arrow.
