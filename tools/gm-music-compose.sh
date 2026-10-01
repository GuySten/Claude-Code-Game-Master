#!/bin/bash
# gm-music-compose.sh - Composed music for main villains, bosses and heroes
# (local AI: MusicGen, on this computer's GPU — optional)
#
#   gm-music-compose.sh setup [--cpu]        Install the composer (its own .compose-venv, ~3 GB)
#   gm-music-compose.sh check                Which GPU/CPU it would use
#   gm-music-compose.sh test                 Time one 30-second piece (first run downloads the model)
#   gm-music-compose.sh theme "<villain>" [--boss] [--look "..."]   Compose a theme now
#   gm-music-compose.sh anthem "<PC>"        Compose a player character's heroic anthem now
#   gm-music-compose.sh normalize            Make this campaign's composed music louder (older, quiet pieces)
#   gm-music-compose.sh status               What has been composed for this campaign
#   gm-music-compose.sh remove               Uninstall the composer (deletes .compose-venv)
#
# With the composer set up and a table open, the table composes on its own, in the
# background: a theme for each main villain (say --theme X --villain), a battle theme
# for each boss (--boss), and every PC's anthem (played by say --heroic "<PC>").
# Without it the game keeps its other music. MUSIC_COMPOSE=off in .env turns it off.

source "$(dirname "$0")/common.sh"

VENV="$PROJECT_ROOT/.compose-venv"
compose_py() {
    if [ -f "$VENV/Scripts/python.exe" ]; then echo "$VENV/Scripts/python.exe"
    elif [ -f "$VENV/bin/python" ]; then echo "$VENV/bin/python"
    fi
}

ACTION="${1:-help}"
shift || true

case "$ACTION" in
    setup)
        if ! command -v uv >/dev/null 2>&1; then
            error "uv is needed (the installer sets it up): https://docs.astral.sh/uv/"
            exit 1
        fi
        # CUDA 12.6 builds of PyTorch still support GTX 10-series cards (newer CUDA
        # 12.8 builds dropped them). --cpu: no NVIDIA GPU (slow: minutes per piece).
        INDEX="https://download.pytorch.org/whl/cu126"
        [ "$1" = "--cpu" ] && INDEX="https://download.pytorch.org/whl/cpu"
        info "Creating the composer's own environment in .compose-venv (the game stays CPU-only)..."
        uv venv "$VENV" --python 3.11 || exit 1
        PY="$(compose_py)"
        if [ "$(uname -s)" = "Darwin" ]; then
            uv pip install --python "$PY" torch || exit 1
        else
            info "Installing PyTorch from $INDEX (about 2.5 GB)..."
            uv pip install --python "$PY" torch --index-url "$INDEX" || exit 1
        fi
        uv pip install --python "$PY" "transformers>=4.40" soundfile numpy || exit 1
        success "Composer installed. Next: bash tools/gm-music-compose.sh test"
        ;;
    check)
        PY="$(compose_py)"
        [ -z "$PY" ] && { error "Not set up yet: bash tools/gm-music-compose.sh setup"; exit 1; }
        "$PY" "$LIB_DIR/music_compose.py" --check
        ;;
    test)
        PY="$(compose_py)"
        [ -z "$PY" ] && { error "Not set up yet: bash tools/gm-music-compose.sh setup"; exit 1; }
        info "Composing a 30-second test piece (the first run also downloads the ~2.5 GB model)..."
        RESULT=$("$PY" "$LIB_DIR/music_compose.py" --benchmark) || exit 1
        echo "$RESULT" | $PYTHON_CMD -c "
import json, pathlib, sys
d = json.loads(sys.stdin.read().strip().splitlines()[-1])
print(f\"Composed {d['seconds']} s of music in {d['elapsed']:.0f} s on the {d['device'].upper()}.\")
print('Listen: ' + pathlib.Path(d['path']).resolve().as_uri())
print(f\"A villain theme (30 s) takes about {d['elapsed']/60:.1f} min; a hero's anthem (20 s) about {d['elapsed']*0.7/60:.1f} min.\")"
        ;;
    theme|anthem|normalize|status)
        $PYTHON_CMD "$LIB_DIR/composer.py" "$ACTION" "$@"
        ;;
    remove)
        rm -rf "$VENV" && success "Composer removed (.compose-venv deleted). Composed music stays."
        ;;
    *)
        sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
        ;;
esac
