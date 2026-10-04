#!/usr/bin/env python3
"""A character's theme played by an orchestra of recorded instruments, not by an AI.

The tune comes from lib/music_compose.py's leitmotif (the notes); this arranges it
(harmony, bass, brass, choir, timpani, cymbals) and plays the arrangement through
a SoundFont of real instrument recordings (MuseScore_General: free, MIT licensed),
then puts the orchestra in a concert hall (a convolution reverb). No model, no
GPU: seconds on any computer, the same notes every time.

  python3 lib/orchestra.py "Kestrel" --class Barbarian --stage 3 --out kestrel.ogg

The arrangement grows with the character's story (character_arcs): a lone horn at
the seed of their story; strings and horns for the theme; brass and choir when
heroic; the legendary version, the whole orchestra, at the finale.
"""

import argparse
import math
import os
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import music_compose  # noqa: E402

SF2_URL = "https://ftp.osuosl.org/pub/musescore/soundfont/MuseScore_General/MuseScore_General.sf2"
SF2 = Path(os.environ.get("ORCHESTRA_SF2") or Path.home() / ".cache" / "gm-orchestra" / "MuseScore_General.sf2")
RATE = 44100

# channel: (bank, preset, pan 0..127, volume 0..127)   (General MIDI numbering)
PARTS = {
    "violins": (0, 48, 50, 112),      # Strings Fast: the tune
    "flutes": (0, 73, 70, 80),        # an octave above it, when the theme comes home
    "horns": (0, 60, 74, 118),        # French horns: the tune, an octave below
    "trumpets": (0, 56, 84, 96),      # the tune, from the climb on
    "strings": (0, 49, 40, 92),       # Strings Slow: the chords
    "tremolo": (0, 44, 46, 84),       # Strings Tremolo: the intro, the climax
    "choir": (0, 52, 64, 90),         # Choir Aahs: the chords, heroic and up
    "cellos": (0, 42, 30, 112),       # the bass line (the ostinato, when it drives)
    "basses": (0, 43, 36, 104),       # Contrabass: an octave under the cellos
    "trombones": (0, 57, 90, 92),     # root and fifth
    "tuba": (0, 58, 80, 96),
    "timpani": (0, 47, 64, 118),
    "kit": (128, 48, 64, 100),        # Orchestra Kit: bass drum, snare, cymbals
    # (more colours, for arrangements: lib/arrangement.py)
    "violins2": (0, 48, 76, 100),     # a second violin section, right of centre
    "piccolo": (0, 72, 72, 76),
    "oboe": (0, 68, 58, 90),
    "english_horn": (0, 69, 60, 90),
    "clarinets": (0, 71, 54, 90),
    "bassoons": (0, 70, 70, 100),
    "brass": (0, 61, 64, 100),        # Brass Section: a big, blended brass chord
    "harp": (0, 46, 36, 96),
    "celesta": (0, 8, 80, 84),
    "glockenspiel": (0, 9, 84, 80),
    "bells": (0, 14, 70, 96),         # Tubular Bells: a tolling bell
    "organ": (0, 19, 64, 92),         # Church Organ
    "pizzicato": (0, 45, 44, 96),     # Strings Pizzicato
    "taiko": (0, 116, 64, 120),       # Taiko drums: war drums
    "toms": (0, 117, 58, 104),        # Melodic Tom
    "reverse_cymbal": (0, 119, 64, 96),
    "solo_violin": (0, 40, 70, 110),  # one violin, alone: exposed, quick, edgy
}
DRUMS = {"kit"}
LEAD_DB = 4.0          # the tune's notes, mixed this much over the rest
BASS_DRUM, CRASH = 35, 49
STAGES = ("seed", "theme", "heroic", "legendary")

# How fast each kind of tune goes, at the legendary pace (the unit's beat: a quarter,
# or a dotted quarter in 6/8).
TEMPO = {"fanfare": 76, "bugle": 72, "ostinato": 64, "soaring": 60, "hymn": 54}
PULSED = {"ostinato", "fanfare", "bugle"}     # their bass drives in eighths; the others sustain

# Which instruments are playing, by the character's stage (0 seed .. 3 legendary).
LAYERS = {
    0: {"horns"},
    1: {"horns", "violins", "strings", "cellos", "basses", "timpani"},
    2: {"horns", "violins", "strings", "cellos", "basses", "timpani", "trumpets", "trombones",
        "tuba", "choir", "kit"},
    3: set(PARTS),
}


