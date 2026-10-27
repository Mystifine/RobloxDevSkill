#!/usr/bin/env sh
# Installs the roblox-dev skill with a single source of truth.
#
#   Global (default): base = $HOME.     --local [--project DIR]: base = the project folder (default: current directory).
#
#   1. If <base>/.agents exists          -> install to <base>/.agents/skills/roblox-dev
#      and, if <base>/.claude also exists -> symlink <base>/.claude/skills/roblox-dev to that folder (never a second copy).
#   2. Else if <base>/.claude exists     -> install to <base>/.claude/skills/roblox-dev.
#   3. Else                              -> create <base>/.agents/skills and install there.
#
# Global installs keep their git history (update by re-running). Local installs drop .git so the project can commit them.
# An existing install is updated, an existing foreign link is left untouched, and --force reinstalls a non-git copy.
set -eu

NAME=roblox-dev
REPO=${ROBLOX_DEV_REPO:-https://github.com/Mystifine/RobloxDevSkill.git}
LOCAL=0
FORCE=0
PROJECT=$(pwd)

while [ $# -gt 0 ]; do
	case "$1" in
	--local) LOCAL=1 ;;
	--force) FORCE=1 ;;
	--project)
		[ $# -ge 2 ] || { echo "--project needs a directory" >&2; exit 2; }
		PROJECT=$2
		shift
		;;
	*) echo "unknown option: $1" >&2; exit 2 ;;
	esac
	shift
done

command -v git >/dev/null 2>&1 || { echo "git is required." >&2; exit 1; }

if [ "$LOCAL" = 1 ]; then
	BASE=$(cd "$PROJECT" && pwd)
else
	BASE=${HOME:?HOME is not set}
fi
AGENTS=$BASE/.agents
CLAUDE=$BASE/.claude

if [ ! -d "$AGENTS" ] && [ -d "$CLAUDE" ]; then
	PRIMARY=$CLAUDE
else
	PRIMARY=$AGENTS
fi
TARGET=$PRIMARY/skills/$NAME

if [ -L "$TARGET" ]; then
	echo "Already installed: $TARGET is a link to $(readlink "$TARGET") (left untouched)."
elif [ -e "$TARGET" ]; then
	if [ -d "$TARGET/.git" ]; then
		git -C "$TARGET" pull --ff-only --quiet
		echo "Updated $TARGET"
	elif [ "$FORCE" = 1 ]; then
		rm -rf "$TARGET"
	else
		echo "$TARGET exists and is not a git checkout. Re-run with --force to replace it." >&2
		exit 1
	fi
fi
if [ ! -e "$TARGET" ] && [ ! -L "$TARGET" ]; then
	mkdir -p "$(dirname "$TARGET")"
	git clone --depth 1 --quiet "$REPO" "$TARGET"
	[ "$LOCAL" = 1 ] && rm -rf "$TARGET/.git"
	echo "Installed $TARGET"
fi

# Claude points at the single copy instead of holding its own.
if [ "$PRIMARY" = "$AGENTS" ] && [ -d "$CLAUDE" ]; then
	LINK=$CLAUDE/skills/$NAME
	if [ -L "$LINK" ] || [ -e "$LINK" ]; then
		if [ -L "$LINK" ] && [ "$(cd -P "$LINK" 2>/dev/null && pwd)" = "$(cd -P "$TARGET" && pwd)" ]; then
			echo "Claude link OK: $LINK"
		else
			echo "warning: $LINK already exists and does not point to $TARGET; left untouched." >&2
		fi
	else
		mkdir -p "$CLAUDE/skills"
		if [ "$LOCAL" = 1 ]; then
			SOURCE=../../.agents/skills/$NAME # relative, so the project stays movable
		else
			SOURCE=$TARGET
		fi
		ln -s "$SOURCE" "$LINK" || {
			echo "could not create the symlink $LINK (on Windows use install.ps1)." >&2
			exit 1
		}
		echo "Linked $LINK -> $TARGET"
	fi
fi
