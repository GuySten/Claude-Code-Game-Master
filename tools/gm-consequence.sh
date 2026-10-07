#!/bin/bash
# gm-consequence.sh - Consequence tracking (thin wrapper for consequence_manager.py)

source "$(dirname "$0")/common.sh"

if [ "$#" -lt 1 ]; then
    echo "Usage: gm-consequence.sh <action> [args]"
    echo ""
    echo "Actions:"
    echo "  add <description> <trigger>    - Add new consequence"
    echo "  tick                           - Fire consequences matching the current scene (auto on move/time)"
    echo "  check                          - Check pending consequences"
    echo "  resolve <id>                   - Resolve a consequence (it happened)"
    echo "  void <id> [--reason \"...\"]      - Void a mistaken consequence (it never happened)"
    echo "  list-resolved                  - List resolved consequences"
    echo ""
    echo "Examples:"
    echo "  gm-consequence.sh add \"Guards searching for party\" \"2 days\""
    echo "  gm-consequence.sh check"
    echo "  gm-consequence.sh resolve abc123"
    exit 1
fi

require_active_campaign

ACTION="$1"
shift

case "$ACTION" in
    add)
        if [ "$#" -lt 2 ]; then
            echo "Usage: gm-consequence.sh add <description> <trigger> [--trigger-type T --match M --expiry E]"
            echo "Triggers: immediate, next visit, 2 days, next session, etc."
            echo "Structured: --trigger-type on_location|on_npc|on_time|on_event --match <value> [--expiry <date|cond>]"
            exit 1
        fi
        DESC="$1"; TRIG="$2"; shift 2
        $PYTHON_CMD "$LIB_DIR/consequence_manager.py" add "$DESC" "$TRIG" "$@"
        ;;

    check)
        $PYTHON_CMD "$LIB_DIR/consequence_manager.py" check "$@"
        ;;

    tick)
        $PYTHON_CMD "$LIB_DIR/consequence_manager.py" tick
        ;;

    log)
        $PYTHON_CMD "$LIB_DIR/consequence_manager.py" log
        ;;

    rollback)
        $PYTHON_CMD "$LIB_DIR/consequence_manager.py" rollback
        ;;

    resolve)
        if [ "$#" -lt 1 ]; then
            echo "Usage: gm-consequence.sh resolve <id>"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/consequence_manager.py" resolve "$1"
        ;;

    void)
        if [ "$#" -lt 1 ]; then
            echo "Usage: gm-consequence.sh void <id> [--reason \"why it was a mistake\"]"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/consequence_manager.py" void "$@"
        ;;

    list-resolved)
        $PYTHON_CMD "$LIB_DIR/consequence_manager.py" list-resolved
        ;;

    *)
        echo "Unknown action: $ACTION"
        echo "Valid actions: add, check, tick, log, rollback, resolve, void, list-resolved"
        exit 1
        ;;
esac

# Propagate Python exit code
exit $?
