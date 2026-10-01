#!/bin/bash
# pyfind.sh - pick the fastest working Python, for scripts that run very often
# (hooks, the status line), where `uv run` would add noticeable delay.
#
#   source tools/pyfind.sh; pick_python "$PROJECT_ROOT" && "${PY[@]}" script.py
#
# Prefers the project's own environment (.venv on macOS/Linux, .venv\Scripts on
# Windows), then any system Python that really runs, then the Windows `py`
# launcher. Sets the array PY (an array, so paths with spaces stay intact).

export PYTHONUTF8=1 PYTHONIOENCODING=utf-8

pick_python() {
    local root="${1:-.}" candidate
    PY=()
    for candidate in "$root/.venv/bin/python" "$root/.venv/Scripts/python.exe"; do
        if [ -x "$candidate" ]; then
            PY=("$candidate")
            return 0
        fi
    done
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "" >/dev/null 2>&1; then
            PY=("$candidate")
            return 0
        fi
    done
    if command -v py >/dev/null 2>&1; then
        PY=(py -3)
        return 0
    fi
    return 1
}