# --- harmony ---
def _triads(scale: List[int]) -> List[Tuple[int, frozenset]]:
    """The scale's major and minor triads: (degree, pitch classes)."""
    out = []
    for i in range(7):
        r, third, fifth = scale[i], scale[(i + 2) % 7], scale[(i + 4) % 7]
        if (fifth - r) % 12 == 7 and (third - r) % 12 in (3, 4):
            out.append((i, frozenset({r % 12, third % 12, fifth % 12})))
    return out


PRIOR = {0: 0.5, 3: 0.5, 6: 0.5, 4: 0.35, 5: 0.3, 1: 0.15, 2: 0.0}
CADENCE = {4: 0.4, 6: 0.4, 3: 0.25}           # into the tonic: V, bVII (the epic one), IV


def _spans(tune: dict) -> List[Tuple[float, float]]:
    """Where the chords change: every half bar (a bar in 3/4), after the pickup."""
    bar, total, pickup = tune["bar"], sum(b for _, b in tune["notes"]), tune.get("pickup", 0)
    step = bar / 2 if tune["meter"] != "3/4" else bar
    spans, t = [], float(pickup)
    while t < total - 1e-6:
        spans.append((t, min(total, t + step)))
        t += step
    return spans


def _onsets(tune: dict) -> List[Tuple[float, float, int]]:
    out, t = [], 0.0
    for st, b in tune["notes"]:
        out.append((t, b, st))
        t += b
    return out


def harmonize(tune: dict) -> List[Tuple[float, float, int, frozenset]]:
    """A chord for each span: the progression that best fits the tune (its strong
    notes in the chord), moves well (V-I, bVII-I) and ends home. [(start, end,
    degree, pitch classes)] in units."""
    scale = tune["scale"] if isinstance(tune["scale"], list) else music_compose._scale(tune["scale"])
    chords = _triads(scale)
    notes, spans = _onsets(tune), _spans(tune)
    fit = []
    for a, b in spans:
        row = []
        for deg, pcs in chords:
            s = PRIOR.get(deg, 0)
            for t0, d, st in notes:
                w = min(b, t0 + d) - max(a, t0)
                if w <= 0:
                    continue
                strong = 2.0 if t0 <= a + 1e-6 else 1.0
                s += w * strong * (1.0 if st % 12 in pcs else -0.8)
            row.append(s)
        fit.append(row)
    n, k = len(spans), len(chords)
    # Viterbi over (chord, how many spans it has held): a chord held past a bar and a
    # half costs, so the harmony moves under the long notes as a film score's does.
    R = 4
    neg = float("-inf")
    best = [[fit[0][j] + (1.0 if chords[j][0] == 0 else 0) if r == 1 else neg for r in range(R + 1)]
            for j in range(k)]
    back = []
    for i in range(1, n):
        row = [[neg] * (R + 1) for _ in range(k)]
        arg = [[None] * (R + 1) for _ in range(k)]
        for j, (deg, _) in enumerate(chords):
            last = i == n - 1
            for p in range(k):
                for r in range(1, R + 1):
                    if best[p][r] == neg:
                        continue
                    if p == j:
                        nr = min(R, r + 1)
                        s = best[p][r] - (0.5 * (nr - 2) if nr > 2 and not last else 0)
                    else:
                        nr = 1
                        s = best[p][r] + (CADENCE.get(chords[p][0], 0) if deg == 0 else 0)
                    s += fit[i][j] + (6 if last and deg == 0 else 0)
                    if s > row[j][nr]:
                        row[j][nr], arg[j][nr] = s, (p, r)
        best = row
        back.append(arg)
    j, r = max(((j, r) for j in range(k) for r in range(1, R + 1)), key=lambda x: best[x[0]][x[1]])
    path = [j]
    for arg in reversed(back):
        j, r = arg[j][r]
        path.append(j)
    path.reverse()
    return [(a, b, chords[j][0], chords[j][1]) for (a, b), j in zip(spans, path)]


def _root(scale: List[int], deg: int) -> int:
    return scale[deg] % 12


def _in_range(pc: int, lo: int, hi: int) -> int:
    n = lo + (pc - lo) % 12
    return n if n <= hi else n - 12


