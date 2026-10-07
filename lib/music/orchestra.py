#!/usr/bin/env python3
"""A character's theme played by an orchestra of recorded instruments, not by an AI.

The tune comes from lib/music_compose.py's leitmotif (the notes); this arranges it
(harmony, bass, brass, choir, timpani, cymbals) and plays the arrangement through
a SoundFont of real instrument recordings (MuseScore_General: free, MIT licensed - and,
for some parts, libraries of their own, fetched once: lib/music/CREDITS.md), then puts the
orchestra in a concert hall (a convolution reverb). No model, no
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # (lib/)
from music import music_compose  # noqa: E402

SF2_URL = "https://ftp.osuosl.org/pub/musescore/soundfont/MuseScore_General/MuseScore_General.sf2"
SF2 = Path(os.environ.get("ORCHESTRA_SF2") or Path.home() / ".cache" / "gm-orchestra" / "MuseScore_General.sf2")
RATE = 44100
# A real chorus (the Sonatina Symphonic Orchestra's men's and women's sections, CC
# Sampling Plus 1.0): a recording for every note, long natural loops - the host heard
# its men as people where the sound set's choir, stretched low, read as an organ.
# Built once from the recordings into its own SoundFont (fetch_choir); parts naming it
# play from it, or from the sound set's choir if it can't be had.
CHOIR_SF2 = Path(os.environ.get("ORCHESTRA_CHOIR_SF2") or SF2.parent / "sso-chorus.sf2")
# Soft vowels: Mihai Sorohan's Vowel Ensemble (a mixed choir, a recording on every white
# note C3-C6; renders free for any music, the recordings not to be passed on - so they
# are fetched here, never kept in the repo). Its "oo" and "oh" were heard as people
# where the sound set's "oo", stretched between few recordings, was heard as instruments.
VOWEL_SF2 = Path(os.environ.get("ORCHESTRA_VOWEL_SF2") or SF2.parent / "vowel-choir.sf2")
VOWEL_URL = "https://www.mediafire.com/file/bhdzds4tgtsocdp/Vowel_Choir_SFZ.zip"
# Real orchestral percussion: a gong (a big tam-tam, the only real gong here - the kit's
# "gong" is a General MIDI crash cymbal), an anvil, a brake drum and an orchestral bass
# drum, from Versilian Studios' VSCO 2 Community Edition and its Versilian Community Sample
# Library (both CC0 1.0: public domain). Built once from the recordings into its own
# SoundFont (fetch_percussion), every velocity layer and round-robin they have.
PERC_SF2 = Path(os.environ.get("ORCHESTRA_PERC_SF2") or SF2.parent / "perc.sf2")
VSCO2 = "https://raw.githubusercontent.com/sgossner/VSCO-2-CE/440300901dfe9275fd84e0b7763af1f8443ae62e/"
VCSL = "https://raw.githubusercontent.com/sgossner/VCSL/c1ea7bcc3c7309650ab0da9d15c9cd1fbc4a4c7e/"
# A real electric guitar: Unreal Instruments' "Standard Guitar" (a humbucker recorded DI -
# straight from the guitar, no amp - every note B1-E5 in stereo, its left and right separate
# takes: double-tracked; up to 16 round-robins; sustain and palm-mute, down and up strokes).
# Its readme's terms: "ライセンスフリーです / クレジット表記は不要です" - license free, no
# credit required (and no liability). The sampled GM distortion guitar was heard as "someone
# trying to hurt the guitar": a recording of a distortion with no speaker cabinet, its buzz at
# 2.5-3 kHz as loud as its fundamental, 9 dB over the orchestra there. Here the DI goes
# through an amp and a cabinet in the engine (_guitar_stem), on the whole chord as a real amp
# does, two passes panned hard left and right - the host: "great". Its sustain and palm-mute
# down strokes (3 takes a note, each channel a take of its own) are built once into a
# SoundFont (fetch_guitar); the recordings are fetched, never kept in the repo.
GUITAR_SF2 = Path(os.environ.get("ORCHESTRA_GUITAR_SF2") or SF2.parent / "guitar.sf2")
GUITAR_PAGE = "https://unreal-instruments.wixsite.com/unreal-instruments/standard-guitar"
GUITAR_URL = ("https://drive.usercontent.google.com/download?id=1uoV7icZV1_IjiOGKM7Wm5_K5UkF41Fm3"
              "&export=download&confirm=t")             # (UI_Standard_Guitar.rar, 716 MB)
SSO = "https://raw.githubusercontent.com/peastman/sso/32bbdb169aef636b8216029a2e056424ba7c2abb/Sonatina%20Symphonic%20Orchestra/"

# channel: (bank, preset, pan 0..127, volume 0..127)   (General MIDI numbering)
PARTS = {
    "violins": (0, 48, 50, 112),      # Strings Fast: the tune (a note under SHORT_S: STRINGS_SHORT)
    "flutes": (0, 73, 70, 80),        # an octave above it, when the theme comes home
    "horns": (0, 0, 74, 118, "brass"),   # the horn section (VPO, Westlund's): the tune, an octave below
    "trumpets": (0, 56, 84, 96),      # the tune, from the climb on
    "strings": (0, 49, 40, 92),       # Strings Slow: the chords
    "tremolo": (0, 44, 46, 84),       # Strings Tremolo: the intro, the climax
    "choir": (0, 52, 64, 90),         # Choir Aahs: the chords, heroic and up
    "cellos": (0, 42, 30, 112),       # the bass line (the ostinato, when it drives)
    "basses": (0, 43, 36, 104),       # Contrabass: an octave under the cellos
    "trombones": (0, 2, 90, 92, "brass"),  # the trombone section (VPO, No Budget Orchestra's): root and fifth
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
    "horn_solo": (0, 0, 74, 118, "horn_solo"),  # one horn (VSCO 2 CE's F horn): a tune that must cut through
    "men_choir": (0, 0, 60, 100, "chorus"),   # a real men's chorus, "ah": chant, monks, doom
    "chorus": (0, 2, 64, 100, "chorus"),      # the real chorus, men under women, "ah": present, sacred, epic
    "choir_oo": (0, 0, 66, 100, "vowels"),    # a soft mixed choir on "oo": ethereal, holy, wonder
    "choir_oh": (0, 1, 62, 100, "vowels"),    # the same on "oh": warmer, rounder, a lament
    "gong": (0, 0, 70, 112, "perc"),          # a real tam-tam: one stroke rings ~25 s
    "bass_drum": (0, 1, 58, 112, "perc"),     # the orchestral bass drum (the kit's is a pop kick)
    "anvil": (0, 2, 80, 100, "perc"),         # struck metal: a forge, a machine
    "brake_drum": (0, 3, 48, 100, "perc"),    # a car's brake drum hit with a hammer: dry, clanging metal
    # a real electric guitar through an amp, double-tracked (power chords only): one instrument,
    # two articulations - the same strings, the same amp (a new pick stops what rang)
    "guitar": (0, 0, 64, 100, "guitar"),      # open, ringing: power chords, held or picked
    "guitar_mute": (0, 6, 64, 100, "guitar"), # palm-muted chugs: the chug between the open chords
    # a rock organ: a tonewheel organ, overdriven, through a rotating speaker - synthesized
    # (_organ_stem), not sampled: its bank and preset (GM's Rock Organ) are only its name
    "rock_organ": (0, 18, 64, 100),
}
# Where a part's own sound set can't be had: the sound set's choir; for the percussion, the
# GM kit's nearest (bank, preset, its key): a crash cymbal for the gong, the cowbell, an agogo.
FALLBACK = {"men_choir": (0, 52), "chorus": (0, 52), "choir_oo": (0, 52), "choir_oh": (0, 52),
            "horns": (0, 60), "trombones": (0, 57), "horn_solo": (0, 60),   # (the sound set's horns, trombones)
            "gong": (128, 48, 57), "bass_drum": (128, 48, 35), "anvil": (128, 48, 67), "brake_drum": (128, 48, 56),
            "guitar": (0, 30), "guitar_mute": (0, 30)}   # (the GM distortion guitar, through a cabinet)
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
        self.bends: List[Tuple[float, str, float]] = []             # (seconds, part, semitones)
        self.organ: Dict[str, str] = {}         # the rock organ's "drawbars", "percussion", "speaker"
        self.speaker: List[Tuple[float, bool]] = []     # (seconds, fast?): its rotating speaker switched

    def rotate(self, at: float, fast: bool) -> None:
        """The rock organ's rotating speaker switched to fast (or slow) here: it eases there."""
        self.speaker.append((at, bool(fast)))

    def bend(self, part: str, at: float, semitones: float) -> None:
        """The part's pitch, bent from here on (a slide, a wavering): -12 .. 12."""
        self.bends.append((at, part, max(-12.0, min(12.0, semitones))))

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
        n = max(1, int((t1 - t0) / 0.18))             # (a swelling rumble, not a rattle)
        for i in range(n):
            f = i / n
            sc.note("timpani", tonic_timp, t0 + i * 0.18, 0.45, v0 + (v1 - v0) * f ** 1.5)

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


def fetch_choir(dest: Path = None, quiet: bool = False) -> Path:
    """The real chorus: its 42 recordings (56 MB, once) built into a SoundFont of three
    presets - 0 men (G2-F#4), 1 women (G4-C6), 2 both - with the loops, tuning and
    levels from its own SFZ."""
    dest = dest or CHOIR_SF2
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        return dest
    import re
    import tempfile
    import urllib.parse
    import numpy as np
    import soundfile
    from music import sf2write
    if not quiet:
        print("[orchestra] downloading the chorus (56 MB, once)", file=sys.stderr, flush=True)
    def get(rel):
        with urllib.request.urlopen(SSO + urllib.parse.quote(rel), timeout=60) as r:
            return r.read()
    sfz = get("Chorus - Performance/includes/mixed-chorus.sfz").decode()
    names = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
    def midi(n):
        m = re.fullmatch(r"([a-g])(#?)(-?\d)", n.lower())
        return 12 * (int(m.group(3)) + 1) + names[m.group(1)] + (1 if m.group(2) else 0)
    regions = []
    with tempfile.TemporaryDirectory() as tmp:
        for block in sfz.split("<region>")[1:]:
            kv = dict(re.findall(r"(\w+)=(\S+)", block))
            name = Path(kv["sample"]).name
            wav = Path(tmp) / name
            wav.write_bytes(get(f"Samples-looped/Chorus/{name}"))
            audio, rate = soundfile.read(str(wav), dtype="float32", always_2d=True)   # (any format,
            audio = (np.clip(audio, -1, 1) * 32767).astype("int16")                 # scaled to 16-bit)
            regions.append({"audio": audio, "rate": rate, "key": midi(kv.get("pitch_keycenter") or kv["lokey"]),
                            "ls": int(kv["loop_start"]), "le": int(kv["loop_end"]), "tune": int(kv.get("tune", 0)),
                            "vol": float(kv.get("volume", 0)), "men": "-male-" in name})
    regions.sort(key=lambda r: r["key"])
    loudest = max(r["vol"] for r in regions)
    def zones(rs, lo_ext, hi_ext):
        out = []
        for i, r in enumerate(rs):
            lo = r["key"] if i else min(r["key"], lo_ext)
            hi = r["key"] if i < len(rs) - 1 else max(r["key"], hi_ext)
            out.append({**r, "lo": lo, "hi": hi, "att_cb": round((loudest - r["vol"]) * 10), "release_s": 0.6})
        return out
    men = [r for r in regions if r["men"]]
    women = [r for r in regions if not r["men"]]
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(".part")
    sf2write.write(part, [("Men", zones(men, 40, 69)), ("Women", zones(women, 62, 88)),
                          ("Mixed", zones(men, 40, men[-1]["key"]) + zones(women, women[0]["key"], 88))],
                   "Sonatina Symphonic Orchestra chorus (CC Sampling Plus 1.0)")
    part.replace(dest)
    return dest


