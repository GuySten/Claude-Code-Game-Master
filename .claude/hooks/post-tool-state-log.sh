#!/bin/bash
# Advisory PostToolUse hook: log state-writing tool calls so missed persists can
# be audited. ADVISORY ONLY — never blocks; always exits 0 even on any error.
set +e

DIR="${CLAUDE_PROJECT_DIR:-.}"
INPUT=$(cat 2>/dev/null)

# Any working Python (the project's venv first; on Windows "python3" may not exist).
# Found next to this hook, wherever Claude Code's project directory points.
HOOK_ROOT="$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)"
PY=(python3)
source "$HOOK_ROOT/tools/pyfind.sh" 2>/dev/null && pick_python "$HOOK_ROOT"

# Best-effort extract of the bash command (no jq dependency).
CMD=$(printf '%s' "$INPUT" | "${PY[@]}" -c "import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
except Exception:
    print('')" 2>/dev/null)

case "$CMD" in
    *gm-player.sh*|*gm-npc.sh*|*gm-session.sh*move*|*gm-consequence.sh*add*|*gm-condition.sh*)
        mkdir -p "$DIR/.ship-it" 2>/dev/null
        printf '%s STATE-WRITE: %s\n' "$(date -u +%FT%TZ 2>/dev/null)" "$CMD" \
            >> "$DIR/.ship-it/state-writes.log" 2>/dev/null
        ;;
esac

exit 0
