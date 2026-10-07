#!/bin/bash
# gm-clock.sh - Threat clocks (thin wrapper for threat_clocks.py)
#
#   gm-clock.sh list                          Show all clocks
#   gm-clock.sh add "Name" 6 [--on time|event] [--consequence "..."] [--linked-plot "..."]
#                                             New clock with N segments; the
#                                             consequence fires into the world when it fills
#   gm-clock.sh advance "Name" [--ticks 2]    Advance one clock by hand
#   gm-clock.sh set "Name" N [--reason ".."]  Set a clock to N (the fiction outran it)
#   gm-clock.sh track "The Hunger"            A named track (rules.md / ruleset.json systems):
#   gm-clock.sh track "The Hunger" +1 --reason "blood spilled near the Stone"
#   gm-clock.sh track "The Hunger" 0 --reason "the Stone was fed"
#                                             show / move (+N, -N) / set (N); stored in
#                                             threat-clocks.json as an event clock marked
#                                             "track" (never ticked by time); a threshold
#                                             crossed upward fires its consequence.
#                                             --max N creates a track the kit doesn't declare.
#   gm-clock.sh tick-time                     Advance all time-clocks (auto-run by gm-time.sh)
#   gm-clock.sh beats                         Filled clocks = dramatic beats due
#   gm-clock.sh remove "Name"                 Remove a clock
#   gm-clock.sh choose "prompt" "fork" [--trigger ...]  Record a dramatic-choice fork
#
# All commands accept --json.

source "$(dirname "$0")/common.sh"

require_active_campaign

$PYTHON_CMD "$LIB_DIR/threat_clocks.py" "$@"
