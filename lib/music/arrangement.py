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
  "loop_from": 0,        # a loop with an entry: [start, loop_from) plays once (a boss stage's
                         # strong opening), then [loop_from, length) loops; the file says where
                         # (a LOOPSTART tag) and the table plays it so. Default: start
  "role": "theme",       # what it's for: theme, villain, battle, lament, place, ... "stage"
                         # (a boss stage also says which: "stage": 2 - a later stage is
                         # mastered louder than the one before it)
                         # (a boss stage: entry + body - the critic's stage checks), "pre_end",
                         # "turn" and "place" (steady by design: no climax check), "comic"
  "ritard": {"from": 84, "amount": 0.4},     # slowing to the end (40% slower at the last note)
  "dynamics": [[-12, 60], [0, 80], [36, 96], [60, 124]],   # velocity, linear between points
  "statements": [{"at": 0}],                 # where the tune is played (default: once, at 0; [] for none);
                         # optional "from"/"to" (a slice of the tune, in its own units) and
                         # "shift" (semitones): {"at": 96, "from": 0, "to": 36, "shift": -12},
                         # and "stretch" (augmentation: 2 plays it at half speed, 4 at a quarter,
                         # at the piece's own tempo - a chant over a fast engine)
  "keys": [{"from": 96, "to": 192, "shift": 2}],  # a key change: the chords there are read in
                         # the new key (pair it with that statement's "shift": 2), so "I" is
                         # still home - the new home; alone (no statement there) it moves a
                         # passage's chords - give motifs placed there the same "shift"
  "melody": [            # who plays the tune, when, and how many semitones from as written
    {"from": 0, "to": 18, "parts": {"horns": 0}, "vel": 8},
    {"from": 18, "to": 36, "parts": {"violins": 12}}
  ],
  "progression": {"at": 0, "chords": "i bVI iv v | i bVII bVI*0.5 iv*0.5 i", "repeat": 2},
                         # chords a bar each (or "every": units), "*2" twice as long - added
                         # to "chords"; a list of them for several passages
  "chords": [            # roman numerals in the tune's key, [from, to, chord]: counted
                         # from the tonic's MAJOR scale, so in F minor i = Fm, iv = Bbm,
                         # bIII = Ab, bVI = Db, bVII = Eb, V = C, bII = Gb
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
                         # "spans": [[0, 132], [138, 201]] instead of from/to: the same entry
                         # in several sections (harmony, patterns, rolls)
  "figures": {"waltz": [ # an accompaniment written ONCE (harmony entries, no from/to), then
    {"play": "bass", "range": ["D2", "C#3"], "pattern": "x--", "legato": 0.95},
    {"play": "chord", "range": ["A3", "F4"], "pattern": " oo", "vel": -6}]},
                         # play: chord, bass, root, third, fifth, root5, octaves, or
                         # arpeggio - one chord tone per pattern hit, cycling through the
                         # chord's tones in "range" ("order": up / down / updown); a figure
                         # or entry for several "parts" uses one "range" for all of them
                         # (give parts that need different ranges entries of their own)
                         # played in "harmony" wherever wanted: {"figure": "waltz", "part":
                         # "cellos", "spans": [[0, 132], [237, 432]], "vel": -12, "octave": -1}
                         # (part, vel and octave apply to every entry of the figure)
  "lines": [             # anything written out: countermelodies, ostinati, fanfares
                         # ("lead": true marks a line carrying a tune: the critic measures
                         # it over the rest, like the tune's statements)
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
                         # {note index: semitones, or a pitch} - the corrupted interval
                         # (indexes count in the whole motif, also inside a "take"; "at"
                         # places the first note taken); repeat / every; "notes" may be
                         # added to the same line too
                         # "double": [{"part": "chorus", "octave": -1, "vel": -4}] on any
                         # line or placement: the same notes on other parts, written once
                         # ("octave"/"shift" count from the line as placed, after its own)
  "patterns": [          # percussion (or any part) on one note, in a rhythm
    {"part": "kit", "note": "snare", "from": 36, "to": 60, "pattern": "xoooox", "vel": -30},
    {"part": "timpani", "note": "root", "from": 0, "to": 84, "pattern": "x     ", "vel": -6}
  ],                     # note: a pitch, "root"/"fifth" (of the chord, in the timpani's
                         # lowest octave, D2-C#3 - for drums; a pitched part's root is a
                         # "harmony" entry), or
                         # snare, bd, crash, cymbal, china, splash, ride, triangle, gong (on
                         # the kit, a GM crash cymbal: the real gong is the "gong" part); the
                         # gong, anvil, brake_drum and bass_drum parts play their one sound
                         # for any of these names or "root" (a pitch moves it a little)
  "rolls": [{"part": "timpani", "note": "G#2", "from": 57, "to": 60, "vel": [70, 120]}],
  "unhinge": [{"parts": ["strings", "tremolo", "violins"], "from": 36, "to": 40, "drift": 0.6,
               "wobble": 0.3}],    # those parts waver and drift off pitch, each its own way,
                         # and come back true by the end
  "hits": [{"part": "kit", "note": "crash", "at": 60, "len": 6, "vel": 124}],
  "organ": {"speaker": [[0, "slow"], [32, "fast"]], "drawbars": "888800000", "percussion": "third"},
                         # the rock organ's: its rotating speaker switched slow / fast there (it
                         # eases into it: the horn in ~1 s, the drum in ~4; default "fast" all
                         # through - "speaker": "slow" for all of it), its drawbars (16' to 1',
                         # default 888800000) and percussion ("second", "third"; default none)
  "mix": {"choir": 3},   # dB up or down for a part in this piece (all parts are already
                         # evened out: the same velocity is the same loudness)
  "lead": 4              # the tune's notes are mixed this many dB over the rest (default 4);
}                        # a "melody" entry's "gain" adds to it, a "lines" entry's sets its own

Choir (and organ, strings) voices take over a second to bloom: give them notes of a
beat or longer, held chords, not quick rhythms; let brass and drums carry those. (The
string sections are different: see Parts.)

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
  voice, a lone solo (solo_violin, oboe, english_horn, flute, horn_solo), a run - "lines";
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
flutes, piccolo, oboe, english_horn, clarinets, bassoons, horns, horn_solo, trumpets,
trombones, tuba, brass, choir, chorus (E2-E6), men_choir (E2-A4; above E4 it sounds like an instrument), choir_oo, choir_oh (A2-D#6), harp, celesta, glockenspiel, bells, organ,
timpani, taiko, toms, reverse_cymbal, kit (bd, snare, cymbals): as many as wanted.
Short string notes are automatic: a note on violins, violins2, cellos or basses shorter than
0.3 s (orchestra.SHORT_S) plays from real staccato/spiccato recordings, which speak at once (a
crisp stroke, as loud as a held note at the same velocity); longer notes play the sustained
strings, as before. Write quick string figures as they are - no pizzicato double to make them
heard (pizzicato is a colour of its own, played as it is). A note of 0.3 s up to the time its
sustained recording takes to speak is the one to avoid: shorter (a lower "legato") or held.
horns and trombones are real sections (Virtual Playing Orchestra's); horn_solo is one real
horn (F2-F5): the voice for a tune that must cut through - a horn call, a hero's line over
the band - clearer than the section. The brass sits drier than the strings (less hall).
Real percussion (struck, let ring): gong (a big tam-tam, ~25 s ring: transformations and
the biggest arrivals); anvil and brake_drum (metal hits, sparingly: a forge, a machine);
bass_drum (the orchestral one: weight under a tutti or a march).
A real electric guitar, through an amp, double-tracked left and right: guitar (open power
chords, ringing to the next pick) and guitar_mute (palm-muted chugs) - one instrument, one
amp: a new pick stops what rang, and "mix": {"guitar": dB} sets both. B1-E5; power chords
only ("root5", "root", "octaves": a third turns to mud). A surprise held back for a later
stage, never a bed for every piece. guitar_lead: a lead guitar of its own (overdriven, singing,
near centre; one note at a time, legato, a delayed vibrato on held notes; E2-G5, best E4-E5) -
a short solo in a later stage, where the chant rests (no falling slides: comic).
A rock organ, synthesized: rock_organ, a tonewheel organ (888800000) overdriven through a
rotating speaker, fast by default ("organ" switches it) - the church organ gone wild: riffs,
stabbed and held chords, C2-C7. Rarer still than the guitar: a boss's third stage or later.
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


def expand_figures(spec: Dict[str, Any]) -> Dict[str, Any]:
    """The spec with "harmony" figures and "spans" written out. A figure is an
    accompaniment written once ("figures": {name: [harmony entries without from/to]}) and
    played wherever wanted: {"figure": name, "part": ..., "spans": [[from, to], ...],
    "vel": offset, "octave": n}. Any "harmony", "patterns" or "rolls" entry may give
    "spans" instead of from/to (the same entry in several sections)."""
    figures = spec.get("figures") or {}
    keys = ("harmony", "patterns", "rolls")
    # Several parts at once: "parts": [...] on any harmony / patterns / rolls / hits entry, and
    # "at": [...] on a hit (a tutti written once, played as often as wanted).
    many = {}
    for k in keys + ("hits",):
        out_k, touched = [], False
        for e in spec.get(k) or []:
            if isinstance(e, dict) and isinstance(e.get("parts"), list) and k != "melody":
                touched = True
                out_k += [{**{x: v for x, v in e.items() if x != "parts"}, "part": pt} for pt in e["parts"]]
            else:
                out_k.append(e)
        if k == "hits":
            spread = []
            for e in out_k:
                if isinstance(e, dict) and isinstance(e.get("at"), list):
                    touched = True
                    spread += [{**e, "at": a} for a in e["at"]]
                else:
                    spread.append(e)
            out_k = spread
        if touched:
            many[k] = out_k
    if many:
        spec = {**spec, **many}
    if not figures and not any("spans" in e or "figure" in e for k in keys for e in spec.get(k) or []
                               if isinstance(e, dict)):
        return spec

    def octave(rng, n):
        if not n or not rng:
            return rng
        return [name_of(pitch(x) + 12 * int(n)) for x in rng]

    out = {**spec}
    for k in keys:
        entries = []
        for e in spec.get(k) or []:
            if not isinstance(e, dict) or ("spans" not in e and "figure" not in e):
                entries.append(e)
                continue
            spans = e.get("spans") or [[e["from"], e["to"]]]
            if "figure" in e:
                if e["figure"] not in figures:
                    raise ArrangementError(f"no such figure: {e['figure']!r} (figures: {', '.join(figures) or 'none'})")
                parts = [dict(t) for t in figures[e["figure"]]]
            else:
                parts = [{x: v for x, v in e.items() if x != "spans"}]
            for a, b in spans:
                for t in parts:
                    one = {**t, "from": a, "to": b}
                    if "figure" in e:
                        if "part" in e and "part" not in t:      # (a figure's own part wins)
                            one["part"] = e["part"]
                        if "vel" in e:
                            one["vel"] = float(t.get("vel", 0)) + float(e["vel"])
                        if e.get("octave") and "range" in one:
                            one["range"] = octave(one["range"], e["octave"])
                    entries.append(one)
        out[k] = entries
    return out


def expand_motifs(spec: Dict[str, Any]) -> Dict[str, Any]:
    """The spec with every "lines" entry that places a motif written out as plain notes,
    and every "double" (the line played by other parts too) written out as lines.
    A motif is written once ("motifs": {name: notes from time 0}) and placed as often as
    wanted, each time transformed: shift (semitones) / octave, stretch (time), invert
    (mirrored round its first note), retro (backwards), take [i, j] (a fragment: notes
    i..j-1), alter {index: semitones or a pitch} (the corrupted interval), repeat / every."""
    spec = expand_figures(spec)
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


def _organ(spec: Dict[str, Any], sc: "orchestra.Score", T) -> None:
    """The rock organ's settings ("organ"): its drawbars, its percussion, its rotating speaker
    ("slow", "fast", or [[time, "slow" | "fast"], ...]: switched there, easing into it)."""
    org = spec.get("organ")
    if not org:
        return
    if not isinstance(org, dict):
        raise ArrangementError('"organ" is {"speaker": ..., "drawbars": "888000000", "percussion": ...}')
    bars = org.get("drawbars")
    if bars is not None:
        if not re.fullmatch(r"[0-8]{9}", str(bars)):
            raise ArrangementError(f'"drawbars" {bars!r}: nine digits 0-8, 16\' to 1\' (e.g. "888000000")')
        sc.organ["drawbars"] = str(bars)
    perc = org.get("percussion")
    if perc:
        if perc not in orchestra.ORGAN_PERC:
            raise ArrangementError(f'"percussion" {perc!r}: "second", "third" or none')
        sc.organ["percussion"] = perc
    speaker = org.get("speaker", "fast")
    for at, speed in ([[None, speaker]] if isinstance(speaker, str) else speaker):
        if speed not in ("slow", "fast"):
            raise ArrangementError(f'the speaker\'s {speed!r}: "slow" or "fast"')
        if at is None:
            sc.organ["speaker"] = speed
        else:
            sc.rotate(max(0.0, T(float(at))), speed == "fast")


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
    bars = {"4/4": 4, "3/4": 3, "2/4": 2, "6/8": 6}             # (the generator's METERS lack 2/4)
    if t.get("meter") in bars:                                  # ...and a set meter (bars, beats)
        tune = {**tune, "meter": t["meter"], "bar": bars[t["meter"]]}
    key = tune["key"]
    notes, u = [], 0.0
    for st, b in tune["notes"]:
        notes.append((u, b, st))
        u += b
    tune_len = u
    # (an explicit empty list: no tune at all - a sketch whose melody is written in "lines")
    statements = spec["statements"] if isinstance(spec.get("statements"), list) else [{"at": 0}]
    written_len = tune_len
    played = []                                                 # (time, units, MIDI as written)
    for s in statements:
        at, lo, hi = float(s.get("at", 0)), float(s.get("from", 0)), float(s.get("to", tune_len))
        k = float(s.get("stretch", 1))
        if k <= 0:
            raise ArrangementError(f'a statement\'s "stretch" must be above 0 (got {k:g})')
        for u0, b, st in notes:
            if lo - 1e-9 <= u0 < hi - 1e-9:
                played.append((at + (u0 - lo) * k, min(b, hi - u0) * k, key + st + int(s.get("shift", 0))))
    start = float(spec.get("start", 0))
    if not played:                     # a sketch with no tune ends with its last written note
        ends = [float(x[1]) for x in list(spec.get("chords", [])) + progression_chords(spec, tune["bar"])]
        ends += [float(x.get("to", 0)) for k in ("harmony", "patterns", "rolls") for x in spec.get(k, [])]
        ends += [float(n[0]) + float(n[2]) for x in spec.get("lines", []) for n in x.get("notes", [])]
        ends += [float(x.get("at", 0)) + float(x.get("len", 0)) for x in spec.get("hits", [])]
        tune_len = max(ends, default=tune_len)
    length = float(spec.get("length") or max((p[0] + p[1] for p in played), default=tune_len))
    loop = bool(spec.get("loop"))
    loop_from = float(spec.get("loop_from", start)) if loop else start
    if not start <= loop_from < length:
        raise ArrangementError(f"loop_from {loop_from:g} is outside the piece ({start:g} to {length:g})")
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
    _organ(spec, sc, T)

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
            elif play == "arpeggio":                    # one chord tone per hit, through the range
                if not h.get("pattern"):
                    raise ArrangementError('"play": "arpeggio" needs a "pattern" (one tone per hit)')
                tones = [k for k in range(lo, hi + 1) if k % 12 in c["pcs"]]
                if not tones:
                    raise ArrangementError(f'arpeggio on {part}: no tone of {c["symbol"]} in {h.get("range")}')
                order = h.get("order", "up")
                keys = (tones[::-1] if order == "down" else
                        tones + tones[-2:0:-1] if order == "updown" else tones)
            else:
                raise ArrangementError("play is chord, bass, root, third, fifth, root5, octaves or arpeggio, "
                                       f"not {play!r}")
            if play == "arpeggio":
                # counted from the harmony's own start, like the pattern: it flows across chords
                for i, (t0, hold, acc) in enumerate(_pattern_hits(h["pattern"], a, b, step)):
                    if s0 - 1e-9 <= t0 < s1 - 1e-9:
                        note(part, keys[i % len(keys)], t0, hold * step,
                             dyn(t0) + float(h.get("vel", 0)) + (ACCENT if acc else 0), legato)
            elif h.get("pattern"):
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
        if part in orchestra.PERC and (what in KIT or what in ("root", "fifth")):
            return orchestra.PERC[part]["key"]      # (one struck sound: its own key)
        if isinstance(what, str) and what in KIT:
            return KIT[what]
        if what in ("root", "fifth"):
            c = chord_at(x)
            if c is None:
                raise ArrangementError(f'"{what}" at {x}: there is no chord there')
            return place(c[what], 38, 49)           # (the drums' lowest octave, D2-C#3: under the bass)
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
            "loop_from": T(loop_from) if loop else None, "loop_from_u": loop_from,
            "statements": statements, "tune_len": written_len,
            "played": played, "prog": prog, "T": T, "unit": unit, "beat": beat, "start": start,
            "length": length, "dyn_pts": dyn_pts, "chord_at": chord_at}


def loop_start(spec: Dict[str, Any], rate: int = orchestra.RATE) -> Optional[int]:
    """Where a loop with an entry loops back to, in samples (None: from the top, or no loop)."""
    if not spec.get("loop") or "loop_from" not in spec:
        return None
    at = _build(spec)["loop_from"]
    return int(round(at * rate)) or None


STING_SECONDS = 15.0    # a one-shot shorter than this is a sting (boss-music.md: a little louder)
STAGE_STEP_DB = 2.0     # each later boss stage ("stage": 2, 3) plays this much louder than the last
STAGE_LIMIT_DB = 8.0    # (and may limit its peaks harder to get there: the Saint's stage 2 takes 6.3 dB)
# The host, of a stage 2 mastered 1.6 dB quieter than stage 1 (its bigger climax left the
# limiter less room): "the second stage does not have more emotion; the change is minimal".


def render(spec: Dict[str, Any], rate: int = orchestra.RATE, sf2: Path = orchestra.SF2):
    """An arrangement played by the orchestra -> (stereo float32 samples, rate). A loop with
    an entry ("loop_from") loops back to loop_start(spec), not to its first sample."""
    score, seconds, loop = build(spec)
    mix = spec.get("mix") or {}
    if loop:
        dry = orchestra.play(score, seconds + 3.0, sf2, rate, mix)  # (what rings past the end)
        at = loop_start(spec, rate) or 0
        wet = orchestra.hall(dry, rate, loop_at=int(round(seconds * rate)), loop_from=at)
        later = max(0, int(spec.get("stage", 1)) - 1) if spec.get("role") == "stage" else 0
        if later:                          # a later boss stage: louder than the one before
            return orchestra.master(wet, rate, loop=True, loop_from=at, hot_db=STAGE_STEP_DB * later,
                                    limit_db=STAGE_LIMIT_DB), rate
        return orchestra.master(wet, rate, loop=True, loop_from=at), rate
    dry = orchestra.play(score, seconds, sf2, rate, mix)
    if seconds < STING_SECONDS:            # a sting plays over the loops: a little hotter
        return orchestra.master(orchestra.hall(dry, rate), rate, hot_db=orchestra.STING_HOT_DB,
                                limit_db=orchestra.STING_LIMIT_DB), rate
    return orchestra.master(orchestra.hall(dry, rate), rate), rate


# --- the score critic: what a listener would notice, measured (I can't hear) ---
PERCUSSIVE = {"timpani", "taiko", "toms", "kit", "reverse_cymbal", "bells", "harp", "glockenspiel",
              "celesta", "pizzicato", *orchestra.PERC}  # (struck: playing a note again is normal)
DRUMS = {"timpani", "taiko", "toms", "kit", "reverse_cymbal", *orchestra.PERC}
ROLL_EVERY = 0.18          # seconds between a roll's strokes (about 5.5 a second: the host's pick)


def _where(ctx: Dict[str, Any], u: float) -> str:
    bar = ctx["tune"]["bar"]
    return "the intro" if u < 0 else f"bar {int(u // bar) + 1}"


def check(spec: Dict[str, Any], listen: bool = True) -> List[Tuple[str, str]]:
    """What's wrong with an arrangement, as [(level, finding)]: "error" (fix it),
    "warn" (very likely heard), "note" (a choice to confirm). ``listen``: also
    render it, to measure what's heard (the tune over the rest, the choir, a loop's
    seam): a few seconds."""
    written = spec                                   # (as written: a lead line keeps its "double")
    spec = expand_motifs(spec)
    ctx = _build(spec)
    sc, tune, T, unit = ctx["score"], ctx["tune"], ctx["T"], ctx["unit"]
    bar = tune["bar"]
    out: List[Tuple[str, str]] = []
    add = lambda level, msg: out.append((level, msg))          # noqa: E731
    # A falling bend on brass or low reeds is a raspberry: the host, on a corrupted
    # champion's boss fight whose trumpet stabs fell a fifth and whose trombone call slid
    # down: "it sounds like he farts". And a slide bends the whole part, chords and all.
    blown = {"trumpets", "trombones", "tuba", "horns", "horn_solo", "brass", "bassoons",
             orchestra.GUITAR_LEAD}                         # (and a lead guitar's falling bend)
    chorded = {h.get("part") for h in spec.get("harmony", [])}
    for line in spec.get("lines", []):
        bent = [n for n in line.get("notes", []) if len(n) > 4 and isinstance(n[-1], dict) and n[-1].get("slide")]
        falls = [n for n in bent if float(n[-1]["slide"]) <= -2]
        if line.get("part") in blown and falls and spec.get("role") != "comic":
            add("warn", f"{line['part']}: {len(falls)} note(s) bend down on brass, low reeds or the lead guitar - heard as comic "
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
    def snappy(part: str, a: float, b: float) -> bool:        # speaks at once: a quick instrument, or
        return (part not in orchestra.SPEAKS or orchestra.SPEAKS[part] < 0.1    # a string part's short
                or (part in orchestra.STRINGS_SHORT and b - a < orchestra.SHORT_S))   # note (its own recordings)
    quick = {(round(a, 3), k % 12) for part, got in by_part.items()
             for a, b, k in got if snappy(part, a, b)}                  # (a quick attack doubling it)
    for part, got in by_part.items():
        lo, hi = orchestra.RANGES.get(part, (0, 127))
        bad = [k for _, _, k in got if not lo <= k <= hi]
        if bad:
            add("error", f"{part}: {len(bad)} note(s) out of its range ({name_of(lo)}-{name_of(hi)}), "
                         f"e.g. {name_of(bad[0])}")
        speak = orchestra.SPEAKS.get(part)
        if speak:
            # (a string part's notes under SHORT_S play from its short-note recordings: they speak at once)
            stroke = orchestra.SHORT_S if part in orchestra.STRINGS_SHORT else 0.0
            short = [(a, b) for a, b, k in got if stroke <= b - a < 1.5 * speak and (round(a, 3), k % 12) not in quick]
            if short and len(short) >= 0.25 * len(got) and stroke:
                add("warn", f"{part}: {len(short)} of {len(got)} notes are shorter than it takes to speak "
                            f"({1.5 * speak:.2f}s) but too long for its short-note recordings (under {stroke:.2f}s: "
                            f"a crisp stroke that speaks at once): they sound at under half its level, smeared. "
                            f"Make them shorter than {stroke:.2f}s (a lower \"legato\"), give it held notes, or "
                            f"double them with a quick instrument")
            elif short and len(short) >= 0.25 * len(got):
                add("warn", f"{part}: {len(short)} of {len(got)} notes are shorter than it takes to speak "
                            f"({1.5 * speak:.2f}s): they sound at under half its level, smeared. Double "
                            f"them with a quick instrument (horns, trumpets, flutes, clarinets, bassoons, "
                            f"pizzicato), or give it held notes")
    # The same note started again while it still sounds (the second cuts the first).
    for name in notes:
        if name.partition(":")[0] in PERCUSSIVE or name.partition(":")[0] in orchestra.GUITAR:
            continue                                         # (a drum struck again, a string picked again)
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
    # The distorted guitar plays power chords: root, fifth, octave (a fourth: a fifth inverted).
    # A third, sixth, seventh or second through its amp turns to mud - the distortion's own
    # difference tones beat against the chord.
    struck: Dict[float, set] = {}
    for part in orchestra.GUITAR:
        if part == orchestra.GUITAR_LEAD:
            continue                                        # (the lead: single notes, its own amp)
        for a, b, k in by_part.get(part, []):
            struck.setdefault(round(a, 3), set()).add(k)
    muddy = sorted(t for t, ks in struck.items()
                   if any((y - x) % 12 not in (0, 5, 7) for x in ks for y in ks))
    if muddy:
        add("warn", f"guitar: {len(muddy)} chord(s) with a third, sixth, seventh or second (first at "
                    f"{muddy[0]:.1f} s) - through its distortion that turns to mud: power chords only "
                    "(\"play\": \"root5\", \"root\", \"octaves\"; root, fifth, octave)")
    # The lead guitar is one player: a note struck while another sounds cuts it (one voice).
    lead_on = sorted((a, b) for a, b, _ in by_part.get(orchestra.GUITAR_LEAD, []))
    cut = sum(1 for (a0, b0), (a1, _) in zip(lead_on, lead_on[1:]) if a1 < b0 - 0.05)
    if cut:
        add("warn", f"guitar_lead: {cut} note(s) start while another still sounds - the lead plays one "
                    "note at a time (a new note ends the last): a chord or a second voice is another part's")
    # The electric guitar is a special surprise, kept for a boss's later stages (the host: "electric
    # guitar will only be used on bosses' later stages. It is a special surprise"): a stage 2+ or a
    # cue of one ("stage": 2), never a theme, a place, a player's theme or a first stage.
    if any(by_part.get(part) for part in orchestra.GUITAR) and int(spec.get("stage", 1) or 1) < 2:
        add("warn", "guitar: the electric guitar is kept for a boss's later stages (a \"stage\" of 2 or "
                    "more, or a cue of one) - a special surprise, never a theme, a place or a first stage")
    # The rock organ is a rarer surprise still, held back for a boss's third stage (the host:
    # "rock organ sounds cool"): a stage 3+ or a cue of one ("stage": 3).
    if any(by_part.get(part) for part in orchestra.ORGAN) and int(spec.get("stage", 1) or 1) < 3:
        add("warn", "rock_organ: the rock organ is a rare surprise held back for a boss's third stage (a "
                    "\"stage\" of 3 or more, or a cue of one) - never a theme, a place or an earlier stage")
    # The tune: all played, and against its chords.
    melody = spec.get("melody") or []
    silent = [u0 for u0, _, _ in ctx["played"]
              if not any(float(m.get("from", ctx["start"])) - 1e-9 <= u0 < float(m.get("to", ctx["length"])) - 1e-9
                         and m.get("parts") for m in melody)]
    if silent:
        add("warn", f"the tune isn't played at {_where(ctx, silent[0])} ({len(silent)} notes): "
                    "no \"melody\" entry covers it")
    rubs = []
    fit, total = 0.0, 0.0                 # the tune's time on a chord tone (or a 9th / 6th colour)
    for u0, d, k in ctx["played"]:
        c = ctx["chord_at"](u0)
        if c is None:
            add("error", f"no chord at {_where(ctx, u0)}, under the tune")
            break
        total += d
        if k % 12 in c["pcs"] or (k - c["root"]) % 12 in (2, 9):
            fit += d
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
    # A loop with an entry (a boss stage's opening, played once): the stage change is itself
    # a climax - "after stage change the music should start strong" (the host); the research:
    # a transformation restarts the music in its new form, opening with a signature attack.
    # The checks below of how the piece grows look at the loop body only.
    # (a boss stage: "role": "stage" - or the older form, a battle loop with an entry. A
    # pre-end, a turn cue or a theme with a played-once intro is not a stage.)
    role = spec.get("role")
    is_stage = ctx.get("loop_from") is not None and (role == "stage" or (role == "battle" and ctx.get("loop_from")))
    entry_u = ctx["loop_from_u"] if is_stage else None
    if entry_u is not None:
        entry = [n for u, n, _ in layers if u < entry_u - 1e-9]
        layers = [x for x in layers if x[0] >= entry_u - 1e-9]
        body_peak = max((n for _, n, _ in layers), default=0)
        if entry and max(entry) < 0.75 * body_peak:
            add("warn", f"the entry (before loop_from) peaks at {max(entry)} parts, the loop at {body_peak}: "
                        "a stage's entry is the stage change's climax - start strong (most of the stage's "
                        "forces, its signature figure) - and keep that energy into the body (composing.md 4)")
        if entry and len(entry) > 4:
            add("note", f"the entry is {len(entry)} bars: it plays once, under the GM's narration of the "
                        "change - 1 to 4 bars is usual")
    # A boss stage's loop (an entry, then a body that loops; "role": "battle"): a table stage
    # runs 10 to 40 minutes, so the body is long - the research: 3-5 minutes, something new
    # every 8-16 bars - and the boss's tune is heard whole, as written, so the table knows
    # it (a leitmotif is recognised in a reprise far more easily than in a variation; the
    # host could not tell whether a stage 2 had stage 1's tune).
    if entry_u is not None and ctx["loop"]:
        body_s = ctx["seconds"] - (ctx["loop_from"] or 0)
        if body_s < 150:
            add("warn", f"the loop body is {body_s:.0f} s: a stage plays 10-40 minutes - 150 s at least "
                        "(3-5 min is the research's length), with something new every 8-16 bars")
        t = spec.get("tune") or {}
        has_tune = isinstance(t, dict) and (t.get("written") or (t.get("seed") and t.get("seed") != "sketch"))
        if ctx["played"] or has_tune:
            whole = [x for x in ctx["statements"] if float(x.get("from", 0)) <= 1e-9 and
                     float(x.get("at", 0)) >= entry_u - 1e-9 and
                     float(x.get("to", ctx["tune_len"])) >= ctx["tune_len"] - 1e-9]
            if not whole:
                add("warn", "the loop body never states the boss's tune whole, as written (a statement from "
                            "its start to its end; a new key or register is fine): the table can't learn it "
                            "from fragments and variants alone")
    # A climax needs something to arrive: if the piece already plays at nearly its full
    # texture from the start, its peak adds nothing (the host, of the Ashen Saint's second
    # stage - 16-19 parts from bar 1, 20 at the "climax": "a climax without the climax").
    if len(layers) >= 8 and role not in ("pre_end", "turn", "place"):   # (steady by design)
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
        if entry_u is not None and len(before) >= 4:
            def heard(u0: float, u1: float):
                ps, top = set(), 0
                a_s, b_s = T(u0), T(u1)
                for t, on, name, key, _ in sc.events:
                    if on and a_s - 1e-6 <= t < b_s - 1e-6:
                        ps.add(name.partition(":")[0])
                        top = max(top, key)
                return ps, top
            u_pk = layers[peak_i][0]
            # the body's opening: 16 bars, but at most its first 30 s and never into the
            # peak's own bars (at a slow tempo 16 bars ran to 110 s, so the peak had to
            # wait behind 40 s of filler before the critic would believe it)
            u0 = layers[0][0]
            u1 = u0 + 16 * bar
            if T(u1) - T(u0) > 30:
                u1 = u0 + 16 * bar * 30 / (T(u1) - T(u0))
            open_ps, open_top = heard(u0, min(u1, u_pk - 2 * bar))
            pk_ps, pk_top = heard(u_pk - 2 * bar, u_pk + 2 * bar)
            if not (pk_ps - open_ps) and pk_top <= open_top:
                add("warn", f"the peak ({_where(ctx, u_pk)}) brings nothing the body's opening didn't have: "
                            "save a part or a register for it (the open choir, full brass, the top octave, "
                            "the tune's grandest setting) - the host: \"a climax without the climax\"")
        elif len(before) >= 4:
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
            add("warn", f"a join at {_where(ctx, u0)}: {', '.join(stopped) or 'nothing'} stop as "
                        f"{', '.join(started)} start - heard as another piece glued on. Carry a layer "
                        "or two across it and build the bars before it")
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
    if host_checks:
        # The sound set's strengths, blended (the host, of Kestrel's theme: "a weak start and
        # weaker instruments, and weaker combination"): its brass and low reeds are its weakest
        # recordings exposed - judged at each tune note, by everything carrying it there.
        exposed = {"horns", "trumpets", "trombones", "tuba", "brass", "bassoons"}
        alone = []
        for u0, _, _ in ctx["played"]:
            carriers = {pt for m in spec.get("melody") or []
                        if float(m.get("from", ctx["start"])) - 1e-9 <= u0 < float(m.get("to", ctx["length"])) - 1e-9
                        for pt in (m.get("parts") or {})}
            if carriers and carriers <= exposed:
                alone.append((u0, carriers))
        if alone:
            parts = sorted(set().union(*(c for _, c in alone)))
            add("warn", f"the tune is on {' + '.join(parts)} alone at {_where(ctx, alone[0][0])} "
                        f"({len(alone)} notes): this sound set's brass and low reeds are its weakest "
                        "recordings exposed - blend them (horns + violins, bassoons + cellos) or give "
                        "the tune to strings or woods (rule 13)")
        for l in written.get("lines") or []:
            if isinstance(l, dict) and l.get("lead") and l.get("part") in exposed and not any(
                    isinstance(d, dict) and d.get("part") not in exposed for d in l.get("double") or []):
                add("warn", f"the lead line on {l.get('part')} is exposed: double it with strings or woods "
                            "(rule 13)")
    if host_checks:
        # Played notes per part (base part name: a tune's carrier is "part:..."), from the score.
        held: Dict[Tuple[str, int], List[Tuple[float, float]]] = {}
        played_notes: List[Tuple[str, float, float]] = []
        men_high: List[Tuple[float, int]] = []
        for t, on, part, key, vel in sorted(sc.events, key=lambda e: (e[0], -e[1])):
            base = part.split(":")[0]
            if on:
                held.setdefault((base, key), []).append((t, vel))
            elif held.get((base, key)):
                t0, _ = held[(base, key)].pop(0)
                played_notes.append((base, t0, t - t0))
                if base == "men_choir" and key > 64:
                    men_high.append((t0, key))
        # A sampled choir can't change notes fast: the host, of a hymn sung on eighth notes at
        # 126 ("the choir cannot do fast changes, they sound like an instrument"). Measured: that
        # piece changed notes 156 times in under 0.5 s; every liked piece held each note 0.7 s+.
        # And the men's choir again, of a hook sung at 0.56 s a note: "the men choir cannot do fast
        # changes" - the choirs the host accepted never moved faster than 0.71 s.
        for part in ("choir", "chorus", "men_choir", "choir_oo", "choir_oh"):
            ons = sorted({round(t0, 3) for b, t0, _ in played_notes if b == part})
            quick = [b for a, b in zip(ons, ons[1:]) if b - a < 0.7]
            if quick:
                add("warn", f"the {part} changes notes {len(quick)} time(s) in under 0.7 s (first at "
                            f"{quick[0]:.1f} s): a sampled choir can't sing that fast - it sounds like an "
                            "instrument. Keep the voices on notes of 0.7 s or more (the tune's long notes, "
                            "held chords) and give the quick notes to strings or woods (rule 13)")
        # The men's choir's top sounds like an instrument (the host, of a men's choir rising to F4-G#4;
        # one that stayed at D#4 and below drew no complaint).
        if men_high:
            add("warn", f"the men_choir sings above E4 {len(men_high)} time(s) (first at {min(men_high)[0]:.1f} s, up to "
                        f"{NAMES[max(k for _, k in men_high) % 12]}{max(k for _, k in men_high) // 12 - 1}): its top "
                        "sounds like an instrument (host) - keep it at E4 and below, and take a rising line "
                        "higher on the `chorus`")

        # Brass stabs: the host, of a stage with ~45 short brass-section stabs a minute: "the
        # trumpets are too jarring". Liked pieces used a few (Kestrel's trumpets: 6 notes, saved
        # for the climb). This sound set's brass is harsh when it stabs over and over.
        stabs = [t0 for b, t0, d in played_notes if b in ("brass", "trumpets") and d < 0.35]
        per_min = len(stabs) / max(ctx["seconds"] / 60.0, 1e-9)
        if len(stabs) >= 12 and per_min > 15:
            add("warn", f"{len(stabs)} short brass/trumpet stabs ({per_min:.0f} a minute, from {stabs[0]:.1f} s): "
                        "this sound set's brass is jarring in repeated short stabs (host). Use a few, "
                        "held longer, or give the hits to low strings, timpani and trombones blended")
    if host_checks:
        # Dissonance is a spice, not a bed: the host, of a stage with a semitone clash sounding 97%
        # of the time ("terrible... painful to hear"); the liked pieces sound one 11-21% of the time.
        perc = {"timpani", "kit", "taiko", "toms", "cymbal", "gong", "bells", "glockenspiel", "triangle",
                *orchestra.PERC}
        sounding: Dict[Tuple[str, int], int] = {}   # a count: a re-struck held note overlaps itself
        t_prev, clash_t, total = 0.0, 0.0, 0.0
        for t, on, part, key, vel in sorted(sc.events, key=lambda e: (e[0], -e[1])):
            if t > t_prev:
                ks = sorted({k for (pt, k), c in sounding.items() if c > 0 and pt.split(":")[0] not in perc})
                if ks:
                    total += t - t_prev
                    if any(b - a in (1, 13, 25) for i, a in enumerate(ks) for b in ks[i + 1:]):
                        clash_t += t - t_prev
            t_prev = t
            sounding[(part, key)] = sounding.get((part, key), 0) + (1 if on else -1)
        if total > 0 and clash_t / total > 0.4:
            add("warn", f"a semitone (or minor-ninth) clash sounds {clash_t / total:.0%} of the time: constant "
                        "dissonance is painful to sit through (host; the liked pieces: 11-21%) - keep the "
                        "grind for cadences, cracks and the peak, over chords that otherwise sound clean")
    if not listen:
        return out
    # Listening: render the layers apart and measure them.
    import numpy as np
    rate = 22050
    mix = spec.get("mix") or {}

    # A line marked "lead": true is a tune too (an ally's phrase written as a motif line):
    # measured against the rest like the tune's own statements.
    lead_lines = [l for l in expand_motifs(spec).get("lines") or [] if isinstance(l, dict) and l.get("lead")]
    lead_parts = {l.get("part") for l in lead_lines}
    voices = ("choir", "chorus", "men_choir", "choir_oo", "choir_oh")

    def which(n: str) -> str:
        return "lead" if ":" in n or n in lead_parts else "choir" if n in voices else "rest"

    heard = orchestra.play_layers(sc, ctx["seconds"], which, rate=rate, mix=mix, send=False)
    silent = np.zeros(int((ctx["seconds"] + 0.5) * rate), dtype="float32")
    lead, choir, rest = (np.asarray(heard[k]).mean(axis=1) if k in heard else silent
                         for k in ("lead", "choir", "rest"))

    def db(x) -> float:
        return float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)) if len(x) else -240.0

    for mi, m in enumerate(melody):
        a, b = float(m.get("from", ctx["start"])), float(m.get("to", ctx["length"]))
        i, j = int(T(a) * rate), int(T(min(b, ctx["length"])) * rate)
        if j - i < rate // 2 or db(lead[i:j]) < -200:
            continue
        gap = db(lead[i:j]) - db(rest[i:j])
        if gap < -2:
            add("error", f"the tune is buried at {_where(ctx, a)}-{_where(ctx, b - 1e-6)}: {gap:+.0f} dB "
                         f"under the rest (give melody entry #{mi} \"gain\": {round(3 - gap) + float(m.get('gain', 0)):g})")
        elif gap < 1:
            add("warn", f"the tune is barely over the rest at {_where(ctx, a)}-{_where(ctx, b - 1e-6)}: "
                        f"{gap:+.0f} dB (melody entry #{mi} \"gain\": {round(3 - gap) + float(m.get('gain', 0)):g} would put it at +3)")
    for li, raw in enumerate(written.get("lines") or []):
        if not (isinstance(raw, dict) and raw.get("lead")):
            continue
        l = expand_motifs({**written, "lines": [{k: v for k, v in raw.items() if k != "double"}]})["lines"][0]
        ns = l.get("notes") or []
        if not ns:
            continue
        a, b = min(float(n[0]) for n in ns), max(float(n[0]) + float(n[2]) for n in ns)
        i, j = int(T(a) * rate), int(T(min(b, ctx["length"])) * rate)
        if j - i < rate // 2 or db(lead[i:j]) < -200:
            continue
        gap = db(lead[i:j]) - db(rest[i:j])
        if gap < 1:
            add("warn", f"the lead line ({l.get('part')}) at {_where(ctx, a)}-{_where(ctx, b - 1e-6)} is "
                        f"{gap:+.0f} dB over the rest (lead line #{li} \"gain\": "
                        f"{round(3 - gap) + float(raw.get('gain', 0)):g} would put it at +3; or thin what's under it)")
    # A theme grows every phrase up to its peak (the host: "all the new themes feel a bit
    # repetitive"; measured, the liked one never held still more than ~6 s - parts joining,
    # the level rising - while the weaker one sat 20 s on the same six parts at one level).
    if spec.get("role") == "theme" and not ctx["loop"]:
        full = lead + choir + rest
        win = 2 * rate
        lv = [db(full[i:i + win]) for i in range(0, len(full) - win + 1, win)]
        if lv:
            peak = int(np.argmax(lv))
            active = [set() for _ in lv]
            onset: Dict[Tuple[str, int], float] = {}
            for t, is_on, name, key, _ in sorted(sc.events, key=lambda e: (e[0], e[1])):
                part = name.partition(":")[0]
                if is_on == 1:
                    onset[(part, key)] = t
                elif is_on == 0 and (part, key) in onset:
                    a = onset.pop((part, key))
                    for w in range(int(a // 2), min(len(lv), int(t // 2) + 1)):
                        active[w].add(part)
            start, worst = None, (0, 0)
            for j in range(peak + 1):
                if lv[j] < -60:                                 # (silence before it starts)
                    start = None
                    continue
                if start is None or len(active[j] - active[start]) > 0 or lv[j] >= lv[start] + 2:
                    start = j
                if (j - start + 1) > worst[1] - worst[0]:
                    worst = (start, j + 1)
            secs = 2 * (worst[1] - worst[0])
            if secs >= 10:
                add("warn", f"the theme holds still for {secs} s before its peak ({worst[0] * 2}-{worst[1] * 2} s: "
                            f"no part joins, the level rises under 2 dB) - grow every phrase: a carrier or a "
                            f"layer joins, or the level climbs (rule 10)")
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
        lf = float(ctx.get("loop_from") or 0)
        m = int(lf * rate)                                  # where it loops back to
        q = rate                                            # (a second each side: a downbeat isn't a step)
        if m:
            # Heard on a repeat, the body's start follows the loop's end - not the entry,
            # whose ff still rings in the first pass: play the body's opening alone.
            first = orchestra.Score()
            first.events = [(t - lf, *e) for t, *e in sc.events if lf - 1e-6 <= t < lf + 1.0]
            opening = orchestra.play(first, 1.0, rate=rate, mix=mix).mean(axis=1)[:q]
        else:
            opening = full[:q]
        start = opening.copy()
        start[:len(tail[:q])] += tail[:q]                   # (the end's ring, wrapped over it)
        end = db(full[n - q:n])
        step = db(start) - end
        if end < -120 and db(start) > -120:
            add("warn", "the loop's seam: its last second is silent, then the start comes in - carry the "
                        "music to the end, into a swell, roll or pickup")
        elif step > 4 or step < -4:
            add("warn", f"the loop's seam steps {step:+.0f} dB (end -> start, as heard on a repeat): "
                        + ("swell into it - a crescendo, a roll or a pickup in the last bar" if step > 0
                           else "the end is louder than where it loops back to: let the end settle, or "
                                "start the body stronger"))
    # A stage's body keeps its entry's energy: the host, of bodies that fell 9-11 dB right
    # after the entry, "it dies after the transformation".
    if is_stage:
        full = lead + choir + rest
        m = int(ctx["loop_from"] * rate)
        after = full[m:m + int(min(12.0, ctx["seconds"] - ctx["loop_from"]) * rate)]
        drop = db(full[:m]) - db(after)
        if m > rate // 2 and len(after) > rate and drop > 4:
            add("warn", f"the body falls {drop:.0f} dB right after the entry: the music dies after the stage "
                        "change. Open the body on the full drive (within about 3 dB of the entry); put the "
                        "dip later (a breakdown a third to halfway through)")
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


def fix(spec: Dict[str, Any], listen: bool = True,
        found: Optional[List[Tuple[str, str]]] = None) -> Tuple[Dict[str, Any], List[str]]:
    """The critic's mechanical fixes, applied: notes moved by octaves into their
    instrument's range (a whole line or placement if one shift fits, else note by note),
    harmony ranges kept inside the instrument's, a quick doubling for a slow-speaking
    line's short notes, the choir's level, the tune's level (a melody entry's "gain"), a
    lead line's level. Musical decisions (too many parts entering at once, a loop's seam)
    are left to the composer."""
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
    for level, msg in (found if found is not None else check(s, listen=listen)):
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
        m = re.search(r'melody entry #(\d+) "gain": (-?[\d.]+)', msg)
        if m and int(m.group(1)) < len(s.get("melody") or []):
            entry = s["melody"][int(m.group(1))]
            if float(entry.get("gain", 0)) < float(m.group(2)):
                entry["gain"] = float(m.group(2))
                changes.append(f"melody entry #{m.group(1)}: \"gain\" {m.group(2)} (the tune on top, +3 dB)")
            continue
        m = re.search(r'lead line #(\d+) "gain": (-?[\d.]+)', msg)
        if m and int(m.group(1)) < len(s.get("lines") or []):
            line = s["lines"][int(m.group(1))]
            if float(line.get("gain", 0)) < float(m.group(2)):
                line["gain"] = float(m.group(2))
                changes.append(f"lead line #{m.group(1)} ({line.get('part')}): \"gain\" {m.group(2)} (on top, +3 dB)")
            continue
    return s, changes


def describe(seed: str, mode: str = "major", cls: str = "", stage: int = 1, dark: int = 0,
             gen: int = 1, written: Optional[Dict[str, Any]] = None, key: Optional[str] = None) -> str:
    """The tune, for writing an arrangement: its key, meter, and every note with its time
    (``key``: moved there, as a score's ``"tune": {"key": ...}`` moves it)."""
    tune = music_compose.leitmotif(seed, mode, cls, stage=stage, dark=dark, gen=gen, written=written)
    if key:
        tune = {**tune, "key": pitch(key)}
    h0, hn = tune.get("hook") or (0, 0)
    bar = tune["bar"]
    made = "written" if written else f"{mode}{', ' + cls if cls else ''}, stage {stage}, dark {dark}"
    lines = [f"{seed} ({made}): "
             f"tonic {name_of(tune['key'])}, {tune['meter']} ({'eighths' if tune['meter'] == '6/8' else 'beats'}), "
             f"{tune['scale'] if isinstance(tune['scale'], str) else 'scale ' + str(tune['scale'])}, "
             f"{tune['kind']}, {sum(b for _, b in tune['notes']):g} units = "
             f"{sum(b for _, b in tune['notes']) / bar:g} bars",
             "at      bar.pos  note   units"]
    pick = float(tune.get("pickup") or 0)
    if pick:
        lines.insert(1, f"bars count from the first downbeat, as in `grid` (bar 0: the {pick:g}-unit pickup); "
                        f"a statement at unit (N-1)*{bar:g} - {pick:g} puts the tune's bar k on bar N+k-1")
    u = 0.0
    for i, (st, b) in enumerate(tune["notes"]):
        v = u - pick
        hook = "  (the hook)" if h0 <= i < h0 + hn else ""
        lines.append(f"{u:<7g} {int(v // bar) + 1:>3}.{v % bar:<4g} {name_of(tune['key'] + st):<6} {b:g}{hook}")
        u += b
    lines.append("chords that hold each bar's main notes (a menu, not an answer - chromatic ones included):")
    lines += [f"  {label}: {' '.join(cs)}" for label, cs in fitting_chords(tune)]
    return "\n".join(lines)


def grid(tune: Dict[str, Any], tempo: float, entry_bars: int = 0, body_seconds: float = 150.0,
         section_bars: int = 8) -> str:
    """The arithmetic of a piece, done for the composer: the bar grid in units and seconds,
    the tune's length in bars, where to place a whole statement so its first downbeat lands
    on a bar line (after its pickup), the entry, and a body long enough - in whole sections.
    (Two benchmark composers spent about half their time thinking before writing a note,
    much of it beat arithmetic.)"""
    bar = float(tune["bar"])
    beat = 3 if tune["meter"] == "6/8" else 1
    unit_s = 60.0 / tempo / beat
    bar_s = bar * unit_s
    pick = float(tune.get("pickup") or 0)
    tune_u = sum(b for _, b in tune["notes"])
    tune_bars = (tune_u - pick) / bar
    body_bars = int(-(-body_seconds // bar_s))
    body_bars = int(-(-body_bars // section_bars) * section_bars)          # whole sections
    lines = [f"{tune['meter']} at {tempo:g}: 1 unit = {unit_s:.3f} s, 1 bar = {bar:g} units = {bar_s:.2f} s",
             f"the tune: {tune_u:g} units ({pick:g} pickup + {tune_bars:g} bars); a whole statement lasts "
             f"{tune_u * unit_s:.1f} s",
             f"to land its first downbeat on bar N of the body, place it at unit (N-1)*{bar:g} - {pick:g}"]
    if entry_bars:
        lines.append(f"entry: {entry_bars} bars = units {-entry_bars * bar:g} to 0 ({entry_bars * bar_s:.1f} s): "
                     f"\"start\": {-entry_bars * bar:g}, \"loop\": true, \"loop_from\": 0")
    lines.append(f"body: {body_bars} bars = units 0 to {body_bars * bar:g} = {body_bars * bar_s:.1f} s "
                 f"(at least {body_seconds:g} s, whole {section_bars}-bar sections): \"length\": {body_bars * bar:g}")
    third, half, peak = round(body_bars / 3), round(body_bars / 2), round(body_bars * 0.75)
    lines.append(f"the breakdown a third to halfway through: bars {third + 1}-{half}; the peak about bar "
                 f"{peak + 1} (units {peak * bar:g}, {peak * bar_s:.0f} s into the body)")
    lines.append(f"sections ({section_bars} bars each): bar  units  seconds   | a whole statement placed to start here")
    for k in range(0, body_bars, section_bars):
        at = k * bar - pick
        fits = at + tune_u <= body_bars * bar + 1e-9 and at >= -pick
        lines.append(f"  bar {k + 1:>3}  {k * bar:>6g}  {k * bar_s:>6.1f}   | "
                     + (f"\"at\": {at:g} -> bars {k + 1}-{k + int(-(-tune_bars // 1))}" if fits else "(runs past the end)"))
    return "\n".join(lines)


def fitting_chords(tune: Dict[str, Any]) -> List[Tuple[str, List[str]]]:
    """For each bar of the tune, every chord in a wide palette (diatonic, borrowed and
    chromatic-mediant) that holds the bar's main notes (the long and strong ones) - a menu
    for a composer, never one answer: a single suggestion would steer every piece to the
    plain choice (the host: "won't the suggested chord hurt creativity?"). -> [(label, chords)]:
    "pickup", then "bar 1" from the first downbeat (the bars `grid` counts)."""
    palette = ["i", "I", "ii", "iiø", "bII", "III", "bIII", "iv", "IV", "v", "V", "vi", "bVI",
               "VI", "bVII", "vii°"]
    bar, key = tune["bar"], tune["key"]
    pick = float(tune.get("pickup") or 0)
    weight: Dict[int, Dict[int, float]] = {}
    v = -pick
    for st, b in tune["notes"]:
        strong = 1.5 if abs(v % bar) < 1e-6 else 1.0
        w = weight.setdefault(int(v // bar), {})          # (-1: the pickup)
        w[(key + st) % 12] = w.get((key + st) % 12, 0.0) + b * strong
        v += b
    out = []
    for bi in range(-1 if pick else 0, int(-(-v // bar))):
        w = weight.get(bi) or {}
        total = sum(w.values()) or 1.0
        held = [(sum(x for pc, x in w.items() if pc in chord(c, key)["pcs"]) / total, c) for c in palette]
        out.append(("pickup" if bi < 0 else f"bar {bi + 1}",
                    [c for f, c in sorted(held, key=lambda x: -x[0]) if f >= 0.7] or ["(passing notes: any)"]))
    return out


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
    t.add_argument("--key", help="show it moved to this tonic (e.g. F4), as the score's tune \"key\" moves it")
    p = sub.add_parser("play", help="play an arrangement (a JSON file)")
    p.add_argument("file")
    p.add_argument("--out", required=True)
    c = sub.add_parser("check", help="the score critic: what a listener would notice")
    c.add_argument("file")
    c.add_argument("--quick", action="store_true", help="read the score only (don't render it)")
    gr = sub.add_parser("grid", help="the arithmetic of a piece: the bar grid in units and seconds, "
                                     "where whole statements land, the entry and body lengths")
    gr.add_argument("seed")
    gr.add_argument("--written", required=True, help="the tune file (music/tunes/<who>.json)")
    gr.add_argument("--tempo", type=float, required=True)
    gr.add_argument("--entry", type=int, default=0, help="entry bars (a boss stage)")
    gr.add_argument("--body", type=float, default=150.0, help="body seconds at least (a stage: 150)")
    gr.add_argument("--section", type=int, default=8, help="bars per section")
    mk = sub.add_parser("make", help="the whole loop in one: apply the mechanical fixes, run the critic, "
                                     "and render when nothing is left but notes")
    mk.add_argument("file")
    mk.add_argument("--out", help="the audio file to write (default: next to the score, .ogg)")
    fx = sub.add_parser("fix", help="apply the critic's mechanical fixes (ranges, quick doublings, "
                                    "the choir's level, a loop's seam), then check again")
    fx.add_argument("file")
    fx.add_argument("--out", help="write the fixed score here (default: in place)")
    fx.add_argument("--quick", action="store_true", help="read the score only (don't render it)")
    a = ap.parse_args()
    if a.cmd == "tune":
        written = json.loads(Path(a.written).read_text(encoding="utf-8")) if a.written else None
        print(describe(a.seed, "minor" if a.minor else "major", a.cls, a.stage, a.dark, a.gen, written, a.key))
        return
    if a.cmd == "grid":
        written = json.loads(Path(a.written).read_text(encoding="utf-8"))
        tune = music_compose.leitmotif(a.seed, "major", "", written=written)
        print(grid(tune, a.tempo, a.entry, a.body, a.section))
        return
    if a.cmd == "make":
        import time as _time
        t0 = _time.time()
        path = Path(a.file)
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
            # The score alone first (seconds): a range, a doubling, a missing chord... are
            # reported before the slow part - listening to the layers, then the render.
            quick = check(spec, listen=False)
            fixed, changes = fix(spec, listen=False, found=quick)
            quick = check(fixed, listen=False) if changes else quick
            if any(lv in ("error", "warn") for lv, _ in quick):
                found = quick
            else:
                found = check(fixed)
                more_fixed, more = fix(fixed, found=found)
                if more:
                    fixed, changes = more_fixed, changes + more
                    found = check(fixed)
            if changes:
                path.write_text(json.dumps(fixed, indent=1, ensure_ascii=False), encoding="utf-8")
        except (ArrangementError, KeyError, TypeError, ValueError) as e:
            sys.exit(f"[arrangement] {a.file}: {e}")
        for c in changes:
            print(f"FIXED {c}")
        for level, msg in found:
            print(f"{level.upper():5} {msg}")
        errs, warns = (sum(lv == k for lv, _ in found) for k in ("error", "warn"))
        print(f"{len(changes)} fix(es); {errs} error(s), {warns} warning(s), "
              f"{sum(lv == 'note' for lv, _ in found)} note(s)")
        if errs or warns:
            sys.exit(f"not rendered: fix the error(s) and warning(s) above, then make again "
                     f"({_time.time() - t0:.0f} s)")
        samples, rate = render(fixed)
        out = Path(a.out) if a.out else path.with_suffix(".ogg")
        landing = None if fixed.get("loop") else int(round(build(fixed)[1] * rate))
        made = music_compose.write(samples, rate, out, loop_start=loop_start(fixed, rate), landing=landing)
        print(f"MADE {made} ({len(samples) / rate:.1f}s{', a loop' if fixed.get('loop') else ''}"
              f"{f', loops from {loop_start(fixed, rate) / rate:.2f}s' if loop_start(fixed, rate) else ''}) "
              f"in {_time.time() - t0:.0f} s")
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
    landing = None if spec.get("loop") else int(round(build(spec)[1] * rate))   # (a sting: where it lands)
    path = music_compose.write(samples, rate, Path(a.out), loop_start=loop_start(spec, rate), landing=landing)
    print(f"{path} ({len(samples) / rate:.1f}s{', a loop' if spec.get('loop') else ''})")


if __name__ == "__main__":
    main()
