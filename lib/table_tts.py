#!/usr/bin/env python3
"""Natural read-aloud voices for the online table, made on the host computer.

A browser reads aloud with the voices its device has, and many devices have no
Hebrew voice at all (Chrome on Windows ships none), so Hebrew narration comes
out in an English voice. Instead, the host makes the audio with Microsoft's
free neural voices (the edge-tts package, which needs the internet) and every
player's page plays the same natural voice. Audio is cached per text + voice
in table/tts/, so a beat everyone hears is made once.
"""

import asyncio
import hashlib
import importlib.util
import threading
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

# voice id -> (language, the name shown to players)
VOICES: Dict[str, Tuple[str, str]] = {
    "he-IL-HilaNeural": ("he", "Hila"),
    "he-IL-AvriNeural": ("he", "Avri"),
    "en-US-AriaNeural": ("en", "Aria"),
    "en-US-GuyNeural": ("en", "Guy"),
}
MAX_CHARS = 600          # one chunk of narration (the page sends sentences, ~220 chars)
CACHE_FILES = 400        # keep the newest; a long evening is a few hundred chunks
TIMEOUT = 25             # seconds to wait for the voice service


class Unavailable(Exception):
    """The voice service can't be used right now (not installed, or offline)."""


def installed() -> bool:
    return importlib.util.find_spec("edge_tts") is not None


def _edge(text: str, voice: str, dest: Path) -> None:
    try:
        import edge_tts
    except ImportError:
        raise Unavailable("edge-tts is not installed — run: uv sync")

    async def run():
        await asyncio.wait_for(edge_tts.Communicate(text, voice).save(str(dest)), TIMEOUT)

    asyncio.run(run())


_guard = threading.Lock()
_locks: Dict[str, threading.Lock] = {}


def synthesize(text: str, voice: str, cache_dir: Path,
               engine: Optional[Callable[[str, str, Path], None]] = None) -> Path:
    """The mp3 for ``text`` in ``voice`` (made now, or from the cache)."""
    if voice not in VOICES:
        raise ValueError(f"unknown voice {voice!r}")
    text = " ".join(str(text).split())[:MAX_CHARS]
    if not text:
        raise ValueError("nothing to read")
    key = hashlib.sha1(f"{voice}\n{text}".encode("utf-8")).hexdigest()
    out = Path(cache_dir) / f"{key}.mp3"
    with _guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:                       # two players asking for the same beat: made once
        if out.is_file() and out.stat().st_size:
            out.touch()
            return out
        out.parent.mkdir(parents=True, exist_ok=True)
        part = out.with_suffix(".part")
        try:
            (engine or _edge)(text, voice, part)
        except Unavailable:
            part.unlink(missing_ok=True)
            raise
        except Exception as e:       # offline, service refused, timed out...
            part.unlink(missing_ok=True)
            raise Unavailable(f"the online voice service didn't answer ({type(e).__name__}: {e})")
        if not part.is_file() or not part.stat().st_size:
            part.unlink(missing_ok=True)
            raise Unavailable("the online voice service sent no audio")
        part.replace(out)
    with _guard:
        _locks.pop(key, None)
    _prune(out.parent)
    return out


def _prune(cache_dir: Path) -> None:
    files = sorted(cache_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[CACHE_FILES:]:
        old.unlink(missing_ok=True)