def _voicing(pcs: frozenset, root: int, prev: Optional[List[int]], lo: int, hi: int) -> List[int]:
    """Four close voices of the chord in [lo, hi], moving as little as they can."""
    cands = []
    for bottom in sorted(pcs):
        n0 = _in_range(bottom, lo, lo + 11)
        v = [n0]
        while len(v) < 3:
            nxt = v[-1] + 1
            while nxt % 12 not in pcs:
                nxt += 1
            v.append(nxt)
        v.append(v[0] + 12)
        if v[-1] <= hi:
            cands.append(v)
    if prev is None:
        return min(cands, key=lambda v: abs(v[0] % 12 - root % 12))
    return min(cands, key=lambda v: sum(abs(a - b) for a, b in zip(v, prev)))


# --- the score ---
class Score:
    def __init__(self):
        self.events: List[Tuple[float, int, str, int, int]] = []   # (seconds, on?, part, key, vel)

    def note(self, part: str, key: int, start: float, length: float, vel: float,
             gain_db: float = 0.0) -> None:
        """``gain_db``: this note's layer is mixed that much louder (the tune's notes:
        LEAD_DB), as "part:dB"."""
        if length <= 0:
            return
        vel = int(max(1, min(127, vel)))
        if gain_db:
            part = f"{part}:{gain_db:g}"
        self.events.append((start, 1, part, key, vel))
        self.events.append((start + length, 0, part, key, 0))


