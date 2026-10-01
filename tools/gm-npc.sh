#!/bin/bash
# gm-npc.sh - Create and update NPCs (Hybrid Architecture)
# Uses Python modules for validation and data operations

# Source common utilities
source "$(dirname "$0")/common.sh"

# Usage: gm-npc.sh <action> <name> [additional args]
# Examples:
#   gm-npc.sh create "Grimnar" "dwarf blacksmith" "friendly"
#   gm-npc.sh update "Grimnar" "insulted by player"
#   gm-npc.sh status "Grimnar"

if [ "$#" -lt 1 ]; then
    echo "Usage: gm-npc.sh <action> [name] [args]"
    echo ""
    echo "=== NPC Management ==="
    echo "  create <name> <description> <attitude>  Create new NPC"
    echo "  update <name> <event>                   Add event to NPC history"
    echo "  status <name>                           Show NPC details"
    echo "  voice <name>                            Show NPC canonical voice lines"
    echo "  enhance <name> <description>            Update NPC description"
    echo "  list [--attitude X] [--location Y]      List all NPCs"
    echo ""
    echo "=== Tags ==="
    echo "  tag-location <name> <loc1> [loc2...]    Add location tags"
    echo "  untag-location <name> <loc1> [loc2...]  Remove location tags"
    echo "  tag-quest <name> <quest1> [quest2...]   Add quest tags"
    echo "  untag-quest <name> <quest1> [quest2...] Remove quest tags"
    echo "  tags <name>                             Show NPC tags"
    echo ""
    echo "=== Party Members ==="
    echo "  promote <name>                          Make NPC a party member"
    echo "  demote <name>                           Remove party member status"
    echo "  party                                   List all party members with HP/AC"
    echo "  companion <name> <PC>                   A PC's familiar, pet or mount (portrait + on their sheet)"
    echo ""
    echo "=== Party Member Stats (requires promote first) ==="
    echo "  hp <name> <+/-amount>                   Damage/heal party member"
    echo "  xp <name> <+amount>                     Award XP to party member"
    echo "  set <name> <field> <value>              Set stat (ac, level, class, race, attack, damage, hp_max)"
    echo "  equip <name> <item>                     Add equipment"
    echo "  unequip <name> <item>                   Remove equipment"
    echo "  condition <name> add/remove <cond>      Manage conditions (poisoned, stunned, etc)"
    echo "  feature <name> add/remove <feature>     Manage features (Second Wind, etc)"
    echo ""
    echo "Examples:"
    echo "  gm-npc.sh create \"Carl\" \"A dungeon crawler\" \"friendly\""
    echo "  gm-npc.sh promote \"Carl\"                 # Make Carl a party member"
    echo "  gm-npc.sh set \"Carl\" ac 14               # Set Carl's AC"
    echo "  gm-npc.sh equip \"Carl\" \"Chitin Armor\"    # Give Carl armor"
    echo "  gm-npc.sh hp \"Carl\" -4                   # Carl takes 4 damage"
    echo "  gm-npc.sh party                          # See all party members"
    exit 1
fi

require_active_campaign

ACTION="$1"
shift  # Remove action from arguments

# Special handling for actions that don't require a name
if [ "$ACTION" = "list" ]; then
    $PYTHON_CMD "$LIB_DIR/npc_manager.py" list "$@"
    exit $?
fi

if [ "$ACTION" = "party" ]; then
    $PYTHON_CMD "$LIB_DIR/npc_manager.py" party
    exit $?
fi

# All other actions require a name as first argument
if [ "$#" -lt 1 ]; then
    echo "Error: Action '$ACTION' requires a name argument"
    exit 1
fi

NAME="$1"
shift  # Remove name from arguments

