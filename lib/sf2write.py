"""Moved to lib/music/sf2write.py (the music package: the engine, no game imports).
This name still works - ``import sf2write`` is the package's module itself."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from music import sf2write as _module  # noqa: E402

if __name__ == "__main__":
    pass
else:
    sys.modules[__name__] = _module
