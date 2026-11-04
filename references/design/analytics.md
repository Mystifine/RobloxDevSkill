# Analytics: funnels, custom events and fields

Funnels show where players stop between ordered steps, which is what each iteration of a game acts on. An experience gets only 10, so plan all of them at once, use custom fields before spending a slot, and measure everything else with custom events.

## Limits (Creator Hub limits table; Roblox staff on the DevForum)
- **10 funnels per experience, onboarding included** (the limits table lists Onboarding and Shop among the 10). An 11th funnel's events succeed but are dropped and never shown, with no warning.
- **Limits are counted per day.** A funnel you stop sending frees its slot the next day; the dashboard keeps showing it until 90 days after its last event, and nothing deletes it sooner. Servers still on an old build keep sending its funnels, so a slot frees only once the last of them closes.
- 100 steps per funnel; 100 custom event names. Server only, published places only (never the client or Studio).
- Up to 3 custom fields on funnel, custom and economy events (`Enum.AnalyticsCustomFieldKeys.CustomField01..03.Name`, string values): unlimited values per field, but past 8,000 combined values they are grouped as "Other".
- One rate budget for all events: 120 + 20 per CCU per minute.
- **How steps count:** only a step's first instance counts (repeats still spend rate budget); logging a later step completes every earlier one; a player's saved step expires after 180 days with no event in that funnel, and they return as a new user (this does not free the slot). One-time funnels need no `funnelSessionId`; recurring ones do (a GUID per visit, or `<playerId>-<itemId>` across sessions); the last 10 per user per funnel are tracked, and an older id counts as a new session.
- **The dashboard** groups a funnel by cohort (the day each player entered), applies filters to step 1 only, and breaks down by age, platform and the like or by custom field. Events aggregate daily: allow up to 24 hours.

## Funnel, custom event or field
| You want | Use |
|---|---|
| Drop-off between the ordered steps of one path | A funnel |
| A count or a value: how many reached level 50, minutes to the first upgrade, kills per match | A custom event (`LogCustomEvent`, value optional) |
| The same path or count per variant (class, map, egg tier, offer, live event, test arm) | One funnel or event, the variant in a custom field |
| Failures and friction (cannot afford, storage full); optional side steps (a chest, a side shop) | A custom event with a bounded reason field |
| Currency sources and sinks | `LogEconomyEvent` ([game-economy.md](game-economy.md)) |

Fields before names, for events too: one `PlantSeed` event with `Plant - Cabbage`, never a `PlantCabbage` event.

## The 10 slots *(default)*
Allocate all ten in the design plan's Funnels table before the first ships, and keep them in one registry module (name, slot, kind, steps, fields, status, retire date). The server logger refuses a funnel the registry lacks; a test fails when more than 10 are live.

| Slot | Funnel | Kind | Steps, for example |
|---|---|---|---|
| 1 | Onboarding | Lifetime | First join, then one per lesson to the tutorial's end |
| 2 | First-session core loop | Lifetime | Post tutorial, first action, first reward, first upgrade |
| 3 | Aha moment | Lifetime | Post tutorial, the steps toward the moment the game turns fun (first hatch, first win, first weapon equipped), that moment |
| 4 | Monetization | Recurring, per store visit | Store opened, item viewed, purchase prompted, purchase granted |
| 5 | Core feature A (pets) | Lifetime | Post tutorial, menu opened, egg bought, egg hatched, pet equipped |
| 6 | Core feature B (trading) | Recurring, per trade | Trade opened, item added, request sent, trade completed |
| 7 | Progression or endgame | Lifetime | Post tutorial, max level, rebirth opened, rebirth confirmed, first rebirth upgrade |
| 8 | Flex: drill-down | Temporary | Another funnel's worst step split into its moments: prompt shown, confirm tapped, action done |
| 9 | Flex: live ops | Recurring, per event | One funnel for every event, `Event - <name>` as a field and `<playerId>-<event>` as the session: event seen, joined, first task, halfway, finished, reward claimed |
| 10 | Flex: sandbox | Empty | A new feature's funnel until it earns a permanent slot; while empty, a stray 11th name drops nothing that matters |

