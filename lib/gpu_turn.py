"""One AI model on the graphics card at a time.

Pictures (Forge or ComfyUI) keep their model in RAM and use the GPU in turns:
whoever wants the card takes this lock, which every process of the game shares
(the table's background painter and the GM's own picture commands).

    with gpu_turn("pictures"):
        ...
"""

import os
import sys
import tempfile
import time
from pathlib import Path

LOCK_PATH = Path(os.environ.get("GPU_LOCK_FILE") or Path(tempfile.gettempdir()) / "gm-gpu-turn.lock")
# Longer than one piece or picture takes: past this, go ahead anyway rather than hang.
WAIT_LIMIT = float(os.environ.get("GPU_TURN_WAIT", "900"))


class gpu_turn:
    def __init__(self, who: str = "", wait: float = WAIT_LIMIT):
        self.who, self.wait, self.f, self.held = who, wait, None, False

    def _try(self) -> bool:
        try:
            if os.name == "nt":
                import msvcrt
                self.f.seek(0)
                msvcrt.locking(self.f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            return False

    def __enter__(self) -> "gpu_turn":
        try:
            LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.f = open(LOCK_PATH, "a+")
        except OSError:
            return self                          # no lock file: carry on unguarded
        start = time.time()
        while not self._try():
            if time.time() - start > self.wait:
                print(f"[gpu] waited {self.wait:.0f} s for the graphics card; going ahead ({self.who})",
                      file=sys.stderr, flush=True)
                return self
            time.sleep(0.25)
        self.held = True
        return self

    def __exit__(self, *exc) -> None:
        if self.f is None:
            return
        try:
            if self.held:
                if os.name == "nt":
                    import msvcrt
                    self.f.seek(0)
                    msvcrt.locking(self.f.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.f.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            self.f.close()
            self.f, self.held = None, False
