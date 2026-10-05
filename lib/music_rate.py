"""Moved to lib/music/music_rate.py (the music package: the engine, no game imports).
This name still works - ``import music_rate`` is the package's module itself."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from music import music_rate as _module  # noqa: E402

if __name__ == "__main__":
    _module.main()
else:
    sys.modules[__name__] = _module
