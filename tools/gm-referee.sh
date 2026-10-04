#!/bin/bash
# gm-referee.sh - The referee: checks, saves and attacks resolved from the records,
# never from the GM's say-so (lib/referee.py). Every roll is public at the open table
# and every decision goes to the campaign's referee log.
#
#   gm-referee.sh enemy '<stat block JSON>'          # a foe, locked (from the monster-manual agent)
#   gm-referee.sh initiative                          # everyone in the fight + every PC
#   gm-referee.sh attack "Pip" "Grak" "Shortsword" [--long-range]
#   gm-referee.sh check "Pip" stealth --dc hard       # very-easy easy medium hard very-hard nearly-impossible
#   gm-referee.sh check "Pip" stealth --vs-passive "Grak" perception
#   gm-referee.sh save "Pip" dex --vs-spell-of "Mage" | --vs-ability "Grak" "Spit" | --dc medium --source "falling rocks"
#   gm-referee.sh damage "Grak" 2d6 --source "Fire Bolt (Ran)"   |   heal "Pip" 1d8+2 --source "Cure Wounds"
#   gm-referee.sh hide "Pip"    |   help "Bram" "Pip"   |   cover "Pip" half
#   gm-referee.sh field "Shaking floor" --effect dis:attack --effect dis:check-dex [--unless-trait tremorsense]
#   gm-referee.sh status        # the fight as JSON (what the combat-referee agent reads)
#   gm-referee.sh log [--last N] / report            # check that the GM is fair

source "$(dirname "$0")/common.sh"

require_active_campaign

$PYTHON_CMD "$LIB_DIR/referee.py" "$@"
