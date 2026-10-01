#!/usr/bin/env bash
# gm-statusline.sh - Always-on game HUD for the AI Game Master.
#
# Auto-derives a 3-line heads-up display from the active campaign's state
# files (character.json + campaign-overview.json). The agent does NOTHING
# extra: these files are already persisted every turn per the golden rule,
# and Claude Code re-runs this script after every assistant message.
#
# Wired via the project's .claude/settings.json `statusLine` setting, so it
# only overrides the global status line inside this repo.

input=$(cat)  # Claude Code JSON payload on stdin (unused; we read state files)

# Anchor to repo root via this script's location, not cwd.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Reads the sheets with Python (no jq needed, so it works on Windows too).
source "$ROOT/tools/pyfind.sh"
pick_python "$ROOT" || PY=(python3)

# 256-color palette (kept light: docs warn multi-line + heavy ANSI can glitch)
GREEN=$'\033[38;5;42m'
AMBER=$'\033[38;5;214m'
RED=$'\033[38;5;203m'
TEAL=$'\033[38;5;51m'
GOLD=$'\033[38;5;220m'
DIM=$'\033[38;5;244m'
FAINT=$'\033[38;5;238m'
BOLD=$'\033[1m'
RESET=$'\033[0m'
SEP="${DIM}·${RESET}"
SEPV="${FAINT}│${RESET}"   # vertical segment separator for the vitals line

# Horizontal rule that frames the HUD (drawn both above and below it) to set it
# apart from the conversation above and the input/permissions area below. Width
# auto-detects the terminal; falls back to 80 when stdout is not a tty (the usual
# case for a status-line subprocess). Args let the rule react to danger state:
#   divider [rule_color] [ornament_color]
# Defaults are a calm faint rule with a teal ornament.
divider() {
    local rule="${1:-$FAINT}" orn="${2:-$TEAL}"
    local cols mid half left right
    cols=$(tput cols 2>/dev/null)
    case "$cols" in ''|*[!0-9]*) cols=80 ;; esac
    [ "$cols" -gt 120 ] && cols=120
    [ "$cols" -lt 24  ] && cols=24
    mid="◆"                                  # single-width ornament (no wrap)
    half=$(( (cols - 1) / 2 ))
    printf -v left  '%*s' "$half" '';            left="${left// /─}"
    printf -v right '%*s' "$(( cols - 1 - half ))" ''; right="${right// /─}"
    printf '%s%s%s%s%s%s%s\n' "$rule" "$left" "$orn" "$mid" "$rule" "$right" "$RESET"
}

