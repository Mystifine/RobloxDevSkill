#!/usr/bin/env bash
# Stable permission-matched entrypoint; Node owns process and state handling.
set -eu
# Printed commands (resume, wait, clean) repeat the path the caller used, with ~ for the home folder.
self="$0"
case "$self" in "$HOME"/*) self="~/${self#"$HOME"/}" ;; esac
export CODEX_HANDOFF_SELF="$self"
if command -v cygpath >/dev/null 2>&1; then
  export CODEX_HANDOFF_BASH="$(cygpath -m "$BASH")"
  here="$(cygpath -m "$(dirname "$0")")"
else
  here="$(dirname "$0")"
fi
exec node "$here/handoff.mjs" "$@"
