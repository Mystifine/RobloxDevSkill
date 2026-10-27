# Onboarding, tutorials and funnels

## Tutorial design: show, don't tell
- **One short sentence per step** (aim 3-6 words: "Tap the gate"). Motion, glow and pointers teach; text only names the action. No paragraphs, no stacked tips.
- **One step = one target + one player action.** It completes on the action itself (tap, move, pickup), never a Next button. Reward each step at once (sound, pop, currency); get the player acting within about 20 s of joining.
- **Assist heavily.** The player always sees where to look, go or press. Re-point after about 6 s idle and after a failed try; a stuck player never guesses.
- **Strip the screen.** Hide every HUD piece and window the lesson does not use; disable what it does not need (shop, offers, teleports, other keybinds, popups, monetization prompts) and block input outside the target. Reveal UI as it is taught. Restore on finish, **skip**, death and rejoin. Always offer a skip.
- **Server owns progress.** Persist the step, validate completion on the server, make steps idempotent and rejoin-safe; nothing farmable or blockable.
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
- The dashboard takes **up to 10 funnels**. The docs do not say whether onboarding counts: assume it does (plan 9 custom plus onboarding).
- **Server only, published places only.** Onboarding: `LogOnboardingFunnelStepEvent(player, step, name, fields)`. Others: `LogFunnelStepEvent(player, funnel, sessionId, step, name, fields)`.
- Only a step's first instance counts (repeats still spend rate budget). Skipping ahead completes earlier steps. A saved step expires after 180 days.
- One-time funnels (onboarding, progression) need no `funnelSessionId`. Recurring ones (shop, upgrades) do (GUID or `<playerId>-<itemId>`); only the 10 most recent per user per funnel are tracked.
- **Custom fields**: up to 3 per event, keys `Enum.AnalyticsCustomFieldKeys.CustomField01/02/03.Name`, string values, at most 8,000 combinations overall. Write values as `Dimension - Value`. Events share one rate budget (120 + 20 per CCU per minute).

**Rules**
- **Reuse the same funnels forever.** Never create V2/V3 and never rename: design the set once. Separate versions with custom fields (field 1 `Version - N` or `Origin - <cohort>`, field 2 content or cohort, field 3 device or segment) and compare by date range plus field filter. A step-name change only shows a warning on the step, so keep meanings stable and append new steps instead of reordering.
- **Onboarding funnel**: one step per lesson in order, named by the action. Log on server validation, never on UI show. Blockers go to bounded custom events.
- **Post-progression funnels** cover the first ~2 hours: enrol at tutorial completion, 10-20 steps that are concrete first-time milestones in play order (first run, first reward, first upgrade, first return, tier steps, first purchase). Persist enrolment cohort and step cursor in the save so a returning player keeps their cohort. Record time since start as a field or event, not a new funnel.
- Failures and friction (cannot afford, storage full) are custom events with a bounded reason list, not extra steps.
- Verify the step order with a mock transport in tests; real data appears only from published servers.

Docs: [funnel events](https://create.roblox.com/docs/production/analytics/funnel-events), [custom fields](https://create.roblox.com/docs/production/analytics/custom-fields).
