"""Moved to lib/music/tune_score.py (the music package: the engine, no game imports).
This name still works - ``import tune_score`` is the package's module itself."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from music import tune_score as _module  # noqa: E402

if __name__ == "__main__":
    _module.main()
else:
    sys.modules[__name__] = _module
