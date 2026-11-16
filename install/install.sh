#!/usr/bin/env sh
# Installs, updates, checks or removes the roblox-dev skill, keeping a single source of truth. INSTALL.md has the steps.
#
#   sh install.sh               install, or update an existing install
#   sh install.sh --update      update an existing install (fails when there is none)
#   sh install.sh --status      where it is installed and at which version (exit 1 when it is not)
#   sh install.sh --uninstall   remove it and Claude's link to it; --purge also deletes its learning notes and Codex handoff state
#
#   Global (default): base = $HOME.     --local [--project DIR]: base = the project folder (default: current directory).
#
#   1. If <base>/.agents exists          -> install to <base>/.agents/skills/roblox-dev
#      and, if <base>/.claude also exists -> symlink <base>/.claude/skills/roblox-dev to that folder (never a second copy).
#   2. Else if <base>/.claude exists     -> install to <base>/.claude/skills/roblox-dev.
#   3. Else                              -> create <base>/.agents/skills and install there.
#
# Global installs keep their git history (update by re-running). Local installs drop .git so the project can commit them;
# --update replaces such a copy. Installed checkouts exclude the repository's development-only .mcp.json.
# An existing install is updated, an existing foreign link is left untouched, and --force reinstalls a non-git copy.
# --uninstall removes only this skill: a folder whose SKILL.md is named roblox-dev, or a link to one, which goes alone and
# never takes the folder it points to. A global uninstall also takes the Codex handoff's permission rules out of Claude's
# settings (with Node), and keeps the learning notes and Codex handoff state unless --purge. --force removes anything
# else found at the skill's two paths.
set -eu

NAME=roblox-dev
REPO=${ROBLOX_DEV_REPO:-https://github.com/Mystifine/RobloxDevSkill.git}
LOCAL=0
FORCE=0
PURGE=0
ACTION=install
PROJECT=$(pwd)

while [ $# -gt 0 ]; do
	case "$1" in
	--local) LOCAL=1 ;;
	--force) FORCE=1 ;;
	--purge) PURGE=1 ;;
	--update | --uninstall | --status)
		[ "$ACTION" = install ] || { echo "use one of --update, --uninstall and --status" >&2; exit 2; }
		ACTION=${1#--}
		;;
	--project)
		[ $# -ge 2 ] || { echo "--project needs a directory" >&2; exit 2; }
		PROJECT=$2
		shift
		;;
	*) echo "unknown option: $1" >&2; exit 2 ;;
	esac
	shift
done
[ "$PURGE" = 0 ] || [ "$ACTION" = uninstall ] || { echo "--purge goes with --uninstall" >&2; exit 2; }

if [ "$LOCAL" = 1 ]; then
	BASE=$(cd "$PROJECT" && pwd)
else
	BASE=${HOME:?HOME is not set}
fi
AGENTS=$BASE/.agents
CLAUDE=$BASE/.claude
AGENTS_SKILL=$AGENTS/skills/$NAME
CLAUDE_SKILL=$CLAUDE/skills/$NAME

exists() { [ -e "$1" ] || [ -L "$1" ]; }
# This skill, not another one: its SKILL.md is named roblox-dev.
is_skill() { [ -f "$1/SKILL.md" ] && grep -q '^name:[[:space:]]*roblox-dev[[:space:]]*$' "$1/SKILL.md"; }
version() { command -v git >/dev/null 2>&1 && git -C "$1" log -1 --format='%h %cs' 2>/dev/null || true; }
same_dir() { [ "$(cd -P "$1" 2>/dev/null && pwd)" = "$(cd -P "$2" 2>/dev/null && pwd)" ]; }

if [ "$ACTION" = status ]; then
	FOUND=0
	for P in "$AGENTS_SKILL" "$CLAUDE_SKILL"; do
		exists "$P" || continue
		FOUND=1
		if [ -L "$P" ]; then
			WHAT="a link to $(readlink "$P")"
		elif [ -d "$P/.git" ]; then
			WHAT="a git checkout at $(version "$P")"
		else
			WHAT="a copy without git history"
		fi
		is_skill "$P" || WHAT="$WHAT (no SKILL.md named roblox-dev: not this skill)"
		echo "$P: $WHAT"
	done
	[ "$FOUND" = 1 ] || { echo "roblox-dev is not installed under $BASE."; exit 1; }
	exit 0
fi

