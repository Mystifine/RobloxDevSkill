# Reference HUD artwork

Reinstalled on November 1, 2026 after confirming StarterGui was empty. Both containers contain zero scripts. Fresh synthetic layout checks at 844x390, 390x844, 1024x768, and 1918x1008 (reserving 58px for the topbar) each checked 1,038 GuiObjects with zero UIBounds findings and no overflowing TextLabels. Desktop Play measurement confirmed the four custom topbar plates match the native 44px height and vertical center. Temporary previews were removed and Studio returned to Edit.

The existing client startup separately creates `PlayerGui.PlusOneGui` and `PlusOneTopbar`. Those older runtime interfaces were hidden only in the temporary Play session for inspection; their source and startup behavior remain intact. They will overlap the new static HUD in Play until that older UI creation is disabled or integrated. The new StarterGui UI is visual only, as requested.

Installed in the connected `+1 Template` Studio place:

- `StarterGui.ReferenceSimulatorHUD`
- `StarterGui.ReferenceSimulatorTopbar`

These contain static GUI instances only. There are no Scripts, LocalScripts, ModuleScripts, event connections, purchases, or live stat bindings in either container. Captions and sample values are editable TextLabels.

The supplied screenshot determines the composition and saturated glossy cartoon style. The world background and Roblox's native menu/chat controls are not part of the custom HUD.

`icons-atlas.png` was created with the built-in image generation tool. It has a transparent RGBA background and twelve original cartoon illustrations. Roblox asset: `rbxassetid://136387010934188`. The uploaded 1254px atlas is transcoded to 1024px; the authoring helper applies the corresponding crop-coordinate scale. The exact generation prompt is saved in `prompt.txt`.

`../../build_reference_hud.luau` is an offline Studio authoring command, not a runtime script installed in the place. It rebuilds only the two named GUI containers.

Initial verification used Studio Edit previews at iPhone 17 Pro landscape (749x381 viewport), portrait (401x777), iPad Pro M5 13in (1374x1030), and desktop (1590x755). UIBounds reported zero findings for both ScreenGuis at those sizes. The portrait capture used a temporary 58px inset, then removed it. The audit's outer pairwise loop yielded in batches to avoid freezing Studio; its geometry rules were unchanged. This initial check missed native topbar alignment because it did not include Play mode.

Topbar correction: measured the native Roblox-logo plate and all four custom plates together in the running client on desktop, phone landscape/portrait, and tablet. All plates were 44px high, with a 0px vertical-centre difference after the fix. The original custom row was 12px too high. `QuickAccess` now anchors to the bottom of the engine-provided topbar safe rectangle with the measured 2px bottom clearance. Native constraints and layout padding tighten horizontal gaps on portrait: 4px gaps, final right edge 400px inside the 401px viewport. No runtime script was added. The change is persisted in StarterGui and in the authoring helper. The skill now requires the live native comparison before topbar alignment may be called verified. Studio was returned to the default viewport and left in Play, matching the user's starting mode. No place publishing was performed.

Compact HUD correction: lower-left counters now use separate square icon slots and left-aligned amount slots in horizontal layouts. The icon-to-text and friend-text-to-button clearances are 4px after including text outlines. The plus plate has a 1:1 aspect constraint and a 24–28px size range; measured width/height difference was 0px on desktop, phone landscape/portrait, and tablet. All six prices use the native Robux character U+E002 in the same TextLabel as the amount, with no drawn token geometry. Play previews confirmed glyph rendering, and stress values `999.9T` / `Friend Boost: +999%` fit on the phone (friend text 12px high). Final phone landscape/portrait and desktop UIBounds checks reported zero findings. The phone's stat group also clears the navigation cards. Temporary stress values and locally hidden unrelated runtime HUDs were discarded; original sample values are saved in StarterGui. No scripts were added. Studio was returned to its default viewport in Edit, matching this correction's starting mode.
