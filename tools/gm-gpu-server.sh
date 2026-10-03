#!/bin/bash
# gm-gpu-server.sh - Lend this computer's GPU to a game hosted elsewhere
# (thin wrapper for lib/gpu_server.py; see GAME-NIGHT.md)
#
# Run it on the host's laptop, next to Forge (and the music composer, if set up),
# then expose it with a tunnel and give the GM the link and the password:
#
#   bash tools/gm-gpu-server.sh [--port 7861] [--password PW]
#   cloudflared tunnel --url http://localhost:7861
#
# Without --password it uses GPU_SERVER_PASSWORD from .env, else makes a new one.

source "$(dirname "$0")/common.sh"

$PYTHON_CMD "$LIB_DIR/gpu_server.py" "$@"
exit $?