if [ "$ACTION" = uninstall ]; then
	cd "$BASE" # never stand inside a folder being removed
	if [ "$LOCAL" = 0 ]; then
		CONFIG=${CLAUDE_CONFIG_DIR:-$CLAUDE}
		SETTINGS=$CONFIG/settings.json
		# The Codex handoff's permission rules name this skill's wrapper: take them out while its installer is still here.
		if [ -f "$SETTINGS" ] && grep -q 'roblox-dev/scripts/codex/handoff.sh' "$SETTINGS"; then
			MJS=
			for P in "$AGENTS_SKILL" "$CLAUDE_SKILL"; do
				if [ -f "$P/scripts/codex/install.mjs" ]; then MJS=$P/scripts/codex/install.mjs; break; fi
			done
			if [ -n "$MJS" ] && command -v node >/dev/null 2>&1 && CLAUDE_CONFIG_DIR=$CONFIG node "$MJS" --uninstall; then
				:
			else
				echo "warning: $SETTINGS still allows the roblox-dev Codex handoff wrapper. Delete its permissions.allow entry naming roblox-dev/scripts/codex/handoff.sh and the autoMode.allow rule starting 'Running the roblox-dev Codex handoff wrapper'." >&2
			fi
		fi
	fi
	REMOVED=0
	# Claude's entry first: it may be a link to the .agents copy, judged before that copy goes.
	for P in "$CLAUDE_SKILL" "$AGENTS_SKILL"; do
		exists "$P" || continue
		if [ -L "$P" ]; then
			TO=$(readlink "$P")
			if [ "$P" = "$CLAUDE_SKILL" ] && same_dir "$P" "$AGENTS_SKILL"; then
				rm -f "$P" # the link alone, never what it points to
				echo "Removed Claude's link $P"
				REMOVED=$((REMOVED + 1))
			elif [ ! -e "$P" ] || is_skill "$P" || [ "$FORCE" = 1 ]; then
				rm -f "$P"
				echo "Removed the link $P -> $TO (the folder it points to was not touched)"
				REMOVED=$((REMOVED + 1))
			else
				echo "warning: $P links to $TO, which is not the roblox-dev skill; left untouched. --force removes the link." >&2
			fi
		elif is_skill "$P" || [ "$FORCE" = 1 ]; then
			rm -rf "$P"
			echo "Removed $P"
			REMOVED=$((REMOVED + 1))
		else
			echo "warning: $P is not the roblox-dev skill (no SKILL.md named roblox-dev); left untouched. --force removes it." >&2
		fi
	done
	if [ "$LOCAL" = 0 ]; then
		for PAIR in "${ROBLOX_DEV_LEARNING_HOME:-$BASE/.roblox-dev/learning}|learning notes" "${CODEX_HANDOFF_HOME:-$CONFIG/codex-handoffs}|Codex handoff state"; do
			DIR=${PAIR%%|*}
			WHAT=${PAIR#*|}
			exists "$DIR" || continue
			if [ "$PURGE" = 1 ]; then
				rm -rf "$DIR"
				echo "Removed the $WHAT in $DIR"
			else
				echo "Kept the $WHAT in $DIR (--purge deletes them)."
			fi
		done
		if [ "$PURGE" = 1 ]; then rmdir "$BASE/.roblox-dev" 2>/dev/null || true; fi
	fi
	if [ "$REMOVED" = 0 ]; then
		echo "roblox-dev was not installed under $BASE."
	else
		echo "Start a new agent session so its skill list no longer shows roblox-dev."
	fi
	exit 0
fi

command -v git >/dev/null 2>&1 || { echo "git is required." >&2; exit 1; }

if [ ! -d "$AGENTS" ] && [ -d "$CLAUDE" ]; then
	PRIMARY=$CLAUDE
else
	PRIMARY=$AGENTS
fi
TARGET=$PRIMARY/skills/$NAME

if [ "$ACTION" = update ] && ! exists "$TARGET"; then
	if exists "$CLAUDE_SKILL" && [ ! -L "$CLAUDE_SKILL" ]; then
		# An install from before .agents existed: update it where it is.
		PRIMARY=$CLAUDE
		TARGET=$CLAUDE_SKILL
	else
		echo "roblox-dev is not installed at $TARGET; run without --update to install it." >&2
		exit 1
	fi
fi

if [ -L "$TARGET" ]; then
	echo "Already installed: $TARGET is a link to $(readlink "$TARGET") (left untouched; update that checkout itself)."
elif [ -e "$TARGET" ]; then
	if [ -d "$TARGET/.git" ]; then
		OLD=$(version "$TARGET")
		printf '%s\n' '/*' '!/.mcp.json' | git -C "$TARGET" sparse-checkout set --no-cone --stdin
		git -C "$TARGET" pull --ff-only --quiet
		NEW=$(version "$TARGET")
		if [ "$OLD" = "$NEW" ]; then echo "Up to date: $TARGET at $NEW"; else echo "Updated $TARGET: $OLD -> $NEW"; fi
	elif [ "$FORCE" = 1 ] || { [ "$ACTION" = update ] && is_skill "$TARGET"; }; then
		echo "Replacing the copy at $TARGET"
		rm -rf "$TARGET"
	else
		echo "$TARGET exists and is not a git checkout. Re-run with --force to replace it." >&2
		exit 1
	fi
fi
if [ ! -e "$TARGET" ] && [ ! -L "$TARGET" ]; then
	mkdir -p "$(dirname "$TARGET")"
	git clone --depth 1 --no-checkout --quiet "$REPO" "$TARGET"
	printf '%s\n' '/*' '!/.mcp.json' | git -C "$TARGET" sparse-checkout set --no-cone --stdin
	git -C "$TARGET" checkout --quiet
	[ "$LOCAL" = 1 ] && rm -rf "$TARGET/.git"
	echo "Installed $TARGET"
fi

# Claude points at the single copy instead of holding its own.
if [ "$PRIMARY" = "$AGENTS" ] && [ -d "$CLAUDE" ]; then
	LINK=$CLAUDE_SKILL
	if [ -L "$LINK" ] || [ -e "$LINK" ]; then
		if [ -L "$LINK" ] && same_dir "$LINK" "$TARGET"; then
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
