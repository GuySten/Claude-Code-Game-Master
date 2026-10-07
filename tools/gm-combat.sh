#!/bin/bash
# gm-combat.sh - Persisted combat state (optional; for fights worth tracking)
#
#   gm-combat.sh start
#   gm-combat.sh add-enemy "Orc Warrior" 22 --ac 17 --init 12 [--zone "at the gate"]
#   gm-combat.sh zone "Legolas" "on the chain, 15 ft up"   # where they are (any combatant or
#                              # PC; shown in the header and on the table's party panel);
#                              # gm-combat.sh zone "Legolas" clears it
#   gm-combat.sh hp "Orc Warrior" -5
#   gm-combat.sh condition "Orc Warrior" add prone
#   gm-combat.sh next-turn
#   gm-combat.sh header        # render the combat header
#   gm-combat.sh end           # clear state (award XP/loot via gm-player afterwards)
#
# Add --json to any command for a structured envelope.

source "$(dirname "$0")/common.sh"

require_active_campaign

$PYTHON_CMD "$LIB_DIR/combat_manager.py" "$@"
