#!/bin/bash
# gm-music-library.sh - Starter music library for the online table
# (thin wrapper for lib/music_library.py)
#
#   gm-music-library.sh list                 What's in music/library.json (✓ = downloaded)
#   gm-music-library.sh fetch [--mood M]     Download the missing tracks into music/
#
# Files are named <mood>-<title>.mp3, so `gm-table.sh say --mood <mood>` plays them
# automatically. Credits (the licenses require them) go to music/CREDITS.md and
# show on the table page while a track plays.

source "$(dirname "$0")/common.sh"

$PYTHON_CMD "$LIB_DIR/music_library.py" "$@"
