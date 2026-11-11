# Onboarding and tutorials

## Tutorial design: show, don't tell
- **One short sentence per step** (aim 3-6 words: "Tap the gate"). Motion, glow and pointers teach; text only names the action. No paragraphs, no stacked tips.
- **One step = one target + one player action.** It completes on the action itself (tap, move, pickup), never a Next button. Reward each step at once (sound, pop, currency); get the player acting within about 20 s of joining.
- **Assist heavily.** The player always sees where to look, go or press. Re-point after about 6 s idle and after a failed try; a stuck player never guesses.
- **Enforced and dummy-proof** *(default)*. The player cannot reset, open other UI, trigger other features or do anything that breaks the lesson: disable the reset button (`SetCore("ResetButtonCallback", false)`), hide every HUD piece and window the step does not use, disable what it does not need (shop, offers, teleports, other keybinds, popups, monetization prompts), block input outside the target, and make the player unable to die or fall out of the area. Reveal UI as it is taught. Relax this only for tutorials that are explicitly suggestive, optional or non-enforcing (a tip, a hint ring); say so in the design.
- **Server owns progress.** Validate each step on the server and reject out-of-order or unexpected requests; steps are idempotent, never farmable or blockable. Persist only completion. **Leaving mid-tutorial resets the whole run** *(default)*: the next join starts at step 1 and anything the tutorial granted or spawned is undone. Cutscenes keep their required skip, which restores state through its own path.
- **Mobile first.** Targets at least 44 px, pointers inside safe insets, check with the device emulator on touch.
- **Measure it.** When building or changing a tutorial, give it the onboarding funnel ([analytics.md](analytics.md)).
- **Test a step without playing up to it:** a Studio-only hook (a player attribute the server reads only under `RunService:IsStudio()`) starts the real flow at a named step, on a scratch store, never the owner's save ([studio-testing.md](../code/studio-testing.md#specs-in-studio)).
- **A replay for developers,** when one is asked for, is allowed by a rank check on the server, keeps its step in server memory, and grants, saves and logs nothing: its rewards go to nobody, a lesson match is practice (no pay, wins or quests), and it sends no funnel step. A whole run then leaves the save untouched, so leaving part way cannot trigger the unfinished-tutorial reset.

## Pointers: pick one per target, never stack them
| Target | Use |
|---|---|
| UI element | Focus cut-out: a rounded frame with a huge UIStroke running off screen darkens everything else; ring ping; bobbing arrow |
| Nearby 3D object | Same dark focus around the object's projected bounds (or Highlight), plus a floating billboard arrow above it (AlwaysOnTop, bob about 1 Hz, a few px) |
| Far place | Beam from the character (`Attachment0`) to the target, both ends about 1.5 studs above the floor (ground the target with a ray, then lift) so it never digs in; fade both ends; chevrons flowing to the target, drawn pointing down their image |
| Key reveal | Camera nudge of 2 s or less, then hand control back. Never during movement lessons |

A hand or arrow image points the way its texture draws it, not the way its name says: one placed left of its button pointed away from it, which only a zoomed capture showed. Check the direction in a capture and mirror it to the side with room ([icons.md](../ui/icons.md)).

Templates: [scripts/TutorialGuide.luau](../../scripts/TutorialGuide.luau): `spotlight` (dark hole plus input sinks), `screenRect`, `arrow`, `beam`, `lookAt`, `lock` (hide HUD, sink keys, restore). Checked in Studio. Use the project's own pointer or beam first if it has one, and match its style.
