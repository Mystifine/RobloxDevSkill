# Journeys: branching progression

A journey maps progression as stages, each holding the alternative actions that count as the same progress, and shows which paths players actually take. Use one when players reach equivalent milestones by different valid routes or orders (a choice of first activity, quests in any order, store categories before one checkout). One required order is a funnel; repeated or cyclic activity is custom events. The fields, registry and release rules in [analytics.md](analytics.md) apply here too.

## Logging
- `AnalyticsService:LogJourneyEvent(player, journeyName, nodeName, journeySessionId, customFields)`, server only, after the server has validated that the player reached that node. Up to 3 custom fields, the same values on every event of a session.
- Names in code match the published configuration exactly: keep them in constants. The configuration sets each node's stage, so code never sends a stage index. Publishing a configuration adds no logging: the calls must exist in the code.
- **Session id:** a journey a player can repeat (a store visit, a run) uses one id for every event of an attempt and a new `HttpService:GenerateGUID(false)` for the next; a one-time journey omits it.

## Progression rules
- Roblox adds stage 0, `__entry__`: never configure or log it.
- Repeating the current node does not advance; a node of the same or an earlier stage never moves progress back.
- **Jumping to a later stage records the stages between as skipped** (a funnel counts them as completed).
- A node missing from the configuration version the player acquired does not advance them.
- Any node of the final stage counts as reaching it.
- Saved progress expires after 180 days without events; the player restarts at `__entry__`.
- So a journey models no loops or backtracking: give repeated activity custom events, or make each attempt its own session.

## Stages and names
- 2-10 stages, 1-10 nodes each. Nodes in one stage are alternatives that mean equal progress, never unrelated actions grouped for convenience. A node is a real state reached, at a milestone boundary, not every micro-action.
- Journey names: letters, digits, `.`, `-` and `_`, at most 50 characters (the engine drops longer ones), no leading `_`.
- Node names: at most 50 characters, unique within a stage (the same name may appear in another stage); no leading `__`, commas, double quotes, apostrophes, line breaks or NUL.
- No documented cap on journeys per experience.

## Configuring
- **Creator Hub:** Analytics → Journeys → Create, add stages and nodes, Next, Acknowledge; it gives a Luau snippet.
- **Open Cloud** (API key or OAuth; `universe:write` to draft, publish and restore, `universe:read` to read): the `JourneysConfig` repository at `/creator-configs-public-api/v1/configs/universes/<UNIVERSE_ID>/repositories/JourneysConfig`.
  - `PATCH /draft` changes only the journeys sent (`null` deletes one); `PUT /draft:overwrite` replaces the whole state and **deletes every journey left out**.
  - `POST /publish` with `deploymentStrategy` `Immediate` (what Creator Hub uses) or `GradualRollout` (15 minutes); it returns a `configVersion` and clears the draft. Publish messages never start with `_`, `RBX_` or `ROBLOX_`.
  - Each draft call returns a `draftHash`; sending a stale one fails with 400.
  - `GET` reads the published values, `GET /full` adds metadata, `GET /revisions` lists history, `POST /revisions/{revisionId}/restore` stages a revision without publishing it.
  - Shape: `entries` maps each journey name to `{"stages": [{"stage_index": 1, "nodes": [{"node_name": "..."}]}]}`; `stage_index` is unique and contiguous from 1 (0 is reserved). The API accepts one stage; Creator Hub needs two to save.

## Versions
- Each saved edit publishes a new configuration version. Players keep the version they acquired (progress is never migrated); each new session uses the version active when it began.
- Configurations are processed daily: of several published in one day, only the latest is used for that day's new users and sessions. Publish one version a day when each must be compared.
- Keep the journey name for ordinary edits and compare versions with the version filter; keep a node's name while its meaning holds. A new name only for a different system. The configuration version is Roblox's; the game's content version is yours, a field captured at entry.

## Reading it
- **Users view:** each player's first-time progression across sessions. **Sessions view:** each attempt on its own, for repeatable journeys such as store visits.
- Both show totals, final-stage reach, the biggest drop-off node and stage, a Sankey of node paths, a path breakdown and churn by node or stage. Filters: name, version, custom fields 1-3, age group, gender, payer, new user, OS and platform.
- The date range picks the acquisition cohort; its progress counts for 90 days after the range ends.

Docs: [journey events](https://create.roblox.com/docs/production/analytics/journey-events), [journeys in Open Cloud](https://create.roblox.com/docs/cloud/guides/journeys).
