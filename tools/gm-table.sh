#!/bin/bash
# gm-table.sh - The online table: every player joins from their own computer
# (thin wrapper for lib/table_server.py)
#
#   gm-table.sh start [--port 8765] [--code word-123]   Open the table (background server)
#   gm-table.sh status                    URLs, table code, who is seated, unread actions
#   gm-table.sh wait [--all] [--timeout S] Block until players act, print their actions
#   gm-table.sh inbox                     Print unread player actions (no waiting)
#   gm-table.sh say "<narration>"         Post narration to every player's screen
#   gm-table.sh say --stdin               ...reading the narration from stdin
#   gm-table.sh say "..." --to "<pc>"     Whisper to one player only
#   gm-table.sh say "..." --image f.png   Attach an image from the campaign's images/
#   gm-table.sh free "<pc>"               Free a seat (player switching devices)
#   gm-table.sh stop                      Close the table
#   gm-table.sh serve [...]               Run the server in the foreground instead

source "$(dirname "$0")/common.sh"

require_active_campaign

ACTION=$1
shift

case "$ACTION" in
    "start")
        TABLE_DIR="$WORLD_STATE_DIR/table"
        mkdir -p "$TABLE_DIR"
        if $PYTHON_CMD "$LIB_DIR/table_server.py" status 2>/dev/null | grep -q "^TABLE OPEN"; then
            $PYTHON_CMD "$LIB_DIR/table_server.py" status
            exit 0
        fi
        rm -f "$TABLE_DIR/server.json"
        nohup $PYTHON_CMD "$LIB_DIR/table_server.py" serve "$@" > "$TABLE_DIR/server.log" 2>&1 &
        for _ in $(seq 1 50); do
            [ -f "$TABLE_DIR/server.json" ] && break
            sleep 0.2
        done
        if [ ! -f "$TABLE_DIR/server.json" ]; then
            echo "[ERROR] The table server did not start. Log:"
            cat "$TABLE_DIR/server.log"
            exit 1
        fi
        cat "$TABLE_DIR/server.log"
        echo ""
        echo "Players: open the link and enter the table code."
        echo "Friends elsewhere: run a tunnel (see: gm-table.sh help) and share its https link."
        ;;

    "serve"|"status"|"wait"|"inbox"|"say"|"free"|"stop")
        $PYTHON_CMD "$LIB_DIR/table_server.py" "$ACTION" "$@"
        ;;

    *)
        echo "The online table — every player joins from their own computer's browser."
        echo ""
        echo "Usage: gm-table.sh <action> [args]"
        echo "  start [--port N] [--code C]   Open the table (runs in the background)"
        echo "  status                        Links, table code, seated players, unread actions"
        echo "  wait [--all] [--timeout S]    Wait for player actions (--all: until everyone acted)"
        echo "  inbox                         Unread player actions, without waiting"
        echo "  say \"<text>\" [--to PC] [--image FILE] | say --stdin"
        echo "                                Post narration (or a whisper / an illustration)"
        echo "  free \"<pc>\"                   Free a seat so a player can rejoin from a new device"
        echo "  stop                          Close the table"
        echo ""
        echo "Who can connect:"
        echo "  - This computer:        http://localhost:8765/"
        echo "  - Same Wi-Fi / network: the 'Same Wi-Fi' link printed by start"
        echo "  - Over the internet:    expose the port with a tunnel, then share its https link:"
        echo "        cloudflared tunnel --url http://localhost:8765     (free, no account)"
        echo "        ngrok http 8765                                     (free account)"
        echo "        tailscale funnel 8765                               (Tailscale users)"
        echo "    Anyone with the link still needs the table code to sit down."
        ;;
esac

exit $?