def arrange(tune: dict, stage: int = 3, dark: int = 0) -> Tuple[Score, float]:
    """The orchestra's score for a tune at a stage of the story -> (score, seconds)."""
    meter, bar, kind = tune["meter"], tune["bar"], tune["kind"]
    beat_units = 3 if meter == "6/8" else 1
    bpm = TEMPO.get(kind, 66) * (0.92 if stage >= 3 else 1.0) * (0.9 if dark else 1.0)
    unit = 60.0 / bpm / beat_units                             # seconds per unit
    layers = LAYERS[max(0, min(3, stage))]
    scale = tune["scale"] if isinstance(tune["scale"], list) else music_compose._scale(tune["scale"])
    key = tune["key"]
    notes = _onsets(tune)
    total = sum(b for _, b in tune["notes"])
    top_i = max(range(len(notes)), key=lambda i: notes[i][2])
    climax, climax_end = notes[top_i][0], notes[top_i][0] + notes[top_i][1]
    last = notes[-1][0]
    intro = 2 * bar if stage >= 2 else (bar if stage == 1 else 0)
    T = lambda u: (intro + u) * unit                           # noqa: E731  units -> seconds
    sc = Score()

    def level(u: float) -> float:                              # 0.45 .. 1: the build to the climax
        if u >= climax:
            return 1.0
        return 0.45 + 0.55 * (u / max(climax, 1e-6)) ** 1.3

    def on(part: str, u: float) -> bool:                       # who plays, and from when
        if part not in layers:
            return False
        if stage < 3:
            return True
        return {"trumpets": u >= 0.6 * climax, "trombones": u >= 0.45 * climax,
                "tuba": u >= 0.45 * climax, "choir": u >= 0.3 * climax,
                "flutes": u >= climax_end, "kit": u >= 0.45 * climax}.get(part, True)

    # The tune.
    for i, (u, d, st) in enumerate(notes):
        k, start, length = key + st, T(u), d * unit - 0.03
        v = 70 + 50 * level(u)
        held = d >= 2 * beat_units
        if on("violins", u):
            sc.note("violins", k, start, length, v, LEAD_DB)
        if on("horns", u):
            sc.note("horns", k - 12, start, length, v + (8 if stage == 0 else 0), LEAD_DB)
        if on("trumpets", u):
            sc.note("trumpets", k, start, length, v - 6 + (10 if held else 0), LEAD_DB)
        if on("flutes", u) and k + 12 <= 96:
            sc.note("flutes", k + 12, start, length, v - 10, LEAD_DB)

    # The chords, the bass, the low brass.
    prog = harmonize(tune)
    prev = None
    end_s = T(total)
    for a, b, deg, pcs in prog:
        root = _root(scale, deg)
        start, length = T(a), (b - a) * unit
        final = b >= total - 1e-6
        if final:
            length = end_s - start
        v = 50 + 45 * level(a)
        voice = _voicing(pcs, key % 12 + root, prev, 52, 72)
        prev = voice
        for n in voice:
            if on("strings", a):
                sc.note("strings", n, start, length, v)
            if on("choir", a):
                sc.note("choir", n + 12 if n < 57 else n, start, length, v - 8)
        bass = _in_range((key + root) % 12, 36, 47)
        if on("cellos", a):
            if kind in PULSED and not final:
                step = 1 if meter == "6/8" else 0.5
                t, i = a, 0
                while t < b - 1e-6:
                    accent = (t - tune.get("pickup", 0)) % (bar / 2 if meter != "3/4" else bar) < 1e-6
                    sc.note("cellos", bass, T(t), step * unit * 0.6, (v + (14 if accent else 0)) * 1.05)
                    t, i = t + step, i + 1
            else:
                sc.note("cellos", bass, start, length, v + 10)
        if on("basses", a):
            sc.note("basses", bass - 12 if bass - 12 >= 28 else bass, start, length, v + 8)
        if on("trombones", a):
            sc.note("trombones", _in_range((key + root) % 12, 45, 56), start, length, v)
            sc.note("trombones", _in_range((key + root + 7) % 12, 50, 61), start, length, v - 6)
        if on("tuba", a):
            sc.note("tuba", _in_range((key + root) % 12, 31, 42), start, length, v + 4)
        # Timpani and bass drum on the strong beats.
        downbeat = abs(((a - tune.get("pickup", 0)) / bar) % 1) < 1e-6
        if on("timpani", a) and (downbeat or final):
            sc.note("timpani", _in_range((key + root) % 12, 40, 51), start, 1.2, v + 18)
        if on("kit", a) and downbeat:
            sc.note("kit", BASS_DRUM, start, 1.0, v + 5)

    tonic_timp = _in_range(key % 12, 40, 51)

    def roll(t0: float, t1: float, v0: float, v1: float) -> None:
        n = max(1, int((t1 - t0) / 0.11))             # (a swelling rumble, not a rattle)
        for i in range(n):
            f = i / n
            sc.note("timpani", tonic_timp, t0 + i * 0.11, 0.28, v0 + (v1 - v0) * f ** 1.5)

    # The intro: the pulse and a timpani roll swelling into the theme.
    if intro:
        if "tremolo" in layers:
            for n in (_in_range(key % 12, 48, 59), _in_range((key + 7) % 12, 52, 63)):
                sc.note("tremolo", n, 0, T(0) + 0.3, 70)
        if "timpani" in layers:
            roll(0, T(0) - 0.05, 25, 92 if stage >= 3 else 80)
        if "cellos" in layers and kind in PULSED:
            step = 1 if meter == "6/8" else 0.5
            t = 0.0
            while t < intro - 1e-6:
                acc = t % (bar / 2 if meter != "3/4" else bar) < 1e-6
                sc.note("cellos", _in_range(key % 12, 36, 47), t * unit, step * unit * 0.6, 72 + (16 if acc else 0))
                t += step
        if "choir" in layers and stage >= 3:
            sc.note("choir", _in_range(key % 12, 57, 68), bar * unit, bar * unit, 80)
            sc.note("choir", _in_range((key + 7) % 12, 60, 71), bar * unit, bar * unit, 80)

    # The climax: a roll into it, tremolo under it, a cymbal on it.
    if stage >= 2:
        roll(max(T(0), T(climax) - bar * unit * 0.5), T(climax) - 0.05, 60, 120)
        if "tremolo" in layers:
            sc.note("tremolo", _in_range(key % 12, 48, 59), T(climax), (climax_end - climax) * unit, 90)
        sc.note("kit", CRASH, T(climax), 3.0, 120)
        sc.note("kit", CRASH, T(last), 3.0, 124)
    # The last note: held, a roll under it, and the final stroke.
    if "timpani" in layers and stage >= 1:
        roll(T(last) + 0.4, end_s - 0.1, 70, 122)
        sc.note("timpani", tonic_timp, end_s - 0.05, 2.0, 127)
        if "kit" in layers:
            sc.note("kit", BASS_DRUM, end_s - 0.05, 2.0, 127)
    return sc, end_s


