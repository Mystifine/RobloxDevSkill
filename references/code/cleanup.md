# Cleaning up a project

Removing what the shipped game no longer uses: retired systems, a template's leftovers, code kept only for old saves, status logs that grew by appending, and pipeline files. Code rules: [coding.md](coding.md).

## Retiring a system

**When a project outgrows a template, or a feature is retired, delete the system end to end; never leave it flagged off** *(default)*. A template's switched-off systems kept running or kept being maintained: a per-world flag false in every world (`gameplayEnabled = false`), five services still bootstrapped every start, a tutorial controller that returned at once because of the flag, shop passes hidden by a `legacy` flag, 7 of 35 integration specs reporting "skipped: template system disabled", 13 unit specs testing formulas nothing used, 27 of 44 economy config keys with no reader, reward-formula inputs fixed at neutral values (rebirths 0, unused relic and event multipliers), and state-sync fields, HUD bindings, client remotes, sound cues and icons for the dead systems.
- **Signs that find them:** a flag that is off everywhere, specs that skip, config entries hidden by a flag, comments like "kept for saves" or "template", and per-key reader counts (`grep -c "Config.Key"` across the source: 0 means dead).
- **Order:** the composition root's list; then every reference, by grep; then lint, whose unused-variable warnings caught four leftovers; then the specs. Unit specs went from 86 to 73, all passing; integration from 28 passed and 7 skipped to 26 passed and 0 skipped.
- **Save code goes too before launch:** an unreleased game keeps no migration or reconciliation for old states, and what stays is validation ([coding.md](coding.md#data)); one `grant` per product ([monetization.md](../design/monetization.md#purchases)).
- **A pre-launch clean slate is one store version, not code:** asked to start every save over before launch, a load path already validation-only, apart from an unread schema version, two dead template fields and a rebuild of an overhead tag for an older build, needed no new code. One version suffix on every store name (profiles, ordered boards, the gift inbox, stock counts), the testers' QA switches left alone, emptied everything without touching the old stores.

## The project's docs

**Status docs hold the current state: replace, never append** *(default)*. Round-by-round entries had grown a test-results log to 127 KB, assumptions to 61 KB, tooling notes to 50 KB and known issues to 43 KB, beside a separate implementation-status log; superseded entries sat next to current ones, resolved issues stayed listed, and the owner found them piling up. Rewritten as current state, 376 KB became 86 KB: Another owner asked for the same clean slate outright: no dated data or references in any Markdown, only facts about what the game is now, and no working from historical material.
- **Test results:** a short baseline table, what the specs cover and what was not covered, replaced on each run.
- **Known issues:** open ones only, grouped by owner actions, balance, technical limits and unverified; an issue goes once it is fixed.
- **Assumptions:** the decisions in force, grouped by system; a decision goes once it is superseded.
- **Tooling:** a workflow reference, not session logs. No separate status log.

Write the rule into the project's `AGENTS.md`: replace the test baseline, and remove an issue or a decision once it is fixed or superseded.

## Files

Pipeline intermediates once the uploads are recorded: [uploading.md](../safety/uploading.md). Review renders, captures and audits never sit beside the assets ([SKILL.md](../../SKILL.md), Efficient execution).
