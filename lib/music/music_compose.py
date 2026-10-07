#!/usr/bin/env python3
"""Tunes, and the audio helpers the orchestra's pieces go through.

A character's leitmotif (``leitmotif``: a tune from their name and class, built the
way film themes are) and the GM's hand-written tunes (``written_tune``), which the
orchestra (orchestra.py, arrangement.py) plays; and the helpers a rendered piece
goes through: loudness (``normalize``, ``limit``), soft edges (``fade``), and
``write`` (OGG, with its loop point). Nothing here needs more than numpy and
soundfile.

    python lib/music_compose.py --normalize a.ogg b.ogg     # bring pieces up to volume
    python lib/music_compose.py --leitmotif NAME --class Fighter --out DIR
                                                            # a leitmotif as a plain melody
"""

import argparse
import json
import os
from pathlib import Path
from typing import Optional

# How loud a finished piece is (gated RMS, dBFS: close to LUFS for music); -14
# matches what music services play at.
LOUDNESS_DB = float(os.environ.get("COMPOSE_LOUDNESS", "-14"))
CEILING = 0.89                  # -1 dBFS: headroom for the OGG encoder
MAX_GAIN_DB = 30                # never blow near-silence up into hiss

def fade(samples, rate: int, fade_in: float, fade_out: float):
    """Soft edges, so a looping theme has no click at its seam."""
    import numpy as np
    out = np.array(samples, dtype="float32", copy=True)
    n_in = min(len(out), int(rate * fade_in))
    n_out = min(len(out), int(rate * fade_out))
    if n_in:
        out[:n_in] *= np.linspace(0.0, 1.0, n_in, dtype="float32")
    if n_out:
        out[-n_out:] *= np.linspace(1.0, 0.0, n_out, dtype="float32")
    peak = float(np.max(np.abs(out))) if len(out) else 0.0
    if peak > 0.98:
        out *= 0.98 / peak
    return out


