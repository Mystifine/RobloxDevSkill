# Developing the skill

## Skill optimization

The goal: fewer tokens each time the skill is used, with every detail kept. Keep the values and thresholds, names and APIs, the order of steps, the failure signs and their fixes, and the evidence behind a rule. Repetition and misplaced text go; knowledge stays.

**What a task pays for:**
- `SKILL.md`: every task. It holds only the always-on rules (a line or two each), the route table and the scripts list.
- **A reference:** every task routed to it, for the whole file. Each line should serve most of those tasks.
- **A script:** only when it is read or run.
- **`README.md` and `INSTALL.md`:** never. They are for people and for developing the skill, so test records, history and this section live here, not in the references.

Characters / 4 is close enough to tokens. `tests/python/test_skill_shape.py` holds the budgets and fails CI over them: `SKILL.md` at 2,200 tokens, its description at 450 characters, a reference at 4,500 (`game-design.md`, read whole by design tasks, at 6,000, and `ui.md` at 5,200), and the total a typical task loads. It also fails on a broken link or anchor, and on a reference no route can reach.

The skill grew from 880 tokens in `SKILL.md` and 4,000 in references to 3,600 and 57,000 before these limits existed, with almost no repeated text: what cost tokens was what each task was made to load. So, in order: move rare detail out of `SKILL.md`, split a file whose routes need only part of it, and name other skills only for the case that needs them. A skill outside this repository counts: one route cost 13,000 tokens that way. Folders are for people and save nothing.

**Rules:**
1. **Measure before and after.** Give the counts in the commit: `SKILL.md`, each reference changed, and what a typical route loads (`SKILL.md` plus its reference).
2. **One home per fact.** Each rule, value or process lives in the reference that owns its task. Anywhere else links to it (`[skins.md](references/rigs/skins.md)`) instead of restating it. A rule in `SKILL.md` keeps a one-line form there and its details in the reference, never the same text twice.
3. **Route narrowly.**
   - One reference per task family. Split a file when its routes mostly need only a part of it, giving each part its own route row. Merge two files that always load together.
   - Within a file, what every task needs comes first; rare cases, edge cases and background come last.
   - Point to another reference only for the case that needs it ("when X, read Y"), never a general "see also".
4. **Cut words, not facts.** Drop restatements, hedges, filler and examples that only repeat the rule; prefer short list items to paragraphs. Keep every number, name, API, step order, failure signature and fix.
5. **Evidence in one sentence, with no date.** An observation that justifies a rule stays in the reference as a plain statement. The story of how it was found goes in the commit or here, undated too. `tests/python/test_no_dates.py` fails on a date in a note.
6. **Scripts carry their own detail.** When a script enforces a rule, the reference says what to run and what its findings mean. The script's header documents its options and checks.
7. **Nothing that loads by itself.** Keep `CLAUDE.md`, `AGENTS.md` and similar files out of the skill folder: an agent may load them whenever it reads a file there, and every use would pay.
8. **Check that nothing was lost.** `python tests/facts_check.py <commit before the rewrite>` lists every number, backticked name and URL that vanished from the docs. Read the diff line by line too: every removed fact must still exist in its home, or be a true duplicate. Then run the checks and one real task with the skill loaded.

## Quality updates

The maintainer's learning notes become changes to the skill through [quality-update.md](../references/learning/quality-update.md), under the rules above.
