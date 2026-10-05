"""Moved to lib/music/arrangement.py (the music package: the engine, no game imports).
This name still works - ``import arrangement`` is the package's module itself."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from music import arrangement as _module  # noqa: E402

if __name__ == "__main__":
    _module.main()
else:
    sys.modules[__name__] = _module