# --- the sound ---
def fetch(dest: Path = SF2, quiet: bool = False) -> Path:
    """The SoundFont: downloaded once (215 MB) to ~/.cache/gm-orchestra."""
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(".part")
    if not quiet:
        print(f"[orchestra] downloading the instruments (215 MB, once): {SF2_URL}", file=sys.stderr, flush=True)
    with urllib.request.urlopen(SF2_URL, timeout=60) as r, open(part, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    part.replace(dest)
    return dest


def available() -> bool:
    try:
        import tinysoundfont  # noqa: F401
    except ImportError:
        return False
    return SF2.is_file()


# How loud each instrument's recording is (dB, a note at velocity 100, at its channel
# volume, against the median): measured from MuseScore_General. The sound set's
# instruments differ by 23 dB (the horns are loud recordings, the choir and the
# tremolo strings quiet ones), so each part is mixed at -LOUDNESS + BALANCE: the
# same velocity is the same loudness, then the orchestra's own balance.
LOUDNESS = {
    "tremolo": -11.3, "glockenspiel": -11.1, "celesta": -10.3, "piccolo": -8.0, "choir": -6.9,
    "clarinets": -5.4, "violins2": -4.5, "strings": -4.4, "flutes": -4.0, "pizzicato": -3.5,
    "organ": -2.6, "toms": -2.6, "violins": -0.8, "bells": 0.0, "basses": 0.0, "kit": 0.2,
    "harp": 0.2, "oboe": 0.4, "bassoons": 1.9, "english_horn": 2.7, "reverse_cymbal": 5.4,
    "taiko": 5.5, "trumpets": 5.7, "brass": 6.6, "timpani": 6.9, "tuba": 8.2, "cellos": 8.6,
    "trombones": 9.7, "horns": 11.8, "solo_violin": 2.9,
}
# How long each instrument's recording takes to speak (seconds to half its level), and
# where it plays (MIDI, its practical range): for the score critic (arrangement.check).
SPEAKS = {"choir": 0.18, "strings": 0.48, "violins": 0.50, "violins2": 0.26, "english_horn": 0.42,
          "cellos": 0.24, "tremolo": 0.16, "organ": 0.10, "oboe": 0.12, "brass": 0.08, "horns": 0.06}
RANGES = {
    "violins": (55, 100), "violins2": (55, 96), "strings": (36, 96), "tremolo": (36, 96),
    "pizzicato": (28, 96), "cellos": (36, 76), "basses": (28, 60), "flutes": (60, 96),
    "piccolo": (74, 108), "oboe": (58, 91), "english_horn": (52, 81), "clarinets": (50, 91),
    "bassoons": (34, 72), "horns": (41, 77), "trumpets": (54, 82), "trombones": (40, 72),
    "tuba": (28, 58), "brass": (36, 84), "choir": (40, 81), "harp": (24, 103),
    "celesta": (60, 108), "glockenspiel": (79, 108), "bells": (60, 77), "organ": (24, 96),
    "timpani": (38, 55), "solo_violin": (55, 100),
}
# How late each instrument's recording is heard after its note starts (seconds to come
# within 9 dB of its full level, measured from MuseScore_General, less the ~20 ms a
# listener forgives): play() starts its notes that much early, so instruments
# playing together are heard together, on the beat (the violins doubling a quick
# clarinet were ~150 ms behind it). The reverse cymbal is written to swell into the
# beat; the string pad, which holds chords, is moved at most 250 ms. The host, on a
# tune they knew (Ode to Joy): "clearly better". (Another sound set's instruments need
# their own measurement.)
ADVANCE = {"violins": 0.15, "violins2": 0.18, "cellos": 0.09, "tremolo": 0.115, "choir": 0.13,
           "strings": 0.25, "trombones": 0.02, "organ": 0.015, "flutes": 0.012, "piccolo": 0.01,
           "solo_violin": 0.032}
# How much room each recording carries already (dB: its energy after a short note is
# released, against the note's), measured from MuseScore_General for the instruments
# whose sound stops when they do (bowed strings, the choir and ringing instruments
# are left out: their own ring isn't a room). The hall adds about HALL_ROOM to a dry
# one; each part is sent to it just enough to end at that same room, so the orchestra
# sounds like one place (the host heard recordings with their own room as a different
# acoustic: "the difference is mainly in the acoustics").
ROOM = {"flutes": -20.8, "horns": -17.5, "trumpets": -39.3, "trombones": -25.5, "tuba": -25.6,
        "piccolo": -22.3, "oboe": -24.1, "english_horn": -34.2, "clarinets": -33.4, "bassoons": -25.6,
        "brass": -20.9, "organ": -15.4, "pizzicato": -24.9, "taiko": -20.9, "toms": -28.9}
HALL_ROOM = -12.8


def send_db(room: Optional[float]) -> float:
    """The hall send (dB) for a recording carrying ``room`` dB of its own room."""
    if room is None:
        return 0.0
    need = 10 ** (HALL_ROOM / 10) - 10 ** (room / 10)
    return -12.0 if need <= 10 ** ((HALL_ROOM - 12) / 10) else max(-12.0, 10 * math.log10(need) - HALL_ROOM)


BALANCE = {
    "horns": 2, "trumpets": 3, "trombones": 2, "brass": 3, "violins": 1, "strings": -3,
    "tremolo": -2, "choir": 3, "timpani": 2, "taiko": 3, "glockenspiel": -2, "piccolo": -2,
    "reverse_cymbal": -2,
}


def level_db(part: str, mix: Optional[Dict[str, float]] = None) -> float:
    """The gain a part is mixed at (dB): measured loudness evened out, the
    orchestra's balance, and the piece's own "mix" adjustments."""
    return -LOUDNESS.get(part, 0.0) + BALANCE.get(part, 0) + float((mix or {}).get(part, 0))


_DRY = None


def _dry_type():
    """An array type for play()'s dry mix that carries its hall send (``.send``)."""
    global _DRY
    if _DRY is None:
        import numpy as np

        class Dry(np.ndarray):
            send = None
        _DRY = Dry
    return _DRY


def play(score: Score, seconds: float, sf2: Path = SF2, rate: int = RATE,
         mix: Optional[Dict[str, float]] = None, align: bool = True):
    """The score through the SoundFont -> stereo float32 (n, 2), dry. Each part (and
    each layer of one: "horns:4", the tune's notes) is played on its own and mixed
    at its level (level_db, plus the layer's dB), so a piece can use any number."""
    import numpy as np
    import tinysoundfont
    syn = tinysoundfont.Synth(gain=-12, samplerate=rate)
    sfid = syn.sfload(str(sf2))
    total = int((seconds + 0.5) * rate)
    out = np.zeros((total, 2), dtype="float32").view(_dry_type())
    out.send = np.zeros((total, 2), dtype="float32")      # what goes to the hall (see ROOM)
    groups: Dict[str, list] = {}
    for e in score.events:
        groups.setdefault(e[2], []).append(e)
    for name, events in groups.items():
        part, _, layer = name.partition(":")
        early = ADVANCE.get(part, 0.0) if align else 0.0
        if early:                                           # (heard on the beat: see ADVANCE)
            events = [(max(0.0, t - early), *rest) for t, *rest in events]
        bank, preset, pan, vol = PARTS[part]
        ch = 9 if part in DRUMS else 0
        syn.program_select(ch, sfid, bank, preset, part in DRUMS)
        syn.control_change(ch, 7, vol)
        syn.control_change(ch, 10, pan)
        stem = np.zeros((total, 2), dtype="float32")
        pos = 0
        for t, is_on, _, key, vel in sorted(events, key=lambda e: (e[0], e[1])):
            at = min(total, int(t * rate))
            if at > pos:
                stem[pos:at] = np.frombuffer(syn.generate(at - pos), dtype="float32").reshape(-1, 2)
                pos = at
            if is_on:
                syn.noteon(ch, key, vel)
            else:
                syn.noteoff(ch, key)
        if pos < total:
            stem[pos:] = np.frombuffer(syn.generate(total - pos), dtype="float32").reshape(-1, 2)
        syn.sounds_off(ch)
        syn.generate(256)                                   # (let the cut voices go)
        gain = level_db(part, mix) + (float(layer) if layer else 0.0)
        out += stem * np.float32(10 ** (gain / 20))
        out.send += stem * np.float32(10 ** ((gain + send_db(ROOM.get(part))) / 20))
    return out


def hall(dry, rate: int = RATE, rt60: float = 2.3, wet: float = 0.28, seed: int = 7,
         loop_at: Optional[int] = None):
    """A concert hall: the dry orchestra (its hall send, when play() made it: see
    ROOM) convolved with a synthetic hall response
    (early reflections, then a diffuse tail that darkens as it decays); the tail
    is left to ring after the last chord, or, for a loop (``loop_at``: its length
    in samples), rings on over its start, so the seam can't be heard."""
    import numpy as np
    rng = np.random.default_rng(seed)
    n = int(rt60 * 1.3 * rate)
    t = np.arange(n) / rate
    decay = np.exp(-6.91 * t / rt60)
    ir = np.zeros((n, 2))
    for c in range(2):
        noise = rng.standard_normal(n)
        lo = np.empty(n)                                   # darker as it decays: a one-pole lowpass
        a = 0.0
        alpha = np.clip(0.55 - 0.45 * t / rt60, 0.08, 0.55)
        for i in range(0, n, 64):
            seg = noise[i:i + 64]
            k = alpha[i]
            for j, x in enumerate(seg):
                a += k * (x - a)
                lo[i + j] = a
        ir[:, c] = lo * decay
        for ms, g in ((11, .6), (19, .45), (27, .4), (37, .3), (53, .25)):     # early reflections
            i = int((ms + 3 * c) * rate / 1000)
            ir[i, c] += g * (1 if (ms + c) % 2 else -1)
    pre = int(0.018 * rate)
    ir = np.vstack([np.zeros((pre, 2)), ir])
    ir /= np.sqrt((ir ** 2).sum(axis=0))
    tail = len(ir)
    size = 1 << int(math.ceil(math.log2(len(dry) + tail)))
    out = np.zeros((len(dry) + tail, 2))
    send = getattr(dry, "send", None)
    send = dry if send is None else send
    dry = np.asarray(dry)
    for c in range(2):
        y = np.fft.irfft(np.fft.rfft(send[:, c], size) * np.fft.rfft(ir[:, c], size), size)
        out[:, c] = y[:len(dry) + tail]
    mix = out * wet
    mix[:len(dry)] += dry * (1 - wet * 0.5)
    if loop_at:                                            # a loop: what rings past its end
        n = loop_at                                        # sounds over its start
        for at in range(n, len(mix), n):
            seg = mix[at:at + n]
            mix[:len(seg)] += seg
        return mix[:n].astype("float32")
    end = len(dry) + int(rt60 * rate)                      # ring out for one decay, then stop
    return mix[:end].astype("float32")


def master(x, rate: int = RATE, loop: bool = False):
    """Loudness like the rest of the table's music, no clipped peaks, a soft fade."""
    import numpy as np
    mono = x.mean(axis=1)
    now = music_compose.loudness_db(mono, rate)
    gain = 10 ** (min(music_compose.LOUDNESS_DB - now, music_compose.MAX_GAIN_DB) / 20)
    x = x * np.float32(gain)
    peak = np.abs(x).max(axis=1)
    limited = music_compose.limit(peak, rate)
    g = np.where(peak > 1e-9, limited / np.maximum(peak, 1e-9), 1.0).astype("float32")
    x = x * g[:, None]
    if not loop:                                            # (a loop has no ends)
        n = int(rate * 1.2)
        x[-n:] *= np.linspace(1, 0, n, dtype="float32")[:, None] ** 2
    return x


def render(seed: str, cls: str = "", stage: int = 3, dark: int = 0, rate: int = RATE,
           sf2: Path = SF2):
    """A character's theme by the orchestra -> (stereo float32 samples, rate)."""
    tune = music_compose.leitmotif(seed, "major", cls, stage=stage, dark=dark)
    score, seconds = arrange(tune, stage, dark)
    return master(hall(play(score, seconds, sf2, rate), rate), rate), rate


def main() -> None:
    ap = argparse.ArgumentParser(description="A character's theme, played by a sampled orchestra.")
    ap.add_argument("name", help="the character (their name is their tune's seed)")
    ap.add_argument("--class", dest="cls", default="")
    ap.add_argument("--stage", type=int, default=3, help="0 seed, 1 theme, 2 heroic, 3 legendary")
    ap.add_argument("--dark", type=int, default=0)
    ap.add_argument("--out", required=True, help="a file, or a folder (named for the character)")
    ap.add_argument("--fetch", action="store_true", help="download the instruments if missing")
    if "--fetch-only" in sys.argv[1:]:
        print(fetch())
        return
    a = ap.parse_args()
    if a.fetch or not SF2.is_file():
        fetch()
    samples, rate = render(a.name, a.cls, a.stage, a.dark)
    out = Path(a.out)
    if out.is_dir():
        import composer
        out = out / f"anthem-{composer.slug(a.name)}-orchestra-{STAGES[max(0, min(3, a.stage))]}.ogg"
    path = music_compose.write(samples, rate, out)
    print(f"{path} ({len(samples) / rate:.1f}s)")


if __name__ == "__main__":
    main()
