"""The music engine: written scores for a sampled orchestra, and everything that makes,
checks and judges them. It imports nothing from the game; the game reaches it through
lib/score_music.py (campaign music: themes, anthems, places, a boss's stages), and the
table plays the files it writes.

    arrangement   the score format (JSON), its critic (check), fix, play
    orchestra     the sampled orchestra: parts, ranges, levels, the real choirs
    music_compose tunes (the leitmotif generator, written tunes), rendering helpers
    tune_score    a melody scored against thousands of real tunes
    host_judge    the host's taste, approximated: blind tune and finals judging
    sf2write      building a SoundFont from recordings
    devices, music_rate, music_library   character devices, an audio rater, the CC library

The old module names (lib/arrangement.py, ...) are aliases of these.
"""
import hashlib
import re


def slug(name: str) -> str:
    """A file-name stem for a piece. A name with letters outside a-z (קסטרל)
    gets a short fingerprint of the whole name, or every Hebrew name would come
    out as the same "piece" and overwrite the others' music."""
    name = str(name)
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40]
    if re.fullmatch(r"[\x00-\x7f]*", name) and base:
        return base
    tag = hashlib.sha1(name.strip().encode("utf-8")).hexdigest()[:8]
    return f"{base}-{tag}" if base else f"piece-{tag}"
