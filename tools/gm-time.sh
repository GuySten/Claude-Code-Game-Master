#!/bin/bash
# gm-time.sh - Update campaign time (wrapper for time_manager.py)
#
#   gm-time.sh <time_of_day> <date> [--ticks N] [--duration "<text>"]
# Time-clocks (advance_on=time) advance by elapsed magnitude:
#   default: same time of day, same date (a scene beat: minutes, a climb, a room) → 0;
#            a new time of day ("Dusk" → "Night", "before dawn" → "Dawn") or a new date → 1
#   --duration: minutes / rounds / under 4 hours → 0, 4-23 hours → 1, N days → N, N weeks → 7*N
#   --ticks N: exactly N (wins over everything; --ticks 0 never moves a clock)

source "$(dirname "$0")/common.sh"

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: gm-time.sh <time_of_day> <date> [--ticks N] [--duration \"<text>\"]"
    echo "Example: gm-time.sh \"Dawn\" \"16th day of Harvestmoon, Year 1247\""
    echo "         gm-time.sh \"Noon\" \"19th of Harvestmoon\" --duration \"3 days\""
    echo "Time-clocks: a step within the same time of day and date ticks 0 (a scene beat);"
    echo "a new time of day or date ticks 1; --duration scales it (under 4 hours = 0,"
    echo "N days = N, N weeks = 7N); --ticks N forces exactly N."
    exit 1
fi

TIME_OF_DAY="$1"
DATE="$2"
shift 2

TICKS_FLAG=""
DURATION=""
while [ $# -gt 0 ]; do
    case "$1" in
        --ticks)
            if [ $# -lt 2 ]; then
                echo "[ERROR] --ticks requires a number" >&2
                exit 1
            fi
            TICKS_FLAG="$2"
            shift 2
            ;;
        --duration)
            if [ $# -lt 2 ]; then
                echo "[ERROR] --duration requires a value" >&2
                exit 1
            fi
            DURATION="$2"
            shift 2
            ;;
        *)
            echo "[ERROR] Unknown argument: $1" >&2
            echo "Usage: gm-time.sh <time_of_day> <date> [--ticks N] [--duration \"<text>\"]"
            exit 1
            ;;
    esac
done

require_active_campaign

# Pressure: time passing advances every advance_on=time threat clock, scaled to
# how much time actually passed. Worked out BEFORE the update: the default
# compares the time being set with the current one.
RESOLVE_ARGS=(ticks --to "$TIME_OF_DAY" "$DATE")
if [ -n "$TICKS_FLAG" ]; then
    RESOLVE_ARGS+=(--ticks "$TICKS_FLAG")
fi
if [ -n "$DURATION" ]; then
    RESOLVE_ARGS+=(--duration "$DURATION")
fi
CLOCK_TICKS=$($PYTHON_CMD "$LIB_DIR/time_manager.py" "${RESOLVE_ARGS[@]}")
RESULT=$?
if [ $RESULT -ne 0 ]; then exit $RESULT; fi

$PYTHON_CMD "$LIB_DIR/time_manager.py" update "$TIME_OF_DAY" "$DATE"
RESULT=$?
if [ $RESULT -ne 0 ]; then exit $RESULT; fi

if [ "$CLOCK_TICKS" != "0" ]; then
    echo "Time-clocks: +$CLOCK_TICKS"
    $PYTHON_CMD "$LIB_DIR/threat_clocks.py" tick-time --ticks "$CLOCK_TICKS"
else
    echo "Time-clocks: no tick (a scene beat: same time of day and date). --ticks N to force."
fi

# Reactivity: time passing can fire on_time consequences (e.g. nightfall, deadlines).
echo ""
bash "$TOOLS_DIR/gm-consequence.sh" tick
exit 0