# Same world-state as every other tool (GM_WORLD_STATE_BASE, relative to the repo).
BASE="${GM_WORLD_STATE_BASE:-$ROOT/world-state}"
case "$BASE" in /*|[A-Za-z]:*) ;; *) BASE="$ROOT/$BASE" ;; esac
ACTIVE_FILE="$BASE/active-campaign.txt"
if [ ! -f "$ACTIVE_FILE" ] || [ ! -s "$ACTIVE_FILE" ]; then
    divider
    printf '%s⚔ %sGM%s  %sno campaign yet%s  %s  %s%s/gm%s %sto begin — import a book, build a world, or jump into a one-shot%s\n' \
        "$TEAL" "$BOLD" "$RESET" "$DIM" "$RESET" "$SEP" "$BOLD" "$TEAL" "$RESET" "$DIM" "$RESET"
    divider
    exit 0
fi
ACTIVE=$(tr -d '[:space:]' < "$ACTIVE_FILE")

CAMP="$BASE/campaigns/$ACTIVE"
CHAR="$CAMP/character.json"
OVER="$CAMP/campaign-overview.json"

if [ ! -f "$CHAR" ]; then
    divider
    printf '%s⚔ %sGM%s  %s%s%s  %sno character yet%s  %s  %s%s/gm%s %sto begin — "who are you in this world?"%s\n' \
        "$TEAL" "$BOLD" "$RESET" "$BOLD" "$ACTIVE" "$RESET" "$DIM" "$RESET" "$SEP" "$BOLD" "$TEAL" "$RESET" "$DIM" "$RESET"
    divider
    exit 0
fi

# --- Character fields -------------------------------------------------------
IFS=$'\t' read -r NAME RACE CLASS LEVEL AC GP HP_CUR HP_MAX XP_CUR XP_NEXT LOC < <(
    "${PY[@]}" "$ROOT/lib/hud_fields.py" char "$CHAR" | tr -d '\r'
)

# Conditions array -> status label; fall back to HP-derived state.
CONDS=$("${PY[@]}" "$ROOT/lib/hud_fields.py" conds "$CHAR" 2>/dev/null | tr -d '\r')

# --- Overview fields (location/time/date) -----------------------------------
DATE="" ; TOD="" ; OLOC=""
if [ -f "$OVER" ]; then
    IFS=$'\t' read -r DATE TOD OLOC < <(
        "${PY[@]}" "$ROOT/lib/hud_fields.py" over "$OVER" | tr -d '\r'
    )
fi
# Prefer overview's live location if present.
[ -n "$OLOC" ] && LOC="$OLOC"

# --- HP bar -----------------------------------------------------------------
BAR_W=10
if [ "$HP_MAX" -gt 0 ] 2>/dev/null; then
    PCT=$(( HP_CUR * 100 / HP_MAX ))
    FILLED=$(( HP_CUR * BAR_W / HP_MAX ))
else
    PCT=0 ; FILLED=0
fi
[ "$FILLED" -gt "$BAR_W" ] && FILLED=$BAR_W
[ "$FILLED" -lt 0 ] && FILLED=0
EMPTY=$(( BAR_W - FILLED ))

# HP state drives the bar color AND the frame: calm when healthy, amber when
# wounded, a bold red glow when critical.
if   [ "$PCT" -ge 50 ]; then HPC="$GREEN"; STATE="Normal";   RULEC="$FAINT";        ORNC="$TEAL";          STATEC="$DIM"
elif [ "$PCT" -ge 25 ]; then HPC="$AMBER"; STATE="Wounded";  RULEC="$AMBER";        ORNC="$AMBER";         STATEC="$AMBER"
else                         HPC="$RED";   STATE="Critical"; RULEC="${BOLD}${RED}"; ORNC="${BOLD}${RED}";  STATEC="${BOLD}${RED}"
fi
# A named condition (poisoned, etc.) overrides the label but keeps the HP color.
[ -n "$CONDS" ] && { STATE="$CONDS"; [ "$PCT" -ge 50 ] && STATEC="$AMBER"; }

BAR=""
[ "$FILLED" -gt 0 ] && printf -v F "%${FILLED}s" && BAR="${F// /█}"
[ "$EMPTY"  -gt 0 ] && printf -v E "%${EMPTY}s"  && BAR="${BAR}${E// /░}"

# --- Render (3 lines) -------------------------------------------------------
# Build each line as a string, then emit. Clearer than one packed printf.

L1="${TEAL}⚔ ${BOLD}${NAME}${RESET}  ${DIM}Lv${LEVEL} ${RACE} ${CLASS}${RESET}  ${SEP}  ${AMBER}${LOC}${RESET}"
L2="  HP ${HPC}${BAR}${RESET} ${HP_CUR}/${HP_MAX} ${SEPV} ${DIM}AC${RESET} ${AC} ${SEPV} ${GOLD}${GP}gp${RESET} ${SEPV} ${DIM}XP${RESET} ${XP_CUR}/${XP_NEXT} ${SEPV} ${STATEC}${STATE}${RESET}"

# Top rule — frames the HUD off from the conversation above.
divider "$RULEC" "$ORNC"

printf '%s\n' "$L1"
printf '%s\n' "$L2"

# Line 3: world clock (only if we have it)
if [ -n "$DATE" ] || [ -n "$TOD" ]; then
    printf '  %s%s %s %s%s\n' "$DIM" "$DATE" "$SEP" "$TOD" "$RESET"
fi

# Closing rule — separates the HUD from the input / permissions area below.
divider "$RULEC" "$ORNC"
