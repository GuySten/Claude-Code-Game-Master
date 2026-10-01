#!/bin/bash
# gm-models.sh - Choose which Claude models run the game (thin wrapper for lib/model_presets.py)
#
#   gm-models.sh                     Show the current models and the presets
#   gm-models.sh recommended         Opus GM, Sonnet story helpers, Haiku lookups (best balance)
#   gm-models.sh budget              Sonnet GM, Haiku helpers (cheapest that plays well)
#   gm-models.sh premium             Opus everywhere it matters (quality first)
#   gm-models.sh inherit             Helpers follow the GM's model (the original setup)
#   gm-models.sh <preset> --gm sonnet   Same, with a different GM model
#
# Helpers are set in .claude/agents/*.md; the GM's model goes to
# .claude/settings.local.json (personal, not committed). Applies from the next
# Claude Code session; in a running one, use /model.

source "$(dirname "$0")/common.sh"

$PYTHON_CMD "$LIB_DIR/model_presets.py" "$@"
