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
#   gm-table.sh say "..." --lang he       The Hebrew version of a beat (mixed-language tables)
#   gm-table.sh say "..." --mood combat   Music follows the scene's mood automatically
#   gm-table.sh say "..." --theme "Lich" --boss   An enemy's own theme (boss = exciting version)
#   gm-table.sh music <track>|list|stop   Shared background music for every player
#   gm-table.sh music theme "<enemy>" [file]      Play / assign an enemy's theme
#   gm-table.sh music boss "<boss>" stage 2|pre_end|<event> [--via rise|break] | hit | end victory|requiem|escape|wipe
#                                                 A named boss's fight in stages (its <boss>-<cue> files)
#   gm-table.sh track "<name>" <value>[/<max>] [--note ".."] | off   (a clock or a PC's track on every page)
#   gm-table.sh say "..." --theme "Lich" --villain --look "..."  A main villain (composed theme, portrait)
#   gm-table.sh say "..." --heroic "<pc>"  A PC's heroic moment: their anthem, then the scene's music
#   gm-table.sh say "..." --loot "<item>" --loot-look "..." --loot-for "<pc>"  Important loot, painted
#   gm-table.sh translate --stdin         Translate players' actions for the rest of the table
#   gm-table.sh redo "<pc>" "..." --lang en  An action can't work: say why; they choose again (fresh clock)
#   gm-table.sh warn "<pc>" "..." --lang en  Cruelty to clear innocents: warn; they choose again (once)
#   gm-table.sh punish "<pc>" death|madness|curse --reason "..."  They insisted (judgment music)
#   gm-table.sh atone "<pc>"              Lift a curse once they have atoned in the story
#   gm-table.sh grow "<pc>" growth|bond|wound|healing|darkness|light|finale "what happened"
#                                         A moment in the story changed them (their theme follows)
#   gm-table.sh round 90 | round off      How long the GM waits for everyone (default 60 s)
#   gm-table.sh alias "Marta" "מרתה"      Another spelling of a name (hover cards)
#   gm-table.sh free "<pc>"               Free a seat (player switching devices)
#   gm-table.sh kick "<pc>"               Remove a character nobody is playing (to departed/)
#   gm-table.sh stop                      Close the table
#   gm-table.sh serve [...]               Run the server in the foreground instead

source "$(dirname "$0")/common.sh"

require_active_campaign

ACTION=$1
shift

case "$ACTION" in
    "serve"|"start"|"status"|"wait"|"inbox"|"say"|"redo"|"warn"|"punish"|"atone"|"grow"|"translate"|"music"|"free"|"stop"|"round"|"alias"|"languages"|"track")
        $PYTHON_CMD "$LIB_DIR/table_server.py" "$ACTION" "$@"
        ;;

    "kick")         # (its own clause: remove a character nobody plays)
        $PYTHON_CMD "$LIB_DIR/table_server.py" "$ACTION" "$@"
        ;;

    *)
        echo "The online table — every player joins from their own computer's browser."
        echo ""
        echo "Usage: gm-table.sh <action> [args]"
        echo "  languages [en he fr ...]      The adventure's languages (choose when it starts;"
        echo "                                default: English only). Every beat, action, sheet and"
        echo "                                hover card then exists in each: players switch any time"
        echo "  start [--port N] [--code C]   Open the table (runs in the background)"
        echo "  status                        Links, table code, seated players, unread actions"
        echo "  wait [--all] [--timeout S]    Wait for the round: every player acted, or 60 s after the first"
        echo "  inbox                         Unread player actions, without waiting"
        echo "  say \"<text>\" [--to PC] [--image FILE] | say --stdin"
        echo "        [--lang CODE]           Post narration (or a whisper / an illustration /"
        echo "                                one language's version of a beat)"
        echo "  music <track> [--volume V]    Shared background music: a file in music/, an https"
        echo "                                audio link, or ambient:wind|rain|storm|cave|fire|dungeon"
        echo "  music list | music stop       What can play (per mood) / silence"
        echo "  say ... --mood M              Music follows the scene: calm tavern travel mystery dread"
        echo "                                dungeon combat boss sad storm victory silence"
        echo "  say ... --theme \"<enemy>\" [--boss] [--villain] [--look \"...\"]"
        echo "                                The enemy's own theme (boss: the exciting one), and portrait"
        echo "  say ... --heroic \"<pc>\"       A heroic moment: the PC's anthem, then the scene's music"
        echo "  say ... --loot \"<item>\" [--loot-look \"...\"] [--loot-for PC]  Important loot, painted"
        echo "  translate --stdin             Actions (and untagged beats) in the other languages (JSON by id)"
        echo "  round <seconds>|off           How long the GM waits for everyone once someone acts"
        echo "  alias \"<name>\" \"<spelling>\"   Another spelling of a name, for the hover cards"
        echo "  music theme \"<enemy>\" [file]  Play / assign an enemy's theme; music themes lists them"
        echo "  music boss \"<boss>\" stage N|pre_end|<event> [--via rise|break] | hit | end victory|requiem|escape|wipe"
        echo "                                A boss fight in stages: its <boss>-stageN / -rise / -break / -hit /"
        echo "                                -victory / -requiem / -escape / -wipe files in music/"
        echo "  track \"<name>\" <value>[/<max>] [--note \"..\"] | off   a clock or track on every player's page"
        echo "  music auto on|off             Let --mood change the music (default on)"
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
        echo ""
        echo "Voice: players can speak their actions (🎤) and hear the story read aloud (🔊), in"
        echo "English or Hebrew. The microphone needs https or localhost — on another computer,"
        echo "use the tunnel's https link (even on the same Wi-Fi). Chrome, Edge or Safari."
        ;;
esac

exit $?
