# Game design

For designing a new game, redesigning or auditing one, or adding a system that changes how a game plays, progresses or earns. The output is a local plan, `docs/game-design.md` *(default)*, written from [assets/GAME_DESIGN_PLAN.md](../assets/GAME_DESIGN_PLAN.md), never only a chat reply. Currencies, pacing, odds, prices, offers and update cadence are in [game-economy.md](game-economy.md); load it when the work touches them.

## Modes

| Mode | Do |
|---|---|
| **New game** | The whole process below, [game-economy.md](game-economy.md) and the whole template. |
| **Redesign or audit** | First rebuild the game as it is from its code and data (configs, services, saves, existing design notes, analytics if shared): its real loops, its pacing from the numbers (not the pitch), what works (keep it), what is thin. Then run the process on the gaps. The plan adds Today, What changes and Existing players. |
| **One system** | Read the plan (without one, the code's current loops). Name the pillar, loop and track the system serves and what it consumes and produces; a system that serves no pillar or feeds no loop is not built. Run the review rows it touches, then update the plan's sections and changelog. |

## The bar

A design is ready when all six hold (the review at the end checks each):

1. **Plays into one fantasy.** The player performs the fantasy with their own verbs and visibly grows into it.
2. **Targets one direction.** One primary kind of play (collect, build, fight, survive, express, explore) that every system feeds and every update extends. No side games.
3. **Simple to play.** One core verb, learnable in seconds without reading; systems arrive one at a time.
4. **Deep to master.** New kinds of decisions keep opening for weeks; skill and knowledge pay; nothing is solved by picking the biggest number.
5. **Long-term progression.** Several tracks on staggered cadences, simulated pacing, a prestige that adds new things, an endgame at launch.
6. **Engaging, fair fun.** The moment-to-moment feels good on its own; reasons to stay, return and bring friends are designed, not hoped for; monetization amplifies the fantasy and never sells relief from friction it added.

## Process

1. **Intake.** Read what exists (docs, `AGENTS.md`, configs, the code's loops) and the brief. Settle the fantasy seed or genre, audience and ages, platforms (phone first unless told otherwise), team size and art capacity, timeline, monetization stance, constraints (IP, saves to keep). Ask at most three blocking questions; otherwise assume, and list every assumption in the plan.
2. **Fantasy and direction:** the fantasy statement, three pillars, the direction and how it expands, the hook nobody else has, comparable games (what to take, what to avoid), 2-3 kinds of fun.
3. **Core verb and first ten minutes:** the verb, its feel (toy test) and a minute-by-minute first session.
4. **Loop stack:** moment, core, session, meta, social and live loops, each reward feeding the next.
5. **Progression:** tracks, unlock schedule, pacing targets, prestige, endgame, catch-up.
6. **Depth:** layers of decisions with the time each opens, the meaningful-choice test, skill and knowledge ceilings, how systems interact.
7. **Engagement:** first-session beats, session, return and social hooks, the first eight weeks of live content.
8. **Economy:** currencies, faucets and sinks, curves; simulate with [PacingSim](../scripts/PacingSim.luau) and adjust until the pacing targets hold ([game-economy.md](game-economy.md)).
9. **Monetization:** offers mapped to the fantasy, prices, when offers appear, compliance ([game-economy.md](game-economy.md)).
10. **Production:** systems mapped to code, data and save fields; launch content counts; a vertical slice; a build order with a measurement per step; a roadmap along the direction.
11. **Metrics:** KPIs with targets, funnels (onboarding, then one post-tutorial funnel per progression feature: [onboarding.md](onboarding.md)), economy events, experiments, pivot criteria.
12. **Review and write:** score the review table, fix every failing row or record why it stays, then write the plan and reply (Writing the plan, below).

## Fantasy

- **Statement:** "You are a ___ who ___ to become ___." A role and a verb the player performs, not a theme: "a diver who hauls treasure from ever deeper wrecks to become a legend of the sea," not "ocean treasure."
- **Grow into it.** Start humble, end legendary, and let others see every step: a bigger base, a rarer crew, a louder aura, a title. Rewards are fantasy objects first and numbers second.
- **Fantasy map.** Every system names the fantasy beat it delivers. A chore with no beat (walking every load to a sell pad so an auto-sell pass has something to remove) is cut or given one (a trader who pays more for rarer finds).
- **Every layer keeps the promise:** title, icon and thumbnail, then the first 30 seconds, the core verb, rewards, status, offers.
- **Thumbnail test.** The most exciting moment fits one image and a few words. If no moment deserves the thumbnail, design one. Home recommendations need a custom thumbnail that truthfully shows the game.
- **Own the hook.** Borrowed or look-alike IP brings players in but is not a brand and carries takedown risk. Give the game something it owns: a mascot, a mechanic, a world.
- **Kinds of fun:** pick 2-3 primary ones (sensation, fantasy, narrative, challenge, fellowship, discovery, expression, submission) and derive mechanics from them, not the reverse.

## Direction

- Name the **direction** in one word and its **expansion axis**, what "more" means: "collect: rarer heroes, more forms, more mutations"; "build: bigger plots, new buildings, production chains."
- Every system consumes or produces something on the axis (weather → mutations → index → luck → rolls). An isolated system is a minigame: fewer, interlocking systems beat many shallow ones.
- Updates extend the axis with a twist (a new rule, enemy behavior or resource interaction), never only a reskin with bigger numbers.

## Simple to play

- **One core verb, one input:** tap or hold on a phone, one key, one gamepad button. Learnable in under ten seconds without text; everything else layers on it.
- **Toy test.** The verb is satisfying with no goal attached: instant feedback (about 100 ms), sound, particles, numbers, camera kick, scaled to the result (a crit, a rare or a break gets more).
- **Progressive disclosure.** Start with the verb, one reward and one upgrade. Unlock each system when the player needs it (by progress, not a timer), each with a one-step pointer ([onboarding.md](onboarding.md)). The HUD starts minimal and grows.
- **No busywork.** Auto-equip the best, auto-target, bulk actions, sensible defaults: attention goes to choices, not menu management. Never add a chore to sell its removal.
- **Readable at a glance.** One rarity color language everywhere (the genre's usual ladder runs grey, green, blue, purple, gold, red, rainbow) with a second cue (shape, icon, effect) for color-blind players and small screens; numbers in short form (1.2K, 3.4M) everywhere.
- **Failure is cheap.** Short loops, instant retry, temporary setbacks (stun, knockback, a slower minute). Permanent loss only when risk is the fantasy, opt-in and clearly signposted.

## Depth

Depth is how many kinds of meaningful decisions and skills open up over time, not how many systems exist.

| Source | The player decides or masters | Fits |
|---|---|---|
| Composition and synergy | team roles, type matchups, set bonuses, traits | collection, TD, combat |
| Allocation and timing | what to upgrade first, when to prestige, spend or save, when to fire a boost (stacked with weather or an event) | sims, tycoons, RNG |
| Risk and reward | push deeper or bank, safe or risky upgrade, PvP zones | survival, extraction, stealing |
| Execution | timing windows, weak points, aim, routes, dodges | action, obby, combat |
| Knowledge and discovery | hidden recipes, secret tiers, condition combos (weather × place × time), boss patterns | all; fuels videos, wikis and chat |
| Space | placement, layout, routing | TD, tycoon, builder |
| Market and society | trade values, co-op roles, group strategy | trading games |

- Pick 2-3 primary sources that fit the direction and say where each lives in the plan.
- **Meaningful-choice test:** a choice is real only if reasonable players pick differently by situation, goal or style. A dominant option is no choice: merge it, cut it, or give the others a niche. "Highest damage per slot" is no decision.
- **Layer it.** Each layer adds a new *kind* of decision and opens once the last is understood: the verb (minute 0), a first build choice (about 10 min), synergy (about an hour), prestige timing and optimization (days 1-3), mastery, min-maxing or the market (week 1 on) *(start)*.
- **Bigger numbers are length, not depth.** A tier that only multiplies stats adds hours, not decisions; each major tier also changes a rule.
- **Skill pays, idle stays valid.** Plan the factor by which active play beats idle (say 2-3x) and keep idle progress real. Skilled players climb faster; nobody has to be skilled.
- **Measure allocation depth:** simulate the casual player (`cheapest`) and the optimizer (`value`) with PacingSim ([game-economy.md](game-economy.md)). No gap means allocation choices do not matter; a huge one punishes casual players. Aim for a noticeable but forgiving gap (1.2-2x as a start).
- Keep secrets for discovery, never for purchases: odds and prices are always shown.

## Loops

| Loop | Time | Answers | Must deliver |
|---|---|---|---|
| Moment | 1-10 s | Does doing this feel good? | feedback on every action |
| Core | 30 s - 3 min | What do I do? | act → reward → upgrade → act stronger |
| Session | 10-30 min | Why play now? | a goal reachable this session and a hook to return |
| Meta | days - weeks | Why come back? | tracks: prestige, collection, zones, mastery |
| Social | any | Why with others? | co-op, trade, show off, compete |
| Live | weekly | What's new? | updates, events, limited content |

- Each loop's reward is the next loop's input; a reward that feeds nothing is cut. Draw the stack in the plan.
- **Three goals always in view:** one about 2 minutes away (a HUD progress bar), one for this session, one long-term (a menu away).
- **Rhythm:** something notable (an unlock, an event, a big reward) every 5-10 minutes; calm stretches broken by spikes.

## Long-term progression

- **4-6 tracks of different kinds and cadences**, so one is always nearly done: power (upgrades, levels, gear), collection (index, variants, sets), world (zones, tiers), prestige (rebirth for a permanent bonus and new content), mastery (per-item mastery, achievements, records), status (titles, auras, boards, cosmetics).
- **Pacing targets for the median player**, in active play *(start; tune per genre)*: first action within 20 s, first reward within 30 s, first upgrade within 1 min, a second system by 3-5 min, the fantasy's big moment by 10 min (a rare reveal, a break, a transformation; scripted if needed), the first session ending at 15-25 min with something in progress, the first prestige or tier change within 1-3 sessions, a layer of depth still closed on day 7, the endgame for engaged free players in 3-8 weeks, an endless layer after it.
- **Curves.** Costs grow geometrically (about 1.07-1.15 per level for frequent small upgrades, 2-10x per tier for zones and big unlocks) while income grows through upgrades and milestone multipliers, so the time to the next goal rises slowly until a prestige resets it. Write the formulas in the plan and simulate them ([game-economy.md](game-economy.md)).
- **Slow, never stop.** Where progress slows, open another track (collection, quests, an event), never a wall only Robux opens.
- **Prestige** unlocks when a run slows past the session target. The climb after it is clearly faster (2-3x or more). It grants a permanent bonus *and* something new (a zone, a mechanic, a cosmetic), shows a preview ("Rebirth for x2.5: back to Zone 3 in about 6 min"), and pays a diminishing function of the run (square root or log of lifetime earnings) so that timing it is a decision.
- **Endgame at launch:** an endless mode (infinite floors, waves or tiers), rare variants to complete, weekly-reset boards newcomers can win, mastery cosmetics, trading. Everything that ends hands over to a track that does not.
- **Catch-up:** friend boosts and new-player multipliers let a late friend play beside a veteran.
- **Numbers and saves.** Luau numbers are doubles: integers are exact up to 2^53 (about 9.0e15) and overflow to inf past about 1.8e308. Plan the top of the curve now: past 9e15 exact counts break (display is fine); past 1e308 use a mantissa-exponent number from day one. Never save NaN or inf. Save shapes change only through the project's schema and migrations ([coding.md](coding.md)).

## Engagement and retention

Roblox's Recommended for You weighs most the play-through rate (plays per impression), first-play bounce (leaving after a short first session), play days per user (D1, D2-7, D8-28) and playtime per user (counted up to 60 minutes per user per game per day); then intentional co-play days, qualified play sessions, spend days and Robux per user ([Discovery](https://create.roblox.com/docs/discovery), checked 2026-10-28). Creator Rewards (since 2025-07-24) pay a flat amount per active spender who plays 10 minutes in a day, but only in the first three experiences that player launches that day, plus a revenue share on new or returning users who arrive by link or by searching the game's name ([announcement](https://devforum.roblox.com/t/introducing-creator-rewards-earn-more-by-growing-the-community/3777628); terms may change). So:

- **Win the first minutes:** action within 20 s, a reward at once, the big moment within 10 min; tutorials per [onboarding.md](onboarding.md).
- **More days, not longer days:** a satisfying daily session of 10-60 minutes and a reason to return tomorrow beat marathon sessions.
- **Be one of the first launches of the day:** a daily reward or a timer that finished overnight.
- **Session hooks:** goals that finish within the session, quest chains, in-session streaks, a server event every 10-15 minutes ("Meteor Shower in 2:00").
- **End on a hook, not a wall:** something growing, hatching or accruing while away (capped offline earnings), and the next session's first goal in view.
- **Return hooks:** daily rewards with a forgiving streak, daily and weekly quests, a rotating shop, timed events, updates with an in-game countdown, real-time timers, group rewards, and experience notifications: 13+ only, opt-in through `ExperienceNotificationService:PromptOptIn`, at most one a day, personal and actionable, never false urgency, never required to progress ([docs](https://create.roblox.com/docs/production/promotion/experience-notifications)).
- **Variable rewards, honestly.** Odds on every roll, pity for the tiers players chase, reveals skippable after the first few, no fake near misses, shown odds equal to real ones, no scripted outcome after the onboarding gift.
- **Respect the player:** no energy systems that stop play, no punishment for logging off, limited-time content returns in rotation, no pressure tactics aimed at children.

## Social and multiplayer

- **Solo works, friends are better:** a reason to play together (friend boost, co-op events, helping that the game pays for), invites (`SocialService:PromptGameInvite`), and catch-up so mixed levels can play together. Co-play days count toward recommendations, and new players who arrive by link or search earn Creator Rewards (above).
- **Visible status:** others see progress in the shared space: base, crew, auras, titles, rare-pull banners.
- **A shared moment each session:** a world boss, a server-wide event, an announcement everyone benefits from.
- **Choose interactions deliberately:** parallel play, co-op, helping, trading, competition, conflict. Conflict (stealing, raiding, PvP) drives engagement but needs protection windows and limited, recoverable losses, and is opt-in where the audience is young.
- **Works without chat:** many players can't text-chat, so social systems need pings, emotes, quick chat and trade windows. Text players write for others (names, signs) goes through `TextService` filtering.
- **Server size:** plot games have one plot per player slot (6-12 is typical; hubs 20-50). Decide whether server hopping is embraced (server events) or neutralized (personal RNG).

## Roblox realities

- **Phone first:** touch, small screens, low-end hardware, short sessions on the go; then gamepad and desktop ([ui.md](ui.md)).
- **Wide ages, many young players:** play needs no reading; icons, numbers and color carry meaning; text is short and translatable. Characters follow [characters.md](characters.md).
- **Within the maturity label:** design to the label the project declares (Minimal when unknown; only Minimal and Mild reach Roblox Kids). Hits, defeats, monsters and horror default to the stylized effects in [no-gore.md](no-gore.md), and every new asset passes its upload rules; action, scares and Halloween stay.
- **No pause, transient servers:** players drop in and out at any moment; progress persists per player.
- **Fast exits:** a slow load or an empty first minute is a bounce. Unit counts, effects and plot sizes in the design must fit a low-end phone.
- **Never:** gambling, off-platform trades, unfiltered player text.

## Genre patterns

| Genre | Fantasy | Core loop | Long tracks | Depth | Traps |
|---|---|---|---|---|---|
| Simulator | grow absurdly strong or rich | act → collect → sell → upgrade → new zone | zones, pets, rebirths, index | team optimization, rebirth timing, enchants | number inflation only; chores |
| Tycoon | own and grow a business | earn → buy buildings → base grows | completion, rebirth, decor | layout, product mix | buy-every-button with no choice |
| RNG / collection | find the one-in-a-million | roll → reveal → keep, equip or sell → luck | index, luck, auras, crafting | luck timing with weather, crafting, sets | no decision beyond rolling; luck inflation; odds rules |
| Tower defense | command a legendary army | summon → place and upgrade through waves → rewards | roster, traits, evolutions, modes, endless | placement, synergy, in-match economy | power creep voiding collections; paid power |
| Obby | conquer the impossible climb | attempt → fail → retry → checkpoint | stages, tiers, badges, times | routes, tricks, speedruns | unfair spikes; skips as the only offer |
| Co-op horror / survival runs | survive together | run → learn threats → escape or die → unlock | meta unlocks, floors, achievements | threat knowledge, roles, resources | runs too long for phones; dull solo |
| Roleplay / life | live another life with friends | pick a role → play together → customize | homes, vehicles, pets | expression, creativity | nothing for a solo player to do |
| Battlegrounds / combat | be the fighter | fight → earn → unlock moves or characters | roster, mastery, ranks | execution, combos, matchups | balance, toxicity, paid power |
| Growth / idle | grow something precious | plant or place → real time passes → harvest → better seeds | rarities, mutations, plot size | timing around weather and events, mutation stacking, market | waiting with nothing to do; dupes, inflation |
| Fishing / hunting | catch the legendary | cast → minigame → catch → sell or log → better gear | bestiary, gear, places | conditions (time, weather, place) × gear, minigame skill | minigame fatigue |

## Review

Score each row 0-2 in the plan (0 missing, 1 present but generic, 2 concrete with numbers). The plan is finished only with no 0s; every 1 goes to open questions.

| Check | 2 means |
|---|---|
| Fantasy | one sentence; every system has a beat; a thumbnail moment exists |
| Direction | one direction; every system feeds it; the roadmap extends it |
| First minutes | action within 20 s, reward within 30 s, big moment within 10 min |
| Simple | one-input verb; at most 3 HUD currencies; systems unlock one at a time |
| Depth | 3+ kinds of decision across 3+ layers; no dominant option; active beats idle by a planned factor |
| Progression | 4+ tracks; pacing table from simulation; prestige adds something new; endgame at launch |
| Goals | a 2-minute, a session and a long-term goal always in view |
| Engagement | session, return and social hooks, each concrete |
| Social | a reason to play with friends; visible status; a shared moment each session |
| Economy | faucets and sinks listed; sinks scale; number range planned |
| Monetization | amplifies the fantasy; free path finishes; paid random items compliant; no chore for sale |
| Platform | phone-first controls and HUD; low-end budget; little text; within its maturity label, stylized hits and defeats |
| Live ops | content as data; 6-12 week roadmap; event framework |
| Feasibility | small vertical slice; a measurement per build step; content counts fit the team |

**Red flags:** a chore sold back as a pass; numbers as the only progression; a system that feeds nothing; menus before play; text tutorials; energy timers; hard paywalls; paid power in PvP; fake scarcity or countdowns; hidden or misleading odds; permanent loss for young players; content beyond the maturity label; reskin-only updates; no endgame; PC-first controls; borrowed IP as the only hook; unbounded multiplier stacks; a prestige that only multiplies.

## Writing the plan

- **Where:** `docs/game-design.md` *(default)*, from [assets/GAME_DESIGN_PLAN.md](../assets/GAME_DESIGN_PLAN.md); a redesign keeps the template's Today, What changes and Existing players sections. If a plan exists, update it and add a changelog line; never start a second plan. Read earlier idea notes and absorb or link them.
- **What it explains**, to someone who never played: how the game is played, the fantasy and how each system feeds it, how players progress, where the depth is, where the engagement comes from, how it earns, what ships first.
- **Specific beats general:** names, numbers, times and places everywhere. Not "players enjoy collecting" but "a Mythic (1 in 25,000, 48 h of rolling for the median player at 6 rolls a minute) plays a 5 s cutscene and a server banner."
- Numbers stay *(start)* until play-tested; formulas and simulation output sit beside the tables they produce.
- Diagrams (loop stack, unlock timeline) in Mermaid or ASCII; a phone HUD sketch in ASCII.
- Then reply in chat with the pitch, the three biggest decisions, the open questions and the plan's path.