# Delegate to Python module based on action
case "$ACTION" in
    create)
        if [ "$#" -ne 2 ]; then
            echo "Usage: gm-npc.sh create <name> <description> <attitude>"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" create "$NAME" "$1" "$2"
        ;;

    update)
        if [ "$#" -ne 1 ]; then
            echo "Usage: gm-npc.sh update <name> <event>"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" update "$NAME" "$@"
        ;;

    status)
        STATUS_OUTPUT=$($PYTHON_CMD "$LIB_DIR/npc_manager.py" status "$NAME" "$@")
        STATUS_CODE=$?
        echo "$STATUS_OUTPUT"

        # Auto-query RAG for NPC context if vectors exist
        CAMPAIGN_DIR=$(bash "$TOOLS_DIR/gm-campaign.sh" path 2>/dev/null)
        RAG_OUTPUT=""
        RAG_CODE=0
        if [ -d "$CAMPAIGN_DIR/vectors" ]; then
            echo ""
            echo "Source Material Context"
            echo "======================="
            RAG_OUTPUT=$($PYTHON_CMD "$LIB_DIR/entity_enhancer.py" search "$NAME personality dialogue background" -n 4 --excerpt-chars 250)
            RAG_CODE=$?
            echo "$RAG_OUTPUT"
        fi

        STATUS_CHARS=${#STATUS_OUTPUT}
        RAG_CHARS=${#RAG_OUTPUT}
        STATUS_TOKENS=$(estimate_tokens_from_chars "$STATUS_CHARS")
        RAG_TOKENS=$(estimate_tokens_from_chars "$RAG_CHARS")
        log_token_usage "gm-npc-status" "name_chars=${#NAME}" "status_chars=$STATUS_CHARS" "status_tokens_est=$STATUS_TOKENS" "rag_chars=$RAG_CHARS" "rag_tokens_est=$RAG_TOKENS"

        if [ $STATUS_CODE -ne 0 ]; then
            exit $STATUS_CODE
        fi
        if [ $RAG_CODE -ne 0 ]; then
            exit $RAG_CODE
        fi
        ;;

    enhance)
        if [ "$#" -ne 1 ]; then
            echo "Usage: gm-npc.sh enhance <name> <enhanced_description>"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" enhance "$NAME" "$1"
        ;;

    tag-location)
        if [ "$#" -lt 1 ]; then
            echo "Usage: gm-npc.sh tag-location <name> <location1> [location2 ...]"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" tag-location "$NAME" "$@"
        ;;

    untag-location)
        if [ "$#" -lt 1 ]; then
            echo "Usage: gm-npc.sh untag-location <name> <location1> [location2 ...]"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" untag-location "$NAME" "$@"
        ;;

    tag-quest)
        if [ "$#" -lt 1 ]; then
            echo "Usage: gm-npc.sh tag-quest <name> <quest1> [quest2 ...]"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" tag-quest "$NAME" "$@"
        ;;

    untag-quest)
        if [ "$#" -lt 1 ]; then
            echo "Usage: gm-npc.sh untag-quest <name> <quest1> [quest2 ...]"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" untag-quest "$NAME" "$@"
        ;;

    tags)
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" tags "$NAME"
        ;;

    # Party member commands
    promote)
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" promote "$NAME"
        ;;

    companion)
        if [ "$#" -ne 1 ]; then
            echo "Usage: gm-npc.sh companion <name> <player character>   (or: none)"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" companion "$NAME" "$1"
        ;;

    demote)
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" demote "$NAME"
        ;;

    hp)
        if [ "$#" -ne 1 ]; then
            echo "Usage: gm-npc.sh hp <name> <+/-amount>"
            echo "Example: gm-npc.sh hp \"Carl\" -4"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" hp "$NAME" "$1"
        ;;

    xp)
        if [ "$#" -ne 1 ]; then
            echo "Usage: gm-npc.sh xp <name> <+amount>"
            echo "Example: gm-npc.sh xp \"Carl\" +100"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" xp "$NAME" "$1"
        ;;

    set)
        if [ "$#" -ne 2 ]; then
            echo "Usage: gm-npc.sh set <name> <field> <value>"
            echo "Fields: ac, level, class, race, attack, damage, hp_max"
            echo "Example: gm-npc.sh set \"Carl\" ac 14"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" set "$NAME" "$1" "$2"
        ;;

    equip)
        if [ "$#" -ne 1 ]; then
            echo "Usage: gm-npc.sh equip <name> <item>"
            echo "Example: gm-npc.sh equip \"Carl\" \"Chitin Armor\""
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" equip "$NAME" "$1"
        ;;

    unequip)
        if [ "$#" -ne 1 ]; then
            echo "Usage: gm-npc.sh unequip <name> <item>"
            echo "Example: gm-npc.sh unequip \"Carl\" \"Torn Shirt\""
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" unequip "$NAME" "$1"
        ;;

    condition)
        if [ "$#" -ne 2 ]; then
            echo "Usage: gm-npc.sh condition <name> add/remove <condition>"
            echo "Example: gm-npc.sh condition \"Carl\" add poisoned"
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" condition "$NAME" "$1" "$2"
        ;;

    feature)
        if [ "$#" -ne 2 ]; then
            echo "Usage: gm-npc.sh feature <name> add/remove <feature>"
            echo "Example: gm-npc.sh feature \"Carl\" add \"Second Wind\""
            exit 1
        fi
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" feature "$NAME" "$1" "$2"
        ;;

    voice)
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" voice "$NAME" "$@"
        ;;

    inner-life)
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" inner-life "$NAME" "$@"
        ;;

    set-inner)
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" set-inner "$NAME" "$@"
        ;;

    mood)
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" mood "$NAME" "$@"
        ;;

    appearance)
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" appearance "$NAME" "$@"
        ;;

    set-appearance)
        $PYTHON_CMD "$LIB_DIR/npc_manager.py" set-appearance "$NAME" "$@"
        ;;

    *)
        echo "Error: Unknown action '$ACTION'"
        echo "Run 'gm-npc.sh' without arguments to see all available actions"
        exit 1
        ;;
esac

# Exit with the same status as the Python command
exit $?