- **Fit the slots to the game.** When the aha moment is a core feature's first use, slot 3 is that feature's funnel: give the spare slot to the next feature. Main features beyond the slots get custom events.
- **A flex slot answers one question, then frees.** Record the question and end date in the registry. Retire the funnel once it is answered and the fix shows in the main funnel; reuse the slot the day after its last server closes.
- **Drill-down steps may be what the player was shown**, reported by the client and checked in order by the server. It is a separate funnel because the main funnel's steps are never inserted or reordered.
- **Monetization:** log the last step where the server grants the purchase (`ProcessReceipt` for developer products, `PromptGamePassPurchaseFinished` on the server for passes), never when the client's prompt closes. Its fields are what is known when the store opens (`Source - HUD`, `Source - Out of coins`, payer or not); the item is not known yet, so it goes in the economy or a custom event.
- **Experiments:** the test arm is a field, frozen at enrollment, on the funnels the change touches; never a funnel per arm.

## Rules
- Design the set once and reuse it forever: no V2/V3, no renames (a step-name change only shows a warning on the step); keep meanings stable and append steps, never reorder.
- **A custom field is a segment label, fixed when the player enters the funnel.** Every step of one funnel session sends the same values; a value that changes mid-funnel splits one player across segments, and filters read step 1 only. So a field can hold only a variant known at step 1: a class picked at step 3 belongs to a funnel that starts at the pick, or to a custom event. Anything that changes (time since start, blockers, resources) is a custom event or event value, not a field.
- **Scheme** *(default)*. Lifetime funnels: field 1 `Origin - <Cohort>_T<tutorial>_A<schema>_B<build at enrollment>`, field 2 the funnel's variant (a handful of values, frozen at enrollment) or constant, field 3 constant. Per-attempt funnels (a run, a gate, a store visit): the same Origin without the build, field 2 a bounded context (dungeon or tier, store source), field 3 a bounded state (readiness, party, payer), both **frozen at session start**. Onboarding: Cohort / `Version - N; Build - N` / Content. Bump the tutorial or schema number only when its meaning changes.
- **Keep every field's value set bounded** for the funnel's whole life: bucket long tails (24 dungeons into about 6 tiers), one spelling per meaning (a new spelling starts a new series), no raw numbers, GUIDs or names. Write values as `Dimension - Value`. The three fields multiply, so a value that changes every publish belongs only where the other two fields have few values.
- **Sync the published build automatically**: `game.PlaceVersion` is the number in the place's Version History (0 if never published). Read it server-side, label Studio separately, and remember a server keeps the version it started on. A funnel spanning days or publishes freezes the build with its enrollment (saved beside the cohort), or one player's steps land in different builds. Where a field cannot afford a value per publish, compare builds by date range instead. Never a new funnel for a build.
- **Onboarding funnel**: step 1 on join (`PlayerAdded`) for a player who has not finished the tutorial, so the drop is measured from spawn; then one step per lesson in order, named by the action, logged on server validation (never on UI show).
- **Progression funnels are post-tutorial** *(default)*, so they show how players who finished the tutorial behave. The server enrolls a player when it saves the tutorial as complete and sends no progression step, lifetime or per attempt, before that: the onboarding funnel covers the tutorial, and a milestone the tutorial scripts or grants (a guided first run, a starter pet) says nothing about what players choose. Step 1 of every lifetime progression funnel is that enrollment (`Post tutorial`), so they all start from the same count of graduates. Players who finished the tutorial before the funnels shipped enroll on their next join as their own cohort (`Existing`); read the new graduates (`Fresh`). Persist cohort, labels and step cursors in the save so a returning player keeps them. A game without a tutorial enrolls on first join.
- **One feature per funnel** *(default)*: the core loop, each system (pets, base, crafting) and the tier ladder each hold only that feature's first-time milestones in its own order (a few to 20 within about the first 2 hours: first run, first clear, first return; first upgrade, second, third). Features advance in parallel and logging a later step completes every earlier one, so a mixed funnel records steps the player never took and hides which feature loses them. Within a funnel, send a step only after its predecessors (hold one that arrives early).
- Test the step order with a mock transport; real data appears only from published servers.

## Iterating *(default)*
- Find the step with the largest drop and change one thing there: a contextual prompt, a first success before the player explores further, a cheaper first step.
- Publish, then read the same step of the same funnel: by the build in the Origin field, or by date range, comparing a whole week before with a whole week after so the weekday mix matches. Never start a new funnel to measure a fix.
- One change per measured step per publish; two at once leave the result unexplained.

Docs: [funnel events](https://create.roblox.com/docs/production/analytics/funnel-events), [custom events](https://create.roblox.com/docs/production/analytics/custom-events), [custom fields](https://create.roblox.com/docs/production/analytics/custom-fields), [limits](https://create.roblox.com/docs/production/analytics/event-types), [staff on the daily limits](https://devforum.roblox.com/t/clarification-on-funnel-analytics-limits/3084051).
