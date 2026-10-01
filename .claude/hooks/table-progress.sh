#!/bin/bash
# PreToolUse hook: tell the online table what the GM is doing right now, so the
# players' progress bar can say "rolling dice", "updating the character sheets"...
# A no-op unless a table is open. NEVER blocks or fails a tool call: always exits 0,
# and the report is sent in the background with a 1-second timeout.
set +e

DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
INPUT=$(cat 2>/dev/null)

CMD=$(printf '%s' "$INPUT" | python3 -c "import sys, json
try:
    print(json.load(sys.stdin).get('tool_input', {}).get('command', ''))
except Exception:
    print('')" 2>/dev/null)

case "$CMD" in
    *gm-table.sh*) exit 0 ;;   # wait / say open and close the turn themselves
    *dice.py*) STAGE=dice ;;
    *gm-player.sh*|*gm-npc.sh*|*gm-condition.sh*|*gm-combat.sh*) STAGE=sheets ;;
    *gm-session.sh*move*|*gm-location.sh*|*gm-time.sh*) STAGE=moving ;;
    *gm-context.sh*|*gm-search.sh*|*gm-lore.sh*|*gm-recall.sh*|*gm-session.sh*context*) STAGE=lore ;;
    *gm-consequence.sh*|*gm-clock.sh*|*gm-plot.sh*|*gm-note.sh*) STAGE=threads ;;
    *gm-image.sh*) STAGE=image ;;
    *) exit 0 ;;
esac

BASE="${GM_WORLD_STATE_BASE:-$DIR/world-state}"
CAMPAIGN=$(cat "$BASE/active-campaign.txt" 2>/dev/null) || exit 0
INFO="$BASE/campaigns/$CAMPAIGN/table/server.json"
[ -f "$INFO" ] || exit 0

( python3 - "$INFO" "$STAGE" <<'PY' >/dev/null 2>&1 & )
import json, sys, urllib.request
info = json.load(open(sys.argv[1]))
req = urllib.request.Request(
    f"http://127.0.0.1:{info['port']}/api/gm/activity", method="POST",
    data=json.dumps({"stage": sys.argv[2]}).encode(),
    headers={"X-Host-Key": info["host_key"], "Content-Type": "application/json"})
urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=1)
PY

exit 0