def fetch_vowels(dest: Path = None, quiet: bool = False) -> Path:
    """The vowel choir: its zip (160 MB, once), the "oo" (U) and "oh" recordings built into a
    SoundFont - preset 0 "oo", 1 "oh" - with long crossfaded loops (the files have none)."""
    dest = dest or VOWEL_SF2
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        return dest
    import re
    import tempfile
    import zipfile
    import soundfile
    from music import sf2write
    if not quiet:
        print("[orchestra] downloading the vowel choir (160 MB, once)", file=sys.stderr, flush=True)
    names = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    with tempfile.TemporaryDirectory() as tmp:
        zpath = Path(tmp) / "vowels.zip"
        with urllib.request.urlopen(VOWEL_URL, timeout=120) as r, open(zpath, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
        presets = []
        with zipfile.ZipFile(zpath) as z:
            for label, vowel in (("Oo", "U"), ("Oh", "Oh")):
                zones = []
                for n in z.namelist():
                    m = re.search(rf"choir {vowel} samples/{vowel}_([A-G])(\d)_[^/]*\.wav$", n)
                    if not m:
                        continue
                    z.extract(n, tmp)
                    audio, rate = soundfile.read(str(Path(tmp) / n), dtype="float32", always_2d=True)
                    audio, ls, le = sf2write.crossfade_loop(sf2write.to_int16(audio), rate, 0.8, 0.8, 0.3)
                    zones.append({"audio": audio, "rate": rate, "ls": ls, "le": le, "release_s": 0.5,
                                  "key": 12 * (int(m.group(2)) + 1) + names[m.group(1)]})
                zones.sort(key=lambda r: r["key"])
                for i, r in enumerate(zones):          # each recording covers the notes nearest it
                    r["lo"] = r["key"] - 3 if i == 0 else (zones[i - 1]["key"] + r["key"]) // 2 + 1
                    r["hi"] = r["key"] + 3 if i == len(zones) - 1 else (r["key"] + zones[i + 1]["key"]) // 2
                if not zones:
                    raise OSError(f"no {vowel} recordings in the vowel choir's zip")
                presets.append((label, zones))
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(".part")
    sf2write.write(part, presets, "Mihai Sorohan Vowel Ensemble (for renders only)")
    part.replace(dest)
    return dest


# The real percussion, a preset each (PARTS' preset numbers): the key it sounds unaltered
# at (any drum name or "root" in a score plays this key), the keys around it it may be
# pitched to, the velocity layers (the top velocity each plays to, its round-robins - played
# in turn, so a repeated stroke is never the same recording twice), how long a stroke is
# kept ringing, and whether a new stroke stops the last (a drum head struck again). Struck
# percussion is let ring (l.v.): a note's end doesn't stop it. (A struck metal anvil or brake
# drum, and the bass drum, ring 1-6 s; the gong ~25 s, pitched down a few semitones bigger.)
_G, _B = VSCO2 + "Percussion/", VCSL + "Idiophones/Struck%20Idiophones/"
PERC = {
    "gong": {"preset": 0, "key": 50, "lo": 45, "hi": 52, "ring": 26.0, "choke": False,
             "layers": [(50, [_G + "gongHit_p.wav"]), (84, [_G + "gongHit_mf.wav"]),
                        (112, [_G + "gongHit_f.wav"]), (127, [_G + "gongHit_fff.wav"])]},
    "bass_drum": {"preset": 1, "key": 36, "lo": 34, "hi": 38, "ring": 6.5, "choke": True,
                  "layers": [(top, [_G + f"BDrumNewhit_v{v}_rr{r}_Sum.wav" for r in (1, 2)])
                             for v, top in enumerate((24, 44, 60, 76, 92, 108, 127), 1)]},
    "anvil": {"preset": 2, "key": 60, "lo": 58, "hi": 62, "ring": 2.5, "choke": True,
              "layers": [(top, [_B + f"Anvil/Anvil_Hit{h}_v{v}_rr1_Mid.wav" for h in (1, 2)])
                         for v, top in enumerate((64, 100, 127), 1)]},
    "brake_drum": {"preset": 3, "key": 55, "lo": 53, "hi": 57, "ring": 2.0, "choke": True,
                   "layers": [(top, [_B + f"Brake%20Drum/BrakeDrum1_Hammer_v{v}_rr1_Mid.wav"])
                              for v, top in enumerate((64, 100, 127), 1)]},
}
RR_KEYS = 64            # (a part's n-th round-robin is stored n * 64 keys above its own)


def fetch_percussion(dest: Path = None, quiet: bool = False) -> Path:
    """The real percussion: its 27 recordings (32 MB, once) built into a SoundFont of four
    presets (PERC): each stroke trimmed to its ring and faded, played once (not looped),
    the velocity layers levelled to step up at most 3 dB from one to the next (the
    synth's velocity does the rest: a recording's own level jumps up to 20 dB)."""
    dest = dest or PERC_SF2
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        return dest
    import numpy as np
    import soundfile
    import tempfile
    from music import sf2write
    if not quiet:
        print("[orchestra] downloading the percussion (32 MB, once)", file=sys.stderr, flush=True)

    def get(url, tmp):
        wav = Path(tmp) / "stroke.wav"
        with urllib.request.urlopen(url, timeout=60) as r:
            data = r.read(64 << 20)                         # (a stroke is a few MB: no more)
        wav.write_bytes(data)
        audio, rate = soundfile.read(str(wav), dtype="float32", always_2d=True)
        if audio.shape[1] == 1:
            audio = np.repeat(audio, 2, axis=1)
        return audio[:, :2], rate

    def trim(audio, rate, ring):
        mono = np.abs(audio).max(axis=1)
        start = max(0, int(np.argmax(mono > 0.02 * mono.max())) - int(0.004 * rate))
        x = audio[start:start + int(ring * rate)].astype("float64")
        w = int(0.05 * rate)
        env = np.sqrt(np.convolve(x.mean(1) ** 2, np.ones(w) / w, mode="same"))
        live = np.nonzero(env > env.max() * 10 ** (-70 / 20))[0]      # (to 70 dB down)
        x = x[:live[-1] + 1] if len(live) else x
        fade = min(len(x) // 6, int(2.5 * rate))
        x[len(x) - fade:] *= np.cos(np.linspace(0, np.pi / 2, fade))[:, None] ** 2
        return x

    presets = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, p in PERC.items():
            layers = []
            for top, urls in p["layers"]:
                takes = []
                for url in urls:
                    audio, rate = get(url, tmp)
                    takes.append((trim(audio, rate, p["ring"]), rate))
                first = [x[:int(0.5 * r)] for x, r in takes]
                level = float(np.mean([10 * np.log10(np.mean(x ** 2) + 1e-20) for x in first]))
                layers.append((top, takes, level))
            make_up = [0.0] * len(layers)                   # (dB, from the loudest layer down)
            for i in range(len(layers) - 2, -1, -1):
                gap = layers[i + 1][2] + make_up[i + 1] - layers[i][2]
                make_up[i] = gap - min(3.0, gap / 2) if gap > 0 else 0.0
            peak = max(np.abs(x).max() * 10 ** (g / 20) for (_, takes, _), g in zip(layers, make_up) for x, _ in takes)
            zones, vlo = [], 1
            for (top, takes, level), g in zip(layers, make_up):
                gain = 10 ** (g / 20) * 0.95 / peak
                for i, (x, rate) in enumerate(takes):
                    audio = sf2write.to_int16((x * gain).astype("float32"))
                    key = p["key"] + RR_KEYS * i
                    zones.append({"audio": audio, "rate": rate, "key": key, "lo": key - (p["key"] - p["lo"]),
                                  "hi": key + (p["hi"] - p["key"]), "vlo": vlo, "vhi": top, "loop": False,
                                  "ls": 8, "le": len(audio) - 8, "release_s": 1.5,
                                  "excl": p["preset"] + 1 if p["choke"] else 0})
                vlo = top + 1
            presets.append((p["preset"], name, zones))
    presets.sort()
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(".part")
    sf2write.write(part, [(n, z) for _, n, z in presets], "VSCO 2 CE / VCSL percussion (CC0)")
    part.replace(dest)
    return dest


# --- the real strings' short notes, the real brass ---
# Recordings the host chose in blind tests over the sound set's (the strings lab, Oct 2026):
# - short string notes (In the Hall of the Mountain King, "clearly better"): the Sonatina
#   Symphonic Orchestra's staccato 1st violins and basses, VSCO 2 CE's spiccato violas and
#   cellos. The sound set's "Strings Fast" takes 0.16 s to come within 9 dB of its level (these:
#   0.03-0.055 s), so a 0.12-0.2 s note of it sounds 4-12 dB under a long one - smeared;
# - the horn and trombone sections (Ode to Joy, twice "a tad better"): Mattias Westlund's horn
#   section, No Budget Orchestra's trombone section;
# - a solo horn on a tune that must cut through, the brass drier than the strings ("6b is the
#   best"): VSCO 2 CE's F horn.
# The recordings as Virtual Playing Orchestra 3 (Paul Battersby) gathers them - trimmed ("-PB"),
# looped, described by its SFZ files - from a mirror pinned to one commit (FLAC: the same audio
# as VPO's WAVs, compared sample for sample, but without their loop points, which are kept here:
# VPO_LOOPS); the F horn from VSCO 2 CE's own SFZ branch, pinned. Each keeps its licence:
#   Sonatina Symphonic Orchestra (Mattias Westlund): Creative Commons Sampling Plus 1.0;
#   VSCO 2 Community Edition (Versilian Studios): CC0 1.0 (public domain);
#   Mattias Westlund's horn section ("Brass 2011-11-07 Horns Sustain"): CC BY-SA 3.0;
#   No Budget Orchestra (ssj71), the trombones: CC BY-SA 4.0;
#   VPO's SFZ files and edits: free to use and pass on with credit (virtualplaying.com).
# The attribution licences ask for credit: lib/music/CREDITS.md. Fetched, never kept in the repo.
VPO = "https://raw.githubusercontent.com/studiorack/virtual-playing-orchestra/9ab3329bb136834d33dcabb734b76053d5606b83/"
VSCO2_SFZ = "https://raw.githubusercontent.com/sgossner/VSCO-2-CE/6dd651d55dde97fd4028699be9d4481f26917891/"
STRINGS_SHORT_SF2 = Path(os.environ.get("ORCHESTRA_STRINGS_SHORT_SF2") or SF2.parent / "strings-short.sf2")
BRASS_SF2 = Path(os.environ.get("ORCHESTRA_BRASS_SF2") or SF2.parent / "vpo-brass.sf2")
HORN_SOLO_SF2 = Path(os.environ.get("ORCHESTRA_HORN_SOLO_SF2") or SF2.parent / "horn-solo.sf2")

# A string note shorter than this plays from the short-note recordings, a longer one from the
# sound set's sustained strings - in every score, nothing to write. Measured (velocity 100, the
# sound set): a 0.25 s note of its strings peaks 1.7-3.1 dB under its long notes' level, a 0.3 s
# note 0.3-2.5 dB (0.2 s: 2.8-4.3; 0.15 s: 4.5-8.4 dB), and a 0.3 s note sounds 0.42-0.59 s
# with its release - as long as a short recording's stroke (0.33-0.6 s). Under 0.3 s the
# sustained recordings are still speaking when the note ends; from 0.3 s they have spoken, and a
# stroke would end before a longer note does.
SHORT_S = 0.3
# The players' unevenness VPO's SFZ files give their sections (pitch_random=12 cents,
# amp_random=1.5 dB, delay_random=0.012 s): each note a little off in level and time (the same
# every render: seeded by the part), and in pitch - the notes take turns on three channels tuned
# DETUNE apart (the synth can't detune one note of a chord; the spread is VPO's random one's).
HUMAN_DB, HUMAN_DELAY = 1.5, 0.012
DETUNE = (-8.0, 0.0, 8.0)       # cents

# The parts with short notes - one section with its long notes: the same pan and volume, hall
# send, width and position. Each: its SFZ (in VPO); how the stroke ends (a one-shot rings to its
# end, released "one_shot" s after it starts; else the note's end starts the SFZ's "release");
# how it is placed, as the lab placed it at our part's width and position - violins and violas
# stereo, their width and position set after the synth to the long notes' (measured over the
# part's range, every third semitone: "side", the side signal's gain, and "tilt_db", the left over
# the right), cellos and basses mono, the two microphones summed (the basses' aligned by
# "mono_lag" samples: they comb less) and panned where the sound set's mono ones are; how soon it
# speaks ("speak", to within 9 dB) and is started early ("advance": as the lab timed it, its
# attacks where the long notes' are heard); and "trim_db": a short note's peak (50 ms) where a
# long note at the same velocity holds (measured against MuseScore_General's, velocity 100; the
# same from 40 to 125 - "soft": a soft layer turned down to meet the loud one).
STRINGS_SHORT = {
    "violins": {"preset": 0, "sfz": "Strings/1st-violin-SEC-staccato.sfz", "one_shot": 1.0, "release": None,
                "mono_lag": None, "side": 1.105, "tilt_db": 0.05, "speak": 0.05, "advance": 0.067, "trim_db": -14.17},
    "violins2": {"preset": 2, "sfz": "Strings/viola-SEC-staccato.sfz", "one_shot": None, "release": 4.0,
                 "mono_lag": None, "side": 1.661, "tilt_db": 2.17, "speak": 0.04, "advance": 0.057, "trim_db": -17.17},
    "cellos": {"preset": 4, "sfz": "Strings/cello-SEC-staccato.sfz", "one_shot": None, "release": 2.0,
               "mono_lag": 0, "speak": 0.055, "advance": 0.072, "trim_db": 0.39,
               "soft": (62, 3.9)},    # (its soft layer, to velocity 62, 3.9 dB over the loud one where
                                      # they meet: turned down, so a soft note is as loud as a long one)
    "basses": {"preset": 6, "sfz": "Strings/bass-SEC-staccato.sfz", "one_shot": None, "release": 2.0,
               "mono_lag": -58, "speak": 0.055, "advance": 0.072, "trim_db": -12.13},
}
for _p, _s in STRINGS_SHORT.items():          # (two round-robins each: played in turn, per key)
    _s.update({"font": "strings_short", "presets": [[_s["preset"]], [_s["preset"] + 1]], "human": True})

# The parts that play their own recordings (a font of their own) through _sampled_stem: their
# presets (a list per round-robin, a preset per velocity layer), the velocity crossfade between
# the layers (VPO's xfin/xfout: equal power), as the lab placed them - one microphone (summing a
# section's two combs it), at the sound set's position; how soon each speaks (ADVANCE), its hall
# send (dB: so it ends at the room the sound set's part did - 0.5 s notes, measured after the
# hall, here: the horns -4.0, where the lab's own player had -5.75; the trombones and the solo
# horn as the lab's), "trim_db": the same velocity as loud as the sound set's part (measured: Ode
# to Joy, the tune at velocity 100 - the solo horn against the sound set's horns, as the lab
# levelled it - and the trombones' chords at 88; the same within 1 dB from velocity 40 to 125).
OWN = {
    "horns": {"font": "brass", "presets": [[0, 1]], "xfade": [("in", 75, 127), ("out", 75, 127)],
              "human": True, "advance": 0.022, "send_db": -4.0, "trim_db": 1.64},
    "trombones": {"font": "brass", "presets": [[2, 3]], "xfade": [("in", 75, 90), ("out", 75, 90)],
                  "human": True, "advance": 0.002, "send_db": -2.0, "trim_db": 7.28},
    "horn_solo": {"font": "horn_solo", "presets": [[0]], "human": False, "advance": 0.025, "send_db": -0.25,
                  "trim_db": 1.47},
}
# The brass sits drier than the strings: its hall send this much under what matches the room
# ("6b is the best": a solo horn on the tune, the brass's send -6 dB, the tune's lift).
BRASS_DRY_DB = -6.0
BRASS_DRY = {"horns", "horn_solo", "trombones", "tuba", "trumpets", "brass"}

# The trombones' ff recordings are 3 dB over their mp ones (against the sound set's trombone at
# the same velocity): turned down, so a soft chord is as loud, for its velocity, as a loud one
# (its trim_db is 3 dB more for it).
BRASS_EVEN_DB = {("trombones", "ff"): 3.0}
# The brass sections' loops (VPO's WAVs carry them; its FLACs do not): (start, end) inclusive.
VPO_LOOPS = {
    "2_A": (64512, 210431), "2_Bb_p": (33318, 121749), "2_F": (62976, 199423), "2_F_p": (35570, 108296),
    "3_A": (62976, 247551), "3_Ab_p": (37378, 132097), "3_C": (52096, 183538), "3_Eb": (75520, 217343),
    "3_Eb_p-PB-loop": (36914, 129106), "3_Gb": (52992, 131327), "4_A": (65920, 162303), "4_B_p": (22741, 100877),
    "4_C": (52736, 167679), "4_Db_p": (34728, 135436), "4_Eb": (83456, 199660), "4_Gb": (94080, 194969),
    "4_Gb_p": (30245, 111385), "5_C": (84608, 169599),
    "horns-sus-ff-a#2-PB-loop": (137089, 260752), "horns-sus-ff-a#3-PB-loop": (110759, 200300),
    "horns-sus-ff-a#4-PB-loop": (91457, 171062), "horns-sus-ff-c#3-PB-loop": (67586, 193763),
    "horns-sus-ff-c#4-PB-loop": (80072, 161186), "horns-sus-ff-c#5-PB-loop": (51367, 166667),
    "horns-sus-ff-e2-PB-loop": (43074, 161104), "horns-sus-ff-e3-PB-loop": (80055, 195177),
    "horns-sus-ff-e4-PB-loop": (33625, 127592), "horns-sus-ff-e5-PB-loop": (30936, 159653),
    "horns-sus-ff-g2-PB-loop": (92915, 195581), "horns-sus-ff-g3-PB-loop": (31821, 106776),
    "horns-sus-ff-g4-PB-loop": (47691, 127710), "horns-sus-mp-a#2-PB-loop": (84586, 205719),
    "horns-sus-mp-a#3-PB-loop": (81487, 204467), "horns-sus-mp-a#4-PB-loop": (18687, 195585),
    "horns-sus-mp-c#3-PB-loop": (59534, 200560), "horns-sus-mp-c#4-PB-loop": (31591, 161158),
    "horns-sus-mp-c#5-PB-loop": (25744, 140790), "horns-sus-mp-e2-PB-loop": (65876, 265846),
    "horns-sus-mp-e3-PB-loop": (17755, 151550), "horns-sus-mp-e4-PB-loop": (52902, 174650),
    "horns-sus-mp-e5-PB-loop": (40234, 116733), "horns-sus-mp-g2-PB-loop": (34697, 161800),
    "horns-sus-mp-g3-PB-loop": (77013, 177169), "horns-sus-mp-g4-PB-loop": (32587, 105591),
}
_RECORDING_CAP = 24 << 20       # (no recording here is over 5 MB; an SFZ file over 1 MB is not one)


def _download(url: str, cap: int) -> bytes:
    """An untrusted download, read to at most ``cap`` bytes (more: refused, not truncated)."""
    with urllib.request.urlopen(url, timeout=60) as r:
        data = r.read(cap + 1)
    if len(data) > cap:
        raise OSError(f"{url}: over {cap} bytes - not the recording expected")
    return data


def _library_path(folder: str, sample: str) -> str:
    """A sample an SFZ names (relative to its folder, Windows separators), as a path inside the
    library - plain names only: nothing outside the library, no scheme, nothing odd."""
    import re
    parts: List[str] = []
    for p in (folder + "/" + sample.replace("\\", "/")).split("/"):
        if p in ("", "."):
            continue
        if p == "..":
            if not parts:
                raise OSError(f"sample {sample!r} is outside the library")
            parts.pop()
            continue
        if not re.fullmatch(r"[A-Za-z0-9 #_.,()+-]+", p) or p.startswith("."):
            raise OSError(f"sample {sample!r}: not a plain path")
        parts.append(p)
    return "/".join(parts)


def _recording(base: str, rel: str):
    """One recording (WAV or FLAC, decoded from memory) -> (float64 (n, 2), rate)."""
    import io
    import urllib.parse
    import numpy as np
    import soundfile
    audio, rate = soundfile.read(io.BytesIO(_download(base + urllib.parse.quote(rel), _RECORDING_CAP)),
                                 dtype="float64", always_2d=True)
    if not (8000 <= rate <= 192000 and 1 <= audio.shape[1] <= 2 and 0 < len(audio) <= 40 * rate
            and np.isfinite(audio).all()):
        raise OSError(f"{rel}: not a recording expected here ({rate} Hz, {audio.shape})")
    if audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)
    return audio, rate


def _sfz(base: str, rel: str) -> List[dict]:
    """A pinned SFZ file's regions, their samples resolved inside the library ("_rel")."""
    from music import sf2write
    regions = sf2write.parse_sfz(_download(base + rel, 1 << 20).decode("utf-8", "replace"))
    folder = rel.rpartition("/")[0]
    for r in regions:
        r["_rel"] = _library_path(folder, r.get("_default_path", "") + r["sample"])
        if "key" in r:
            for k in ("lokey", "hikey", "pitch_keycenter"):
                r.setdefault(k, r["key"])
    if not regions:
        raise OSError(f"{rel}: no regions")
    return regions


def _region_audio(r: dict, x, rate: int, vel: int = 100):
    """A region's recording as its SFZ plays it at ``vel`` (what the synth can't: its volume and
    pan, its envelope's attack, hold and decay - sfzlite's own arithmetic)."""
    import numpy as np
    f = lambda k, d=0.0: float(r.get(k, d))                       # noqa: E731
    x = x * (10 ** (f("volume") / 20) * f("amplitude", 100) / 100)
    pan = f("pan") / 100
    if pan:
        th = (pan + 1) * math.pi / 4
        x = x * np.array([math.cos(th), math.sin(th)]) * math.sqrt(2)
    vf = vel / 127
    att, hold = f("ampeg_attack"), f("ampeg_hold") + f("ampeg_vel2hold") * vf
    dec = f("ampeg_decay") + f("ampeg_vel2decay") * vf
    sus = max(0.0, min(100.0, f("ampeg_sustain", 100))) / 100
    t = np.arange(len(x)) / rate
    env = np.ones(len(x))
    if dec > 0 and sus < 1:
        env = sus + (1 - sus) * np.exp(-np.maximum(t - att - hold, 0) * 5 / dec)
    if att > 0:
        env = np.where(t < att, t / att, env)
    x = x * env[:, None]
    if sus <= 0 and dec > 0:                                      # (a stroke: to 60 dB down)
        x = x[:max(16, int((att + hold + dec * 60 / 43.4) * rate))]
    return x


def _zone(r: dict, audio, rate: int, release_s: float, loop=None, lo=None, hi=None) -> dict:
    """An SF2 zone (sf2write) for an SFZ region's recording (int16 already)."""
    from music import sf2write
    key = sf2write.sfz_key(r.get("pitch_keycenter", r.get("lokey", 60))) - int(float(r.get("transpose", 0)))
    z = {"audio": audio, "rate": rate, "key": key, "release_s": release_s,
         "lo": sf2write.sfz_key(r.get("lokey", 0)) if lo is None else lo,
         "hi": sf2write.sfz_key(r.get("hikey", 127)) if hi is None else hi,
         "vlo": int(r.get("lovel", 1)) or 1, "vhi": int(r.get("hivel", 127)), "tune": int(round(float(r.get("tune", 0))))}
    if loop:
        z.update({"ls": loop[0], "le": loop[1] + 1})
    else:
        z.update({"loop": False, "ls": 8, "le": len(audio) - 8})
    return z


def _cover(zones: List[dict], lo: int, hi: int) -> None:
    """The outermost recordings stretched to cover a part's range (RANGES)."""
    top, bot = max(z["hi"] for z in zones), min(z["lo"] for z in zones)
    for z in zones:
        if z["hi"] == top:
            z["hi"] = max(top, hi)
        if z["lo"] == bot:
            z["lo"] = min(bot, lo)


def _scaled(items, peak: float = 0.95):
    """Float recordings -> int16, all scaled by one gain (their loudest at ``peak``): the levels
    between them (velocity layers, round-robins) kept."""
    import numpy as np
    from music import sf2write
    top = max(float(np.abs(x).max()) for x in items)
    return [sf2write.to_int16((x * (peak / top)).astype("float32")) for x in items]


def fetch_strings_short(dest: Path = None, quiet: bool = False) -> Path:
    """The short string notes: VPO's staccato/spiccato SFZs (STRINGS_SHORT) and their 118
    recordings (13 MB of FLAC, once) built into a SoundFont of eight presets - two round-robins a part
    (STRINGS_SHORT's "preset" and the next) - each recording as its SFZ plays it (volume, pan,
    envelope baked in), placed as STRINGS_SHORT says (stereo, or one mono microphone sum)."""
    dest = dest or STRINGS_SHORT_SF2
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        return dest
    import numpy as np
    from music import sf2write
    if not quiet:
        print("[orchestra] downloading the short string notes (13 MB, once)", file=sys.stderr, flush=True)
    presets = []
    for part, s in sorted(STRINGS_SHORT.items(), key=lambda kv: kv[1]["preset"]):
        rrs: Dict[int, list] = {1: [], 2: []}
        got = {}
        for r in _sfz(VPO, s["sfz"]):
            if r["_rel"] not in got:
                got[r["_rel"]] = _recording(VPO, r["_rel"])
            x, rate = got[r["_rel"]]
            x = _region_audio(r, x, rate)
            if s["mono_lag"] is not None:                       # one microphone sum, aligned
                right = np.roll(x[:, 1], s["mono_lag"])
                if s["mono_lag"] > 0:
                    right[:s["mono_lag"]] = 0
                elif s["mono_lag"] < 0:
                    right[s["mono_lag"]:] = 0
                x = ((x[:, 0] + right) / 2)[:, None]
            rrs[int(r.get("seq_position", 1))].append((r, x, rate))
        flat = [x for rr in rrs.values() for _, x, _ in rr]
        scaled = iter(_scaled(flat))
        release = (s["one_shot"] or s["release"]) * 4 / 3   # (the synth's release: 80 dB in its time; SFZ's: 60)
        for n in sorted(rrs):
            zones = [_zone(r, next(scaled), rate, release) for r, _, rate in rrs[n]]
            for z in zones:
                if s.get("soft") and z["vhi"] <= s["soft"][0]:
                    z["att_cb"] = round(10 * s["soft"][1])
            _cover(zones, *RANGES[part])
            presets.append((f"{part} rr{n}", zones))
    dest.parent.mkdir(parents=True, exist_ok=True)
    part_path = dest.with_suffix(".part")
    sf2write.write(part_path, presets, "Short strings: SSO (CC Sampling Plus 1.0), VSCO 2 CE (CC0), via VPO")
    part_path.replace(dest)
    return dest


def fetch_brass(dest: Path = None, quiet: bool = False) -> Path:
    """The brass sections: VPO's horn and trombone SFZs ("normal": the mod wheel at 0) and their
    44 recordings (15 MB of FLAC, once) built into a SoundFont of four mono presets - 0 horns ff, 1 horns
    mp, 2 trombones ff, 3 trombones mp (OWN's crossfades blend them by velocity) - each the left
    microphone (the section's two microphones summed comb, -4 dB dips), as its SFZ plays it; the
    horns' accent layer (the same recording, 0.15 s held then fading: the attack's bite) a short
    recording of its own beside it."""
    dest = dest or BRASS_SF2
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        return dest
    from music import sf2write
    if not quiet:
        print("[orchestra] downloading the brass sections (15 MB, once)", file=sys.stderr, flush=True)
    presets = []
    for part, rel in (("horns", "Brass/french-horn-SEC-normal-mod-wheel.sfz"),
                      ("trombones", "Brass/trombone-SEC-normal-mod-wheel.sfz")):
        layers: Dict[str, list] = {"ff": [], "mp": []}
        got = {}
        for r in _sfz(VPO, rel):
            if r["_rel"] not in got:
                got[r["_rel"]] = _recording(VPO, r["_rel"])
            x, rate = got[r["_rel"]]
            name = Path(r["_rel"]).stem
            accent = float(r.get("ampeg_sustain", 100)) <= 0
            if not accent and name not in VPO_LOOPS:
                raise OSError(f"{rel}: no loop known for {name}")
            mono = _region_audio(r, x, rate)[:, :1]            # (the left microphone)
            release = float(r.get("ampeg_release", 0.6)) * 4 / 3
            layers["ff" if "xfin_lovel" in r else "mp"].append((r, mono, rate, release, None if accent else VPO_LOOPS[name]))
        scaled = iter(_scaled([x for zs in layers.values() for _, x, _, _, _ in zs]))
        for lay in ("ff", "mp"):
            zones = [_zone(r, next(scaled), rate, rel_s, loop) for r, _, rate, rel_s, loop in layers[lay]]
            if (part, lay) in BRASS_EVEN_DB:
                for z in zones:
                    z["att_cb"] = round(10 * BRASS_EVEN_DB[(part, lay)])
            _cover(zones, *RANGES[part])
            presets.append((f"{part} {lay}", zones))
    dest.parent.mkdir(parents=True, exist_ok=True)
    part_path = dest.with_suffix(".part")
    sf2write.write(part_path, presets, "Brass: Westlund horns (CC BY-SA 3.0), NBO trombones (CC BY-SA 4.0), via VPO")
    part_path.replace(dest)
    return dest


def fetch_horn_solo(dest: Path = None, quiet: bool = False) -> Path:
    """The solo horn: VSCO 2 CE's F horn sustains (its SFZ, 29 recordings with up to four
    velocity layers, 51 MB, once) built into a one-preset SoundFont, the right microphone (mono:
    the two comb when summed), each given a long crossfaded loop over its held tone (the
    recordings, 4-15 s, have none)."""
    dest = dest or HORN_SOLO_SF2
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        return dest
    import numpy as np
    from music import sf2write
    if not quiet:
        print("[orchestra] downloading the solo horn (51 MB, once)", file=sys.stderr, flush=True)
    found = []
    for r in _sfz(VSCO2_SFZ, "FHornSus.sfz"):
        x, rate = _recording(VSCO2_SFZ, r["_rel"])
        found.append((r, _region_audio(r, x, rate)[:, 1:2], rate))
    scaled = _scaled([x for _, x, _ in found])
    zones = []
    for (r, x, rate), a in zip(found, scaled):
        lvl = np.sqrt(np.convolve(a[:, 0].astype("float64") ** 2, np.ones(int(0.05 * rate)) / int(0.05 * rate), "same"))
        body = lvl[int(0.3 * rate):]
        held = np.nonzero(body > np.median(body[:max(1, len(body) // 2)]) * 0.5)[0]
        end = int(0.3 * rate) + (int(held[-1]) if len(held) else len(body) // 2)    # (the tone held, to here)
        end = max(int(1.2 * rate), min(end, len(a) - int(0.05 * rate)))
        start = max(int(0.4 * rate), end - int(3.0 * rate))
        fade = max(0.05, min(0.5, (end - start) / rate / 3))
        audio, ls, le = sf2write.crossfade_loop(a, rate, start / rate, fade, (len(a) - end) / rate)
        zones.append({**_zone(r, audio, rate, float(r.get("ampeg_release", 0.7)) * 4 / 3), "ls": ls, "le": le,
                      "loop": True})
    _cover(zones, *RANGES["horn_solo"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    part_path = dest.with_suffix(".part")
    sf2write.write(part_path, [("F horn", zones)], "VSCO 2 CE F horn (CC0)")
    part_path.replace(dest)
    return dest


def _xfade(xf, vel: float) -> float:
    """A velocity layer's gain (VPO's xfin / xfout, equal power), 1 when it has none."""
    if xf is None:
        return 1.0
    kind, lo, hi = xf
    if kind == "in":
        return 0.0 if vel < lo else 1.0 if vel >= hi else math.sqrt((vel - lo) / (hi - lo))
    return 1.0 if vel <= lo else 0.0 if vel > hi else math.sqrt((hi - vel) / (hi - lo))


def _split_short(events: list) -> Tuple[list, list]:
    """A string part's events -> (its notes shorter than SHORT_S, the rest): each note's on and
    off together (a note left on is long)."""
    ons: Dict[int, list] = {}
    short, long_ = [], []
    for e in sorted(events, key=lambda e: (e[0], e[1])):
        t, is_on, _, key, _ = e
        if is_on == 1:
            ons.setdefault(key, []).append(e)
        elif is_on == 0 and ons.get(key):
            on = ons[key].pop(0)
            (short if t - on[0] < SHORT_S else long_).extend([on, e])
        else:
            long_.append(e)
    long_ += [e for left in ons.values() for e in left]
    return short, long_


def _sampled_stem(syn, font: int, part: str, how: dict, events: list, total: int, rate: int):
    """A part from its own recordings (STRINGS_SHORT, OWN) -> (first sample, stereo stem): each
    note on a channel of its round-robin (per key, in turn) and velocity layer (crossfaded), the
    players' unevenness (HUMAN_*: a channel detuned, a level, a few ms) when ``how`` asks, a
    one-shot let ring; at the sound set's part's pan and volume, so it stands where that did."""
    import zlib
    import numpy as np
    pan, vol = PARTS[part][2], PARTS[part][3]
    rr_sets = how["presets"]
    layers = how.get("xfade") or [None] * len(rr_sets[0])
    human = how.get("human", False)
    dets = DETUNE if human else (0.0,)
    chans = {}
    for r in range(len(rr_sets)):
        for lay in range(len(layers)):
            for d in range(len(dets)):
                chans[(r, lay, d)] = len(chans)
    bends = [(t, vel) for t, is_on, _, _, vel in events if is_on == 2]
    for (r, lay, d), ch in chans.items():
        syn.program_select(ch, font, 0, rr_sets[r][lay])
        syn.control_change(ch, 7, vol)
        syn.control_change(ch, 10, pan)
        syn.set_tuning(ch, dets[d] / 100)
        if bends:
            syn.pitchbend_range(ch, 12)
            syn.pitchbend(ch, 8192)
    ons: Dict[int, list] = {}
    notes = []
    for t, is_on, _, key, vel in sorted(events, key=lambda e: (e[0], e[1])):
        if is_on == 1:
            ons.setdefault(key, []).append((t, vel))
        elif is_on == 0 and ons.get(key):
            t0, v = ons[key].pop(0)
            notes.append((t0, t, key, v))
    notes += [(t0, total / rate, key, v) for key, left in ons.items() for t0, v in left]
    notes.sort()
    if not notes:
        return total, np.zeros((0, 2), dtype="float32")
    rng = np.random.default_rng(zlib.crc32(part.encode()))      # (the same unevenness every time)
    turn: Dict[int, int] = {}
    ev = []
    for i, (t0, t1, key, vel) in enumerate(notes):
        r = turn.get(key, 0) % len(rr_sets)
        turn[key] = turn.get(key, 0) + 1
        late = float(rng.uniform(0, HUMAN_DELAY)) if human else 0.0
        amp = 10 ** (-float(rng.uniform(0, HUMAN_DB)) / 20) if human else 1.0
        off = t0 + how["one_shot"] if how.get("one_shot") else t1
        for lay, xf in enumerate(layers):
            v = int(round(vel * amp * _xfade(xf, vel)))
            if v < 1:
                continue
            ch = chans[(r, lay, i % len(dets))]
            ev.append((t0 + late, 1, ch, key, min(127, v)))
            ev.append((off + late, 0, ch, key, 0))
    ev += [(t, 2, None, 0, sem) for t, sem in bends]
    ev.sort(key=lambda e: (e[0], e[1]))
    first = min(total, int(ev[0][0] * rate))
    chunks, pos = [], first
    for t, kind, ch, key, vel in ev:
        at = min(total, int(t * rate))
        if at > pos:
            chunks.append(np.frombuffer(syn.generate(at - pos), dtype="float32"))
            pos = at
        if kind == 2:
            for c in chans.values():
                syn.pitchbend(c, int(max(0, min(16383, 8192 + vel / 12 * 8191))))
        elif kind == 1:
            syn.noteon(ch, key, vel)
        else:
            syn.noteoff(ch, key)
    step = max(1, rate // 4)
    while pos < total:                                      # ring out, then stop: silence
        piece = np.frombuffer(syn.generate(min(step, total - pos)), dtype="float32")
        chunks.append(piece)
        pos += len(piece) // 2
        if float(np.abs(piece).max(initial=0.0)) < 1e-6:
            break
    for c in chans.values():
        syn.sounds_off(c)
        syn.set_tuning(c, 0.0)
        if bends:
            syn.pitchbend(c, 8192)
    syn.generate(256)
    stem = np.concatenate(chunks).reshape(-1, 2) if chunks else np.zeros((0, 2), dtype="float32")
    side, tilt = how.get("side", 1.0), how.get("tilt_db", 0.0)
    if (side != 1.0 or tilt) and len(stem):                 # (its width: the side signal's gain;
        mid, sd = (stem[:, 0] + stem[:, 1]) / 2, (stem[:, 0] - stem[:, 1]) / 2 * np.float32(side)
        r = 10 ** (tilt / 10)                               # its position: left over right, dB)
        gr = math.sqrt(2 / (1 + r))
        stem = np.stack([(mid + sd) * np.float32(math.sqrt(2 - gr * gr)), (mid - sd) * np.float32(gr)], axis=1)
    return first, (stem * np.float32(10 ** (how.get("trim_db", 0.0) / 20))).astype("float32")


def _plays_own(part: str, fonts: dict) -> bool:
    """Whether a part plays its own recordings here (OWN: their font loaded), not the stand-in."""
    return part in OWN and fonts.get(OWN[part]["font"]) is not None


def part_send_db(part: str, own: bool = False) -> float:
    """A part's hall send (dB): matched to the room its recording carries (ROOM; its own
    recordings: OWN's), the brass's BRASS_DRY_DB under that."""
    base = OWN[part]["send_db"] if own and part in OWN else send_db(ROOM.get(part))
    return base + (BRASS_DRY_DB if part in BRASS_DRY else 0.0)


def part_advance(part: str, short: bool = False, own: bool = False) -> float:
    """How early a part's notes start (ADVANCE): its short notes' and its own recordings' own."""
    if short and part in STRINGS_SHORT:
        return STRINGS_SHORT[part]["advance"]
    if own and part in OWN:
        return OWN[part]["advance"]
    return ADVANCE.get(part, 0.0)


# --- the electric guitar ---
GUITAR = {"guitar": 0, "guitar_mute": 1}        # its parts: the articulation (0 sustain, 1 palm mute)
GUITAR_TAKES = 3        # takes (round-robins) kept a note, each a stereo pair: its left and right
                        # channels are separate takes, one for each pass of the double-tracking
GUITAR_KEYS = (40, 76)  # the recordings kept: E2-E5 (one a semitone; E2's also plays B1-D#2)
GUITAR_LOW = 35         # B1: the lowest note it plays (a 7-string's low B)
GUITAR_RELEASE = 0.08   # a note let go: the hand damps the strings
HALL_ROOM_GUITAR = -13.0  # (its own room as ROOM counts it: as much as the hall's, so the least send)
_GUITAR_ARTS = (("Sus_Down", 4.0, 120, 0.0), ("Mute_Down", 1.0, 104, 6.0))
#               (folder, seconds kept, the velocity its tone is baked at, dB over the sustain)


def _unpack_rar(archive: Path, out: Path, patterns: List[str]) -> None:
    """Extract the files matching ``patterns`` from a RAR archive with whatever can: 7-Zip
    (7zz / 7z / 7za, or the program ORCHESTRA_7Z names), unar, or bsdtar (libarchive)."""
    import subprocess
    tried = []
    for exe in _rar_tools():
        kind = Path(exe).name
        if kind.startswith("unar"):
            cmd = [exe, "-q", "-f", "-o", str(out), str(archive)]           # (all of it)
        elif kind.startswith("bsdtar"):
            cmd = [exe, "-xf", str(archive), "-C", str(out), *patterns]
        else:
            cmd = [exe, "x", "-y", f"-o{out}", str(archive), *patterns, "-r"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return
        tried.append(f"{kind}: {(r.stderr or r.stdout).strip()[-200:]}")
    raise OSError(NO_UNRAR + (f" (tried: {'; '.join(tried)})" if tried else ""))


NO_UNRAR = ("the guitar's recordings come as a RAR archive, and nothing here unpacks one: install "
            "7-Zip (7zz or 7z: the 7zip or p7zip-full package) or unar, or set ORCHESTRA_7Z to a 7-Zip "
            "program, or ORCHESTRA_GUITAR_SRC to the archive unpacked")


def _rar_tools() -> List[str]:
    """The programs here that can unpack a RAR archive (7-Zip first)."""
    import shutil
    named = os.environ.get("ORCHESTRA_7Z")
    found = [shutil.which(t) for t in ([named] if named else []) + ["7zz", "7z", "7za", "unar", "bsdtar"]]
    return [f for f in found if f]


def fetch_guitar(dest: Path = None, quiet: bool = False, src: Optional[Path] = None) -> Path:
    """The real guitar: the Standard Guitar's archive (716 MB, once - or ``src`` /
    ORCHESTRA_GUITAR_SRC: the archive, or a folder it was unpacked to), its sustain and
    palm-mute down strokes E2-E5 (GUITAR_TAKES takes each) built into a SoundFont of
    4 * GUITAR_TAKES mono presets (_guitar_preset: an articulation, a side, a take - each
    channel of a stereo take is a preset of its own: the left pass plays the left takes, the
    right pass the right). Each recording keeps the tone the library gives it at the velocity
    it is baked at (its velocity-tracked low-pass and pickup EQ); played once, not looped."""
    dest = dest or GUITAR_SF2
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        return dest
    import re
    import tempfile
    import numpy as np
    import soundfile
    from music import sf2write
    src = src or os.environ.get("ORCHESTRA_GUITAR_SRC")
    src = Path(src) if src else None
    dest.parent.mkdir(parents=True, exist_ok=True)
    wanted = [f"*_{folder}{i}.flac" for folder, *_ in _GUITAR_ARTS for i in range(1, GUITAR_TAKES + 1)]
    names = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
    with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:       # (~1 GB: beside the cache)
        root = Path(tmp)
        if src is not None and src.is_dir():
            root = src
        else:
            if not _rar_tools():                        # (before a 716 MB download, not after)
                raise OSError(NO_UNRAR)
            archive = src
            kept = dest.parent / "guitar-download.rar"   # (kept until built: a retry needn't fetch it)
            if archive is None and kept.is_file():
                archive = kept
            if archive is None:
                archive = kept.with_suffix(".part")
                if not quiet:
                    print(f"[orchestra] downloading the guitar (716 MB, once): {GUITAR_PAGE}",
                          file=sys.stderr, flush=True)
                with urllib.request.urlopen(GUITAR_URL, timeout=120) as r, open(archive, "wb") as f:
                    while True:
                        chunk = r.read(1 << 22)
                        if not chunk:
                            break
                        f.write(chunk)
                if archive.stat().st_size < 100_000_000:
                    raise OSError(f"the guitar's download is {archive.stat().st_size} bytes, not the "
                                  f"716 MB archive: see {GUITAR_PAGE}")
                archive = archive.replace(kept)
            _unpack_rar(archive, root / "x", wanted)
            root = root / "x"
        presets = [[] for _ in range(2 * 2 * GUITAR_TAKES)]
        peak = 0.0
        found = []
        for art, (folder, keep, vel, lift) in enumerate(_GUITAR_ARTS):
            for path in root.rglob(f"*_{folder}*.flac"):
                m = re.fullmatch(rf"([a-g])(#?)(\d)_{folder}(\d+)\.flac", path.name, re.IGNORECASE)
                if not m or not 1 <= int(m.group(4)) <= GUITAR_TAKES:
                    continue
                key = 12 * (int(m.group(3)) + 1) + names[m.group(1).lower()] + (1 if m.group(2) else 0)
                if not GUITAR_KEYS[0] <= key <= GUITAR_KEYS[1]:
                    continue
                audio, rate = soundfile.read(str(path), dtype="float32", always_2d=True)
                if audio.shape[1] == 1:
                    audio = np.repeat(audio, 2, axis=1)
                mono = np.abs(audio).max(axis=1)
                start = max(0, int(np.argmax(mono > 0.02 * mono.max())) - int(0.002 * rate))
                x = audio[start:start + int(keep * rate), :2].astype("float64")
                fade = int(0.25 * rate)
                x[-fade:] *= np.cos(np.linspace(0, np.pi / 2, fade))[:, None] ** 2
                x = _guitar_tone(x, rate, vel) * 10 ** (lift / 20)
                peak = max(peak, float(np.abs(x).max()))
                found.append((art, int(m.group(4)) - 1, key, x, rate))
        if len({(a, k) for a, _, k, _, _ in found}) < 2 * (GUITAR_KEYS[1] - GUITAR_KEYS[0] + 1) * 0.9:
            raise OSError(f"the guitar's recordings weren't found in {root} (its Samples/Sus_Down and "
                          f"Samples/Mute_Down): see {GUITAR_PAGE}")
        for art, take, key, x, rate in sorted(found, key=lambda f: (f[0], f[1], f[2])):
            x = x * (0.95 / peak)
            for side in (0, 1):
                a = sf2write.to_int16(x[:, side:side + 1].astype("float32"))
                presets[_guitar_preset(art, side, take)].append(
                    {"audio": a, "rate": rate, "key": key, "lo": GUITAR_LOW if key == GUITAR_KEYS[0] else key,
                     "hi": key, "loop": False, "ls": 8, "le": len(a) - 8, "release_s": GUITAR_RELEASE})
    part = dest.with_suffix(".part")
    labels = [f"{('Sus', 'Mute')[i // (2 * GUITAR_TAKES)]} {'LR'[(i // GUITAR_TAKES) % 2]}{i % GUITAR_TAKES + 1}"
              for i in range(len(presets))]
    sf2write.write(part, list(zip(labels, presets)), "Unreal Instruments Standard Guitar (license free)")
    part.replace(dest)
    (dest.parent / "guitar-download.rar").unlink(missing_ok=True)
    return dest


def _guitar_preset(art: int, side: int, take: int) -> int:
    """The guitar SoundFont's preset for an articulation (0 sustain, 1 palm mute), a side
    (0 left pass, 1 right) and a take: PARTS' "guitar" is preset 0, "guitar_mute" preset 6."""
    return art * 2 * GUITAR_TAKES + side * GUITAR_TAKES + take


def _biquad(kind: str, f: float, q: float, gain_db: float, rate: int):
    """An RBJ biquad's (b, a): low-pass, high-pass or peaking EQ."""
    A = 10 ** (gain_db / 40)
    w = 2 * math.pi * min(f, 0.45 * rate) / rate
    c, s = math.cos(w), math.sin(w)
    al = s / (2 * q)
    if kind == "lp":
        b, a = [(1 - c) / 2, 1 - c, (1 - c) / 2], [1 + al, -2 * c, 1 - al]
    elif kind == "hp":
        b, a = [(1 + c) / 2, -(1 + c), (1 + c) / 2], [1 + al, -2 * c, 1 - al]
    else:
        b, a = [1 + al * A, -2 * c, 1 - al * A], [1 + al / A, -2 * c, 1 - al / A]
    return [v / a[0] for v in b], [v / a[0] for v in a]


def _filter(x, sections, rate: int):
    """A cascade of biquads [(kind, f, q, dB)] (or raw (b, a)) applied exactly, in the
    frequency domain (padded a second, so nothing wraps round); x: (n,) or (n, ch)."""
    import numpy as np
    x = np.asarray(x, dtype="float64")
    n = len(x) + rate
    N = _fast_len(n)
    z = np.exp(-1j * np.linspace(0, np.pi, N // 2 + 1))
    H = np.ones_like(z)
    for sec in sections:
        b, a = sec if len(sec) == 2 else _biquad(*sec, rate)
        H *= (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)
    X = np.fft.rfft(x, N, axis=0)
    return np.fft.irfft(X * (H[:, None] if x.ndim == 2 else H), N, axis=0)[:len(x)]


def _guitar_tone(x, rate: int, vel: int):
    """The library's own tone at a velocity, baked in: its velocity-tracked one-pole low-pass
    (30 Hz + 9600 cents at velocity 127) and its pickup EQ ("Magnet", at its default 64)."""
    a = math.exp(-2 * math.pi * min(30 * 2 ** (8 * vel / 127), 18000) / rate)
    k = 64 / 127
    q = lambda bw: 1 / (2 * math.sinh(math.log(2) / 2 * bw))          # noqa: E731
    return _filter(x, [([1 - a, 0, 0], [1, -a, 0]), ("peak", 300, q(2.5), -10 * k),
                       ("peak", 1290, q(1), 6 * k), ("peak", 100, q(3), -9 * k)], rate) * 10 ** (6 * k / 20)


# The amp and cabinet the host heard as "great" (a high-gain amp on the whole chord, so its
# strings intermodulate as in a real one; a 4x12 cabinet's response: a tight low end with
# the cabinet's resonance near 105 Hz, the box dipped at 420 Hz, a little presence, nothing
# much past 6 kHz). The guitar's buzz at 2-4 kHz: 28% of the GM sample's energy, 5% here.
AMP_PRE = (("hp", 110, 0.7, 0.0), ("peak", 750, 0.8, 4.0), ("lp", 6000, 0.7, 0.0))
AMP_GAIN_DB = 36.0
GUITAR_DRIVE = 20.6     # the DI into the amp: a forte part's picking (velocity ~110) at 0.1 RMS
AMP_LEVEL_DB = -30.6    # the amp's output: the guitar, at no "mix", ~6 dB under a forte orchestra
GUITAR_GM_GAIN = 7.0    # offline, the GM guitar through its cabinet: as loud as the real one (measured)
CAB = (("hp", 65, 0.7, 0), ("hp", 65, 0.7, 0), ("peak", 105, 1.2, 7.0), ("peak", 420, 1.0, -3.0),
       ("peak", 2200, 1.0, 2.0), ("peak", 3600, 2.0, -2.0), ("lp", 6000, 0.7, 0), ("lp", 6000, 0.7, 0),
       ("lp", 10000, 0.7, 0),
       ("peak", 200, 1.2, 3.0))    # (the body: the synth's DI is 1-2 dB leaner low than the library's
                                   # own player, which the amp widens - this puts it back, within 1 dB)
# Offline (no guitar.sf2): the GM distortion guitar - a distortion already - through a
# cabinet only, which takes its 2.5-3 kHz buzz down from 28% of its energy to 11%.
CAB_GM = (("hp", 90, 0.7, 0), ("hp", 90, 0.7, 0), ("peak", 120, 1.0, 2.5), ("peak", 3000, 1.2, -5),
          ("peak", 6500, 1.0, -4), ("lp", 5000, 0.7, 0), ("lp", 5000, 0.7, 0), ("lp", 7000, 0.7, 0))


def _amp(di, rate: int):
    """A DI guitar (mono) through the amp: pre-EQ, two asymmetric tanh stages 4x
    oversampled (so the distortion doesn't fold back as fizz), then the cabinet."""
    import numpy as np
    x = _filter(np.asarray(di, dtype="float64") * GUITAR_DRIVE, AMP_PRE, rate)
    out = np.zeros_like(x)
    blk, pad, k = 4 * rate, 4096, 4
    g = 10 ** (AMP_GAIN_DB / 20)
    for i in range(0, len(x), blk):
        a, b = max(0, i - pad), min(len(x), i + blk + pad)
        seg = x[a:b]
        n = len(seg)
        X = np.fft.rfft(seg)
        U = np.zeros(n * k // 2 + 1, dtype=complex)
        U[:len(X)] = X
        u = np.fft.irfft(U, n * k) * k                       # (up 4x)
        u = np.tanh(g * u + 0.15) - np.tanh(0.15)
        u = u - np.convolve(u, np.ones(512) / 512, mode="same")
        u = np.tanh(3.0 * u)
        d = np.fft.irfft(np.fft.rfft(u)[:n // 2 + 1], n) / k  # (and down)
        m = min(blk, len(x) - i)
        out[i:i + m] = d[i - a:i - a + m]
    return _filter(out, CAB, rate) * 10 ** (AMP_LEVEL_DB / 20)


def _studio_room(x, rate: int):
    """A small dry studio room (RT ~0.25 s, 12%): a close-miked cabinet's own air."""
    import numpy as np
    rng = np.random.default_rng(3)
    n = int(0.3 * rate)
    t = np.arange(n) / rate
    ir = rng.standard_normal((n, 2)) * np.exp(-6.91 * t / 0.25)[:, None]
    ir /= np.sqrt((ir ** 2).sum(axis=0))
    N = _fast_len(len(x) + n)
    wet = np.fft.irfft(np.fft.rfft(x, N, axis=0) * np.fft.rfft(ir, N, axis=0), N, axis=0)[:len(x)]
    return x + 0.12 * wet


def _guitar_stem(syn, sfid, fonts, events: list, total: int, rate: int):
    """The guitar (both its parts: one instrument, one amp) -> (first sample, stereo stem).
    Played twice - a left and a right pass, the right one a few ms off on each pick (5-15 ms),
    its velocities varied, its takes others - each pass a DI through the amp, panned hard
    left and right: a double-tracked rhythm guitar. A new pick stops what was ringing (the
    same strings). Offline: the GM distortion guitar, through a cabinet instead of the amp."""
    import numpy as np
    font = fonts.get("guitar")
    own = font is not None
    ons: Dict[Tuple[int, int], list] = {}
    notes = []                                                  # (on, off, key, vel, art)
    for t, is_on, name, key, vel in sorted(events, key=lambda e: (e[0], e[1])):
        art = GUITAR.get(name.partition(":")[0], 0)
        if is_on == 1:
            ons.setdefault((art, key), []).append((t, vel))
        elif is_on == 0 and ons.get((art, key)):
            t0, v = ons[(art, key)].pop(0)
            notes.append((t0, t, key, v, art))
    notes += [(t0, total / rate, key, v, art) for (art, key), left in ons.items() for t0, v in left]
    if not notes:
        return total, np.zeros((0, 2), dtype="float32")
    notes.sort()
    picks = sorted({round(n[0], 4) for n in notes})
    nxt = {p: (picks[i + 1] if i + 1 < len(picks) else 1e9) for i, p in enumerate(picks)}
    first = max(0, int((notes[0][0] - 0.02) * rate))
    end = min(total, int((max(n[1] for n in notes) + 1.0) * rate))
    if end <= first:
        return total, np.zeros((0, 2), dtype="float32")
    sides = []
    for side in (0, 1):
        rng = np.random.default_rng(11 + side)
        shift = {p: (0.0 if side == 0 else float(rng.uniform(0.005, 0.015)) * (1 if rng.random() < 0.5 else -1))
                 for p in picks}
        dvel = {p: (0 if side == 0 else int(round(rng.normal(0, 5)))) for p in picks}
        turn = {0: side, 1: side}                                 # (the right pass: other takes)
        took: Dict[Tuple[int, float], int] = {}
        ev = []
        for t0, t1, key, vel, art in notes:
            p = round(t0, 4)
            if (art, p) not in took:
                took[(art, p)] = turn[art] % GUITAR_TAKES
                turn[art] += 1
            off = min(t1, nxt[p])                               # (a new pick stops it)
            if not own and art == 1:
                off = min(off, t0 + 0.16)                       # (offline: a palm mute, short)
            ch = (art * GUITAR_TAKES + took[(art, p)]) if own else art
            v = int(max(1, min(127, vel + dvel[p])))
            ev.append((max(0.0, t0 + shift[p]), 1, ch, key, v))
            ev.append((max(0.0, off + shift[p]), 0, ch, key, 0))
        ev.sort(key=lambda e: (e[0], e[1]))
        streams = (0, 1) if not own else (None,)
        di = np.zeros(end - first)
        for only in streams:                                    # (offline: the mutes darker, apart)
            for c in range(2 * GUITAR_TAKES if own else 2):
                if own:
                    syn.program_select(c, font, 0, _guitar_preset(c // GUITAR_TAKES, side, c % GUITAR_TAKES))
                else:
                    syn.program_select(c, sfid, *FALLBACK["guitar"])
                syn.control_change(c, 7, 100)
                syn.control_change(c, 10, 64)
            chunks, pos = [], first
            for t, is_on, ch, key, vel in ev:
                if only is not None and ch != only:
                    continue
                at = min(end, int(t * rate))
                if at > pos:
                    chunks.append(np.frombuffer(syn.generate(at - pos), dtype="float32"))
                    pos = at
                if is_on:
                    syn.noteon(ch, key, vel)
                else:
                    syn.noteoff(ch, key)
            if pos < end:
                chunks.append(np.frombuffer(syn.generate(end - pos), dtype="float32"))
            for c in range(2 * GUITAR_TAKES if own else 2):
                syn.sounds_off(c)
            syn.generate(256)
            if not chunks:
                continue
            x = np.concatenate(chunks).reshape(-1, 2).mean(axis=1).astype("float64")[:end - first]
            if only == 1:
                x = _filter(x, [("lp", 2200, 0.7, 0.0)], rate)
            di[:len(x)] += x
        sides.append(_amp(di, rate) if own else _filter(di, CAB_GM, rate))
    stem = _studio_room(np.stack(sides, axis=1) * (1.0 if own else GUITAR_GM_GAIN), rate)
    return first, stem.astype("float32")


# --- the rock organ: a tonewheel organ, overdriven, through a rotating speaker ---
# Synthesized, not sampled: a tonewheel organ IS additive synthesis - 91 near-sine wheels
# spinning all the time, a key connecting nine of them (its drawbars' footages) to the
# output through nine busbar contacts. Then a tube preamp driven hard (the growl) and a
# rotating speaker (a treble horn and a bass drum, spinning slow or fast), miked left and
# right: the sound of 70s heavy rock and of Dancing Mad's last movement. No download.
ORGAN = {"rock_organ"}
# The tonewheel generator's gears (C..B: driving / driven teeth) on a 20 rev/s shaft: its
# tuning, within a cent or so of equal temperament - A is 440 exactly, the rest a little off.
ORGAN_GEARS = (85 / 104, 71 / 82, 67 / 73, 105 / 108, 103 / 100, 84 / 77,
               74 / 64, 98 / 80, 96 / 74, 88 / 64, 67 / 46, 108 / 70)
ORGAN_WHEELS = (24, 114)    # the 91 wheels: C1 (32.7 Hz) to F#8 (5.9 kHz); higher footages fold back
# The drawbars' footages, as semitones from the key: 16', 5 1/3', 8', 4', 2 2/3', 2', 1 3/5',
# 1 1/3', 1' (each a wheel of its own: the fifths and the third are the tempered ones).
DRAWBARS = (-12, 7, 0, 12, 19, 24, 28, 31, 36)
# The rock registration: 888800000 - the four lowest drawbars full out (16', 5 1/3', 8', 4'):
# the fat 888 of 70s rock with the octave that cuts. 888000000 alone, measured through this
# drive, puts 0.1-0.6% of a chord's energy above the 800 Hz crossover: the horn - where the
# speaker's swirl and the organ's bite live - has almost nothing to spin, and under an
# orchestra (strings, brass, choir all in 100-400 Hz) the organ reads as a dull bass pad. The
# 4' gives the horn ~2.5% (a sampled GM rock organ: 13%, brighter than a tonewheel's 888).
# Nothing above the 4' is drawn: no fizz through the drive (the "drawbars" option changes it).
ORGAN_DRAWBARS = "888800000"
ORGAN_LOW, ORGAN_HIGH = 36, 96          # a manual: C2-C7, 61 keys
ORGAN_CLICK_MS = (0.0, 3.0)             # the nine contacts close this far apart as a key goes down
ORGAN_PERC = {"second": (12, 0.20), "third": (19, 0.20)}   # percussion: its footage, its decay (s, fast)
ORGAN_PERC_LEVEL = 1.4  # (its "normal" volume: struck over a full drawbar)
# The tonewheels into the preamp: one note 20-30% distortion (warm), a power chord 35-45%
# (the growl) - the swell (velocity) drives it harder.
ORGAN_DRIVE = 1.0
ORGAN_BIAS = 0.3        # (the tube's asymmetry: one side clips softer - even harmonics, the growl)
ORGAN_LEVEL_DB = -29.5  # the speaker's output: the organ, at no "mix", as loud as the guitar (LUFS, the same riff)
# The rotating speaker (a Leslie 122's): its horn and its drum, their slow (chorale) and fast
# (tremolo) speeds in rev/s, how fast they get there (a time constant, s: the light horn in
# ~1 s, the heavy drum in ~4), the radius that moves the sound (Doppler) and how much louder
# it is facing a mic than facing away. They turn in opposite directions.
LESLIE = {"horn": {"slow": 0.80, "fast": 6.7, "up": 0.33, "down": 0.5, "radius": 0.15,
                   "am": 0.45, "am_hi": 0.75, "spin": 1.0},
          "drum": {"slow": 0.67, "fast": 5.8, "up": 1.3, "down": 1.6, "radius": 0.10,
                   "am": 0.28, "spin": -1.0}}
LESLIE_MICS = (math.radians(75), math.radians(-75))   # left and right of the cabinet, 150 degrees apart
LESLIE_CROSSOVER = 800.0


def _organ_hz(key: int) -> float:
    """A tonewheel's frequency (its gears, not equal temperament)."""
    return 20.0 * ORGAN_GEARS[key % 12] * 2 ** (key // 12 - 1)


def _organ_wheel(key: int) -> int:
    """The wheel a key's footage plays: the generator's top octave folds back, its bottom up."""
    while key > ORGAN_WHEELS[1]:
        key -= 12
    while key < ORGAN_WHEELS[0]:
        key += 12
    return key


def _drawbar_levels(reg: str) -> List[float]:
    """A registration ("888000000") -> each drawbar's level: 8 full, each step 3 dB down, 0 off."""
    reg = (str(reg) + "000000000")[:9]
    return [0.0 if c == "0" else 10 ** (-3 * (8 - int(c)) / 20) for c in reg]


def _oversampled(x, fn, k: int = 4, rate: int = RATE):
    """``fn`` (a waveshaper) on x (mono) run at k times the rate, block by block, so its
    harmonics don't fold back as fizz."""
    import numpy as np
    out = np.zeros_like(x)
    blk, pad = 4 * rate, 4096
    for i in range(0, len(x), blk):
        a, b = max(0, i - pad), min(len(x), i + blk + pad)
        seg = x[a:b]
        n = len(seg)
        U = np.zeros(n * k // 2 + 1, dtype=complex)
        U[:n // 2 + 1] = np.fft.rfft(seg)
        u = fn(np.fft.irfft(U, n * k) * k)
        d = np.fft.irfft(np.fft.rfft(u)[:n // 2 + 1], n) / k
        m = min(blk, len(x) - i)
        out[i:i + m] = d[i - a:i - a + m]
    return out


def _organ_drive(x, rate: int):
    """The speaker's tube preamp, driven hard: an asymmetric soft clip (one side gives
    sooner - even harmonics), 4x oversampled, its DC taken out."""
    import numpy as np
    b = ORGAN_BIAS

    def tube(u):
        return (np.tanh(u + b) - math.tanh(b)) / (1 - math.tanh(b) ** 2)
    y = _oversampled(np.asarray(x, dtype="float64") * ORGAN_DRIVE, tube, 4, rate)
    return _filter(y, [("hp", 30, 0.7, 0.0)], rate)


def _rotor_speed(changes, n: int, rate: int, rotor: dict, fast: bool):
    """A rotor's speed (rev/s) at every sample from the start: ``changes`` [(sample, fast?)],
    each a switch it eases into (slow to fast in its "up" time constant, down in "down")."""
    import numpy as np
    f = np.empty(n)
    for s, v in sorted(changes):
        if s <= 0:                                              # (switched from the start: so it starts)
            fast = v
    cur = rotor["fast" if fast else "slow"]
    marks = [(0, fast)] + [(max(0, min(n, s)), v) for s, v in sorted(changes)] + [(n, None)]
    for (a, want), (b, _) in zip(marks, marks[1:]):
        if b <= a:
            continue
        tgt = rotor["fast" if want else "slow"]
        tau = rotor["up"] if tgt > cur else rotor["down"]
        f[a:b] = tgt + (cur - tgt) * np.exp(-np.arange(b - a) / (rate * tau))
        cur = float(f[b - 1])
    return f


def _delayed(x, d):
    """x read d samples late (d varying, >= 1), linearly interpolated."""
    import numpy as np
    pos = np.arange(len(x)) - d
    i = np.floor(pos).astype(np.int64)
    fr = pos - i
    xp = np.concatenate([x, [0.0]])
    ok = i >= 0
    i0 = np.where(ok, i, len(x))
    i1 = np.where(ok, np.minimum(i + 1, len(x) - 1), len(x))
    return xp[i0] * (1 - fr) + xp[i1] * fr


def _leslie(x, rate: int, first: int, changes, fast: bool = True):
    """The rotating speaker: x (mono, from sample ``first`` of the piece) split at 800 Hz
    to a horn and a drum, each turning (the speed eased between slow and fast at each of
    ``changes`` [(sample, fast?)]), heard by two mics: each rotor's sound moving toward and
    away from a mic (a Doppler delay) and facing it and turning away (louder, and brighter
    for the horn), with the cabinet's back wall a second, later path. -> stereo (n, 2)."""
    import numpy as np
    n = len(x)
    lo = _filter(x, [("lp", LESLIE_CROSSOVER, 0.7071, 0.0)] * 2, rate)
    hi = _filter(x, [("hp", LESLIE_CROSSOVER, 0.7071, 0.0)] * 2 + [("peak", 2000, 0.8, 2.0),
                                                                   ("lp", 6000, 0.7, 0.0), ("lp", 7500, 0.7, 0.0)], rate)
    out = np.zeros((n, 2))
    c = 343.0
    for name, sig in (("horn", hi), ("drum", lo)):
        r = LESLIE[name]
        f = _rotor_speed(changes, first + n, rate, r, fast)
        theta = r["spin"] * 2 * np.pi * np.cumsum(f)[first:] / rate + (0.0 if name == "horn" else 1.3)
        del f
        if name == "horn":                                      # (the horn's highs beam: more swing)
            split = _filter(sig, [("lp", 3000, 0.7071, 0.0)] * 2, rate)
            bands = ((split, r["am"]), (sig - split, r["am_hi"]))
        else:
            bands = ((sig, r["am"]),)
        reach = r["radius"] / c * rate
        for ch, mic in enumerate(LESLIE_MICS):
            for turn, gain, late in ((0.0, 1.0, 0.0), (np.pi, 0.35, 0.0009 * rate)):   # (direct, the back wall)
                cosv = np.cos(theta - mic + turn)
                d = 1.0 + late + reach * (1.0 - cosv)            # (nearer as it faces the mic)
                heard = sum(band * (1.0 + am * cosv) / math.sqrt(1.0 + am * am / 2) for band, am in bands)
                out[:, ch] += gain * _delayed(heard, d)
    return out


def _organ_stem(events: list, total: int, rate: int, organ: Optional[dict] = None):
    """The rock organ -> (first sample, stereo stem). Each key connects its drawbars' wheels
    (free-running: a wheel two keys share is one sine, its phase its own since the organ was
    switched on), each through a contact that closes a moment apart from the others and
    chatters (the key click); single-triggered percussion if asked for; the swell (velocity)
    into the overdriven preamp, then the rotating speaker - fast unless the score says slow
    (``events`` with is_on 3: the speaker switched there, its "vel" 1 fast, 0 slow)."""
    import numpy as np
    organ = organ or {}
    levels = _drawbar_levels(organ.get("drawbars", ORGAN_DRAWBARS))
    perc = ORGAN_PERC.get(organ.get("percussion") or "")
    if perc:
        levels[8] = 0.0                                         # (the percussion takes the 1' bus)
    fast = organ.get("speaker", "fast") != "slow"
    ons: Dict[int, list] = {}
    notes, changes = [], []
    for t, is_on, _, key, vel in sorted(events, key=lambda e: (e[0], e[1])):
        if is_on == 3:
            changes.append((int(t * rate), bool(vel)))
        elif is_on == 1:
            ons.setdefault(key, []).append((t, vel))
        elif is_on == 0 and ons.get(key):
            t0, v = ons[key].pop(0)
            notes.append((t0, t, key, v))
    notes += [(t0, total / rate, key, v) for key, left in ons.items() for t0, v in left]
    if not notes:
        return total, np.zeros((0, 2), dtype="float32")
    notes.sort()
    first = max(0, int((notes[0][0] - 0.01) * rate))
    end = min(total, int((max(n[1] for n in notes) + 0.45) * rate))
    if end <= first:
        return total, np.zeros((0, 2), dtype="float32")
    n = end - first
    rng = np.random.default_rng(1935)                           # (the year it was patented)
    phase = rng.uniform(0, 2 * np.pi, ORGAN_WHEELS[1] + 1)
    gates: Dict[int, list] = {}                                 # wheel -> [(start, end, level)]
    decays: Dict[int, list] = {}                                # wheel -> [(start, end, level, decay)]: percussion
    for i, (t0, t1, key, vel) in enumerate(notes):
        swell = (max(1, min(127, vel)) / 127) ** 1.5
        a, b = int(t0 * rate) - first, int(t1 * rate) - first
        for off, lvl in zip(DRAWBARS, levels):
            if not lvl:
                continue
            w = _organ_wheel(key + off)
            close = a + int(rng.uniform(*ORGAN_CLICK_MS) * rate / 1000)
            opens = max(close + 1, b + int(rng.uniform(0.0, 2.0) * rate / 1000))
            g = gates.setdefault(w, [])
            for edge in (close, opens):                         # (the contact chatters: 1-3 bounces)
                for _ in range(int(rng.integers(1, 4))):
                    s = edge + int(rng.uniform(0.05, 0.6) * rate / 1000)
                    e = s + max(1, int(rng.uniform(0.05, 0.25) * rate / 1000))
                    if edge == close and e < opens:             # (closing: it opens again a moment)
                        g.append((s, e, -lvl * swell))
                    elif edge == opens:                         # (opening: it touches again a moment)
                        g.append((s, e, lvl * swell))
            g.append((close, opens, lvl * swell))
        if perc:                                                # single trigger: only from all keys up
            held = any(o0 < t0 - 0.012 and o1 > t0 for o0, o1, _, _ in notes[:i])
            if not held:
                decays.setdefault(_organ_wheel(key + perc[0]), []).append((a, b, ORGAN_PERC_LEVEL * swell, perc[1]))
    tone = np.zeros(n)
    for w in sorted(set(gates) | set(decays)):
        spans = gates.get(w, []) + [(s, e, 0.0) for s, e, _, _ in decays.get(w, [])]
        lo = max(0, min(s for s, _, _ in spans))
        hi = min(n, max(e for _, e, _ in spans))
        if hi <= lo:
            continue
        env = np.zeros(hi - lo + 1)
        for s, e, lvl in gates.get(w, []):
            s, e = max(lo, min(hi, s)), max(lo, min(hi, e))
            env[s - lo] += lvl
            env[e - lo] -= lvl
        env = np.cumsum(env)[:-1]
        np.maximum(env, 0.0, out=env)                           # (a bounce can't go below open)
        for s, e, lvl, tau in decays.get(w, []):
            s, e = max(lo, s), min(hi, e)
            if e > s:
                env[s - lo:e - lo] += lvl * np.exp(-np.arange(e - s) / (tau * rate))
        f = _organ_hz(w)
        ph = 2 * np.pi * f * (np.arange(lo, hi) + first) / rate + phase[w]
        # a tonewheel is a near-sine: a trace of 2nd and 3rd harmonic (the low wheels more)
        impure = 0.03 if w < 48 else 0.012
        wave = np.sin(ph)
        if 2 * f < rate / 2.2:
            wave += 0.4 * impure * np.sin(2 * ph)
        if 3 * f < rate / 2.2:
            wave += impure * np.sin(3 * ph)
        tone[lo:hi] += env * wave
    tone = _filter(tone, [("hp", 35, 0.7, 0.0)], rate)
    driven = _organ_drive(tone, rate)
    stem = _leslie(driven, rate, first, changes, fast)
    stem = _studio_room(stem, rate) * 10 ** (ORGAN_LEVEL_DB / 20)
    return first, stem.astype("float32")


EXTRA_FONTS = {"chorus": fetch_choir, "vowels": fetch_vowels, "perc": fetch_percussion,
               "guitar": fetch_guitar, "strings_short": fetch_strings_short, "brass": fetch_brass,
               "horn_solo": fetch_horn_solo}


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
    "trombones": 9.7, "horns": 11.8, "horn_solo": 11.8, "solo_violin": 2.9, "men_choir": 5.5, "chorus": 5.6, "choir_oo": 11.5, "choir_oh": 11.6,
    # the real percussion (perc.sf2), set so a mf stroke (velocity 80) peaks (400 ms) like the
    # kit's: the gong like its crash "gong", the bass drum like its bass drum, the anvil and
    # the brake drum like its snare
    "gong": 8.7, "bass_drum": -5.7, "anvil": -6.1, "brake_drum": -2.3,
    # the guitar through its amp (AMP_LEVEL_DB): at no "mix", ~6 dB under a forte orchestra -
    # a distorted guitar is dense (its peaks barely over its body): heard well there
    "guitar": 0.0, "guitar_mute": 0.0,
    # the rock organ through its speaker (ORGAN_LEVEL_DB): set where the guitar sits
    "rock_organ": 0.0,
}
# (The parts that play their own recordings - OWN, STRINGS_SHORT's short notes - are evened out
# to these, the sound set's, by their "trim_db": the same velocity, the same loudness.)
# How long each instrument's recording takes to speak (seconds to half its level), and
# where it plays (MIDI, its practical range): for the score critic (arrangement.check). A string
# part's notes under SHORT_S play from the short-note recordings, which speak at once
# (STRINGS_SHORT's "speak": 0.04-0.055 s): only its longer notes take SPEAKS to speak.
SPEAKS = {"choir": 0.18, "men_choir": 0.1, "chorus": 0.1, "choir_oo": 0.05, "choir_oh": 0.08, "strings": 0.48, "violins": 0.50, "violins2": 0.26, "english_horn": 0.42,
          "cellos": 0.24, "tremolo": 0.16, "organ": 0.10, "oboe": 0.12, "brass": 0.08, "horns": 0.06}
RANGES = {
    "violins": (55, 100), "violins2": (55, 96), "strings": (36, 96), "tremolo": (36, 96),
    "pizzicato": (28, 96), "cellos": (36, 76), "basses": (28, 60), "flutes": (60, 96),
    "piccolo": (74, 108), "oboe": (58, 91), "english_horn": (52, 81), "clarinets": (50, 91),
    "bassoons": (34, 72), "horns": (41, 77), "horn_solo": (41, 77), "trumpets": (54, 82), "trombones": (40, 72),
    "tuba": (28, 58), "brass": (36, 84), "choir": (40, 81), "harp": (24, 103),
    "celesta": (60, 108), "glockenspiel": (79, 108), "bells": (60, 77), "organ": (24, 96),
    "timpani": (38, 55), "solo_violin": (55, 100), "men_choir": (40, 69), "chorus": (40, 88), "choir_oo": (45, 87), "choir_oh": (45, 87),
    # the struck percussion: one sound each, on its own key (PERC; "root" or any drum name in a
    # score plays it), pitched a little around it - the gong down to A2, bigger and slower
    **{part: (p["lo"], p["hi"]) for part, p in PERC.items()},
    # the guitar: B1 (a 7-string's low B, a drop tuning's D2) to E5; power chords sit B1-D4
    "guitar": (GUITAR_LOW, GUITAR_KEYS[1]), "guitar_mute": (GUITAR_LOW, GUITAR_KEYS[1]),
    # the rock organ: a manual's 61 keys, C2-C7
    "rock_organ": (ORGAN_LOW, ORGAN_HIGH),
}
# How late each instrument's recording is heard after its note starts (seconds to come
# within 9 dB of its full level, measured from MuseScore_General, less the ~20 ms a
# listener forgives): play() starts its notes that much early, so instruments
# playing together are heard together, on the beat (the violins doubling a quick
# clarinet were ~150 ms behind it). The reverse cymbal is written to swell into the
# beat; the string pad, which holds chords, is moved at most 250 ms. The host, on a
# tune they knew (Ode to Joy): "clearly better". (Another sound set's instruments need
# their own measurement: the short string notes' and the parts' own recordings' are
# STRINGS_SHORT's and OWN's "advance" - part_advance.)
ADVANCE = {"violins": 0.15, "violins2": 0.18, "cellos": 0.09, "tremolo": 0.115, "choir": 0.13, "men_choir": 0.06, "chorus": 0.06, "choir_oo": 0.02, "choir_oh": 0.06,
           "strings": 0.25, "trombones": 0.02, "organ": 0.015, "flutes": 0.012, "piccolo": 0.01,
           "solo_violin": 0.032}
# How much room each recording carries already (dB: its energy after a short note is
# released, against the note's), measured from MuseScore_General for the instruments
# whose sound stops when they do (bowed strings, the choir and ringing instruments
# are left out: their own ring isn't a room). The hall adds about HALL_ROOM to a dry
# one; each part is sent to it just enough to end at that same room, so the orchestra
# sounds like one place (the host heard recordings with their own room as a different
# acoustic: "the difference is mainly in the acoustics").
ROOM = {"flutes": -20.8, "horns": -17.5, "horn_solo": -17.5, "trumpets": -39.3, "trombones": -25.5, "tuba": -25.6,
        "piccolo": -22.3, "oboe": -24.1, "english_horn": -34.2, "clarinets": -33.4, "bassoons": -25.6,
        "brass": -20.9, "organ": -15.4, "pizzicato": -24.9, "taiko": -20.9, "toms": -28.9,
        # the guitar: close-miked in a small room of its own (_studio_room), sent to the hall
        # only a little (-12 dB) - a rhythm guitar is heard dry, in front, not across a hall
        "guitar": HALL_ROOM_GUITAR,
        "rock_organ": HALL_ROOM_GUITAR}     # (the rock organ's speaker too: in its room, in front)
HALL_ROOM = -12.8
# (A part playing its own recordings is sent as OWN says; the brass BRASS_DRY_DB drier:
# part_send_db.)


def send_db(room: Optional[float]) -> float:
    """The hall send (dB) for a recording carrying ``room`` dB of its own room."""
    if room is None:
        return 0.0
    need = 10 ** (HALL_ROOM / 10) - 10 ** (room / 10)
    return -12.0 if need <= 10 ** ((HALL_ROOM - 12) / 10) else max(-12.0, 10 * math.log10(need) - HALL_ROOM)


BALANCE = {
    "horns": 2, "horn_solo": 2, "trumpets": 3, "trombones": 2, "brass": 3, "violins": 1, "strings": -3,
    "tremolo": -2, "choir": 3, "men_choir": 3, "chorus": 3, "choir_oo": 3, "choir_oh": 3, "timpani": 2, "taiko": 3, "glockenspiel": -2, "piccolo": -2,
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


_SYNTHS: Dict[Tuple[int, str], list] = {}


def _synth(rate: int, sf2: Path, need=()):
    """One synth per rate and sound set, kept for the process (loading the SoundFont took
    about a second, on every play), with the extra sound sets ``need``s loaded on it."""
    import tinysoundfont
    key = (rate, str(sf2))
    if key not in _SYNTHS:
        syn = tinysoundfont.Synth(gain=-12, samplerate=rate)
        _SYNTHS[key] = [syn, syn.sfload(str(sf2)), {}]
    syn, sfid, fonts = _SYNTHS[key]
    for font in need:
        if font not in fonts:
            try:
                fonts[font] = syn.sfload(str(EXTRA_FONTS[font](quiet=True)))
            except Exception as e:                              # offline: the sound set's stand-in
                instead = ("the GM distortion guitar plays it, through a cabinet (orchestra.fetch_guitar "
                           "builds the real one)" if font == "guitar" else
                           "the sound set's sustained strings play the short notes too" if font == "strings_short"
                           else "the sound set's stand-in plays")
                print(f"[orchestra] no {font} ({e}): {instead}", file=sys.stderr)
    return syn, sfid, fonts


def _stem(syn, sfid, fonts, name: str, events: list, total: int, rate: int, short: bool = False,
          organ: Optional[dict] = None):
    """One part (or one layer of one) played alone -> (first sample, stereo float32 stem
    from there): nothing is played before its first note or after its last note has rung
    out (most parts are silent most of a piece). ``short``: a string part's short notes, from
    their own recordings (STRINGS_SHORT). ``organ``: the rock organ's settings (Score.organ)."""
    import numpy as np
    part = name.partition(":")[0]
    if part in GUITAR:                                      # (the guitar: its own player, an amp)
        return _guitar_stem(syn, sfid, fonts, events, total, rate)
    if part in ORGAN:                                       # (the rock organ: synthesized)
        return _organ_stem(events, total, rate, organ)
    if short:
        return _sampled_stem(syn, fonts["strings_short"], part, STRINGS_SHORT[part], events, total, rate)
    if _plays_own(part, fonts):
        return _sampled_stem(syn, fonts[OWN[part]["font"]], part, OWN[part], events, total, rate)
    bank, preset, pan, vol = PARTS[part][:4]
    font, drum, stand_in, own = sfid, part in DRUMS, None, False
    if len(PARTS[part]) > 4:
        if fonts.get(PARTS[part][4]) is not None:
            font, own = fonts[PARTS[part][4]], True
        else:
            bank, preset, *stand_in = FALLBACK[part]
            drum = bank == 128                              # (a GM kit's drum, on its own key)
    perc = PERC.get(part) if own else None                  # the real percussion: let ring,
    turns = len(perc["layers"][0][1]) if perc else 1        # its round-robins in turn
    struck = 0
    bends = any(e[1] == 2 for e in events)
    ch = 9 if drum else 0
    syn.program_select(ch, font, bank, preset, drum)
    syn.control_change(ch, 7, vol)
    syn.control_change(ch, 10, pan)
    if bends:
        syn.pitchbend_range(ch, 12)
        syn.pitchbend(ch, 8192)
    events = sorted(events, key=lambda e: (e[0], e[1]))
    first = min(total, int(events[0][0] * rate)) if events else total
    chunks, pos = [], first
    for t, is_on, _, key, vel in events:
        at = min(total, int(t * rate))
        if at > pos:
            chunks.append(np.frombuffer(syn.generate(at - pos), dtype="float32"))
            pos = at
        if stand_in:
            key = stand_in[0]
        if is_on == 2:
            syn.pitchbend(ch, int(max(0, min(16383, 8192 + vel / 12 * 8191))))
        elif is_on:
            if perc:
                key += RR_KEYS * (struck % turns)
                struck += 1
            syn.noteon(ch, key, vel)
        elif not perc:                                      # (struck percussion rings on)
            syn.noteoff(ch, key)
    step = max(1, rate // 4)
    while pos < total:                                      # ring out, then stop: silence
        piece = np.frombuffer(syn.generate(min(step, total - pos)), dtype="float32")
        chunks.append(piece)
        pos += len(piece) // 2
        if float(np.abs(piece).max(initial=0.0)) < 1e-6:
            break
    syn.sounds_off(ch)
    if bends:
        syn.pitchbend(ch, 8192)
    syn.generate(256)                                       # (let the cut voices go)
    stem = np.concatenate(chunks).reshape(-1, 2) if chunks else np.zeros((0, 2), dtype="float32")
    return first, stem


def _workers(jobs: int) -> int:
    """How many processes play a piece's parts (GM_ORCHESTRA_WORKERS overrides; 1: here)."""
    want = os.environ.get("GM_ORCHESTRA_WORKERS")
    n = int(want) if want and want.isdigit() else (os.cpu_count() or 1)
    if n > 1 and not hasattr(os, "fork"):
        n = 1
    return max(1, min(n, jobs, 8))


def play_layers(score: Score, seconds: float, layer_of, sf2: Path = SF2, rate: int = RATE,
                mix: Optional[Dict[str, float]] = None, align: bool = True, send: bool = True):
    """Like play(), but the parts sum into separate layers: ``layer_of(part name)`` -> a
    layer key (None: left out) -> {key: dry mix (with ``.send`` when ``send``)}. The parts
    play in parallel, one process per core: the synth holds Python's lock."""
    import mmap
    import numpy as np
    groups: Dict[str, list] = {}
    for e in score.events:
        part, colon, layer = e[2].partition(":")
        # the guitar's two parts are one instrument through one amp: played together, as "guitar"
        groups.setdefault("guitar" + colon + layer if part in GUITAR else e[2], []).append(e)
    keys: List = []
    jobs = []
    wanted = {name: layer_of(name) for name in groups}
    need = set()
    for name, k in wanted.items():
        part = name.partition(":")[0]
        if k is not None and len(PARTS[part]) > 4:
            need.add(PARTS[part][4])
        if k is not None and part in STRINGS_SHORT:
            need.add("strings_short")
    syn, sfid, fonts = _synth(rate, sf2, sorted(need))
    organ = dict(getattr(score, "organ", None) or {})
    for name, events in groups.items():
        k = wanted[name]
        if k is None:
            continue
        if k not in keys:
            keys.append(k)
        part = name.partition(":")[0]
        bends = [(t, 2, name, 0, sem) for t, p, sem in getattr(score, "bends", []) if p == part]
        if part in ORGAN:                                   # (3: its speaker switched, "vel" 1 fast)
            bends = [(t, 3, name, 0, int(f)) for t, f in getattr(score, "speaker", [])]
        arts = [(False, events)]
        if part in STRINGS_SHORT and fonts.get("strings_short") is not None:
            short, long_ = _split_short(events)             # (a short note: its own recordings)
            arts = [(s, ev) for s, ev in ((True, short), (False, long_)) if ev]
        for short, evs in arts:
            evs = list(evs) + bends                         # (2: a bend, its semitones as "vel")
            early = part_advance(part, short, _plays_own(part, fonts)) if align else 0.0
            if early:                                       # (heard on the beat: see ADVANCE)
                evs = [(max(0.0, t - early), *rest) for t, *rest in evs]
            jobs.append((name, keys.index(k), evs, short))
    total = int((seconds + 0.5) * rate)
    lanes = 2 if send else 1
    w = _workers(len(jobs))
    shape = (w, len(keys), lanes, total, 2)
    size = int(np.prod(shape)) * 4
    buf = mmap.mmap(-1, max(1, size)) if w > 1 else bytearray(max(1, size))
    acc = np.frombuffer(buf, dtype="float32", count=int(np.prod(shape))).reshape(shape)

    def run(slot: int, mine) -> None:
        for name, k, events, short in mine:
            part, _, layer = name.partition(":")
            first, stem = _stem(syn, sfid, fonts, name, events, total, rate, short,
                                **({"organ": organ} if part in ORGAN else {}))
            if not len(stem):
                continue
            gain = level_db(part, mix) + (float(layer) if layer else 0.0)
            span = slice(first, first + len(stem))
            acc[slot, k, 0, span] += stem * np.float32(10 ** (gain / 20))
            if send:
                hall_db = part_send_db(part, _plays_own(part, fonts))
                acc[slot, k, 1, span] += stem * np.float32(10 ** ((gain + hall_db) / 20))

    if w == 1:
        run(0, jobs)
    else:                                       # longest parts first, each to the least busy
        cost = lambda j: len(j[2]) + 40 * (max(e[0] for e in j[2]) - min(e[0] for e in j[2]))
        shares: List[list] = [[] for _ in range(w)]
        load = [0.0] * w
        for j in sorted(jobs, key=cost, reverse=True):
            i = load.index(min(load))
            shares[i].append(j)
            load[i] += cost(j)
        pids = []
        for slot in range(w):
            pid = os.fork()
            if pid == 0:                                    # (a child: play, then leave at once)
                code = 0
                try:
                    run(slot, shares[slot])
                except BaseException:
                    import traceback
                    traceback.print_exc()
                    code = 1
                os._exit(code)
            pids.append(pid)
        failed = [pid for pid in pids if os.waitpid(pid, 0)[1] != 0]
        if failed:
            raise RuntimeError(f"[orchestra] {len(failed)} of {w} player processes failed")
    out = {}
    for i, k in enumerate(keys):
        dry = acc[:, i, 0].sum(axis=0).view(_dry_type())
        dry.send = acc[:, i, 1].sum(axis=0) if send else None
        out[k] = dry
    del acc
    return out


def play(score: Score, seconds: float, sf2: Path = SF2, rate: int = RATE,
         mix: Optional[Dict[str, float]] = None, align: bool = True):
    """The score through the SoundFont -> stereo float32 (n, 2), dry. Each part (and
    each layer of one: "horns:4", the tune's notes) is played on its own and mixed
    at its level (level_db, plus the layer's dB), so a piece can use any number."""
    import numpy as np
    out = play_layers(score, seconds, lambda name: 0, sf2, rate, mix, align).get(0)
    if out is None:
        total = int((seconds + 0.5) * rate)
        out = np.zeros((total, 2), dtype="float32").view(_dry_type())
        out.send = np.zeros((total, 2), dtype="float32")
    return out


def _fast_len(n: int) -> int:
    """The smallest 2^a 3^b 5^c >= n: an FFT size about as fast as a power of two."""
    best = 1 << int(math.ceil(math.log2(max(1, n))))
    p5 = 1
    while p5 < best:
        p35 = p5
        while p35 < best:
            q = p35
            while q < n:
                q *= 2
            best = min(best, q)
            p35 *= 3
        p5 *= 5
    return best


_IRS: Dict[Tuple[int, float, int], "object"] = {}


def _hall_ir(rate: int, rt60: float, seed: int):
    """The hall's response (stereo, unit energy), built once per process."""
    import numpy as np
    key = (rate, rt60, seed)
    if key in _IRS:
        return _IRS[key]
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
    _IRS[key] = ir
    return ir


def hall(dry, rate: int = RATE, rt60: float = 2.3, wet: float = 0.28, seed: int = 7,
         loop_at: Optional[int] = None, loop_from: int = 0):
    """A concert hall: the dry orchestra (its hall send, when play() made it: see
    ROOM) convolved with a synthetic hall response
    (early reflections, then a diffuse tail that darkens as it decays); the tail
    is left to ring after the last chord, or, for a loop (``loop_at``: its length
    in samples), rings on over its start - or over ``loop_from``, where a loop with an
    entry loops back to - so the seam can't be heard."""
    import numpy as np
    ir = _hall_ir(rate, rt60, seed)
    tail = len(ir)
    send = getattr(dry, "send", None)
    send = dry if send is None else send
    dry = np.asarray(dry)
    out = np.zeros((len(dry) + tail, 2))
    # Block by block (overlap-add): FFTs a few times the response's length, not one the
    # length of the whole piece (a 3-minute loop: 4.2 s -> 1.3 s, the same sound).
    size = _fast_len(4 * tail)
    hop = size - tail + 1
    for c in range(2):
        h = np.fft.rfft(ir[:, c], size)
        for at in range(0, len(dry), hop):
            seg = send[at:at + hop, c]
            y = np.fft.irfft(np.fft.rfft(seg, size) * h, size)[:len(seg) + tail - 1]
            out[at:at + len(y), c] += y
    mix = out * wet
    mix[:len(dry)] += dry * (1 - wet * 0.5)
    if loop_at:                                            # a loop: what rings past its end
        n, m = loop_at, max(0, min(int(loop_from), loop_at - 1))   # sounds over where it loops to
        for at in range(n, len(mix), n - m):
            seg = mix[at:at + n - m]
            mix[m:m + len(seg)] += seg
        return mix[:n].astype("float32")
    end = len(dry) + int(rt60 * rate)                      # ring out for one decay, then stop
    return mix[:end].astype("float32")


# --- mastering: by loudness, not by the loudest sample -----------------------------------
# A piece used to be turned up until its loudest sample sat 1.5 dB over the ceiling, so its
# level was set by its peakiest moment: a dense, sustained passage and a peaky one ended up
# far apart, and a later boss stage (busier, its climax no peakier) could not be made louder
# than the one before by its step (the Ashen Saint's stage 2, 2 dB "hotter": its full
# passages 1.5 LU over stage 1's, and only as far as the composer pushed it). Now a piece is brought to a loudness (ITU-R BS.1770 K-weighted, in LUFS)
# and a true-peak look-ahead limiter takes the few peaks that would pass the ceiling.
#
# What is measured: the loudness of a piece's FULL passages - the power mean of its loudest
# fifth of 3-second (short-term) windows - not its integrated loudness. A loop is heard at
# full tilt in its big sections and is compared there (stage 1's loudest against stage 2's),
# and a loop with a long hushed passage would, by its integrated loudness, be raised until
# its climax hit the limiter ("a climax without the climax"); measured on its full passages
# its climax sits at the same level as any other piece's and its quiet parts keep the
# distance below it they were written with. (A fifth, not the single loudest window: one
# drum roll does not set the level.) A loop is measured as it plays, its windows running on
# over its loop point.
MASTER_LUFS = -8.7          # a piece's full passages (the Saint's theme as it was: -8.3; integrated ~-13)
LOUD_SHARE = 0.2            # ... its loudest fifth of 3 s windows
SHORT_TERM_S = 3.0
TRUE_PEAK_DB = -1.5         # the ceiling, true peak (4x oversampled): the OGG never clips
                            # (Vorbis adds up to ~0.7 dB to a dense, limited peak: measured)
LOOKAHEAD_S = 0.005         # the limiter sees a peak 5 ms ahead and is down by the time it comes
RELEASE_S = 0.15            # ... and lets go over ~150 ms
LIMIT_DB = 6.0              # the most the limiter may take off any peak; a piece that would
                            # need more is turned down as a whole (a transient, not the music)
STING_HOT_DB = 1.5          # a short one-shot (a hit, a break, a victory tag) over the loops: hotter
STING_LIMIT_DB = 4.0        # (but its hit keeps its punch: a sting that would need more is quieter)


def _k_filters(rate: int):
    """The two BS.1770 K-weighting biquads (a high shelf, then a high pass) for ``rate``."""
    f0, gain, q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    k = math.tan(math.pi * f0 / rate)
    vh, vb = 10 ** (gain / 20), 10 ** (gain / 20) ** 0.4996667741545416
    a0 = 1 + k / q + k * k
    shelf = ([(vh + vb * k / q + k * k) / a0, 2 * (k * k - vh) / a0, (vh - vb * k / q + k * k) / a0],
             [1.0, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0])
    f0, q = 38.13547087602444, 0.5003270373238773
    k = math.tan(math.pi * f0 / rate)
    a0 = 1 + k / q + k * k
    high = ([1.0, -2.0, 1.0], [1.0, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0])
    return shelf, high


def _k_weight(y, rate: int):
    """``y`` (samples, channels) K-weighted (by FFT: the biquads' own response)."""
    import numpy as np
    n = len(y)
    size = _fast_len(n + rate // 2)                       # (room for the filters' ring)
    z = np.exp(-2j * np.pi * np.arange(size // 2 + 1) / size)
    h = np.ones(len(z), dtype=complex)
    for b, a in _k_filters(rate):
        h *= (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)
    return np.stack([np.fft.irfft(np.fft.rfft(y[:, c], size) * h, size)[:n] for c in range(y.shape[1])], 1)


def _tile(body, count: int, from_end: bool = False):
    """``count`` samples of a loop's body played over and over (its last ones: ``from_end``)."""
    import numpy as np
    if count <= 0:
        return body[:0]
    reps = -(-count // len(body))
    t = np.concatenate([body] * reps) if reps > 1 else body
    return t[-count:] if from_end else t[:count]


def _k_power(x, rate: int, loop: bool, m: int):
    """Per sample, the K-weighted power (summed over the channels) of ``x`` as it plays: a
    loop runs on SHORT_TERM_S past its end, into where it loops back to (``m``)."""
    import numpy as np
    x = np.asarray(x, dtype="float64")
    if x.ndim == 1:
        x = x[:, None]
    pre = rate // 2                                        # (what came before: the filters settle)
    if loop:
        head = _tile(x, pre, True) if m == 0 else np.zeros((pre, x.shape[1]))
        y = np.concatenate([head, x, _tile(x[m:], int(SHORT_TERM_S * rate))])
    else:
        y = np.concatenate([np.zeros((pre, x.shape[1])), x])
    return (_k_weight(y, rate)[pre:] ** 2).sum(axis=1)


def _measure(p, n: int, rate: int, loop: bool) -> Dict[str, float]:
    """loudness() from _k_power()'s ``p`` (a piece ``n`` samples long)."""
    import numpy as np
    c = np.concatenate([[0.0], np.cumsum(p)])
    lufs = lambda e: -0.691 + 10 * math.log10(max(float(e), 1e-20))
    silent = 10 ** ((-70 + 0.691) / 10)                    # the absolute gate: -70 LUFS

    def windows(size):
        size = size if loop else min(size, n)
        s = np.arange(0, (n - 1 if loop else n - size) + 1, max(1, rate // 10))
        e = (c[s + size] - c[s]) / size
        return e[e > silent]

    block = windows(int(0.4 * rate))                       # integrated: 400 ms blocks, gated
    if not len(block):
        return {"integrated": float("-inf"), "loud": float("-inf"), "short_max": float("-inf")}
    block = block[block > block.mean() * 0.1]              # (the relative gate: -10 LU)
    short = np.sort(windows(int(SHORT_TERM_S * rate)))[::-1]
    if not len(short):
        short = np.array([block.mean()])
    top = short[:max(1, int(round(len(short) * LOUD_SHARE)))]
    return {"integrated": lufs(block.mean()), "loud": lufs(top.mean()), "short_max": lufs(short[0])}


def loudness(x, rate: int = RATE, loop: bool = False, loop_from: int = 0) -> Dict[str, float]:
    """How loud a stereo piece is, BS.1770 (K-weighted, LUFS): "integrated" (gated, the whole
    piece), "loud" (its full passages: the loudest LOUD_SHARE of its 3 s windows - what
    master() sets), "short_max" (its loudest 3 s). A loop is measured as it plays: its
    windows run on over its end into where it loops back to (``loop_from``)."""
    n = len(x)
    m = max(0, min(int(loop_from or 0), n - 1)) if loop else 0
    return _measure(_k_power(x, rate, loop, m), n, rate, loop)


def true_peaks(y, over: int = 4, block: int = 1 << 15, margin: int = 256):
    """Per sample, the loudest point (any channel) between it and the next, 4x oversampled:
    the peaks a DAC or an encoder sees between the samples."""
    import numpy as np
    y = np.asarray(y, dtype="float64")
    if y.ndim == 1:
        y = y[:, None]
    n, ch = y.shape
    out = np.empty(n)
    pad = np.concatenate([np.zeros((margin, ch)), y, np.zeros((margin, ch))])
    ramp = 0.5 - 0.5 * np.cos(np.pi * np.arange(margin) / margin)    # (no wrap-around ringing)
    for a in range(0, n, block):
        k = min(block, n - a)
        taper = np.concatenate([ramp, np.ones(k), ramp[::-1]])
        seg = pad[a:a + k + 2 * margin] * taper[:, None]
        size = len(seg)
        spec = np.fft.rfft(seg, axis=0)
        if size % 2 == 0:
            spec[-1] *= 0.5
        up = np.zeros((size * over // 2 + 1, ch), dtype=complex)
        up[:len(spec)] = spec
        u = np.fft.irfft(up, size * over, axis=0) * over
        out[a:a + k] = np.abs(u[margin * over:(margin + k) * over]).reshape(k, over * ch).max(axis=1)
    return np.maximum(out, np.abs(y).max(axis=1))


def loop_peak(x, loop: bool = False, loop_from: int = 0) -> float:
    """The true peak of a piece as it plays: a loop's end runs on into its loop point."""
    import numpy as np
    if not loop:
        return float(true_peaks(x).max())
    k, body = 1024, x[int(loop_from or 0):]
    return float(true_peaks(np.concatenate([_tile(body, k, True), x, _tile(body, k)])).max())


def _limit_gain(tp, rate: int, ceiling: float, g0: float = 1.0):
    """A look-ahead limiter's gain, from a signal's true_peaks() ``tp`` -> (gain per sample,
    the gain each sample may be at most). The gain is down, along a straight ramp, by the time
    a peak arrives, so no (true) peak passes ``ceiling``; it lets go smoothly (RELEASE_S);
    ``g0``: where it starts."""
    import numpy as np
    tp = np.maximum(tp, np.r_[0.0, tp[:-1]])               # (a sample's gain shapes both sides of it)
    need = np.minimum(1.0, ceiling / np.maximum(tp, 1e-12))
    n = len(need)
    blk = max(1, rate // 1378)                             # ~0.7 ms blocks (32 at 44.1 kHz)
    nb = -(-n // blk)
    r = np.ones(nb * blk)
    r[:n] = need
    r = r.reshape(nb, blk).min(axis=1)
    r = np.minimum(r, np.minimum(np.r_[r[1:], 1.0], np.r_[1.0, r[:-1]]))   # (safe to interpolate)
    look = max(1, int(round(LOOKAHEAD_S * rate / blk)))
    held = r.copy()
    for i in range(1, look + 1):                           # the least gain needed in the next 5 ms...
        held[:-i] = np.minimum(held[:-i], r[i:])
    c = np.concatenate([[0.0], np.cumsum(np.r_[np.ones(look), held])])
    ramp = (c[look + 1:] - c[:-look - 1]) / (look + 1)     # ...reached along a ramp, never late
    rel = 1 - math.exp(-blk / (RELEASE_S * rate))
    g = ramp.tolist()
    prev = g0
    for i, s in enumerate(g):
        prev = s if s <= prev else prev + (s - prev) * rel
        g[i] = prev
    centres = np.arange(nb) * blk + (blk - 1) / 2
    gain = np.interp(np.arange(n), centres, np.asarray(g))
    return np.minimum(gain, need), need


def master(x, rate: int = RATE, loop: bool = False, hot_db: float = 0.0, limit_db: float = LIMIT_DB,
           loop_from: int = 0, report: Optional[Dict[str, float]] = None):
    """Loudness like the rest of the table's music: the piece's full passages brought to
    MASTER_LUFS (``hot_db`` above it: a sting, a later boss stage), its peaks taken by a
    true-peak look-ahead limiter (never more than ``limit_db``: past that the piece is
    turned down), a soft fade at the end of a piece that ends. A loop (``loop``, looping
    back to ``loop_from``) is measured and limited as it plays, over and over: no jump at
    its seam. ``report`` (a dict) is filled in: what was measured and done."""
    import numpy as np
    x = np.asarray(x, dtype="float32")
    n = len(x)
    m = max(0, min(int(loop_from or 0), n - 1)) if loop else 0
    power = _k_power(x, rate, loop, m)
    now = _measure(power, n, rate, loop)
    if now["loud"] == float("-inf"):
        return x.copy()
    ceiling = 10 ** (TRUE_PEAK_DB / 20)
    # The streams the limiter reads, as they play: a loop's body with its own end before it
    # (long enough for the release to forget where it started) and its start after it, so
    # its gain runs on over the seam; an entry with the body after it; a piece with silence.
    pad, settle = int(0.05 * rate), int(3 * rate)
    if loop:
        body = x[m:]
        streams = [np.concatenate([_tile(body, settle, True), body, _tile(body, pad)])]
        if m:
            streams.append(np.concatenate([x[:m], _tile(body, pad)]))
    else:
        streams = [np.concatenate([x, np.zeros((pad, x.shape[1]), dtype=x.dtype)])]
    peaks = [true_peaks(z) for z in streams]
    # The most gain the limiter allows: past it, it would take more than limit_db off a peak.
    most = limit_db - 20 * math.log10(max(max(float(p.max()) for p in peaks), 1e-12) / ceiling)
    target = MASTER_LUFS + hot_db
    most = min(most, music_compose.MAX_GAIN_DB + hot_db)
    gain_db = min(target - now["loud"], most)

    def limited(gain_db):
        gain = 10 ** (gain_db / 20)
        if not loop:
            return _limit_gain(peaks[0] * gain, rate, ceiling)[0][:n]
        g = _limit_gain(peaks[0] * gain, rate, ceiling)[0][settle:settle + len(body)]
        if m:                                              # the entry, heard once, into the body
            ge, need = (a[:m] for a in _limit_gain(peaks[1] * gain, rate, ceiling))
            j = min(m, pad)                                # its last 50 ms meet the body's gain
            w = np.linspace(0, 1, j + 1)[1:]
            ge[-j:] = np.minimum(need[-j:], ge[-j:] + (g[0] - ge[-j:]) * w)
            g = np.concatenate([ge, g])
        return g

    # What the limiter takes off the full passages is made up (a little more gain, limited
    # again) until they reach the target. (K-weighting a slowly changing gain: the gain
    # times the K-weighted signal.)
    tried = []
    for tries in range(5):
        g = limited(gain_db)
        g2 = g.astype("float64") ** 2
        if loop:
            g2 = np.concatenate([g2, _tile(g2[m:], len(power) - n)])
        got = _measure(power * g2 * 10 ** (gain_db / 10), n, rate, loop)["loud"]
        short = target - got
        if short < 0.05 or gain_db >= most - 1e-6 or tries == 4:
            break
        tried.append((gain_db, got))
        slope = 1.0                                        # (dB out per dB in: under 1 where it limits)
        if len(tried) > 1 and tried[-1][0] - tried[-2][0] > 1e-3:
            slope = max(0.25, min(1.0, (tried[-1][1] - tried[-2][1]) / (tried[-1][0] - tried[-2][0])))
        gain_db = min(gain_db + short / slope, most)
    gain = 10 ** (gain_db / 20)
    out = x * (g * gain).astype("float32")[:, None]
    if not loop:                                            # (a loop has no ends)
        k = min(n, int(rate * 1.2))
        out[-k:] *= np.linspace(1, 0, k, dtype="float32")[:, None] ** 2
    if report is not None:
        report.update({"before_lufs": now["loud"], "gain_db": gain_db, "target_lufs": target,
                       "max_reduction_db": -20 * math.log10(max(float(g.min()), 1e-12)),
                       "true_peak_db": 20 * math.log10(max(float(loop_peak(out, loop, m)), 1e-12))})
        report.update({k + "_lufs": v for k, v in loudness(out, rate, loop, m).items()})
    return out


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
        from music import slug
        out = out / f"anthem-{slug(a.name)}-orchestra-{STAGES[max(0, min(3, a.stage))]}.ogg"
    path = music_compose.write(samples, rate, out)
    print(f"{path} ({len(samples) / rate:.1f}s)")


if __name__ == "__main__":
    main()
