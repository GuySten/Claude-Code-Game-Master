#!/bin/bash
# gm-music-compose.sh - Composed music for main villains, bosses and heroes
# (local AI: MusicGen, on this computer's GPU — optional)
#
#   gm-music-compose.sh setup [--cpu]        Install the composer (its own .compose-venv, ~3 GB)
#   gm-music-compose.sh setup --melody       Also the melody model (~3.3 GB): dark twins keep the anthem's tune
#                                            (COMPOSE_MODEL=facebook/musicgen-melody: it composes everything)
#   gm-music-compose.sh setup --orchestra    The sampled orchestra (~215 MB of real instrument recordings, no GPU)
#   gm-music-compose.sh orchestra "<PC>" [--stage 0-3]   Their theme played by the orchestra (default: legendary)
#   gm-music-compose.sh tune "<name>" [--minor] [--stage N]   A tune's notes and times, to arrange it
#   gm-music-compose.sh arrange <file.json>  Play an arrangement (lib/arrangement.py) into the campaign's music
#   gm-music-compose.sh setup --rater        Meta's Audiobox Aesthetics, to rate music 1-10 (~1 GB model)
#   gm-music-compose.sh rate <files...>      Rate pieces: enjoyment, usefulness, complexity, quality
#   gm-music-compose.sh check                Which GPU/CPU it would use
#   gm-music-compose.sh test                 Time one 30-second piece (first run downloads the model)
#   gm-music-compose.sh theme "<villain>" [--boss] [--look "..."]   Compose a theme now
#   gm-music-compose.sh anthem "<PC>"        Compose a player character's heroic anthem (and its dark twin) now
#   gm-music-compose.sh motif "<PC>"         Hear a character's leitmotif (plain melody, and in the minor)
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
        if [ "$1" = "--orchestra" ]; then
            # No AI and no GPU: the notes of the character's tune, played by recorded
            # instruments (the MuseScore_General SoundFont, MIT licensed).
            PY="$(compose_py)"
            if [ -z "$PY" ]; then
                command -v uv >/dev/null 2>&1 || { error "uv is needed (the installer sets it up): https://docs.astral.sh/uv/"; exit 1; }
                uv venv "$VENV" --python 3.11 || exit 1
                PY="$(compose_py)"
            fi
            uv pip install --python "$PY" soundfile numpy || exit 1
            uv pip install --python "$PY" --no-deps tinysoundfont || exit 1   # (its audio-device extra isn't needed)
            "$PY" "$LIB_DIR/orchestra.py" --fetch-only || exit 1
            success "The orchestra is ready. Try: bash tools/gm-music-compose.sh orchestra \"<PC>\""
            exit 0
        fi
        if [ "$1" = "--rater" ]; then
            PY="$(compose_py)"
            if [ -z "$PY" ]; then
                command -v uv >/dev/null 2>&1 || { error "uv is needed (the installer sets it up): https://docs.astral.sh/uv/"; exit 1; }
                uv venv "$VENV" --python 3.11 || exit 1
                PY="$(compose_py)"
            fi
            if ! "$PY" -c "import torch" 2>/dev/null; then
                info "Installing PyTorch (CPU build is enough to rate music)..."
                uv pip install --python "$PY" torch torchaudio --index-url https://download.pytorch.org/whl/cpu || exit 1
            elif ! "$PY" -c "import torchaudio" 2>/dev/null; then
                TORCH_VER="$("$PY" -c 'import torch; print(torch.__version__.split("+")[0])')"
                TORCH_IDX="$("$PY" -c 'import torch; v = torch.version.cuda; print("https://download.pytorch.org/whl/" + ("cu" + v.replace(".", "") if v else "cpu"))')"
                uv pip install --python "$PY" "torch==$TORCH_VER" torchaudio --index-url "$TORCH_IDX" || exit 1
            fi
            uv pip install --python "$PY" audiobox_aesthetics soundfile requests huggingface_hub safetensors || exit 1
            success "The rater is ready. Try: bash tools/gm-music-compose.sh rate music/*.mp3"
            exit 0
        fi
        if [ "$1" = "--melody" ]; then
            PY="$(compose_py)"
            [ -z "$PY" ] && { error "Set up the composer first: bash tools/gm-music-compose.sh setup"; exit 1; }
            # The melody model's processor needs torchaudio, built for the same torch.
            TORCH_VER="$("$PY" -c 'import torch; print(torch.__version__.split("+")[0])')" || exit 1
            TORCH_IDX="$("$PY" -c 'import torch; v = torch.version.cuda; print("https://download.pytorch.org/whl/" + ("cu" + v.replace(".", "") if v else "cpu"))')"
            info "Installing torchaudio for torch $TORCH_VER..."
            if [ "$(uname -s)" = "Darwin" ]; then
                uv pip install --python "$PY" "torch==$TORCH_VER" torchaudio || exit 1
            else
                uv pip install --python "$PY" "torch==$TORCH_VER" torchaudio --index-url "$TORCH_IDX" || exit 1
            fi
            info "Downloading the melody model (about 3.3 GB, once)..."
            "$PY" "$LIB_DIR/music_compose.py" --fetch-melody || exit 1
            success "Dark twins now keep each anthem's tune. To compose EVERYTHING with it, add"
            echo "  COMPOSE_MODEL=facebook/musicgen-melody   to .env (try: COMPOSE_MODEL=facebook/musicgen-melody bash tools/gm-music-compose.sh test)"
            exit 0
        fi
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
    motif)
        PY="$(compose_py)"
        [ -z "$PY" ] && { error "Not set up yet: bash tools/gm-music-compose.sh setup"; exit 1; }
        CLS="$($PYTHON_CMD "$LIB_DIR/composer.py" class-of "$1" 2>/dev/null)"
        "$PY" "$LIB_DIR/music_compose.py" --leitmotif "$1" --class "$CLS" --out "$(get_campaign_dir 2>/dev/null || echo .)/music/anthems"
        ;;
    orchestra)
        PY="$(compose_py)"
        [ -z "$PY" ] && { error "Not set up yet: bash tools/gm-music-compose.sh setup --orchestra"; exit 1; }
        [ -z "$1" ] && { error "Whose theme? gm-music-compose.sh orchestra \"<PC>\" [--stage 0-3]"; exit 1; }
        CLS="$($PYTHON_CMD "$LIB_DIR/composer.py" class-of "$1" 2>/dev/null)"
        DIR="$(get_campaign_dir 2>/dev/null || echo .)/music/anthems"
        mkdir -p "$DIR"
        "$PY" "$LIB_DIR/orchestra.py" "$@" --class "$CLS" --out "$DIR"
        ;;
    tune)
        PY="$(compose_py)"
        [ -z "$PY" ] && { error "Not set up yet: bash tools/gm-music-compose.sh setup --orchestra"; exit 1; }
        [ -z "$1" ] && { error "Whose tune? gm-music-compose.sh tune \"<name>\" [--minor]"; exit 1; }
        CLS="$($PYTHON_CMD "$LIB_DIR/composer.py" class-of "$1" 2>/dev/null)"
        "$PY" "$LIB_DIR/arrangement.py" tune "$@" --class "$CLS"
        ;;
    arrange)
        PY="$(compose_py)"
        [ -z "$PY" ] && { error "Not set up yet: bash tools/gm-music-compose.sh setup --orchestra"; exit 1; }
        [ -f "$1" ] || { error "No such arrangement: $1"; exit 1; }
        DIR="$(get_campaign_dir 2>/dev/null || echo .)/music/arranged"
        mkdir -p "$DIR"
        "$PY" "$LIB_DIR/arrangement.py" play "$1" --out "$DIR/$(basename "${1%.json}").ogg"
        ;;
    rate)
        PY="$(compose_py)"
        [ -z "$PY" ] && { error "Not set up yet: bash tools/gm-music-compose.sh setup --rater"; exit 1; }
        [ -z "$1" ] && { error "What to rate? gm-music-compose.sh rate <files...>"; exit 1; }
        "$PY" "$LIB_DIR/music_rate.py" "$@"
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
