# Developing the skill

## What the skill is for

It is meant to become the ultimate Roblox dev skill: one generic skill that inherits the skills, experience and good practices of professional developers shipping Roblox games, on the topics most Roblox projects share. Every game needs strong animations, readable UI on every device, effects that land, safe data, a fair economy, and testing that proves it all, so each lesson is learned and developed as part of its common topic, never as one game's feature. It keeps what works in production and the mistakes that cost real time, each with the sign that shows it, what to do instead and the numbers that proved it, so an agent on a similar task recognises the situation before it repeats the mistake. Every edit keeps that knowledge whole.

## Skill optimization

The goal: **every detail kept**, each task loading only what it needs, and every rule clear to an agent reading it cold. Optimizing changes where text lives and how it is worded, never what it says: no lossy compression of any kind. Keep the values and thresholds, names and APIs, the order of steps, the mistakes with their signs and fixes, the worked examples, and the evidence behind a rule with all its numbers. Only exact repetition and misplaced text go.

**What a task pays for:**
- `SKILL.md`: every task. It holds only the always-on rules (a line or two each), the route table and the scripts list.
- **A reference:** every task routed to it, for the whole file. Each line should serve most of those tasks.
- **A script:** only when it is read or run.
- **`README.md` and `INSTALL.md`:** never. They are for people and for developing the skill, so test records, history and this section live here, not in the references.

Characters / 4 is close enough to tokens. `tests/python/test_skill_shape.py` holds the budgets and fails CI over them: `SKILL.md` at 3,000 tokens, its description at 450 characters, a reference at 4,500 (`game-design.md`, read whole by design tasks, at 6,000, `ui.md` at 5,650, `modeling.md` at 5,000 and `vfx.md` at 4,850), and the total a typical task loads. It also fails on a broken link or anchor, and on a reference no route can reach.

**Budgets are alarms, not caps.** When CI fails on one, decide where the text belongs: move rare detail out of `SKILL.md`, give a part its own file (a sub-file its parent links to for the case that needs it, or a route row for a distinct task family), and name other skills only for the case that needs them. When the text belongs where it is, raise the budget to the new total rounded up to 50, with a comment saying why. Never cut knowledge to fit a number. The skill grew from 880 tokens in `SKILL.md` and 4,000 in references to 3,600 and 57,000 before these limits existed, with almost no repeated text: what cost tokens was what each task was made to load, so routing comes before raising. A skill outside this repository counts: one route cost 13,000 tokens that way. Folders are for people and save nothing.

**Rules:**
1. **Measure before and after.** Give the counts in the commit: `SKILL.md`, each reference changed, and what a typical route loads (`SKILL.md` plus its reference).
2. **One home per fact.** Each rule, value or process lives in the reference that owns its task. Anywhere else links to it (`[skins.md](references/rigs/skins.md)`) instead of restating it. A rule in `SKILL.md` keeps a one-line form there and its details in the reference, never the same text twice.
3. **Route narrowly.**
   - One reference per task family. Split a file when its routes mostly need only a part of it, giving each part its own route row, or a sub-file its parent links to when only that parent's tasks need it. Merge two files that always load together.
   - Within a file, what every task needs comes first; rare cases, edge cases and background come last.
   - Point to another reference only for the case that needs it ("when X, read Y"), never a general "see also".
   - Re-shape while you change: any edit, a quality update above all, is the time to split a category that has outgrown one file.
4. **Tighten words, never facts.** Drop restatements, hedges and filler, and prefer short list items to paragraphs, but keep every number, name, API, step order, failure signature, fix and worked example: an example with its own numbers or failure is evidence, not repetition. A second measurement of a rule is corroboration, so keep both.
5. **General rules, not one project's.** A rule names the class it covers (a held weapon, a card grid), never a project's item, and leaves a project's own requirements to its docs; the skill keeps what holds across games within the usual range. Leave out only a project's names, private ids and own requirements, and list what stayed out, with the reason, in the record.
6. **Write each lesson as experience:** the mistake an agent would make (what it did and how it went wrong), the sign that shows it (an error message, a number, how it looked) and what to do, with the numbers that proved the fix. "A shade inside the windows' ScreenGui left the top bar row bright behind a dark sheet; strips in a ScreenGui above it fixed it" teaches more than "shade every layer".
7. **Evidence keeps every number, with no date.** It is as short as its numbers allow: the observation that justifies a rule stays in the reference as plain statements with all their values. The story of how it was found goes in the commit or here, undated too. `tests/python/test_no_dates.py` fails on a date in a note.
8. **Clear to an agent reading it cold.** Each rule stands alone. Give every figure its unit and meaning (`40 degrees a frame`, not "40 a frame"), spell a formula out (`speed / 16 x 1.25`) instead of shorthand, and name the API, property and value as code.
9. **Scripts carry their own detail.** When a script enforces a rule, the reference says what to run and what its findings mean. The script's header documents its options and checks.
10. **Nothing that loads by itself.** Keep `CLAUDE.md`, `AGENTS.md` and similar files out of the skill folder: an agent may load them whenever it reads a file there, and every use would pay.
11. **Check that nothing was lost.** `python tests/facts_check.py <commit before the rewrite>` lists every number, backticked name and URL that vanished from the docs, and `python tests/facts_check.py --notes ID...` every one in a learning note's lessons that never reached the skill. Both look only for presence somewhere in the skill: a number used elsewhere passes, and plain words (a qualifier written without backticks) are never checked. So also read the diff line by line, and each lesson against the rule written from it: every removed or unwritten fact must exist in its home, be a true duplicate, or be named in the record as one project's own. Then run the checks and one real task with the skill loaded.

## Common mistakes when updating the skill

Each was made in an update and caught later:
- **Compressing evidence to save tokens:** turning notes into rules dropped measured outcomes ("3 of 3 dodged, 12 of 12 crit" became "fired as listed"), worked examples (a 7-long tile on a 3.2-wide beam), qualifiers (`AlphaMode` `Overlay`) and a metric's definition. A later pass restored 57 such details.
- **Units and constants shortened past meaning:** "about 35 a frame" for 35 degrees a frame; "scaled with height" for `Animate`'s normalized speed x 16 / 1.25 x the height scale.
- **A second measurement dropped as a duplicate:** a forge light cut from range 16 to 9 beside an existing rule's light cut from 16 to 10 is a second confirmation, not a copy.
- **Cutting to stay under a budget** where the budget should have risen or the file split.
- **Trusting `facts_check` alone:** it passes a number found anywhere and never sees plain words.
- **A note's agent missing a rule the skill already had:** fix the route or the wording, so the file that task loads points to it, never a second copy.
- **Stating a rule from the docs past what was measured:** a reference listing Model, Plugin, Mesh, Image and Audio did not stop `AssetService:CreateAssetAsync` from publishing animations. Write what was measured, and say where the docs differ.

## Quality updates

The maintainer's learning notes become changes to the skill through [quality-update.md](../references/learning/quality-update.md), under the rules above.
