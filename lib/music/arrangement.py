#!/usr/bin/env python3
"""Arrangements: a piece written as notes for the sampled orchestra (lib/orchestra.py).

A character's tune comes from the leitmotif generator (lib/music_compose.py), so it
is always exactly theirs; an arrangement says what the orchestra does with it: who
plays the tune when, the chords, the accompaniment, countermelodies, percussion,
dynamics, tempo. The GM (Claude) writes one per piece, like a composer's score.

See the tune first (its notes, with their times):
    python3 lib/arrangement.py tune "Kestrel" --class Barbarian [--minor] [--stage 3]
Play an arrangement:
    python3 lib/arrangement.py play kestrel.json --out kestrel.ogg

TIME is in the tune's units: beats (4/4, 3/4) or eighth notes (6/8); 0 is where
the tune starts; an intro is at negative times. PITCHES are names ("C#4", "Eb3",
"E#4"; C4 = 60) or MIDI numbers. VEL ("vel") is an offset from the dynamics curve,
except in "hits" and "rolls", where it is the velocity itself (1-127).

{
  "tune": {"seed": "Kestrel", "mode": "major", "cls": "Barbarian", "stage": 3, "dark": 0},
                         # "key": "C4" / "meter": "4/4" set the key the chords are read in
                         # and the bars (a sketch with no tune - "statements": [] - sets both)
                         # mode "minor": the villain's version of the seed's tune; "gen": 2
                         # the generator's second version; "written": a hand-written tune
                         # (music_compose.written_tune: its sections in scale degrees)
  "tempo": 60,           # beats a minute (6/8: dotted quarters)
  "start": -12,          # where the piece starts (an intro before the tune): default 0
  "length": 96,          # where it ends (default: the end of the last statement)
  "loop": false,         # true: a seamless loop of [start, length) (battle music)
  "role": "theme",       # what it's for: theme, villain, battle, lament, ... ("battle": the
                         # critic checks it keeps several lines moving)
  "ritard": {"from": 84, "amount": 0.4},     # slowing to the end (40% slower at the last note)
  "dynamics": [[-12, 60], [0, 80], [36, 96], [60, 124]],   # velocity, linear between points
  "statements": [{"at": 0}],                 # where the tune is played (default: once, at 0; [] for none);
                         # optional "from"/"to" (a slice of the tune, in its own units) and
                         # "shift" (semitones): {"at": 96, "from": 0, "to": 36, "shift": -12}
  "keys": [{"from": 96, "to": 192, "shift": 2}],  # a key change: the chords there are read in
                         # the new key (pair it with that statement's "shift": 2), so "I" is
                         # still home - the new home
  "melody": [            # who plays the tune, when, and how many semitones from as written
    {"from": 0, "to": 18, "parts": {"horns": 0}, "vel": 8},
    {"from": 18, "to": 36, "parts": {"violins": 12}}
  ],
  "progression": {"at": 0, "chords": "i bVI iv v | i bVII bVI*0.5 iv*0.5 i", "repeat": 2},
                         # chords a bar each (or "every": units), "*2" twice as long - added
                         # to "chords"; a list of them for several passages
  "chords": [            # roman numerals in the tune's key, [from, to, chord]
    [0, 6, "I"], [6, 9, "IVadd9"], [9, 12, "I/E#"], [12, 18, "bVII"], [24, 27, "vi7"]
  ],                     # I ii iii IV V vi vii, b/# before, ° ø or + after (vii°7 the diminished
                         # seventh, iiø7 the half-diminished); then 7 maj7 add9
                         # sus4 sus2 6 5 (a power chord); a bass note after a slash: "I/E#"
  "harmony": [           # parts playing the chords
    {"part": "strings", "from": 0, "to": 96, "play": "chord", "range": ["G3", "A#4"], "vel": -20},
    {"part": "cellos", "from": 0, "to": 60, "play": "bass", "range": ["C2", "B2"],
     "pattern": "xoo xoo", "step": 1, "legato": 0.55}
  ],                     # play: chord | bass | root | third | fifth | root5 | octaves
                         # pattern (repeating from "from", one character a "step" of units):
                         # x accent, o a note, - holds the previous one on, space or . a rest
  "lines": [             # anything written out: countermelodies, ostinati, fanfares
    {"part": "horns", "vel": 0, "notes": [[18, "E#4", 3], [21, "G#4", 3], [24, "A#4", 6, 10]]}
  ],                     # [at, pitch, units, (vel offset), ({"slide": semitones over the
                         # note, "wobble": an uneven vibrato's depth in semitones})] - for
                         # one voice at a time (a solo line): a bend moves the whole part
  "motifs": {"call": [[0, "D4", 1], [1, "A4", 1], [2, "D5", 2], [4, "A4", 2]]},
                         # a theme written ONCE (times from 0), then placed in "lines" as
                         # often as wanted, each time transformed - instead of writing
                         # its notes again:
                         # {"part": "trombones", "motif": "call", "at": 16, "shift": 3,
                         #  "stretch": 2, "alter": {"2": -1}, "repeat": 2, "every": 8}
                         # shift (semitones) or octave; stretch 2 = twice as slow (0.5:
                         # twice as fast); invert (mirrored round its first note); retro
                         # (backwards); take [i, j] (a fragment: notes i..j-1); alter
                         # {note index: semitones, or a pitch} - the corrupted interval;
                         # repeat / every; "notes" may be added to the same line too
                         # "double": [{"part": "chorus", "octave": -1, "vel": -4}] on any
                         # line or placement: the same notes on other parts, written once
  "patterns": [          # percussion (or any part) on one note, in a rhythm
    {"part": "kit", "note": "snare", "from": 36, "to": 60, "pattern": "xoooox", "vel": -30},
    {"part": "timpani", "note": "root", "from": 0, "to": 84, "pattern": "x     ", "vel": -6}
  ],                     # note: a pitch, "root"/"fifth" (of the chord, timpani range), or
                         # snare, bd, crash, cymbal, china, splash, ride, triangle, gong
  "rolls": [{"part": "timpani", "note": "G#2", "from": 57, "to": 60, "vel": [70, 120]}],
  "unhinge": [{"parts": ["strings", "tremolo", "violins"], "from": 36, "to": 40, "drift": 0.6,
               "wobble": 0.3}],    # those parts waver and drift off pitch, each its own way,
                         # and come back true by the end
  "hits": [{"part": "kit", "note": "crash", "at": 60, "len": 6, "vel": 124}],
  "mix": {"choir": 3},   # dB up or down for a part in this piece (all parts are already
                         # evened out: the same velocity is the same loudness)
  "lead": 4              # the tune's notes are mixed this many dB over the rest (default 4);
}                        # a "melody" entry's "gain" adds to it, a "lines" entry's sets its own

Choir (and organ, strings) voices take over a second to bloom: give them notes of a
beat or longer, held chords, not quick rhythms; let brass and drums carry those.

What the tools can make - each sound serves many characters and moods, none is a default:
- a pulse that never stops: a dance (a waltz "xoo", a habanera), a march, an ostinato,
  a ticking clock (pizzicato, high short strokes), a heartbeat (timpani) - "harmony"
  with a "pattern", or "patterns";
- a drone or pedal under moving music: "bass" held with "-", tremolo, organ, basses;
- held chords that swell: strings; choir (smooth, soft-edged, a pad that rings on: distant,
  mystic, a background halo); chorus (a real choir, men under women, "ah": present and
  human - the sacred, a ceremony, a requiem, an epic tutti); men_choir (real men's voices, low: monks, a chant in unison or
  open fifths, doom, an ancient power); choir_oo / choir_oh (a soft mixed choir on "oo" or
  "oh": the ethereal, the holy, wonder, a hushed lament); organ; low brass for weight;
- a written voice: a countermelody, a fanfare (trumpets, horns), an answering second
  voice, a lone solo (solo_violin, oboe, english_horn, flute), a run - "lines";
- bells tolling, a music box (celesta, glockenspiel), a birdlike flute figure;
- drums of war or urgency (taiko, toms, snare, timpani), a roll into a moment, a sudden
  loud hit or dissonant chord after quiet ("hits", a loud chord in "lines"), a reverse
  cymbal into a downbeat;
- a new colour for a return: a key change ("keys" and a statement's "shift"), borrowed,
  diminished or unexpected chords, the tune moved to another register or instrument;
- pitch that is not steady: a note that slides (a sigh, a slash, a siren, a lurch), an
  uneven vibrato (a warped music box, a ghostly or frail voice, a heat shimmer), parts
  drifting apart and back (unease, illusion, a dream, sickness, a curse, a mind
  breaking) - "slide"/"wobble" on "lines" notes, "unhinge" for parts. A falling slide on
  brass or low reeds is comic (a raspberry): bend strings and soft voices, not trumpets;
- growth and shape: "dynamics", parts entering in waves, a "ritard", a "loop".

Parts: violins, violins2, solo_violin (one player: exposed, quick), strings (sustained),
tremolo, pizzicato, cellos, basses,
flutes, piccolo, oboe, english_horn, clarinets, bassoons, horns, trumpets,
trombones, tuba, brass, choir, chorus (E2-E6), men_choir (E2-A4), choir_oo, choir_oh (A2-D#6), harp, celesta, glockenspiel, bells, organ,
timpani, taiko, toms, reverse_cymbal, kit (bd, snare, cymbals): as many as wanted.
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # (lib/)
from music import music_compose  # noqa: E402
from music import orchestra  # noqa: E402

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
LETTER = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
KIT = {"bd": 35, "snare": 38, "crash": 49, "cymbal": 49, "china": 52, "splash": 55,
       "ride": 51, "triangle": 81, "gong": 57}
ACCENT = 14


class ArrangementError(ValueError):
    pass


# --- pitches and chords ---
def pitch_class(name: str) -> int:
    m = re.fullmatch(r"([A-Ga-g])([#b]*)", name.strip())
    if not m:
        raise ArrangementError(f"not a note name: {name!r}")
    return (LETTER[m.group(1).upper()] + m.group(2).count("#") - m.group(2).count("b")) % 12


def pitch(p: Any) -> int:
    """'C#4' (C4 = 60) or a MIDI number -> MIDI number."""
    if isinstance(p, (int, float)):
        return int(p)
    m = re.fullmatch(r"([A-Ga-g][#b]*)(-?\d)", str(p).strip())
    if not m:
        raise ArrangementError(f"not a pitch: {p!r} (like 'C#4', or a MIDI number)")
    letter = m.group(1)
    acc = letter[1:].count("#") - letter[1:].count("b")
    return 12 * (int(m.group(2)) + 1) + LETTER[letter[0].upper()] + acc


def name_of(midi: int) -> str:
    return f"{NAMES[midi % 12]}{midi // 12 - 1}"


DEGREES = {"I": 0, "II": 2, "III": 4, "IV": 5, "V": 7, "VI": 9, "VII": 11}
SUFFIXES = ("maj7", "add9", "sus4", "sus2", "7", "6", "5", "9")


def chord(symbol: str, key: int) -> Dict[str, Any]:
    """'bVII', 'vi7', 'IVadd9', 'I/E#', 'v°' in the key (a MIDI tonic) ->
    {root, bass, pcs (root first), third, fifth}: pitch classes."""
    s = symbol.strip()
    body, _, slash = s.partition("/")
    m = re.match(r"([b#]?)(VII|VI|V|IV|III|II|I|vii|vi|v|iv|iii|ii|i)([°o+ø]|dim|aug)?", body)
    if not m:
        raise ArrangementError(f"not a chord: {symbol!r} (roman numerals: I, bVII, vi7, IVadd9, I/E#)")
    acc, numeral, quality = m.group(1), m.group(2), m.group(3) or ""
    rest = body[m.end():]
    root = (key + DEGREES[numeral.upper()] + (1 if acc == "#" else -1 if acc == "b" else 0)) % 12
    minor = numeral.islower()
    third, fifth = (3 if minor else 4), 7
    if quality in ("°", "o", "dim", "ø"):
        third, fifth = 3, 6
    elif quality in ("+", "aug"):
        third, fifth = 4, 8
    extra: List[int] = []
    while rest:
        suf = next((x for x in SUFFIXES if rest.startswith(x)), None)
        if suf is None:
            raise ArrangementError(f"not a chord: {symbol!r} (can't read {rest!r})")
        rest = rest[len(suf):]
        if suf == "maj7":
            extra.append(11)
        elif suf == "7":                 # °7 is the diminished seventh; ø7 (and 7) the minor one
            extra.append(9 if quality in ("°", "o", "dim") else 10)
        elif suf == "9":
            extra += [10, 2]
        elif suf == "add9":
            extra.append(2)
        elif suf == "6":
            extra.append(9)
        elif suf == "sus4":
            third = 5
        elif suf == "sus2":
            third = 2
        elif suf == "5":
            third = None
    if quality == "ø" and 10 not in extra:          # half-diminished: "iiø" = "iiø7"
        extra.append(10)
    tones = [0] + ([third] if third is not None else []) + [fifth] + extra
    pcs = []
    for t in tones:
        pc = (root + t) % 12
        if pc not in pcs:
            pcs.append(pc)
    return {"root": root, "bass": pitch_class(slash) if slash else root, "pcs": pcs,
            "third": (root + third) % 12 if third is not None else root, "fifth": (root + fifth) % 12}


def place(pc: int, lo: int, hi: int) -> int:
    """The lowest pitch of this pitch class in [lo, hi] (or just under lo + 12)."""
    n = lo + (pc - lo) % 12
    return n if n <= hi else n - 12


def voicing(pcs: List[int], prev: Optional[List[int]], lo: int, hi: int) -> List[int]:
    """Every chord tone, in close position within [lo, hi] (the bottom doubled an
    octave up when there's room for a fourth voice), moving as little as it can."""
    cands = []
    for bottom in pcs:
        for start in (place(bottom, lo, lo + 11), place(bottom, lo, lo + 11) + 12):
            v = [start]
            for _ in range(len(pcs) - 1):
                nxt = v[-1] + 1
                while nxt % 12 not in pcs or nxt % 12 in [x % 12 for x in v]:
                    nxt += 1
                v.append(nxt)
            if len(v) < 4 and v[0] + 12 <= hi and v[0] + 12 > v[-1]:
                v.append(v[0] + 12)
            if v[-1] <= hi and v[0] >= lo:
                cands.append(v)
    if not cands:                                     # a narrow range: as many as fit
        v = sorted({place(pc, lo, hi) for pc in pcs if lo <= place(pc, lo, hi) <= hi})
        return v or [place(pcs[0], lo, lo + 11)]
    if prev is None:
        return min(cands, key=lambda v: (v[0] % 12 != pcs[0], sum(v) / len(v) - (lo + hi) / 2))
    return min(cands, key=lambda v: sum(min(abs(a - b) for b in prev) for a in v))


# --- the piece ---
def _span(item: Dict[str, Any], start: float, end: float) -> Tuple[float, float]:
    return float(item.get("from", start)), float(item.get("to", end))


def _pattern_hits(pattern: str, a: float, b: float, step: float):
    """(time, length in steps, accented) for each note of a pattern repeating over [a, b)."""
    if not pattern:
        raise ArrangementError("an empty pattern")
    out, t, i = [], a, 0
    while t < b - 1e-9:
        c = pattern[i % len(pattern)]
        if c in "xo":
            hold = 1
            j = i + 1
            while pattern[j % len(pattern)] == "-" and a + j * step < b - 1e-9:
                hold, j = hold + 1, j + 1
            out.append((t, hold, c == "x"))
        elif c not in "-. ":
            raise ArrangementError(f"a pattern is x, o, -, or space: {pattern!r}")
        i += 1
        t = a + i * step
    return out


def build(spec: Dict[str, Any]) -> Tuple["orchestra.Score", float, Optional[float]]:
    """An arrangement -> (score, seconds, loop length in seconds or None)."""
    ctx = _build(spec)
    return ctx["score"], ctx["seconds"], ctx["loop"]


def expand_motifs(spec: Dict[str, Any]) -> Dict[str, Any]:
    """The spec with every "lines" entry that places a motif written out as plain notes,
    and every "double" (the line played by other parts too) written out as lines.
    A motif is written once ("motifs": {name: notes from time 0}) and placed as often as
    wanted, each time transformed: shift (semitones) / octave, stretch (time), invert
    (mirrored round its first note), retro (backwards), take [i, j] (a fragment: notes
    i..j-1), alter {index: semitones or a pitch} (the corrupted interval), repeat / every."""
    motifs = spec.get("motifs") or {}
    if not any(isinstance(l, dict) and ("motif" in l or "double" in l) for l in spec.get("lines") or []):
        return spec
    lines = []
    for line in spec.get("lines") or []:
        if "motif" not in line:
            lines.append(line)
            continue
        name = line["motif"]
        if name not in motifs:
            raise ArrangementError(f"no such motif: {name!r} (motifs: {', '.join(motifs) or 'none'})")
        src = [list(n) for n in motifs[name]]
        if not src:
            raise ArrangementError(f"motif {name!r} has no notes")
        idx = list(range(len(src)))
        if line.get("take"):
            i, j = (list(line["take"]) + [len(src)])[:2]
            idx = idx[int(i):int(j)]
            if not idx:
                raise ArrangementError(f"motif {name!r}: take {line['take']} leaves no notes")
        p0 = pitch(src[idx[0]][1])
        t0 = min(float(src[i][0]) for i in idx)
        end = max(float(src[i][0]) + float(src[i][2]) for i in idx)
        stretch = float(line.get("stretch", 1))
        move = int(line.get("shift", 0)) + 12 * int(line.get("octave", 0))
        alter = {int(k): v for k, v in (line.get("alter") or {}).items()}
        bad = [k for k in alter if k not in idx]
        if bad:
            raise ArrangementError(f"motif {name!r}: alter names note(s) {bad} it doesn't play")
        placed = []
        for i in idx:
            n = src[i]
            at, d = float(n[0]) - t0, float(n[2])
            if line.get("retro"):
                at = (end - t0) - (at + d)
            p = pitch(n[1])
            if line.get("invert"):
                p = 2 * p0 - p
            p += move
            if i in alter:
                p = pitch(alter[i]) if isinstance(alter[i], str) else p + int(alter[i])
            placed.append([at * stretch, p, d * stretch] + list(n[3:]))
        placed.sort(key=lambda n: n[0])
        reps, every = int(line.get("repeat", 1)), float(line.get("every", (end - t0) * stretch))
        notes = [[float(line.get("at", 0)) + k * every + n[0]] + n[1:] for k in range(reps) for n in placed]
        out = {k: v for k, v in line.items() if k not in
               ("motif", "at", "shift", "octave", "stretch", "invert", "retro", "take", "alter", "repeat", "every")}
        out["notes"] = notes + list(line.get("notes") or [])
        lines.append(out)
    # "double": the same line played by other parts too - written once
    doubled = []
    for line in lines:
        twins = line.get("double") or []
        base = {k: v for k, v in line.items() if k != "double"}
        doubled.append(base)
        for d in twins if isinstance(twins, list) else [twins]:
            if not isinstance(d, dict) or not d.get("part"):
                raise ArrangementError(f'"double" on {line.get("part")}: give each a "part" (and "octave"/"shift"/"vel")')
            move = int(d.get("shift", 0)) + 12 * int(d.get("octave", 0))
            doubled.append({**{k: v for k, v in base.items() if k not in ("part", "vel")},
                            "part": d["part"], "vel": float(base.get("vel", 0)) + float(d.get("vel", 0)),
                            "notes": [[n[0], pitch(n[1]) + move] + list(n[2:]) for n in base.get("notes") or []]})
    return {**spec, "lines": doubled}


def progression_chords(spec: Dict[str, Any], bar: float) -> List[list]:
    """"progression": {"at": 0, "chords": "i bVI iv v | i bVII bVI iv i", "every": <units,
    default a bar>, "repeat": 1} (or a list of them) -> [[from, to, chord], ...]. A chord
    "iv*2" lasts twice as long, "v*0.5" half; "|" is only for the eye."""
    prs = spec.get("progression") or []
    out = []
    for pr in prs if isinstance(prs, list) else [prs]:
        every, t = float(pr.get("every", bar)), float(pr.get("at", 0))
        tokens = str(pr.get("chords", "")).replace("|", " ").split()
        if not tokens:
            raise ArrangementError('"progression" needs "chords": "i bVI iv v ..."')
        for _ in range(int(pr.get("repeat", 1))):
            for tok in tokens:
                sym, _, mult = tok.partition("*")
                d = every * float(mult or 1)
                out.append([t, t + d, sym])
                t += d
    return out


def _build(spec: Dict[str, Any]) -> Dict[str, Any]:
    """build(), with what the score critic needs too: the tune, the chords, the clock."""
    spec = expand_motifs(spec)
    t = dict(spec.get("tune") or {})
    if not t.get("seed"):
        raise ArrangementError('"tune": {"seed": ...} is needed (the character\'s name)')
    tune = music_compose.leitmotif(t["seed"], t.get("mode", "major"), t.get("cls", ""),
                                   stage=int(t.get("stage", 1)), dark=int(t.get("dark", 0)),
                                   gen=int(t.get("gen", 1)), written=t.get("written"))
    if t.get("key"):                    # a set key (a sketch with no tune: chords read in it)
        tune = {**tune, "key": pitch(t["key"])}
    if t.get("meter") in ("4/4", "3/4", "2/4", "6/8"):    # ...and a set meter (bars, beats)
        tune = {**tune, "meter": t["meter"], "bar": music_compose.METERS[t["meter"]]}
    key = tune["key"]
    notes, u = [], 0.0
    for st, b in tune["notes"]:
        notes.append((u, b, st))
        u += b
    tune_len = u
    # (an explicit empty list: no tune at all - a sketch whose melody is written in "lines")
    statements = spec["statements"] if isinstance(spec.get("statements"), list) else [{"at": 0}]
    played = []                                                 # (time, units, MIDI as written)
    for s in statements:
        at, lo, hi = float(s.get("at", 0)), float(s.get("from", 0)), float(s.get("to", tune_len))
        for u0, b, st in notes:
            if lo - 1e-9 <= u0 < hi - 1e-9:
                played.append((at + u0 - lo, min(b, hi - u0), key + st + int(s.get("shift", 0))))
    start = float(spec.get("start", 0))
    if not played:                     # a sketch with no tune ends with its last written note
        ends = [float(x[1]) for x in list(spec.get("chords", [])) + progression_chords(spec, tune["bar"])]
        ends += [float(x.get("to", 0)) for k in ("harmony", "patterns", "rolls") for x in spec.get(k, [])]
        ends += [float(n[0]) + float(n[2]) for x in spec.get("lines", []) for n in x.get("notes", [])]
        ends += [float(x.get("at", 0)) + float(x.get("len", 0)) for x in spec.get("hits", [])]
        tune_len = max(ends, default=tune_len)
    length = float(spec.get("length") or max((p[0] + p[1] for p in played), default=tune_len))
    loop = bool(spec.get("loop"))
    tempo = float(spec.get("tempo") or 66)
    beat = 3 if tune["meter"] == "6/8" else 1
    unit = 60.0 / tempo / beat
    rit = spec.get("ritard") if not loop else None
    rit_from = float(rit["from"]) if rit else None
    rit_amount = float(rit.get("amount", 0.3)) if rit else 0.0

    def T(x: float) -> float:
        y = x - start
        if rit_from is not None and x > rit_from:
            d = min(x, length) - rit_from
            y += rit_amount * d * d / (2 * max(length - rit_from, 1e-6)) + rit_amount * max(0, x - length)
        return y * unit

    dyn_pts = sorted((float(a), float(v)) for a, v in (spec.get("dynamics") or [[start, 90]]))

    def dyn(x: float) -> float:
        if x <= dyn_pts[0][0]:
            return dyn_pts[0][1]
        for (a, va), (b, vb) in zip(dyn_pts, dyn_pts[1:]):
            if x <= b:
                return va + (vb - va) * (x - a) / max(b - a, 1e-9)
        return dyn_pts[-1][1]

    sc = orchestra.Score()
    used = set()

    def part_ok(part: str) -> str:
        if part not in orchestra.PARTS:
            raise ArrangementError(f"no such part: {part!r} (one of: {', '.join(orchestra.PARTS)})")
        used.add(part)
        return part

    def note(part: str, k: int, u0: float, dur: float, vel: float, legato: float = 0.97,
             gain: float = 0.0) -> None:
        if u0 >= length - 1e-9 and loop:
            return
        sc.note(part_ok(part), int(k), T(u0), max(0.02, (T(u0 + dur) - T(u0)) * legato), vel, gain)

    # the chords
    prog = []
    keys = [(float(k.get("from", start)), float(k.get("to", 1e9)), int(k.get("shift", 0)))
            for k in spec.get("keys") or []]

    def key_at(x: float) -> int:                       # a key change: chords read in the new key
        return key + next((sh for a, b, sh in keys if a - 1e-9 <= x < b - 1e-9), 0)

    for item in list(spec.get("chords") or []) + progression_chords(spec, tune["bar"]):
        a, b, sym = item
        prog.append((float(a), float(b), {**chord(sym, key_at(float(a))), "symbol": sym}))
    prog.sort(key=lambda c: c[0])

    def chord_at(x: float) -> Optional[Dict[str, Any]]:
        for a, b, c in prog:
            if a - 1e-9 <= x < b - 1e-9:
                return c
        return None

    # the tune (its notes a layer of their own, mixed over the rest: "lead" dB)
    lead = float(spec.get("lead", orchestra.LEAD_DB))
    for m in spec.get("melody") or []:
        a, b = _span(m, start, length)
        for u0, d, k in played:
            if a - 1e-9 <= u0 < b - 1e-9:
                for part, shift in (m.get("parts") or {}).items():
                    note(part, k + int(shift), u0, d, dyn(u0) + float(m.get("vel", 0)), float(m.get("legato", 0.97)),
                         lead + float(m.get("gain", 0)))

    # the harmony
    for h in spec.get("harmony") or []:
        part = part_ok(h["part"])
        a, b = _span(h, start, length)
        lo, hi = (pitch(x) for x in h.get("range", ["G3", "G4"]))
        play = h.get("play", "chord")
        prev = None
        legato = float(h.get("legato", 1.0 if not h.get("pattern") else 0.6))
        step = float(h.get("step", 1))
        for ca, cb, c in prog:
            s0, s1 = max(a, ca), min(b, cb)
            if s1 <= s0 + 1e-9:
                continue
            if play == "chord":
                keys = voicing(c["pcs"], prev, lo, hi)
                prev = keys
            elif play in ("bass", "root", "third", "fifth"):
                keys = [place(c[play], lo, hi)]
            elif play == "root5":
                r = place(c["root"], lo, hi)
                keys = [r, r + 7] if r + 7 <= hi else [r - 5, r] if r - 5 >= lo else [r]
            elif play == "octaves":
                r = place(c["bass"], lo, hi)
                keys = [r, r + 12]
            else:
                raise ArrangementError(f"play is chord, bass, root, third, fifth, root5 or octaves, not {play!r}")
            if h.get("pattern"):
                # the pattern counts from the harmony's own start, so it carries across chords
                for t0, hold, acc in _pattern_hits(h["pattern"], a, b, step):
                    if s0 - 1e-9 <= t0 < s1 - 1e-9:
                        for k in keys:
                            note(part, k, t0, hold * step, dyn(t0) + float(h.get("vel", 0)) + (ACCENT if acc else 0), legato)
            else:
                for k in keys:
                    note(part, k, s0, s1 - s0, dyn(s0) + float(h.get("vel", 0)), legato)

    # lines
    for line in spec.get("lines") or []:
        part = part_ok(line["part"])
        for n in line.get("notes") or []:
            at, p, d = float(n[0]), pitch(n[1]), float(n[2])
            extra = float(n[3]) if len(n) > 3 and not isinstance(n[3], dict) else 0.0
            how = next((x for x in n[3:] if isinstance(x, dict)), {})
            note(part, p, at, d, dyn(at) + float(line.get("vel", 0)) + extra, float(line.get("legato", 0.97)),
                 float(line.get("gain", 0)))
            if how.get("slide") or how.get("wobble"):              # a slide and/or an uneven vibrato
                import random
                rnd = random.Random(f"{part}:{at}:{p}")
                t0, t1 = T(at), T(at + d)
                slide, depth = float(how.get("slide", 0)), float(how.get("wobble", 0))
                rate, phase = rnd.uniform(4.5, 8.0), rnd.uniform(0, 6.28)
                steps = max(2, int((t1 - t0) / 0.01))
                for i in range(steps + 1):
                    f = i / steps
                    wob = depth * math.sin(phase + 6.2832 * rate * f * (t1 - t0) * (1 + 0.3 * math.sin(3.1 * f)))
                    sc.bend(part, t0 + f * (t1 - t0), slide * f ** 1.5 + wob)
                sc.bend(part, t1 + 0.005, 0.0)

    def perc_key(part: str, what: Any, x: float) -> int:
        if isinstance(what, str) and what in KIT:
            return KIT[what]
        if what in ("root", "fifth"):
            c = chord_at(x)
            if c is None:
                raise ArrangementError(f'"{what}" at {x}: there is no chord there')
            return place(c[what], 40, 52)
        return pitch(what)

    for p in spec.get("patterns") or []:
        part = part_ok(p["part"])
        a, b = _span(p, start, length)
        step = float(p.get("step", 1))
        for t0, hold, acc in _pattern_hits(p["pattern"], a, b, step):
            note(part, perc_key(part, p.get("note", "root"), t0), t0, max(hold * step, float(p.get("len", 0))),
                 dyn(t0) + float(p.get("vel", 0)) + (ACCENT if acc else 0), float(p.get("legato", 0.9)))

    # Unhinged stretches: the parts named waver and drift off pitch, each its own way (a
    # section going out of tune with itself), and come back by the end - madness spreading
    # through the strings while the rest of the orchestra stays sane (the host's idea).
    for w in spec.get("unhinge") or []:
        import random
        a, b = float(w["from"]), float(w["to"])
        t0, t1 = T(a), T(b)
        for part in w.get("parts") or []:
            part = part_ok(part)
            rnd = random.Random(f"{w.get('seed', 0)}:{part}:{a}")
            drift = rnd.uniform(-1, 1) * float(w.get("drift", 0.6))       # where it sags or rises to
            depth = float(w.get("wobble", 0.3)) * rnd.uniform(0.6, 1.2)
            rate, phase = rnd.uniform(3.0, 7.5), rnd.uniform(0, 6.28)
            steps = max(2, int((t1 - t0) / 0.02))
            for i in range(steps + 1):
                f = i / steps
                env = math.sin(math.pi * f) ** 0.7                          # in, and back to true
                wob = depth * math.sin(phase + 6.2832 * rate * f * (t1 - t0) * (1 + 0.4 * math.sin(2.3 * f + phase)))
                sc.bend(part, t0 + f * (t1 - t0), env * (drift + wob))
            sc.bend(part, t1 + 0.01, 0.0)

    for r in spec.get("rolls") or []:
        part = part_ok(r["part"])
        a, b = float(r["from"]), float(r["to"])
        v0, v1 = (r.get("vel") or [70, 110])
        t0, t1 = T(a), T(b)
        # One swelling rumble, not a rattle: about 9 strokes a second, each ringing
        # into the next, rising smoothly (the host: 14 a second, alternating strong and
        # weak, was "painfully fast" in a battle and "a bit too fast" in a theme).
        every = float(r.get("every", ROLL_EVERY))
        n = max(2, int((t1 - t0) / every))
        k = perc_key(part, r.get("note", "root"), a)
        for i in range(n):
            f = i / (n - 1)
            sc.note(part, k, t0 + (t1 - t0) * i / n, every * 2.5, v0 + (v1 - v0) * f ** 1.5)

    for h in spec.get("hits") or []:
        part = part_ok(h["part"])
        at = float(h["at"])
        k = perc_key(part, h.get("note", "root"), at)
        sc.note(part, k, T(at), (T(at + float(h.get("len", 3))) - T(at)), float(h.get("vel", 110)))

    seconds = T(length)
    return {"score": sc, "seconds": seconds, "loop": seconds if loop else None, "tune": tune,
            "played": played, "prog": prog, "T": T, "unit": unit, "beat": beat, "start": start,
            "length": length, "dyn_pts": dyn_pts, "chord_at": chord_at}


def render(spec: Dict[str, Any], rate: int = orchestra.RATE, sf2: Path = orchestra.SF2):
    """An arrangement played by the orchestra -> (stereo float32 samples, rate)."""
    score, seconds, loop = build(spec)
    mix = spec.get("mix") or {}
    if loop:
        dry = orchestra.play(score, seconds + 3.0, sf2, rate, mix)  # (what rings past the end)
        wet = orchestra.hall(dry, rate, loop_at=int(round(seconds * rate)))
        return orchestra.master(wet, rate, loop=True), rate
    dry = orchestra.play(score, seconds, sf2, rate, mix)
    return orchestra.master(orchestra.hall(dry, rate), rate), rate


# --- the score critic: what a listener would notice, measured (I can't hear) ---
PERCUSSIVE = {"timpani", "taiko", "toms", "kit", "reverse_cymbal", "bells", "harp", "glockenspiel",
              "celesta", "pizzicato"}                  # (struck: playing a note again is normal)
DRUMS = {"timpani", "taiko", "toms", "kit", "reverse_cymbal"}
ROLL_EVERY = 0.18          # seconds between a roll's strokes (about 5.5 a second: the host's pick)


def _where(ctx: Dict[str, Any], u: float) -> str:
    bar = ctx["tune"]["bar"]
    return "the intro" if u < 0 else f"bar {int(u // bar) + 1}"


def check(spec: Dict[str, Any], listen: bool = True) -> List[Tuple[str, str]]:
    """What's wrong with an arrangement, as [(level, finding)]: "error" (fix it),
    "warn" (very likely heard), "note" (a choice to confirm). ``listen``: also
    render it, to measure what's heard (the tune over the rest, the choir, a loop's
    seam): a few seconds."""
    spec = expand_motifs(spec)
    ctx = _build(spec)
    sc, tune, T, unit = ctx["score"], ctx["tune"], ctx["T"], ctx["unit"]
    bar = tune["bar"]
    out: List[Tuple[str, str]] = []
    add = lambda level, msg: out.append((level, msg))          # noqa: E731
    # A falling bend on brass or low reeds is a raspberry: the host, on a corrupted
    # champion's boss fight whose trumpet stabs fell a fifth and whose trombone call slid
    # down: "it sounds like he farts". And a slide bends the whole part, chords and all.
    blown = {"trumpets", "trombones", "tuba", "horns", "brass", "bassoons"}
    chorded = {h.get("part") for h in spec.get("harmony", [])}
    for line in spec.get("lines", []):
        bent = [n for n in line.get("notes", []) if len(n) > 4 and isinstance(n[-1], dict) and n[-1].get("slide")]
        falls = [n for n in bent if float(n[-1]["slide"]) <= -2]
        if line.get("part") in blown and falls and spec.get("role") != "comic":
            add("warn", f"{line['part']}: {len(falls)} note(s) bend down on brass or low reeds - heard as comic "
                        f"(a raspberry; the host: \"it sounds like he farts\"): keep falling slides for strings or "
                        f"soft voices, or set \"role\": \"comic\" if that's the joke")
        if bent and line.get("part") in chorded:
            add("warn", f"{line['part']}: a slide bends the whole part, and it also plays chords here - they sag "
                        f"with it; give the sliding line a part of its own")
    # Every note in its instrument's range; and long enough to speak.
    notes: Dict[str, list] = {}
    on_at: Dict[Tuple[str, int], list] = {}
    for t, is_on, name, key, vel in sorted(sc.events, key=lambda e: (e[0], e[1])):
        if is_on:
            on_at.setdefault((name, key), []).append(t)
        elif on_at.get((name, key)):
            notes.setdefault(name, []).append((on_at[(name, key)].pop(0), t, key))
    by_part: Dict[str, list] = {}
    for name, got in notes.items():
        by_part.setdefault(name.partition(":")[0], []).extend(got)
    quick = {(round(a, 3), k % 12) for part, got in by_part.items() if part not in orchestra.SPEAKS
             or orchestra.SPEAKS[part] < 0.1 for a, _, k in got}           # (a quick attack doubling it)
    for part, got in by_part.items():
        lo, hi = orchestra.RANGES.get(part, (0, 127))
        bad = [k for _, _, k in got if not lo <= k <= hi]
        if bad:
            add("error", f"{part}: {len(bad)} note(s) out of its range ({name_of(lo)}-{name_of(hi)}), "
                         f"e.g. {name_of(bad[0])}")
        speak = orchestra.SPEAKS.get(part)
        if speak:
            short = [(a, b) for a, b, k in got if b - a < 1.5 * speak and (round(a, 3), k % 12) not in quick]
            if short and len(short) >= 0.25 * len(got):
                add("warn", f"{part}: {len(short)} of {len(got)} notes are shorter than it takes to speak "
                            f"({1.5 * speak:.2f}s): they sound at under half its level, smeared. Double "
                            f"them with a quick instrument (horns, trumpets, flutes, clarinets, bassoons, "
                            f"pizzicato), or give it held notes")
    # The same note started again while it still sounds (the second cuts the first).
    for name in notes:
        if name.partition(":")[0] in PERCUSSIVE:
            continue                                         # (a drum is struck again: that's fine)
        active: Dict[int, int] = {}
        clash = 0
        for t, is_on, n, key, _ in sorted((e for e in sc.events if e[2] == name), key=lambda e: (e[0], e[1])):
            if is_on:
                clash += active.get(key, 0) > 0
                active[key] = active.get(key, 0) + 1
            else:
                active[key] = max(0, active.get(key, 0) - 1)
        if clash:
            add("warn", f"{name.partition(':')[0]}: {clash} note(s) restart a note already sounding "
                        "(the second cuts the first): move one to another part")
    # The tune: all played, and against its chords.
    melody = spec.get("melody") or []
    silent = [u0 for u0, _, _ in ctx["played"]
              if not any(float(m.get("from", ctx["start"])) - 1e-9 <= u0 < float(m.get("to", ctx["length"])) - 1e-9
                         and m.get("parts") for m in melody)]
    if silent:
        add("warn", f"the tune isn't played at {_where(ctx, silent[0])} ({len(silent)} notes): "
                    "no \"melody\" entry covers it")
    rubs = []
    for u0, d, k in ctx["played"]:
        c = ctx["chord_at"](u0)
        if c is None:
            add("error", f"no chord at {_where(ctx, u0)}, under the tune")
            break
        if d * unit < 0.45 or k % 12 in c["pcs"]:
            continue
        above = [p for p in c["pcs"] if (k - p) % 12 == 1]
        if above:
            rubs.append(f"{name_of(k)} over {c['symbol']} at {_where(ctx, u0)}")
    if rubs:
        add("note", "held tune notes a half step above a chord tone (a sigh if meant, a clash if not): "
                    + "; ".join(rubs[:4]) + (f" (+{len(rubs) - 4})" if len(rubs) > 4 else ""))
    # Shape: dynamics, and harmony that moves.
    pts = ctx["dyn_pts"]
    span = max(v for _, v in pts) - min(v for _, v in pts)
    if span < 15:
        add("note", f"the dynamics only move {span:.0f} velocity points: is there a build, a climax?")
    run, longest, at, prev = 0.0, 0.0, 0.0, None
    for a, b, c in ctx["prog"]:
        if c["symbol"] == prev:
            run += b - a
        else:
            run, prev = b - a, c["symbol"]
        if run > longest:
            longest, at = run, a
    if longest > 4 * bar:
        add("note", f"one chord holds {longest / bar:g} bars (up to {_where(ctx, at)}): static, if not meant")
    # Texture: how many lines move (start notes) in each bar besides the tune. A theme
    # where only the tune moves over held chords sounds thin and static; battle music
    # wants several moving layers at once (the tune, an answer or countermelody, an
    # ostinato, the drums).
    bounds = []
    u = ctx["start"]
    while u < ctx["length"] - 1e-9:
        bounds.append((u, T(u), T(min(u + bar, ctx["length"]))))
        u += bar
    moving, layers = [], []
    for u0, a, b in bounds:
        onsets: Dict[str, Dict[float, int]] = {}
        for t, is_on, name, *_ in sc.events:
            if is_on and a - 1e-6 <= t < b - 1e-6 and ":" not in name:
                at = onsets.setdefault(name.partition(":")[0], {})
                at[round(t, 3)] = at.get(round(t, 3), 0) + 1
        parts = set(onsets)
        # a line in motion: single notes at two or more moments (not a pad changing chords)
        pitched = {p for p, at in onsets.items() if p not in DRUMS
                   and len(at) >= 2 and min(at.values()) == 1}
        tune_moves = any(a - 1e-6 <= T(x) < b - 1e-6 for x, _, _ in ctx["played"])
        moving.append((u0, len(pitched), len(parts & DRUMS), tune_moves))
        layers.append((u0, len(parts), len(sum((list(at.values()) for at in onsets.values()), []))))
    run = []
    for u0, n, _, tm in moving + [(None, 9, 0, True)]:
        if u0 is not None and tm and n == 0:
            run.append(u0)
            continue
        if len(run) >= 3:
            add("note", f"only the tune moves at {_where(ctx, run[0])}-{_where(ctx, run[-1])} "
                        f"({len(run)} bars of held chords): an answer, a countermelody or an "
                        "inner line in motion would bring it to life")
        run = []
    ctx["texture"] = sum(n for _, n, _, _ in moving) / max(1, len(moving))
    if moving:
        avg = ctx["texture"]
        if spec.get("role") == "battle" and avg < 3:
            add("note", f"battle or loop texture: {avg:.1f} lines move per bar besides the tune "
                        "(pitched parts): big music keeps three or more going - an ostinato, a "
                        "countermelody or answer, a moving bass or inner line - under the tune")
    # A climax needs something to arrive: if the piece already plays at nearly its full
    # texture from the start, its peak adds nothing (the host, of the Ashen Saint's second
    # stage - 16-19 parts from bar 1, 20 at the "climax": "a climax without the climax").
    if len(layers) >= 8:
        pts = ctx["dyn_pts"]

        def dyn(u: float) -> float:                    # the dynamics curve at u
            if u <= pts[0][0]:
                return pts[0][1]
            for (x0, v0), (x1, v1) in zip(pts, pts[1:]):
                if x0 <= u <= x1:
                    return v0 + (v1 - v0) * (u - x0) / max(x1 - x0, 1e-9)
            return pts[-1][1]
        peak_i = max(range(len(layers)), key=lambda i: (dyn(layers[i][0] + bar / 2), layers[i][1]))
        before = [n for _, n, _ in layers[:peak_i]]
        if len(before) >= 4:
            opening = [n for _, n, _ in layers[:max(2, len(layers) // 4)]]
            full = layers[peak_i][1]
            if min(opening) >= 0.8 * full and sorted(before)[len(before) // 2] >= 0.85 * full:
                add("warn", f"the climax ({_where(ctx, layers[peak_i][0])}, {full} parts) has nothing left to "
                            f"arrive: the piece already plays {min(opening)}-{max(opening)} parts from the start. "
                            "Begin thinner and add layers in waves; hold something back for the peak (the choir, "
                            "the brass, the top register, the tune's full form) - the host: \"a climax without "
                            "the climax\"")
    # Seams: a section that drops what was playing and starts a new set of instruments
    # at one moment sounds like another piece glued on (the host, of a climax where the
    # harp, the countermelody and the tune's carriers all stopped as six new parts
    # began: "the climax did not go with what was before"). A climax grows out of what
    # came before: a layer or two carries across, the bars before it build, the new
    # instruments arrive in waves.
    # (The checks the host's verdicts taught - seams, the surprise budget - can be switched
    # off, ARRANGEMENT_HOST_CHECKS=0, to test what they add.)
    host_checks = __import__("os").environ.get("ARRANGEMENT_HOST_CHECKS", "1") != "0"
    sounding: Dict[str, List[Tuple[float, float]]] = {}
    held: Dict[Tuple[str, int], float] = {}
    for t, is_on, name, key, _ in sorted(sc.events, key=lambda e: (e[0], e[1])):
        part = name.partition(":")[0]
        if is_on:
            held[(part, key)] = t
        elif (part, key) in held:
            sounding.setdefault(part, []).append((held.pop((part, key)), t))

    def plays(part: str, a_s: float, b_s: float) -> bool:
        return any(x < b_s - 1e-6 and y > a_s + 1e-6 for x, y in sounding.get(part, []))

    parts_all = [p for p in sounding if p not in DRUMS]
    for i in range(2, len(bounds) - 1 if host_checks else 2):
        u0, a_s, b_s = bounds[i]
        if ctx["loop"] and i >= len(bounds) - 2:
            continue
        before = {p for p in parts_all if plays(p, bounds[i - 1][1], bounds[i - 1][2])}
        earlier = {p for p in parts_all if plays(p, bounds[i - 2][1], bounds[i - 2][2])}
        now = {p for p in parts_all if plays(p, a_s, b_s)}
        after = {p for p in parts_all if plays(p, bounds[i + 1][1], bounds[i + 1][2])}
        stopped = sorted(p for p in before if p not in now and p not in after)
        started = sorted(p for p in now if p not in before and p not in earlier)
        kept = before & now
        if len(started) >= 3 and (len(stopped) >= 2 or len(started) >= 5) and len(stopped) >= len(kept):
            add("warn", f"a seam at {_where(ctx, u0)}: {', '.join(stopped) or 'nothing'} stop as "
                        f"{', '.join(started)} start - heard as another piece glued on. Carry a layer "
                        "or two across it, build the bars before it, and bring the new parts in waves")
        elif len(started) >= 4 and len(now) >= 1.6 * max(1, len(before)):
            add("warn", f"the orchestra jumps from {len(before)} to {len(now)} parts at {_where(ctx, u0)} "
                        f"({', '.join(started)} all start): a climax that doesn't grow out of what came "
                        "before. Build into it over the bars before (a crescendo, a roll, a rising line) "
                        "and bring the new parts in waves")
    # The surprise budget: a surprising tune wants a supportive setting, a simple tune
    # a rich one (the host's 2x2: those pairings beat both-plain and both-rich).
    budget = surprise_budget(ctx, spec) if host_checks and ctx["played"] else None
    if budget:
        tune_pct, chromatic, changes, verdict = budget
        if verdict == "both":
            add("note", f"a surprising tune (surprise at the {tune_pct}th percentile of real tunes) in a "
                        f"surprising setting ({chromatic:.0%} chromatic chords, {changes} key change(s)): "
                        "the host preferred a plainer setting for such a tune - let the tune lead")
        elif verdict == "neither":
            add("note", f"a simple tune (surprise at the {tune_pct}th percentile) in a plain setting "
                        f"({chromatic:.0%} chromatic chords, no key change): spend some surprise in the "
                        "setting - a key change, a chromatic lift at the climax, a breakdown")
    if not listen:
        return out
    # Listening: render the layers apart and measure them.
    import numpy as np
    rate = 22050
    mix = spec.get("mix") or {}

    def layer(keep) -> "np.ndarray":
        part = orchestra.Score()
        part.events = [e for e in sc.events if keep(e[2])]
        return orchestra.play(part, ctx["seconds"], rate=rate, mix=mix).mean(axis=1)

    lead = layer(lambda n: ":" in n)
    choir = layer(lambda n: n in ("choir", "chorus", "men_choir", "choir_oo", "choir_oh"))
    rest = layer(lambda n: ":" not in n and n not in ("choir", "chorus", "men_choir", "choir_oo", "choir_oh"))

    def db(x) -> float:
        return float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)) if len(x) else -240.0

    for m in melody:
        a, b = float(m.get("from", ctx["start"])), float(m.get("to", ctx["length"]))
        i, j = int(T(a) * rate), int(T(min(b, ctx["length"])) * rate)
        if j - i < rate // 2 or db(lead[i:j]) < -200:
            continue
        gap = db(lead[i:j]) - db(rest[i:j])
        if gap < -2:
            add("error", f"the tune is buried at {_where(ctx, a)}-{_where(ctx, b - 1e-6)}: {gap:+.0f} dB "
                         f"under the rest (give that melody entry \"gain\": {round(3 - gap)})")
        elif gap < 1:
            add("warn", f"the tune is barely over the rest at {_where(ctx, a)}-{_where(ctx, b - 1e-6)}: "
                        f"{gap:+.0f} dB (\"gain\": {round(3 - gap)} would put it at +3)")
    # The choir, where it sings.
    w = rate // 2
    sung = [i for i in range(0, len(choir) - w, w) if np.abs(choir[i:i + w]).max() > 1e-3]
    if sung:
        idx = np.concatenate([np.arange(i, i + w) for i in sung])
        gap = db(choir[idx]) - db(rest[idx])
        if gap < -8:
            add("warn", f"the choir is {gap:+.0f} dB under the rest where it sings: it won't be heard "
                        f"(\"mix\": {{\"choir\": {round(-4 - gap)}}}, or thin the orchestra there)")
    # A loop's seam.
    if ctx["loop"]:
        full = (lead + choir + rest)
        n = int(ctx["seconds"] * rate)
        tail = full[n:]
        body = full[:n].copy()
        body[:len(tail)] += tail[:n]
        q = rate // 2
        step = db(body[:q]) - db(body[-q:])
        if abs(step) > 3:
            add("warn", f"the loop's seam steps {step:+.0f} dB (end -> start): bring the ends' dynamics together")
    peak_level = db(lead + choir + rest)
    if peak_level < -60:
        add("error", "the piece is silent")
    return out


def surprise_budget(ctx: Dict[str, Any], spec: Dict[str, Any]):
    """(tune surprise percentile, share of time on chords outside the mode, key changes,
    "both" | "neither" | "balanced"), or None (no tune corpus to measure against)."""
    try:
        from music import tune_score
        if not tune_score.CACHE.is_file():
            return None
        t = spec.get("tune") or {}                     # the tune as written (stage 1): a later
        plain = music_compose.leitmotif(                # stage's held climax reads as rare anyway
            t["seed"], t.get("mode", "major"), t.get("cls", ""), stage=1, dark=int(t.get("dark", 0)),
            gen=int(t.get("gen", 1)), written=t.get("written"))
        tune_pct = tune_score.score(tune_score.from_leitmotif(plain))["surprise"][1]
    except Exception:
        return None
    scale = ctx["tune"]["scale"]
    scale = scale if isinstance(scale, list) else music_compose._scale(scale)
    keys = [(float(k.get("from", ctx["start"])), float(k.get("to", 1e9)), int(k.get("shift", 0)))
            for k in spec.get("keys") or []]
    total = chrom = 0.0
    for a, b, c in ctx["prog"]:
        shift = next((sh for ka, kb, sh in keys if ka - 1e-9 <= a < kb - 1e-9), 0)
        home = {(ctx["tune"]["key"] + shift + st) % 12 for st in scale}
        total += b - a
        if not set(c["pcs"]) <= home:
            chrom += b - a
    chromatic = chrom / total if total else 0.0
    changes = len(keys)
    rich = chromatic >= .15 or changes > 0
    plain = chromatic < .05 and changes == 0
    verdict = ("both" if tune_pct >= 90 and rich else "neither" if tune_pct <= 75 and plain else "balanced")
    return tune_pct, chromatic, changes, verdict


CHOIRS = ("choir", "chorus", "men_choir", "choir_oo", "choir_oh")


def _octave_shift(keys: List[int], lo: int, hi: int) -> Tuple[int, int]:
    """The octave shift (fewest octaves first) putting most of these notes in lo..hi,
    and how many are still out."""
    best = (0, len(keys))
    for k in sorted(range(-4, 5), key=abs):
        out = sum(not lo <= p + 12 * k <= hi for p in keys)
        if out < best[1]:
            best = (k, out)
    return best


def _fold(p: int, lo: int, hi: int) -> Optional[int]:
    while p < lo:
        p += 12
    while p > hi:
        p -= 12
    return p if lo <= p <= hi else None


def _quick_double(keys: List[int]) -> Optional[str]:
    """A quick-speaking instrument whose range holds these notes (by register)."""
    mid = sorted(keys)[len(keys) // 2]
    for part in (("flutes", "clarinets", "bassoons") if mid >= 72 else ("clarinets", "bassoons", "flutes")
                 if mid >= 55 else ("bassoons", "clarinets")):
        lo, hi = orchestra.RANGES.get(part, (0, 127))
        if all(lo <= k <= hi for k in keys):
            return part
    return None


def fix(spec: Dict[str, Any], listen: bool = True) -> Tuple[Dict[str, Any], List[str]]:
    """The critic's mechanical fixes, applied: notes moved by octaves into their
    instrument's range (a whole line or placement if one shift fits, else note by note),
    harmony ranges kept inside the instrument's, a quick doubling for a slow-speaking
    line's short notes, the choir's level, a loop seam's dynamics. Musical decisions
    (too many parts entering at once, a seam's harmony) are left to the composer."""
    import copy
    s = copy.deepcopy(spec)
    changes: List[str] = []
    for i, line in enumerate(s.get("lines") or []):
        part = line.get("part")
        lo, hi = orchestra.RANGES.get(part, (0, 127))
        own = expand_motifs({**s, "lines": [{k: v for k, v in line.items() if k != "double"}]})["lines"][0]
        keys = [pitch(n[1]) for n in own.get("notes") or []]
        if keys and not all(lo <= p <= hi for p in keys):
            k, out = _octave_shift(keys, lo, hi)
            if k and out == 0:
                if "motif" in line:
                    line["octave"] = int(line.get("octave", 0)) + k
                else:
                    line["notes"] = [[n[0], name_of(pitch(n[1]) + 12 * k)] + list(n[2:]) for n in line["notes"]]
                changes.append(f"{part}: line {i} moved {k:+d} octave(s) into its range")
            elif "motif" not in line:
                moved, new = 0, []
                for n in line["notes"]:
                    p = pitch(n[1])
                    q = p if lo <= p <= hi else _fold(p, lo, hi)
                    if q is not None and q != p:
                        n, moved = [n[0], name_of(q)] + list(n[2:]), moved + 1
                    new.append(n)
                line["notes"] = new
                if moved:
                    changes.append(f"{part}: {moved} note(s) of line {i} moved by octaves into its range")
        twins = line.get("double") or []
        for d in twins if isinstance(twins, list) else [twins]:
            dlo, dhi = orchestra.RANGES.get(d.get("part"), (0, 127))
            move = int(d.get("shift", 0)) + 12 * int(d.get("octave", 0))
            dk = [p + move for p in keys]
            if dk and not all(dlo <= p <= dhi for p in dk):
                k, out = _octave_shift(dk, dlo, dhi)
                if k and out == 0:
                    d["octave"] = int(d.get("octave", 0)) + k
                    changes.append(f"{d['part']} (doubling {part}): moved {k:+d} octave(s) into its range")
    for h in s.get("harmony") or []:
        lo, hi = orchestra.RANGES.get(h.get("part"), (0, 127))
        if not h.get("range"):
            continue
        a, b = pitch(h["range"][0]), pitch(h["range"][1])
        na, nb = max(a, lo), min(b, hi)
        if nb - na < 7:                                  # too narrow left: move the window by octaves
            k, _ = _octave_shift([a, b], lo, hi)
            na, nb = max(a + 12 * k, lo), min(b + 12 * k, hi)
        if nb - na < 12 and (a < lo or b > hi):          # an octave at least, so every note of a chord fits
            nb = min(hi, na + 12)
            na = max(lo, nb - 12)
        if (na, nb) != (a, b) and nb > na:
            h["range"] = [name_of(na), name_of(nb)]
            changes.append(f"{h['part']}: harmony range {name_of(a)}-{name_of(b)} -> {h['range'][0]}-{h['range'][1]}")
    for kind in ("patterns", "rolls", "hits"):
        for x in s.get(kind) or []:
            note = x.get("note")
            if isinstance(note, str) and (note in KIT or note in ("root", "fifth")):
                continue
            if note is None:
                continue
            lo, hi = orchestra.RANGES.get(x.get("part"), (0, 127))
            p = pitch(note)
            q = p if lo <= p <= hi else _fold(p, lo, hi)
            if q is not None and q != p:
                x["note"] = name_of(q)
                changes.append(f"{x['part']}: {kind} note {name_of(p)} -> {name_of(q)}")
    for level, msg in check(s, listen=listen):
        m = re.match(r"(\w+): \d+ of \d+ notes are shorter than it takes to speak", msg)
        if m:
            part = m.group(1)
            for line in s.get("lines") or []:
                if line.get("part") != part or line.get("double"):
                    continue
                own = expand_motifs({**s, "lines": [line]})["lines"][0]
                keys = [pitch(n[1]) for n in own.get("notes") or []]
                twin = _quick_double(keys) if keys else None
                if twin:
                    line["double"] = [{"part": twin, "vel": -6}]
                    changes.append(f"{part}: its quick notes doubled by {twin} (so they speak)")
            continue
        m = re.search(r'"mix": \{"choir": (-?\d+)\}', msg)
        if m:
            used = {l.get("part") for k in ("lines", "harmony") for l in s.get(k) or []} & set(CHOIRS)
            for part in sorted(used):
                s.setdefault("mix", {})[part] = round(float(s.get("mix", {}).get(part, 0)) + int(m.group(1)), 1)
            changes.append(f"choir level +{m.group(1)} dB ({', '.join(sorted(used))})")
            continue
        if msg.startswith("the loop's seam steps") and len(s.get("dynamics") or []) >= 2:
            first, last = s["dynamics"][0], s["dynamics"][-1]
            if last[1] != first[1]:
                last[1] = first[1]
                changes.append(f"loop seam: the last dynamics point set to the first's ({first[1]})")
    return s, changes


def describe(seed: str, mode: str = "major", cls: str = "", stage: int = 1, dark: int = 0,
             gen: int = 1, written: Optional[Dict[str, Any]] = None) -> str:
    """The tune, for writing an arrangement: its key, meter, and every note with its time."""
    tune = music_compose.leitmotif(seed, mode, cls, stage=stage, dark=dark, gen=gen, written=written)
    bar = tune["bar"]
    lines = [f"{seed} ({mode}{', ' + cls if cls else ''}, stage {stage}, dark {dark}): "
             f"tonic {name_of(tune['key'])}, {tune['meter']} ({'eighths' if tune['meter'] == '6/8' else 'beats'}), "
             f"{tune['scale'] if isinstance(tune['scale'], str) else 'scale ' + str(tune['scale'])}, "
             f"{tune['kind']}, {sum(b for _, b in tune['notes']):g} units = "
             f"{sum(b for _, b in tune['notes']) / bar:g} bars",
             "at      bar.pos  note   units"]
    u = 0.0
    for st, b in tune["notes"]:
        lines.append(f"{u:<7g} {int(u // bar) + 1:>3}.{u % bar:<4g} {name_of(tune['key'] + st):<6} {b:g}")
        u += b
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Arrangements for the sampled orchestra.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tune", help="show a character's tune, to arrange it")
    t.add_argument("seed")
    t.add_argument("--class", dest="cls", default="")
    t.add_argument("--minor", action="store_true", help="the villain's version")
    t.add_argument("--stage", type=int, default=1)
    t.add_argument("--dark", type=int, default=0)
    t.add_argument("--gen", type=int, default=1, help="the tune generator's version")
    t.add_argument("--written", help="a hand-written tune (JSON): its notes, with times")
    p = sub.add_parser("play", help="play an arrangement (a JSON file)")
    p.add_argument("file")
    p.add_argument("--out", required=True)
    c = sub.add_parser("check", help="the score critic: what a listener would notice")
    c.add_argument("file")
    c.add_argument("--quick", action="store_true", help="read the score only (don't render it)")
    fx = sub.add_parser("fix", help="apply the critic's mechanical fixes (ranges, quick doublings, "
                                    "the choir's level, a loop's seam), then check again")
    fx.add_argument("file")
    fx.add_argument("--out", help="write the fixed score here (default: in place)")
    fx.add_argument("--quick", action="store_true", help="read the score only (don't render it)")
    a = ap.parse_args()
    if a.cmd == "tune":
        written = json.loads(Path(a.written).read_text(encoding="utf-8")) if a.written else None
        print(describe(a.seed, "minor" if a.minor else "major", a.cls, a.stage, a.dark, a.gen, written))
        return
    if a.cmd == "fix":
        path = Path(a.file)
        spec = json.loads(path.read_text(encoding="utf-8"))
        try:
            fixed, changes = fix(spec, listen=not a.quick)
        except (ArrangementError, KeyError, TypeError, ValueError) as e:
            sys.exit(f"[arrangement] {a.file}: {e}")
        Path(a.out or a.file).write_text(json.dumps(fixed, indent=1, ensure_ascii=False), encoding="utf-8")
        for c in changes:
            print(f"FIXED {c}")
        left = check(fixed, listen=not a.quick)
        for level, msg in left:
            print(f"{level.upper():5} {msg}")
        print(f"{len(changes)} fix(es); left: {sum(lv == 'error' for lv, _ in left)} error(s), "
              f"{sum(lv == 'warn' for lv, _ in left)} warning(s), {sum(lv == 'note' for lv, _ in left)} note(s)")
        return
    if a.cmd == "check":
        try:
            found = check(json.loads(Path(a.file).read_text(encoding="utf-8")), listen=not a.quick)
        except (ArrangementError, KeyError, TypeError, ValueError) as e:
            sys.exit(f"[arrangement] {a.file}: {e}")
        for level, msg in found:
            print(f"{level.upper():5} {msg}")
        print(f"{sum(lv == 'error' for lv, _ in found)} error(s), {sum(lv == 'warn' for lv, _ in found)} "
              f"warning(s), {sum(lv == 'note' for lv, _ in found)} note(s)")
        sys.exit(1 if any(lv == "error" for lv, _ in found) else 0)
    try:
        spec = json.loads(Path(a.file).read_text(encoding="utf-8"))
        samples, rate = render(spec)
    except (ArrangementError, KeyError, TypeError, ValueError) as e:
        sys.exit(f"[arrangement] {a.file}: {e}")
    path = music_compose.write(samples, rate, Path(a.out))
    print(f"{path} ({len(samples) / rate:.1f}s{', a loop' if spec.get('loop') else ''})")


if __name__ == "__main__":
    main()
