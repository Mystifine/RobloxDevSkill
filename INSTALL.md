# Install

One real copy, many pointers. The skill lives in `.agents/skills/roblox-dev`; Claude, if present, gets a link to it rather than a second copy, so there is a single source of truth.

## Placement rule

Pick a base: your home folder (**global**, default) or the project folder (**local**, only if the user asks).

| In the base folder | Install the skill to | Claude |
|---|---|---|
| `.agents/` exists | `.agents/skills/roblox-dev` | if `.claude/` exists, link `.claude/skills/roblox-dev` to it |
| only `.claude/` exists | `.claude/skills/roblox-dev` | it is the real copy |
| neither | create `.agents/skills`, install there | none |

Never overwrite an existing `.claude/skills/roblox-dev` that is not already the right link; report it instead.

## Scripts (recommended)

They apply the rule above, update an existing install, and refuse to clobber foreign content. Needs `git`.

Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/Mystifine/RobloxDevSkill/main/install/install.ps1 -OutFile install.ps1
./install.ps1            # global
./install.ps1 -Local     # into the current project instead
```

macOS / Linux:

```sh
curl -fsSLO https://raw.githubusercontent.com/Mystifine/RobloxDevSkill/main/install/install.sh
sh install.sh            # global
sh install.sh --local    # into the current project instead
```

Options: `-Project <dir>` / `--project <dir>` (local target, default: current folder), `-Force` / `--force` (replace a non-git copy). Read a script before running it.

- **Global** installs keep their git history; re-run the script to update.
- **Local** installs drop `.git` so the project can commit the skill; re-run with `-Force` / `--force` to refresh it (without it the script stops rather than replace the copy). Claude's link in a local install is relative on macOS/Linux and a junction on Windows.
- On Windows use the `.ps1` (junctions need no special rights; symlinks do). `install.sh` is for macOS/Linux/WSL.

## Manual steps (what an agent without the scripts should do)

```sh
git clone --depth 1 https://github.com/Mystifine/RobloxDevSkill.git <base>/.agents/skills/roblox-dev
# then, only if <base>/.claude exists:
mkdir -p <base>/.claude/skills
ln -s <base>/.agents/skills/roblox-dev <base>/.claude/skills/roblox-dev          # Windows: New-Item -ItemType Junction -Path ... -Target ...
```

If `.agents` is absent but `.claude` exists, clone straight to `<base>/.claude/skills/roblox-dev` and skip the link. For a local install remove the clone's `.git` folder.

## Optional: Codex handoff (Claude Code)

To let Claude hand work to the Codex CLI, install and log in to Codex, then run the permission installer and the check, as the README's "Codex handoff" section shows. Skip it without Codex; the rest of the skill does not need it.

## Verify

`<base>/.claude/skills/roblox-dev/SKILL.md` and `<base>/.agents/skills/roblox-dev/SKILL.md` should both open, and only the `.agents` one should be a real directory. Start a new agent session so the skill list refreshes.
