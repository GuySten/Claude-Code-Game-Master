#!/bin/bash
# End-to-end smoke test of the game's tools through bash — the way Claude Code
# runs them. Works on Linux, macOS and Windows (Git Bash). Uses a throwaway
# world-state, so it never touches real campaigns.
#
#   bash tests/smoke/game-smoke.sh
set -u
cd "$(dirname "$0")/../.." || exit 1

export GM_WORLD_STATE_BASE=.smoke-world        # relative: the same for bash and Python
rm -rf "$GM_WORLD_STATE_BASE"
PORT="${SMOKE_PORT:-8799}"
FAILED=0

# expect "what" "text the output must contain" command...
expect() {
    local what="$1" want="$2"; shift 2
    local out
    out=$("$@" 2>&1)
    if printf '%s' "$out" | grep -qF -- "$want"; then
        echo "  ok    $what"
    else
        echo "  FAIL  $what — expected '$want' in:"; printf '%s\n' "$out" | sed 's/^/          /' | head -20
        FAILED=1
    fi
}

echo "Game tools smoke test ($(uname -s))"
expect "create a campaign"         "Created campaign"      bash tools/gm-campaign.sh create smoke --campaign-name "Smoke Test"
expect "switch to it"              "smoke"        bash tools/gm-campaign.sh switch smoke
expect "first player (onboard)"    "Pip"          bash tools/gm-player.sh onboard original "Pip" "a halfling rogue"
expect "second player, Hebrew"     "נועה"         bash tools/gm-player.sh join original "נועה" "כוהנת צעירה של האור"
expect "damage lands on Pip"       "HP: 7/10"     bash tools/gm-player.sh hp Pip -3
expect "party lists both"          "[player] נועה" bash tools/gm-player.sh party
expect "dice"                      "1d20+5"       uv run python lib/dice.py "1d20+5"
expect "move (Hebrew place name)"  "פונדק הפנס"    bash tools/gm-session.sh move "פונדק הפנס"
expect "scene context in UTF-8"    "פונדק הפנס"    bash tools/gm-session.sh context
expect "status line HUD"           "Pip"          bash -c "echo '{}' | bash tools/gm-statusline.sh"
expect "json-get (no jq)"          "Smoke Test"   bash tools/json-get.sh "$GM_WORLD_STATE_BASE/campaigns/smoke/campaign-overview.json" campaign_name
expect "model presets"             "recommended"  uv run python lib/model_presets.py
expect "open the table"            "TABLE OPEN"   bash tools/gm-table.sh start --port "$PORT" --code smoke-1
expect "players can reach it"      '"ok": true'   curl -s --max-time 10 --noproxy '*' "http://127.0.0.1:$PORT/api/info?code=smoke-1"
expect "the page is served"        "<title>"      curl -s --max-time 10 --noproxy '*' "http://127.0.0.1:$PORT/"
expect "GM narrates (Hebrew)"      "POSTED"       bash tools/gm-table.sh say "שלום, Pip! The inn is warm." --mood tavern
expect "music follows the mood"    "tavern"       bash tools/gm-table.sh music list
expect "table status"              "TABLE OPEN"   bash tools/gm-table.sh status
expect "close the table"           "closed"       bash tools/gm-table.sh stop
expect "it is really closed"       "closed"       bash tools/gm-table.sh status
expect "save the session"          "Save"         bash tools/gm-session.sh save smoke-save

rm -rf "$GM_WORLD_STATE_BASE"
if [ "$FAILED" -ne 0 ]; then echo "SMOKE TEST FAILED"; exit 1; fi
echo "SMOKE TEST PASSED"