def loudness_db(samples, rate: int) -> float:
    """Gated loudness: the RMS of the 400 ms blocks that aren't silence (as in
    EBU R128, without its frequency weighting). -inf for silence."""
    import numpy as np
    x = np.asarray(samples, dtype="float64")
    block = max(1, int(rate * 0.4))
    if len(x) <= block:
        energy = np.array([float(np.mean(x ** 2)) if len(x) else 0.0])
    else:
        c = np.concatenate([[0.0], np.cumsum(x ** 2)])
        starts = np.arange(0, len(x) - block + 1, max(1, block // 4))
        energy = (c[starts + block] - c[starts]) / block
    energy = energy[energy > 1e-7]                       # absolute gate: -70 dB
    if not len(energy):
        return float("-inf")
    energy = energy[energy > energy.mean() * 0.1]        # relative gate: -10 dB
    return float(10 * np.log10(energy.mean()))


def limit(samples, rate: int, ceiling: float = CEILING):
    """A look-ahead peak limiter: turns the loudest moments down smoothly so no
    sample passes ``ceiling`` (no clipping, no harsh distortion)."""
    import numpy as np
    x = np.asarray(samples, dtype="float32")
    if not len(x) or float(np.max(np.abs(x))) <= ceiling:
        return x
    blk = max(1, int(rate * 0.01))                       # 10 ms blocks
    n = -(-len(x) // blk)
    need = np.ones(n * blk, dtype="float32")
    amp = np.abs(x)
    need[:len(x)] = np.where(amp > ceiling, ceiling / np.maximum(amp, 1e-9), 1.0)
    g = need.reshape(n, blk).min(axis=1)
    g = np.minimum(g, np.minimum(np.r_[g[1:], 1.0], np.r_[1.0, g[:-1]]))   # start early
    release = 1 - np.exp(-1 / (0.15 / 0.01))             # recover over ~150 ms
    for i in range(1, n):
        g[i] = min(g[i], g[i - 1] + (1 - g[i - 1]) * release)
    gain = np.interp(np.arange(len(x)), np.arange(n) * blk + blk / 2, g).astype("float32")
    return np.clip(x * gain, -ceiling, ceiling)


def normalize(samples, rate: int, target_db: float = LOUDNESS_DB):
    """Bring a piece to ``target_db`` loudness (up or down), then limit its peaks."""
    import numpy as np
    x = np.asarray(samples, dtype="float32")
    now = loudness_db(x, rate)
    if now == float("-inf"):
        return x.copy()
    gain_db = min(target_db - now, MAX_GAIN_DB)
    return limit(x * np.float32(10 ** (gain_db / 20)), rate)


def finish(samples, rate: int, loop: bool):
    """Loudness, then soft edges: a looping theme fades at both ends (no click at the
    seam); a piece that ends (an anthem) keeps its final chord, with a short tail."""
    return fade(normalize(samples, rate), rate, 0.4 if loop else 0.05, 1.5 if loop else 0.4)


def heavy(samples, rate: int, bass_db: float = 6.0, bass_below: float = 150.0,
          treble_db: float = -3.0, treble_above: float = 3000.0):
    """A villain's weight: the deep bass
    up (a smooth shelf below ``bass_below``), the highs softened, the rumble under
    25 Hz cut. Zero-phase, on the whole piece (a loop stays seamless)."""
    import numpy as np
    x = np.asarray(samples, dtype="float64")
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / rate)
    gain_db = (bass_db / (1 + (f / bass_below) ** 4)
               + treble_db * (f / treble_above) ** 4 / (1 + (f / treble_above) ** 4))
    rumble = (f / 25.0) ** 8 / (1 + (f / 25.0) ** 8)                   # (steep: 40 Hz keeps 98%)
    return np.fft.irfft(spec * 10 ** (gain_db / 20) * rumble, len(x)).astype("float32")


def crescendo(samples, rate: int, peak_at: float, depth_db: float = 7.0):
    """The build: from ``depth_db`` quieter at the start, swelling (smoothly) to full
    at ``peak_at`` (a fraction of the piece: the tune's climax), then full to the end."""
    import numpy as np
    x = np.asarray(samples, dtype="float32")
    t = np.linspace(0.0, 1.0, len(x), dtype="float64")
    p = np.clip(t / max(peak_at, 1e-3), 0.0, 1.0)
    ramp = p * p * (3 - 2 * p)                                 # smoothstep: no sudden swell
    return (x * 10 ** (-depth_db * (1 - ramp) / 20)).astype("float32")


# --- a character's leitmotif: a tune of their own ---
# Each character gets a motif from their name (always the same) and their class,
# built the way film themes are, laid out as a phrase that goes somewhere; their
# dark twin is the same tune turned villainous.
#
# Heroes' themes come in kinds, with a meter and a mode, as film composers use them:
#   fanfare  - a pickup into a leap up (a 5th, 6th or octave), stepping back down
#              in a fanfare rhythm (Star Wars, Superman)
#   ostinato - a driving repeated note, then the leap (Pirates, Avengers)
#   soaring  - a stepwise rise to a long high note and a turn above it (E.T.)
#   bugle    - a call up the chord (Indiana Jones, Jurassic Park)
#   hymn     - a noble stepwise line (a paladin's or a cleric's)
# in 4/4 (a march), 3/4 or 6/8 (lilting), and major, Lydian (wonder, magic: a
# raised 4th), Mixolydian (folk, roguish: a flat 7th) or Dorian (earthy). Each
# phrase: the motif; the motif again (a step or a third higher, or answered); a
# climb to the climax (a held chord tone, the highest note) about two-thirds in;
# the motif's head home to the tonic, held to the bar line.
#
# Villains' (the Imperial March, Jaws, Mordor): the same tune in the minor (or
# Phrygian, or harmonic minor), its pickup a march of repeated notes, each phrase
# ending on a half-step sigh (minor 6th to 5th), a tritone before the climax, and
# the last phrase falling home through the minor 2nd.
import math  # noqa: E402

T = 1 / 3                                                   # a triplet's share of a beat
MODES = {"ionian": [0, 2, 4, 5, 7, 9, 11], "lydian": [0, 2, 4, 6, 7, 9, 11],
         "mixolydian": [0, 2, 4, 5, 7, 9, 10], "dorian": [0, 2, 3, 5, 7, 9, 10]}
DARK = {"aeolian": [0, 2, 3, 5, 7, 8, 10], "phrygian": [0, 1, 3, 5, 7, 8, 10],
        "harmonic": [0, 2, 3, 5, 7, 8, 11]}
METERS = {"4/4": 4, "3/4": 3, "6/8": 6}                     # a bar, in units (6/8: eighths)
FIGS = {"4/4": [[.75, .25], [T, T, T], [.5, .5]], "3/4": [[.75, .25], [.5, .5], [T, T, T]],
        "6/8": [[2, 1], [1, 1, 1], [1.5, .5, 1]]}
LONG = {"4/4": [2, 1.5, 3], "3/4": [2, 1.5], "6/8": [3, 4, 5]}
KINDS = ["fanfare", "ostinato", "soaring", "bugle", "hymn"]
STYLES = {                                                   # class -> (kinds, meters, modes)
    "fighter": (["fanfare", "bugle"], ["4/4"], ["ionian"]),
    "paladin": (["fanfare", "hymn"], ["4/4", "3/4"], ["ionian"]),
    "barbarian": (["ostinato"], ["4/4", "6/8"], ["dorian", "mixolydian"]),
    "rogue": (["ostinato", "soaring"], ["6/8"], ["mixolydian", "dorian"]),
    "bard": (["soaring", "bugle"], ["6/8", "3/4"], ["mixolydian", "ionian"]),
    "wizard": (["soaring", "bugle"], ["3/4", "4/4"], ["lydian"]),
    "sorcerer": (["soaring", "fanfare"], ["3/4", "6/8"], ["lydian"]),
    "warlock": (["ostinato", "soaring"], ["3/4", "4/4"], ["dorian"]),
    "cleric": (["hymn", "bugle"], ["3/4", "4/4"], ["ionian"]),
    "druid": (["soaring", "hymn"], ["6/8", "3/4"], ["dorian", "lydian"]),
    "ranger": (["bugle", "soaring"], ["6/8", "4/4"], ["dorian", "mixolydian"]),
    "monk": (["ostinato", "hymn"], ["4/4", "3/4"], ["dorian", "ionian"]),
    "artificer": (["ostinato", "bugle"], ["4/4", "6/8"], ["lydian", "mixolydian"]),
}


def _style(cls) -> tuple:
    c = str(cls or "").lower()
    return next((v for k, v in STYLES.items() if k in c), (KINDS, list(METERS), list(MODES)))


def _close(notes: list, degree: int, bar: float, at_least: float) -> list:
    """End a phrase on ``degree``, held to the next bar line (at least ``at_least``)."""
    used = sum(d for _, d in notes)
    return notes + [(degree, round(math.ceil((used + at_least) / bar - 1e-9) * bar - used, 6))]


def _opening(rng, kind: str, meter: str) -> tuple:
    """(pickup, motif): the theme's first phrase, in scale degrees and units."""
    bar, fig, long_ = METERS[meter], rng.choice(FIGS[meter]), rng.choice(LONG[meter])
    one = 1 if meter != "6/8" else rng.choice([1, 2])
    pickup = []
    if kind == "fanfare":
        leap = rng.choice([4, 5, 7, 7])                                    # a 5th, a 6th, an octave
        pickup = rng.choice([[(0, T), (0, T), (0, T)], [(0, .75), (0, .25)], [(4 if leap == 7 else -3, 1)]])
        head = [(0, rng.choice([one, 1.5 * one])), (leap, long_)]
        fill = [(leap - 1 - i, d) for i, d in enumerate(fig)]
    elif kind == "ostinato":
        leap = rng.choice([3, 4, 5])                                       # a 4th, a 5th, a 6th
        cell = rng.choice(FIGS[meter])
        head = [(0, d) for d in cell] + [(0, d) for d in cell[:2]] + [(leap, long_)]
        fill = [(leap - 1, one), (leap - 2, one)]
    elif kind == "soaring":
        leap = rng.choice([4, 5, 7])
        head = [(d, one) for d in range(rng.choice([2, 3]))] + [(leap, long_ + one)]
        fill = [(leap + 1, fig[0]), (leap, fig[-1]), (leap - 1, one)]     # a turn above, then down
    elif kind == "bugle":
        arp = [0, 2, 4, 7] if rng.random() < .6 else [0, 2, 4]
        durs = (fig * 4)[:len(arp) - 1] + [long_]
        head = list(zip(arp, durs))
        leap = arp[-1]
        fill = [(leap - 1, one), (leap - 3, one)]
    else:                                                                  # hymn: a noble stepwise rise
        line = rng.choice([[0, 1, 2, 3, 4], [0, 2, 1, 3, 4], [0, 0, 1, 2, 4], [0, 1, 2, 4, 5], [0, 2, 3, 4, 5],
                           [0, 1, 0, 2, 4], [0, 2, 4, 3, 5], [0, 4, 3, 2, 4], [0, 1, 3, 2, 5], [0, 2, 2, 3, 4]])
        durs = rng.choice([[1, 1, 2, 1], [2, 1, 1, 1], [1.5, .5, 1, 1], [1, .5, .5, 2], [1, 1, 1, 1],
                           [.5, .5, 1, 2], [2, .5, .5, 1], [1, 2, 1, .5]])
        head = [(d, b * one) for d, b in zip(line[:-1], durs)] + [(line[-1], long_)]
        leap = line[-1]
        fill = rng.choice([[(leap - 1, one), (leap - 2, one)], [(leap + 1, one), (leap - 1, one)]])
    motif = head + fill + [(fill[-1][0] - 1, one)]
    landing = rng.choice([1, 2, 4]) if fill[-1][0] - 1 != 4 else rng.choice([2, 5])
    return pickup, _close(motif, landing, bar, one), len(head)


def _twist(rng, motif: list, n_head: int) -> tuple:
    """A character's own touch on the hook: a long note split in two, an even pair
    made dotted, or a neighbour note before the leap (or nothing). (motif, n_head)"""
    how = rng.choice(["none", "split", "dot", "neighbour", "neighbour"])
    head = motif[:n_head]
    if how == "split":
        i = max(range(n_head), key=lambda k: head[k][1])
        if head[i][1] >= 1:
            d, b = head[i]
            return motif[:i] + [(d, b / 2), (d, b / 2)] + motif[i + 1:], n_head + 1
    if how == "dot":
        for i in range(n_head - 1):
            if head[i][1] == head[i + 1][1] and head[i][1] >= .5 and head[i][0] != head[i + 1][0]:
                b = head[i][1]
                return motif[:i] + [(head[i][0], 1.5 * b), (head[i + 1][0], .5 * b)] + motif[i + 2:], n_head
    if how == "neighbour" and n_head >= 2:
        d, b = head[n_head - 2]                                            # (the note before the leap)
        if b >= 1:
            return (motif[:n_head - 2] + [(d, b / 2), (d + 1, b / 2)] + motif[n_head - 1:], n_head + 1)
    return motif, n_head


def _sentence(rng, kind: str, meter: str, mode: str, gen: int = 1):
    """A memorable theme, in the form most film themes use (A A B A): the hook (a
    short motif, its signature leap and rhythm); the hook again (the same, landing
    somewhere new, or a step higher): repetition is what makes it stick;
    development (the hook's head twice more, climbing, to the climax: the highest
    note, heard once, about two-thirds in); and the hook once more, at home, going
    down by step to the tonic, held: what the listener walks away humming.
    In scale degrees; None if it doesn't fit a singable range."""
    bar = METERS[meter]
    one = 1 if meter != "6/8" else 2
    st = lambda d: _semitones(d, MODES[mode])                              # noqa: E731
    pickup, motif, n_head = _opening(rng, kind, meter)
    motif, n_head = _twist(rng, motif, n_head)
    hook = motif[:min(len(motif) - 1, n_head + rng.choice([1, 1, 2]))]     # the head and its first step(s) back
    shift = rng.choice([0, 0, 1])
    again = [(d + shift, b) for d, b in motif]
    if shift == 0:                                                         # the same hook, a new landing
        again = again[:-1] + [(4 if motif[-1][0] != 4 else 2, again[-1][1])]
    rise = rng.choice([1, 1, 2])
    if gen >= 2:                                    # development: the hook, then its head
        frag = hook[:max(2, min(3, len(hook) - 1))]  # in quicker notes, climbing: a new rhythm
        climb = ([(d + rise, b) for d, b in hook] + [(d + 2 * rise, b / 2) for d, b in frag]
                 + [(d + 3 * rise, b / 2) for d, b in frag])
    else:
        climb = [(d + k * rise, b) for k in (1, 2) for d, b in hook]
    peak = max(d for d, _ in pickup + motif + again + climb)
    top = next(c for c in (7, 9, 11, 12, 14) if c > peak)
    climb.append((top, 2.5 * one))                                         # the climax
    fall, cur = [], top                                                    # and a fall from it, by
    while st(cur) - st(4) > 9:                                             # thirds, to the 5th: the hook
        cur -= 2                                                           # comes back smoothly
        fall.append((cur, .5 * one))
    climb += fall + [(4, one)]
    last = hook[-1][0]                                                     # home: the hook, then by step
    if last >= 6 and rng.random() < .5:                                    # up to the high tonic
        path, tonic = list(range(last + 1, 7)), 7
    else:                                                                  # or down to the tonic
        path, tonic = list(range(last - 1, 0, -1)), 0
    home = list(hook) + [(d, one) for d in path]
    before = sum(b for _, b in motif + again + climb + home)
    at_least = 2 * one if meter != "6/8" else 3
    home.append((tonic, round(math.ceil((before + at_least) / bar - 1e-9) * bar - before, 6)))
    every = pickup + motif + again + climb + home
    if st(top) - min(st(d) for d, _ in every) > 19:
        return None
    if gen >= 2:                                    # long notes on the beat
        parts = [pickup, motif, again, climb, home]
        flat, start = list(every), -sum(b for _, b in pickup)
        grid, medium = (1, 2) if meter == "6/8" else (.5, 1)
        for _ in range(6):                          # (moving one note can unsettle the one before)
            new = _align(_align(flat, BEATS[meter], start), grid, start, medium)
            if new == flat:
                break
            flat = new
        out, i = [], 0
        for part in parts:
            out.append(flat[i:i + len(part)])
            i += len(part)
        pickup, motif, again, climb, home = out
    return {"kind": kind, "meter": meter, "mode": mode, "pickup": pickup, "motif": motif,
            "again": again, "climb": climb, "home": home, "hook": len(hook), "gen": gen}


BEATS = {"4/4": 1, "3/4": 1, "6/8": 3}                       # a beat, in units


def _align(notes: list, beat: float, start: float, longer: float = None) -> list:
    """Long notes (a beat or more: ``longer``) start on a beat: the note before one
    that would start off the beat is lengthened, and the long note shortened by as
    much (its end, and everything after, stay where they were)."""
    out = list(notes)
    t = start
    longer = beat if longer is None else longer
    for i, (d, b) in enumerate(out):
        off = (t / beat) % 1
        if i and b >= longer - 1e-9 and 1e-6 < off < 1 - 1e-6:
            delta = round((1 - off) * beat, 6)
            if b - delta >= .5:
                pd, pb = out[i - 1]
                out[i - 1] = (pd, round(pb + delta, 6))
                b = round(b - delta, 6)
                out[i] = (d, b)
                t += delta
        t += b
    return out


def _hero_notes(hero: dict) -> list:
    return [(_semitones(d, _scale(hero["mode"])), b)
            for sec in ("pickup", "motif", "again", "climb", "home") for d, b in hero[sec]]


def memorability(tune: dict) -> float:
    """How memorable a tune is likely to be, from what memorable themes share: its
    hook heard again and again, a strong opening rise, an arch to a single climax
    about two-thirds in, mostly steps with a few leaps, a comfortable range, and
    no drone of one note."""
    t = theme_traits(tune)
    pitch = [p for p, _ in tune["notes"]]
    moves = [b - a for a, b in zip(pitch, pitch[1:]) if b != a]
    stepwise = sum(1 for m in moves if abs(m) <= 2) / max(1, len(moves))
    same = longest = 1
    for a, b in zip(pitch, pitch[1:]):
        same = same + 1 if a == b else 1
        longest = max(longest, same)
    return (2 * min(t["rise"], 12) / 12 + .75 * min(t["hook_repeats"], 4)
            + 2 - 8 * abs(t["climax_at"] - .65) + (1.5 if t["single_climax"] else 0)
            + 1.5 - 5 * abs(stepwise - .7) + (1 if 10 <= t["range"] <= 16 else 0)
            - .4 * max(0, longest - 4))


CANDIDATES = 12                                             # tunes tried per character


def _candidates(seed_hex: str, kind: str, meter: str, mode: str, gen: int = 1) -> list:
    """[(score, i, hero)]: the candidate tunes and their memorability (a tune that
    breaks a hard rule - range, leaps, climax, the bar line - drops to the bottom)."""
    import random
    found = []
    for i in range(60):
        hero = _sentence(random.Random(f"{seed_hex}:{i}" if gen < 2 else f"{seed_hex}:v{gen}:{i}"),
                         kind, meter, mode, gen)
        if hero is None:
            continue
        tune = {"notes": _hero_notes(hero), "bar": METERS[meter], "meter": meter, "key": 60,
                "pickup": sum(b for _, b in hero["pickup"]), "hook": (len(hero["pickup"]), hero["hook"])}
        t = theme_traits(tune)
        fits = (.45 <= t["climax_at"] <= .72 and t["biggest_jump"] <= 12 and t["range"] <= 19
                and t["whole_bars"] and t["ends_home"] and t["gap_fill"] and t["rise"] >= 5)
        value = memorability(tune) - (0 if fits else 20)
        if gen >= 2:
            value += _research_score(tune)
        found.append((value, i, hero))
        if len(found) >= CANDIDATES:
            break
    return found


def _research_score(tune: dict) -> float:
    """Generator v2: the tune scored as music research measures melodies (surprise
    against thousands of folk tunes, rhythmic variety, held notes, long notes on the
    beat: lib/tune_score.py), when its corpus is built; else the plain rhythm checks."""
    try:
        from music import tune_score
        mel = tune_score.from_leitmotif(tune)
        if tune_score.CACHE.is_file():
            return 1.2 * tune_score.score(mel)["composite"]
        f = tune_score.features(mel)
        return 4 * f["long_on_beat"] + 3 * min(1.0, f["rhythm_entropy"] / 2) - 6 * max(0.0, f["held_share"] - .45)
    except Exception:
        return 0.0


def _hero(seed_hex: str, rng, cls, gen: int = 1) -> dict:
    """The character's theme: its kind, meter and mode from their class (and name);
    of twelve candidate tunes, one of the most memorable."""
    import random
    kinds, meters, modes = _style(cls)
    kind, meter, mode = rng.choice(kinds), rng.choice(meters), rng.choice(modes)
    found = _candidates(seed_hex, kind, meter, mode, gen)
    # Among the near-best (within half a point), the name chooses: memorable, and
    # not the same "best" tune for every character of a kind.
    top = max(sc for sc, _, _ in found)
    near = sorted((c for c in found if c[0] >= top - .5), key=lambda c: c[1])
    score, _, best = near[random.Random(seed_hex + ":pick").randrange(len(near))]
    best["memorability"] = round(score, 2)
    return best


def _scale(name: str) -> list:
    """A mode's scale: the heroes' modes, or (a hand-written tune's) a dark one."""
    return MODES.get(name) or DARK[name]


def _semitones(degree: int, scale) -> int:
    octave, idx = divmod(degree, 7)
    return 12 * octave + scale[idx]


def _villain(rng, hero: dict) -> tuple:
    """The same tune, turned villainous: ([(semitones from the tonic, units)], scale name)."""
    name = rng.choice(list(DARK))
    st = lambda d: _semitones(d, DARK[name])                               # noqa: E731
    sigh = lambda b: [(8, b / 2), (7, b / 2)]                              # noqa: E731  minor 6th -> 5th
    meter = hero["meter"]
    bar, one = METERS[meter], (1 if meter != "6/8" else 2)
    march = [(0, 2), (0, 1), (0, 2), (0, 1)] if meter == "6/8" else [(0, .75), (0, .25), (0, .75), (0, .25)]
    out = list(march)
    for sec in ("motif", "again"):                                         # each ends on a sigh
        sec_notes = hero[sec]
        out += [(st(d), b) for d, b in sec_notes[:-1]] + sigh(sec_notes[-1][1])
    climb = [(st(d), b) for d, b in hero["climb"]]
    peak = max(range(len(climb)), key=lambda i: climb[i][0])               # the climax: kept
    tritone = 18 if climb[peak][0] - 6 > 12 else 6                         # (in the climax's octave)
    climb[peak - 1] = (tritone, climb[peak - 1][1])                        # the tritone, before it
    out += climb
    head = [(st(d), b) for d, b in hero["home"][:hero["hook"]]]           # the hook, at home
    while len(head) > 2 and head[-1][0] < 3:                               # (the fall starts above)
        head.pop()
    tail = head + [(3, one), (1, one)]                                     # falling home through the minor 2nd
    used = sum(b for _, b in out + tail)
    out += tail + [(0, round(math.ceil((used + 2 * one) / bar - 1e-9) * bar - used, 6))]
    if hero.get("gen", 1) != 1:                     # (new tunes: long notes on the beat; the old
        grid, medium = (1, 2) if meter == "6/8" else (.5, 1)   # villain themes stay as they were)
        for _ in range(6):
            new = _align(_align(out, BEATS[meter], 0), grid, 0, medium)
            if new == out:
                break
            out = new
    return out, name


# Where the character's story is (lib/character_arcs.py) shapes their theme; its
# hook never changes. The stage: 0 a lone voice (the hook and its answer, home);
# 1 the theme as written; 2 heroic (the climax reaches a third higher); 3 the
# finale's legendary version (and a grand, held ending). Dark deeds borrow darker
# notes, one by one (the 7th, then the 3rd, then the 6th, then the 2nd: toward the
# villain twin); light gives them back.
DARKENING = [(6, 11, 10), (2, 4, 3), (5, 9, 8), (1, 2, 1)]   # (scale index, from, to)


def _darkened(scale: list, dark: int) -> list:
    out, left = list(scale), dark
    for idx, frm, to in DARKENING:
        if left <= 0:
            break
        if out[idx] == frm:
            out[idx], left = to, left - 1
    return out


def _grown(hero: dict, stage: int, dark: int) -> list:
    """The hero's tune at a stage of their story, in semitones."""
    scale = _darkened(_scale(hero["mode"]), dark)
    bar = METERS[hero["meter"]]
    one = 1 if hero["meter"] != "6/8" else 2
    if stage <= 0:                                         # a lone voice: the hook, its answer, home
        body = hero["motif"] + hero["again"][:-1]
        before = sum(b for _, b in body)
        at_least = 2 * one if hero["meter"] != "6/8" else 3
        secs = hero["pickup"] + body + [(0, round(math.ceil((before + at_least) / bar - 1e-9) * bar - before, 6))]
    else:
        climb = list(hero["climb"])
        if stage >= 2:                                     # reaching higher: a third above the climax
            i = max(range(len(climb)), key=lambda k: climb[k][0])
            top, b = climb[i]
            low = min(_semitones(d, scale) for d, _ in hero["pickup"] + hero["motif"] + hero["again"] + hero["home"])
            up = 2 if _semitones(top + 2, scale) - low <= 21 else 1          # (or a step, kept singable)
            first = BEATS[hero["meter"]] if b >= BEATS[hero["meter"]] - 1e-9 else b / 2   # (the lift on a beat)
            climb[i:i + 1] = [(top, first), (top + up, b - first + bar)]
        home = list(hero["home"])
        if stage >= 3:                                     # the legend's ending: held a bar longer
            home[-1] = (home[-1][0], home[-1][1] + bar)
        secs = hero["pickup"] + hero["motif"] + hero["again"] + climb + home
    return [(_semitones(d, scale), b) for d, b in secs]


def written_tune(spec: dict, mode: str = "major", stage: int = 1, dark: int = 0) -> dict:
    """A hand-written tune (the GM's), in the generator's own shape so that every
    version of it works - the villain's, the story stages, the darkening:
    {"seed", "meter": "6/8", "mode": "mixolydian", "key": "C#4" (default: from the
    seed), "kind", "pickup"/"motif"/"again"/"climb"/"home": [[scale degree, units]],
    "hook": notes in the hook}. Degrees: 0 the tonic, 7 the octave, -1 below."""
    return leitmotif(spec.get("seed", "written"), mode, "", stage=stage, dark=dark, written=spec)


def leitmotif(seed: str, mode: str = "major", cls: str = "", stage: int = 1, dark: int = 0,
              gen: int = 1, written: dict = None, **_arc) -> dict:
    """The tune: {key (MIDI tonic), notes [(semitones from the tonic, units)], motif
    (its first statement), hook (where it starts, how many notes), kind, meter,
    scale, memorability}. Same seed and class, same tune; "minor" is the villain;
    ``stage`` and ``dark``: where the character's story is (see _grown)."""
    import hashlib
    import random
    seed_hex = hashlib.sha256(seed.strip().lower().encode("utf-8")).hexdigest()
    rng = random.Random(seed_hex)
    key = 57 + rng.randrange(10)                                           # A3 .. F#4
    if written:
        hero = {k: [tuple(n) for n in written.get(k) or []] for k in ("pickup", "motif", "again", "climb", "home")}
        hero.update(kind=written.get("kind", "written"), meter=written["meter"], mode=written["mode"],
                    hook=int(written.get("hook", len(hero["motif"]))), memorability=0.0, gen="written")
        if written.get("key"):
            from music import arrangement
            key = arrangement.pitch(written["key"])
        hero["memorability"] = round(memorability({"notes": _hero_notes(hero), "bar": METERS[hero["meter"]],
                                                   "pickup": sum(b for _, b in hero["pickup"]),
                                                   "hook": (len(hero["pickup"]), hero["hook"])}), 2)
    else:
        hero = _hero(seed_hex, rng, cls, gen)
    if mode == "minor":
        notes, scale = _villain(random.Random(seed_hex + ":villain"), hero)
        start = 4                                                          # (after the march)
    else:
        scale = hero["mode"]
        notes = _grown(hero, stage, dark)
        start = len(hero["pickup"])
    return {"seed": seed, "mode": mode, "key": key, "notes": notes,
            "motif": notes[start:start + len(hero["motif"])], "hook": (start, hero["hook"]),
            "kind": hero["kind"], "meter": hero["meter"], "scale": scale,
            "shape": [d for d, _ in hero["motif"]], "bar": METERS[hero["meter"]],
            "pickup": sum(b for _, b in hero["pickup"]) if mode != "minor" else 0,
            "memorability": hero["memorability"], "gen": gen if not written else "written"}


def theme_traits(tune: dict) -> dict:
    """What a tune has of a film hero's (or villain's) theme: used to check every one."""
    notes = tune["notes"]
    pitch = [p for p, _ in notes]
    beats = [b for _, b in notes]
    steps = [b - a for a, b in zip(pitch, pitch[1:])]
    total = sum(beats)
    opening = pitch[:8]
    hi = opening.index(max(opening))
    top = pitch.index(max(pitch))
    pcs = {p % 12 for p in pitch}
    return {
        "rise": max(opening) - opening[0],
        "gap_fill": hi + 1 < len(pitch) and pitch[hi + 1] < pitch[hi],
        "fanfare": any(abs(b - .75) < 1e-6 or abs(b - T) < 1e-6 for b in beats),
        "climax_at": sum(beats[:top]) / total,
        "climax_held": beats[top] >= 2,
        "range": max(pitch) - min(pitch),
        "biggest_jump": max(abs(s) for s in steps),
        "ends_home": pitch[-1] % 12 == 0 and beats[-1] >= 2,
        "whole_bars": abs(((total - tune.get("pickup", 0)) / tune["bar"]) % 1) < 1e-6
                      or abs(((total - tune.get("pickup", 0)) / tune["bar"]) % 1 - 1) < 1e-6,
        "minor": 3 in pcs and 4 not in pcs,
        "sighs": sum(1 for s in steps if s == -1),
        "repeated": any(s == 0 for s in steps),
        "tritone": 6 in pcs,
        "falls_home": steps[-1] < 0,
        "hook_repeats": _recurrences(pitch, beats, *tune["hook"]) if tune.get("hook") else 0,
        "single_climax": pitch.count(max(pitch)) == 1,
    }


def _recurrences(pitch: list, beats: list, start: int, length: int) -> int:
    """How many times the hook (its contour and rhythm) is heard in the tune."""
    sign = lambda x: (x > 0) - (x < 0)                                     # noqa: E731
    shape = lambda i: tuple((sign(pitch[i + k + 1] - pitch[i + k]), round(beats[i + k], 3))  # noqa: E731
                            for k in range(length - 1))
    if start + length > len(pitch):
        return 0
    hook = shape(start)
    return sum(1 for i in range(len(pitch) - length + 1) if shape(i) == hook)


def render_leitmotif(seed: str, mode: str = "major", seconds: float = 20, rate: int = 32000,
                     cls: str = "", **arc):
    """The tune as a plain synthesized melody line (to hear the notes alone):
    stretched to ``seconds``; the villain is also an octave lower."""
    import numpy as np
    tune = leitmotif(seed, mode, cls, **arc)
    units = sum(b for _, b in tune["notes"])
    unit_s = seconds / units
    out = np.zeros(int(seconds * rate) + rate, dtype="float64")
    t0 = 0.0
    for st, b in tune["notes"]:
        note = tune["key"] + st - (12 if mode == "minor" else 0)
        hz = 440.0 * 2 ** ((note - 69) / 12)
        n = int(b * unit_s * rate)
        t = np.arange(n) / rate
        env = np.minimum(1.0, t / 0.02) * np.exp(-t / max(0.25, b * unit_s * 0.9))
        tone = sum(a * np.sin(2 * np.pi * hz * k * t) for k, a in ((1, 1.0), (2, .35), (3, .15)))
        i = int(t0 * rate)
        out[i:i + n] += 0.3 * env * tone
        t0 += b * unit_s
    return out[: int(seconds * rate)].astype("float32")


# --- the dark twin of a piece ---
def darken(samples, rate: int, slow: float = 0.84):
    """The same recording, made ominous: slower and lower (0.84 ≈ three semitones
    down, like a tape slowing), its brightness muffled, in a cavernous echo."""
    import numpy as np
    x = np.asarray(samples, dtype="float64")
    if len(x) < 2:
        return x.astype("float32")
    y = np.interp(np.arange(int(len(x) / slow)) * slow, np.arange(len(x)), x)
    size = 1 << (len(y) + int(rate * 2.2)).bit_length()
    spec = np.fft.rfft(y, size)
    freqs = np.fft.rfftfreq(size, 1 / rate)
    spec *= 1 / (1 + (freqs / 2200.0) ** 4)                    # muffled: the highs roll off
    rng = np.random.default_rng(7)
    n_ir = int(rate * 2.0)
    ir = rng.standard_normal(n_ir) * np.exp(-np.arange(n_ir) / (rate * 0.5))
    ir[0] = 0
    ir /= np.sqrt(np.sum(ir ** 2))
    dry = np.fft.irfft(spec, size)[:len(y)]
    wet = np.fft.irfft(spec * np.fft.rfft(ir, size), size)[:len(y)]
    return (0.8 * dry + 0.45 * wet).astype("float32")


def write(samples, rate: int, out: Path, loop_start: Optional[int] = None,
          landing: Optional[int] = None) -> Path:
    """OGG when this soundfile build can (small files), else WAV. ``loop_start``: a loop
    with an entry - the sample it loops back to, kept in the file's comment as
    LOOPSTART=n; ``landing``: a sting's written end, before its reverb (LANDING=n: the
    next cue starts there). The table reads both: table_server.loop_start."""
    tags = " ".join(f"{k}={int(v)}" for k, v in (("LOOPSTART", loop_start), ("LANDING", landing)) if v)
    import soundfile as sf
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        # In blocks: libsndfile's OGG encoder can crash on one very long write.
        channels = 1 if getattr(samples, "ndim", 1) == 1 else samples.shape[1]
        with sf.SoundFile(str(out), "w", samplerate=rate, channels=channels) as f:
            if tags:
                f.comment = tags
            for i in range(0, len(samples), 1 << 16):
                f.write(samples[i:i + (1 << 16)])
        return out
    except Exception:
        wav = out.with_suffix(".wav")
        with sf.SoundFile(str(wav), "w", samplerate=rate, channels=channels) as f:
            if tags:
                f.comment = tags
            f.write(samples)
        return wav


def main() -> None:
    ap = argparse.ArgumentParser(description="Tunes and audio helpers for the orchestra's music")
    ap.add_argument("--out", help="With --leitmotif: the folder to write to")
    ap.add_argument("--normalize", nargs="+", metavar="FILE",
                    help="Bring pieces to the standard loudness, in place")
    ap.add_argument("--class", dest="cls", default="", help="With --leitmotif: the character's class")
    ap.add_argument("--leitmotif", metavar="NAME",
                    help="Write NAME's leitmotif (and its dark twin) as plain melody files to --out's folder")
    args = ap.parse_args()

    if args.normalize:
        import soundfile as sf
        for f in args.normalize:
            try:
                samples, rate = sf.read(f, dtype="float32", always_2d=False)
                before = loudness_db(samples, rate)
                sf.write(f, normalize(samples, rate), rate)
                print(json.dumps({"ok": True, "path": f, "before_db": round(before, 1),
                                  "after_db": round(loudness_db(sf.read(f, dtype="float32")[0], rate), 1)}),
                      flush=True)
            except Exception as e:
                print(json.dumps({"ok": False, "path": f, "error": f"{type(e).__name__}: {e}"}), flush=True)
        return

    if args.leitmotif:
        out = Path(args.out or ".")
        out.mkdir(parents=True, exist_ok=True)
        for mode, s in (("major", 20), ("minor", 30)):
            path = write(render_leitmotif(args.leitmotif, mode, s, cls=args.cls), 32000,
                         out / f"motif-{args.leitmotif.strip().lower().replace(' ', '-')}-{mode}.ogg")
            print(json.dumps({"ok": True, "path": str(path), "mode": mode,
                              **{k: v for k, v in leitmotif(args.leitmotif, mode, args.cls).items()
                                 if k in ("kind", "meter", "scale", "motif")}}, ensure_ascii=False))
        return
    ap.print_help()


if __name__ == "__main__":
    main()
