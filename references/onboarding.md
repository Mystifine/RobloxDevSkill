# Onboarding, tutorials and funnels

## Tutorial design: show, don't tell
- **One short sentence per step** (aim 3-6 words: "Tap the gate"). Motion, glow and pointers teach; text only names the action. No paragraphs, no stacked tips.
- **One step = one target + one player action.** It completes on the action itself (tap, move, pickup), never a Next button. Reward each step at once (sound, pop, currency); get the player acting within about 20 s of joining.
- **Assist heavily.** The player always sees where to look, go or press. Re-point after about 6 s idle and after a failed try; a stuck player never guesses.
- **Enforced and dummy-proof by default.** The player cannot reset, open other UI, trigger other features or do anything that breaks the lesson: disable the reset button (`SetCore("ResetButtonCallback", false)`), hide every HUD piece and window the step does not use, disable what it does not need (shop, offers, teleports, other keybinds, popups, monetization prompts), block input outside the target, and make the player unable to die or fall out of the area. Reveal UI as it is taught. Relax this only for tutorials that are explicitly suggestive, optional or non-enforcing (a tip, a hint ring); say so in the design.
- **Server owns progress.** Validate each step on the server and reject out-of-order or unexpected requests; steps are idempotent, never farmable or blockable. Persist only completion. **Leaving mid-tutorial resets the whole run**: the next join starts at step 1 and anything the tutorial granted or spawned is undone. Cutscenes keep their required skip, which restores state through its own path.
- **Mobile first.** Targets at least 44 px, pointers inside safe insets, check with the device emulator on touch.

## Pointers: pick one per target, never stack them
| Target | Use |
|---|---|
| UI element | Focus cut-out: a rounded frame with a huge UIStroke running off screen darkens everything else; ring ping; bobbing arrow |
| Nearby 3D object | Same dark focus around the object's projected bounds (or Highlight), plus a floating billboard arrow above it (AlwaysOnTop, bob about 1 Hz, a few px) |
| Far place | Beam from the character to the target, both ends about 1.5 studs above the floor (ground the target with a ray, then lift) so it never digs in; fade both ends; flowing chevrons |
| Key reveal | Camera nudge of 2 s or less, then hand control back. Never during movement lessons |

Templates: [scripts/TutorialGuide.luau](../scripts/TutorialGuide.luau): `spotlight` (dark hole plus input sinks), `screenRect`, `arrow`, `beam`, `lookAt`, `lock` (hide HUD, sink keys, restore). Checked in Studio. Use the project's own pointer or beam first if it has one, and match its style.

## Funnels (AnalyticsService; Creator Hub docs checked 2026-10-27)
- The dashboard takes **up to 10 funnels**. The docs do not say whether onboarding counts, so plan **at most 9 in total, onboarding included**, and create only the ones needed now.
- **Server only, published places only.** Onboarding: `LogOnboardingFunnelStepEvent(player, step, name, fields)`. Others: `LogFunnelStepEvent(player, funnel, sessionId, step, name, fields)`.
- Only a step's first instance counts (repeats still spend rate budget). Skipping ahead completes earlier steps. A saved step expires after 180 days.
- One-time funnels (onboarding, progression) need no `funnelSessionId`. Recurring ones (shop, upgrades) do (GUID or `<playerId>-<itemId>`); only the 10 most recent per user per funnel are tracked.
- **Custom fields**: up to 3 per event, keys `Enum.AnalyticsCustomFieldKeys.CustomField01/02/03.Name`, string values, at most 8,000 combinations overall. Write values as `Dimension - Value`. Events share one rate budget (120 + 20 per CCU per minute).

**Rules**
- **Reuse the same funnels forever.** Never create V2/V3 and never rename: design the set once. A step-name change only shows a warning on the step, so keep meanings stable and append new steps instead of reordering.
- **A custom field is a segment label, fixed when the player enters the funnel.** Every step of one funnel session sends the same three values; a value that changes between steps splits one player across segments and ruins per-segment conversion. Anything that changes during the funnel (blockers, durations, resources, what changed at a step) is a custom **event**, not a field.
- **Scheme.** Lifetime funnels: field 1 `Origin - <Cohort>_T<tutorial>_A<schema>_B<build at enrollment>`, fields 2-3 constant. Per-attempt funnels (a run, a gate): the same Origin without the build, field 2 a bounded context (dungeon or tier), field 3 a bounded state (readiness, party), both **frozen at session start**. Onboarding: Cohort / `Version - N; Build - N` / Content. Bump the tutorial or schema number only when its meaning changes; the build changes on its own.
- **Budget the product.** The three fields multiply (8,000 combinations in total, treat it as shared across the whole experience until the docs say otherwise): count the values per funnel, bucket long tails (24 dungeons into about 6 tiers), keep one spelling per meaning (a new spelling starts a new series) and never put raw numbers, GUIDs or names in a field. A value that changes every publish belongs only where the other two fields have few values.
- **Sync the published build automatically**: `game.PlaceVersion` is the number in the place's Version History (0 if never published). Read it server-side, label Studio separately, and note that a server keeps the version it started on. A funnel that spans days or publishes freezes the build with its enrollment (save it beside the cohort), or one player's steps land in different builds and per-build conversion is wrong. Never a new funnel for a build.
- **Onboarding funnel**: one step per lesson in order, named by the action. Log on server validation, never on UI show. Blockers go to bounded custom events.
- **Post-progression funnels** cover the first ~2 hours: enrol at tutorial completion, 10-20 steps that are concrete first-time milestones in play order (first run, first reward, first upgrade, first return, tier steps, first purchase). Persist enrolment cohort and step cursor in the save so a returning player keeps their cohort. Record time since start as a field or event, not a new funnel.
- Failures and friction (cannot afford, storage full) are custom events with a bounded reason list, not extra steps.
- Verify the step order with a mock transport in tests; real data appears only from published servers.

Docs: [funnel events](https://create.roblox.com/docs/production/analytics/funnel-events), [custom fields](https://create.roblox.com/docs/production/analytics/custom-fields).
