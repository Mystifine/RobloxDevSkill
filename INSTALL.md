# Install, update or remove

The skill keeps one real copy, normally `~/.agents/skills/roblox-dev`, and gives Claude a link to it rather than a second copy. Every action below is one command, written so an AI agent can run it for its user.

## For AI agents

When a user gives you this repository's link and asks you to install, update, check or remove the skill:

1. **Pick the installer for the shell:** on Windows, PowerShell and `install.ps1`; on macOS, Linux or WSL, `install.sh`. Both need `git`.
2. **Download it to the temp folder and read it** before running it ([Commands](#commands)).
3. **Run the action asked for.** Install for the user (their home folder) unless they ask for this project only (`-Local` / `--local`).
4. **Ask the user first** before `-Force` / `--force` (it replaces or removes a folder the installer would otherwise leave alone), before `-Purge` / `--purge` (it deletes the learning notes and Codex handoff runs), and before discarding local changes when an update fails.
5. **Check and report:** run the status action, and give the user its lines with any warning the installer printed. Delete the downloaded installer.
6. **Tell the user to start a new agent session,** so the skill list shows the change.

Never copy the skill into another agent's folder by hand, and never delete what the installer reported as left untouched.

## Commands

Windows (PowerShell):

```powershell
$i = Join-Path $env:TEMP 'roblox-dev-install.ps1'
Invoke-RestMethod https://raw.githubusercontent.com/Mystifine/RobloxDevSkill/main/install/install.ps1 -OutFile $i
powershell -NoProfile -ExecutionPolicy Bypass -File $i              # install, or update an existing install
powershell -NoProfile -ExecutionPolicy Bypass -File $i -Update      # update only
powershell -NoProfile -ExecutionPolicy Bypass -File $i -Status      # where it is installed, and which version
powershell -NoProfile -ExecutionPolicy Bypass -File $i -Uninstall   # remove it
Remove-Item $i
```

macOS, Linux or WSL:

```sh
i="${TMPDIR:-/tmp}/roblox-dev-install.sh"
curl -fsSL https://raw.githubusercontent.com/Mystifine/RobloxDevSkill/main/install/install.sh -o "$i"
sh "$i"                 # install, or update an existing install
sh "$i" --update        # update only
sh "$i" --status        # where it is installed, and which version
sh "$i" --uninstall     # remove it
rm "$i"
```

| PowerShell | sh | Does |
|---|---|---|
| `-Local` | `--local` | acts on a project instead of the home folder: the current folder, or `-Project DIR` / `--project DIR` |
| `-Force` | `--force` | installs over, or removes, a folder at the skill's path that is not this skill (ask first) |
| `-Purge` | `--purge` | with uninstall, also deletes the learning notes and the Codex handoff state (ask first) |

`-ExecutionPolicy Bypass` applies to that one run only. Exit codes: 0 done, 1 failed (for status: not installed), 2 a wrong option.

## What each action does

### Install

The base folder is your home (global, the default) or the project (`-Local`). The skill goes where the base already keeps skills:

| In the base folder | The skill goes to | Claude |
|---|---|---|
| `.agents/` exists | `.agents/skills/roblox-dev` | if `.claude/` exists too, `.claude/skills/roblox-dev` becomes a link to it |
| only `.claude/` exists | `.claude/skills/roblox-dev` | it is the real copy |
| neither | `.agents/skills/roblox-dev`, creating the folders | none |

- A global install is a git checkout, so it can update itself. A local install drops `.git`, so the project can commit the skill.
- Installing over an existing install updates it.
- Claude's link is a junction on Windows (no special rights needed) and a symlink on macOS and Linux, relative inside a project.
- The repository's development-only `.mcp.json` is left out of every install (git sparse checkout); a link to a developer's full checkout still shows it.
- An existing `.claude/skills/roblox-dev` that is not already the right link is left untouched and reported.

### Update

Pulls the latest version into a global install (fast-forward only), or replaces a local copy with the latest, and prints the version before and after. It fails when the skill is not installed. When the install has local changes that block the pull, nothing changes: `git -C <install> status` shows them, and the user decides whether to discard them. An install that is itself a link (a developer's working checkout) is left alone: update that checkout with `git pull`.

### Status

Prints each place the skill is installed (`.agents/skills/roblox-dev`, `.claude/skills/roblox-dev`) and what it is: a git checkout at a commit and date, a copy without git history, or a link and what it points to. A folder there that is not this skill says so. Exits 1 when the skill is not installed.

### Uninstall

- Removes `.claude/skills/roblox-dev` and `.agents/skills/roblox-dev` when each is this skill (a folder whose `SKILL.md` is named `roblox-dev`) or a link to it. A link is removed on its own, so the folder it points to (a developer's checkout) is never touched.
- Leaves anything else at those paths untouched and says so; `-Force` / `--force` removes it anyway.
- Global only: takes the Codex handoff's permission rules out of Claude's `settings.json` ([Codex handoff](#optional-codex-handoff-claude-code)). That needs Node; without it, the installer names the two entries to delete by hand.
- Keeps the learning notes (`~/.roblox-dev/learning`) and the Codex handoff state (`~/.claude/codex-handoffs`, unfinished runs included) and prints where they are. `-Purge` / `--purge` deletes them; then `git worktree prune` in a repository clears any Codex worktree it still lists.
- Leaves the `skills` folders, and any other skill in them, in place.

## Manual steps (no installer)

Install, globally:

```sh
git clone --depth 1 --no-checkout https://github.com/Mystifine/RobloxDevSkill.git ~/.agents/skills/roblox-dev
git -C ~/.agents/skills/roblox-dev sparse-checkout set --no-cone '/*' '!/.mcp.json'
git -C ~/.agents/skills/roblox-dev checkout --quiet
mkdir -p ~/.claude/skills && ln -s ~/.agents/skills/roblox-dev ~/.claude/skills/roblox-dev   # only if ~/.claude exists
```

On Windows, link with `New-Item -ItemType Junction -Path "$HOME\.claude\skills\roblox-dev" -Target "$HOME\.agents\skills\roblox-dev"`. If `.agents` is absent but `.claude` exists, clone straight to `.claude/skills/roblox-dev` and skip the link. For a project install, use the project folder as the base and delete the clone's `.git`.

Update: `git -C ~/.agents/skills/roblox-dev pull --ff-only`.

Remove: the link first, on its own (`rm ~/.claude/skills/roblox-dev`; on Windows `cmd /c rmdir "%USERPROFILE%\.claude\skills\roblox-dev"`), then the folder (`rm -rf ~/.agents/skills/roblox-dev`). Never delete a link recursively: on Windows that can empty the folder it points to.

## Optional: Codex handoff (Claude Code)

To let Claude hand work to the Codex CLI, install and log in to Codex, then run the permission installer and the check, as the README's "Codex handoff" section shows. Skip it without Codex; the rest of the skill does not need it. Uninstalling the skill takes the permission rules out again (`node <skill>/scripts/codex/install.mjs --uninstall` does it alone).

## Optional: ffmpeg (watching video)

Watching a video reference or a recording ([video.md](references/art/video.md)) needs ffmpeg and Pillow. The agent asks before installing them; to do it yourself: `winget install --id Gyan.FFmpeg -e` on Windows, `brew install ffmpeg` on macOS or `sudo apt install ffmpeg` on Linux, then `pip install Pillow`.
