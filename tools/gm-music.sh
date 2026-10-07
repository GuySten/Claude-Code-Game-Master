#!/bin/bash
# gm-music.sh - The table's written music: the GM's scores, played by a sampled orchestra
# (real instrument recordings, no GPU)
#
#   gm-music.sh setup                    The orchestra (its own .music-venv; ~215 MB of recordings)
#   gm-music.sh scores                   The scores meant for the table, and what is rendered
#   gm-music.sh render                   Render every new or changed score now
#   gm-music.sh wanted                   What is still waiting to be written
#   gm-music.sh place "<place>"          Sketch a place's music now
#   gm-music.sh orchestra "<PC>" [--stage 0-3]   Their theme played by the orchestra (default: legendary)
#   gm-music.sh tune "<name>" [--minor] [--stage N]   A tune's notes and times, to arrange it
#   gm-music.sh arrange <file.json>      Play an arrangement (lib/arrangement.py) into the campaign's music
#   gm-music.sh motif "<PC>"             Hear a character's leitmotif (plain melody, and in the minor)
#   gm-music.sh setup --rater            Meta's Audiobox Aesthetics, to rate music 1-10 (~1 GB model)
#   gm-music.sh rate <files...>          Rate pieces: enjoyment, usefulness, complexity, quality
#   gm-music.sh judge <args>             The host judge (lib/host_judge.py: tunes, clips, record, validate)
#   gm-music.sh remove                   Uninstall the orchestra (deletes .music-venv)
#
# With the orchestra set up and a table open, the table renders the GM's scores (and
# each PC's anthem, arranged from their tune) in the background and plays them.

source "$(dirname "$0")/common.sh"

VENV="$PROJECT_ROOT/.music-venv"
music_py() {
    if [ -f "$VENV/Scripts/python.exe" ]; then echo "$VENV/Scripts/python.exe"
    elif [ -f "$VENV/bin/python" ]; then echo "$VENV/bin/python"
    fi
}
make_venv() {
    PY="$(music_py)"
    if [ -z "$PY" ]; then
        command -v uv >/dev/null 2>&1 || { error "uv is needed (the installer sets it up): https://docs.astral.sh/uv/"; exit 1; }
        uv venv "$VENV" --python 3.11 || exit 1
        PY="$(music_py)"
    fi
}
need_orchestra() {
    PY="$(music_py)"
    [ -z "$PY" ] && { error "Not set up yet: bash tools/gm-music.sh setup"; exit 1; }
}

ACTION="${1:-help}"
shift || true

case "$ACTION" in
    setup)
        if [ "$1" = "--rater" ]; then
            make_venv
            if ! "$PY" -c "import torch" 2>/dev/null; then
                info "Installing PyTorch (CPU build is enough to rate music)..."
                uv pip install --python "$PY" torch torchaudio --index-url https://download.pytorch.org/whl/cpu || exit 1
            elif ! "$PY" -c "import torchaudio" 2>/dev/null; then
                TORCH_VER="$("$PY" -c 'import torch; print(torch.__version__.split("+")[0])')"
                TORCH_IDX="$("$PY" -c 'import torch; v = torch.version.cuda; print("https://download.pytorch.org/whl/" + ("cu" + v.replace(".", "") if v else "cpu"))')"
                uv pip install --python "$PY" "torch==$TORCH_VER" torchaudio --index-url "$TORCH_IDX" || exit 1
            fi
            uv pip install --python "$PY" audiobox_aesthetics soundfile requests huggingface_hub safetensors || exit 1
            success "The rater is ready. Try: bash tools/gm-music.sh rate music/*.mp3"
            exit 0
        fi
        # The notes of the GM's scores, played by recorded instruments (the
        # MuseScore_General SoundFont, MIT licensed). (setup --orchestra: the same.)
        make_venv
        uv pip install --python "$PY" soundfile numpy || exit 1
        uv pip install --python "$PY" --no-deps tinysoundfont || exit 1   # (its audio-device extra isn't needed)
        "$PY" "$LIB_DIR/orchestra.py" --fetch-only || exit 1
        success "The orchestra is ready. Try: bash tools/gm-music.sh orchestra \"<PC>\""
        ;;
    scores|render|wanted|place)
        $PYTHON_CMD "$LIB_DIR/score_music.py" "$ACTION" "$@"
        ;;
    motif)
        need_orchestra
        CLS="$($PYTHON_CMD "$LIB_DIR/score_music.py" class-of "$1" 2>/dev/null)"
        "$PY" "$LIB_DIR/music_compose.py" --leitmotif "$1" --class "$CLS" --out "$(get_campaign_dir 2>/dev/null || echo .)/music/anthems"
        ;;
    orchestra)
        need_orchestra
        [ -z "$1" ] && { error "Whose theme? gm-music.sh orchestra \"<PC>\" [--stage 0-3]"; exit 1; }
        CLS="$($PYTHON_CMD "$LIB_DIR/score_music.py" class-of "$1" 2>/dev/null)"
        DIR="$(get_campaign_dir 2>/dev/null || echo .)/music/anthems"
        mkdir -p "$DIR"
        "$PY" "$LIB_DIR/orchestra.py" "$@" --class "$CLS" --out "$DIR"
        ;;
    tune)
        need_orchestra
        [ -z "$1" ] && { error "Whose tune? gm-music.sh tune \"<name>\" [--minor]"; exit 1; }
        CLS="$($PYTHON_CMD "$LIB_DIR/score_music.py" class-of "$1" 2>/dev/null)"
        "$PY" "$LIB_DIR/arrangement.py" tune "$@" --class "$CLS"
        ;;
    arrange)
        need_orchestra
        [ -f "$1" ] || { error "No such arrangement: $1"; exit 1; }
        DIR="$(get_campaign_dir 2>/dev/null || echo .)/music/arranged"
        mkdir -p "$DIR"
        "$PY" "$LIB_DIR/arrangement.py" play "$1" --out "$DIR/$(basename "${1%.json}").ogg"
        ;;
    rate)
        PY="$(music_py)"
        [ -z "$PY" ] && { error "Not set up yet: bash tools/gm-music.sh setup --rater"; exit 1; }
        [ -z "$1" ] && { error "What to rate? gm-music.sh rate <files...>"; exit 1; }
        "$PY" "$LIB_DIR/music_rate.py" "$@"
        ;;
    judge)
        need_orchestra
        "$PY" "$LIB_DIR/host_judge.py" "$@"
        ;;
    remove)
        rm -rf "${VENV:?}" && success "The orchestra removed (.music-venv deleted). Rendered music stays."
        ;;
    *)
        sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'
        ;;
esac
