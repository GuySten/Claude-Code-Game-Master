"""Moved to lib/music/devices.py (the music package: the engine, no game imports).
This name still works - ``import devices`` is the package's module itself."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from music import devices as _module  # noqa: E402

if __name__ == "__main__":
    pass
else:
    sys.modules[__name__] = _module
