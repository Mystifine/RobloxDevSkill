# Learning notes

`learn.py check` sent you here: this machine keeps notes on what using the skill teaches, for a later quality update. They stay on this machine, and nothing loads them or acts on them until then.

## What earns a note

One note at the end of a task, holding all its lessons, and only if a lesson is one of these kinds:

| Kind | What happened |
|---|---|
| `preference` | The user said how they want something done, or turned down a result the skill allows |
| `correction` | The user had to correct the result or the approach |
| `skill-wrong` | A rule, value or script in the skill proved wrong or out of date |
| `skill-gap` | The task needed knowledge or a script the skill lacks |
| `routing` | The route loaded the wrong files, or the user's wording missed the route |
| `platform-fact` | Testing showed how Roblox, Blender or a tool really behaves |
| `technique` | An approach worked after the obvious one failed, and would work elsewhere |

Write nothing for a routine success, a fact true of this project alone (it goes in the project's docs), or a guess. A Codex handoff run records nothing; the agent reviewing it does.

## The note

Write it to a temporary file outside the project, in UTF-8. The script adds `id`, `date`, `skill_commit`, `tasks` and `kinds`. Keep prompts verbatim: how the user words a request decides whether a route finds it. Leave out secrets, and describe project code rather than pasting more than a few lines.

```markdown
---
title: What was learned, in under 70 characters
agent: your model's name
project: the project's folder name
references: [ui/ui.md, ui/topbar.md]
outcome: corrected
rounds: 2
---

## Prompt
> The user's first request, verbatim. Then each later message that changed the task, quoted the same way.

## Attachments
What each attachment showed, in words, or None. Name any file passed with --attach, such as concept.png.

## Wanted
What the user was really after, in a sentence or two, including what they never said but reacted to.

## Output
What was delivered (files, assets, commands, not the code), what was checked and how it came out, what was not checked.

## Response
The user's reaction, verbatim where the wording matters, or None.

## Lessons

### The rule, as one imperative sentence
- Kind: correction
- Basis: stated
- Evidence: What happened, in a sentence or two.
- Change: references/ui/topbar.md: what to add or change, or none yet.
```

- `references`: those you read, as the route names them; `[]` if none fit.
- `outcome`: `accepted`, `corrected`, `rejected`, `abandoned` or `unknown`.
- `rounds`: how many times the user sent the work back.
- `Basis`: `stated` by the user, `measured` by testing, or `inferred` by you.
- `Change`: start with the file's path when you can name one, since the digest groups lessons by it.

## Recording

```sh
python scripts/learn.py record NOTE.md [--attach FILE]...
```

- **Exit 0:** kept. Say so in one line.
- **Exit 2:** refused. It lists everything to fix. Fix the note and run it again.

Attach a file only when you have its path and the words above would not be enough. A lesson is no reason to change the skill now: that waits for the quality update, unless the user asks for it as its own task.
