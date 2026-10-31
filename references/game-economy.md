# Game economy, monetization and live ops

Companion to [game-design.md](game-design.md): load it when a design or a system touches currencies, pacing, odds, prices, offers or the update cadence. Its results go in the plan's Economy, Monetization and Live calendar sections ([assets/GAME_DESIGN_PLAN.md](../assets/GAME_DESIGN_PLAN.md)).

## Economy and pacing

- **Few currencies:** one soft (earned by the core loop, spent on power), one premium or rare (earned slowly, may be bought), and a material only when it enables a distinct decision (shards that evolve units). At most three on the HUD; each has sources, sinks, a place on screen and a reason.
- **Faucets and sinks**, tabled per phase with rates per minute. Sinks scale with income, or currency piles up; rich players get fantasy sinks (cosmetics, rerolls, fusions).
- **Offline earnings:** a share of the online rate (10-50%) up to a cap (2-12 h), paid with a welcome-back moment; online stays clearly better.
- **Trading makes the economy a market:** control supply (drop rates, limited items, untradeable starters), add item sinks (fusion consumes copies), keep trades atomic and server-side with a log, and block trading paid items where `IsPaidItemTradingAllowed` is false.
- **Chance arithmetic** for a 1-in-N tier at luck L: chance per roll L/N; half of players have it after about 0.69 N/L rolls, 90% after about 2.3 N/L; after N/L rolls 37% still have none, after 3 N/L 5%. Set target times on the median and the 90th percentile, not the mean. Pity at 2-3x the expected rolls rescues only the unluckiest 5-14% and removes the worst stories. Cap stacked luck (luck × server luck × weather × passes multiplies fast) so the top tier stays rare. The odds shown come from the same function and data the server rolls with.
- **Simulate, don't guess.** Copy [scripts/PacingSim.luau](../scripts/PacingSim.luau) to `tools/pacing/` beside a `model.luau` *(default)* and run it with Lune. Require the game's constants modules where they are pure data, so the plan and the game share one source of truth. Model a prestige as a `save` buy whose `buy` resets the run and adds the bonus, chance as `math.random` in `step`, real-time timers in `away`, and saving for a zone as a `save` buy that becomes available once it is a few minutes of income away. Run `simulate` with the cheapest and the value player (`simulateMany` when there is chance) and paste `report`, `curve` and `rngTable` into the plan. Re-run whenever the numbers change.

## Monetization

Products: game passes (permanent), developer products (repeatable), subscriptions, private servers, paid access, and rewarded video ads where the experience and player are eligible (`AdService`). Creator Rewards pay for engagement itself, so retention is revenue too.

- **Sell amplifiers of the fantasy:** luck, speed, extra slots, more income, cosmetics, VIP, server-wide boosts that make the buyer a hero. Never sell relief from friction added to be sold.
- **The free path finishes the game.** Every power item is reachable free, only slower; in PvP, paid power is capped and cosmetics carry the revenue.
- **Offer at the moment of desire, never in the way:** a full hotbar → more slots; a friend's aura → that cosmetic. No prompts during the core action or the tutorial, and a cap on unsolicited offers per session.
- **Price ladder:** a cheap starter pack of obvious value (the first purchase), impulse items, core passes, high-end items. Passes that stack multiply, so cap the stack.
- **Paid random items** ([policy](https://create.roblox.com/docs/production/monetization/paid-random-items)): anything random bought with Robux *or with currency Robux can buy* (rolls, eggs, spins, capsules, rerolls, random enhancements, fusions), plus the luck boosts and pity that change its odds. Before the spend, show every outcome's odds as percentages summing to 100% (a list behind a labeled button, not a bare (i)); explain boosts with numbers and keep the shown odds live while one is active; update odds when outcomes run out. When `PolicyService:GetPolicyInfoForPlayerAsync` reports `ArePaidRandomItemsRestricted`, give that player one of the policy's alternatives (a free earnable path, a fixed disclosed order, direct purchase) or hide or block the item. A game whose roll currency can be bought falls under this policy.
- **Receipts:** one `ProcessReceipt`, idempotent, granted only after the save succeeds ([coding.md](coding.md)).
- **Track the economy:** `AnalyticsService:LogEconomyEvent` for every source and sink (server only; up to five currencies on the dashboard) ([docs](https://create.roblox.com/docs/production/analytics/economy-events)).

## Live ops and content

- Plan the cadence from day one: an update every 1-2 weeks with an in-game countdown, an event each month, seasonal events, team-hosted live events (server-wide weather, bosses or luck the team triggers).
- **Content is data:** a hero, zone, item or event is a data row plus assets, not new code, so an update is mostly content. Estimate the cost of one content unit (model, data, effects) and fit the roadmap to the team.
- **Roadmap along the direction:** 6-12 weeks, each update a headline, its content and the one twist it adds.
- Limited-time power never disappears for good: events come back, and event currency rules are clear.
