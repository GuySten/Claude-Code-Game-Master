#!/usr/bin/env python3
"""Score a melody the way music-psychology research measures them, against a corpus
of real tunes (public-domain folk and fiddle melodies bundled with music21: the
Essen folksongs, O'Neill's 1850, Ryan's Mammoth Collection, the Nottingham tunes).

Two parts, both measured against the corpus (a tune's value as a percentile of
what thousands of real, sung and played tunes do):

* **Surprise** (after IDyOM, Pearce): a variable-order Markov model of pitch
  intervals and rhythm, trained on the corpus (long-term) and on the tune itself
  as it unfolds (short-term: a repeated hook becomes expected). The mean
  information content per note is how surprising the tune is. Pleasure peaks at
  a middle level of surprise (Gold, Pearce et al. 2019) and earworms pair common
  contours with some unusual intervals (Jakubowski, Muellensiefen et al. 2017), so
  the target is a little above the corpus median, not the extremes.
* **Features** (after FANTASTIC, Muellensiefen): range, interval variety, steps vs
  leaps, rhythmic variety, how much of the tune is held notes, whether long notes
  land on the beat, how much it repeats itself, where its peak is, how tonal it
  is.

    python3 lib/tune_score.py "Kestrel" --class Barbarian [--minor] [--stage N] [--gen 2]
    python3 lib/tune_score.py --json tune.json        ({"notes": [[semitones, units], ...],
                                                       "meter": "6/8", "key": "C#4", ...})
    python3 lib/tune_score.py --build                 (build the corpus model, once)

The composite (0-10) counts how many features sit in the corpus's normal range,
plus surprise near its target. It's a guide built from published findings, not a
validated predictor of taste; read the per-feature report.
"""

import argparse
import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

CACHE = Path(os.environ.get("TUNE_CORPUS") or Path.home() / ".cache" / "gm-orchestra" / "tune-corpus.json")
COLLECTIONS = ("essenFolksong", "oneills1850", "ryansMammoth", "nottingham-dataset")
ORDER = 4                      # the Markov models' longest context
MAX_TUNES = 4000

# A melody here: {"notes": [(midi, dur_ql, pos_ql)], "beat": ql, "bar": ql, "tonic": pc}
#   dur_ql/pos_ql in quarter notes; pos_ql = onset within its bar.


# --- the corpus ---
def _from_music21(score) -> Optional[Dict[str, Any]]:
    from music21 import meter
    parts = score.parts if hasattr(score, "parts") and score.parts else [score]
    part = parts[0]
    ts = next(iter(part.recurse().getElementsByClass(meter.TimeSignature)), None)
    if ts is None:
        return None
    from music21 import key as m21key
    ks = next(iter(part.recurse().getElementsByClass(m21key.KeySignature)), None)
    try:                                   # the key the tune states (fast); else analyse it
        tonic = (ks.tonic.pitchClass if isinstance(ks, m21key.Key)
                 else ks.asKey("major").tonic.pitchClass if ks is not None
                 else score.analyze("key").tonic.pitchClass)
    except Exception:
        return None
    notes = []
    for m in part.getElementsByClass("Measure"):
        pad = float(m.paddingLeft or 0)
        for n in m.notesAndRests:
            if n.isRest:
                continue
            p = n.pitches[-1].midi if n.isChord else n.pitch.midi
            d = float(n.quarterLength)
            if d <= 0:
                continue
            if notes and n.tie is not None and n.tie.type in ("continue", "stop") and notes[-1][0] == p:
                notes[-1] = (p, notes[-1][1] + d, notes[-1][2])
                continue
            notes.append((p, d, float(n.offset) + pad))
    if len(notes) < 12:
        return None
    return {"notes": notes, "beat": float(ts.beatDuration.quarterLength),
            "bar": float(ts.barDuration.quarterLength), "tonic": tonic}


def build(limit: int = MAX_TUNES, quiet: bool = False) -> List[Dict[str, Any]]:
    """Extract the corpus melodies (a few minutes, once) into the cache."""
    import glob
    import music21
    from music21 import converter
    base = Path(music21.__file__).parent / "corpus"
    tunes: List[Dict[str, Any]] = []
    per = limit // len(COLLECTIONS)                 # a balanced sample: every tradition counts
    for c in COLLECTIONS:
        files = [f for f in sorted(glob.glob(str(base / c / "**" / "*.*"), recursive=True))
                 if f.endswith((".abc", ".mxl", ".xml", ".krn"))]
        got_here = 0
        for i, f in enumerate(files):
            try:
                got = converter.parse(f)
            except Exception:
                continue
            scores = list(got.scores) if hasattr(got, "scores") else [got]
            for sc in scores:
                mel = _from_music21(sc)
                if mel and got_here < per:
                    tunes.append({**mel, "from": c})
                    got_here += 1
            if not quiet and i % 25 == 0:
                print(f"[tune_score] {c}: {i}/{len(files)} files, {got_here} tunes", file=sys.stderr, flush=True)
            if got_here >= per:
                break
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(tunes))
    return tunes


def corpus() -> List[Dict[str, Any]]:
    if not CACHE.is_file():
        return build()
    return json.loads(CACHE.read_text())


# --- symbols ---
def _q(x: float, step: float = 1 / 12) -> float:
    return round(round(x / step) * step, 4)


def symbols(mel: Dict[str, Any]) -> Tuple[List[int], List[float]]:
    """(intervals, duration ratios): the pitch and rhythm sequences the models read."""
    n = mel["notes"]
    ints = [max(-12, min(12, b[0] - a[0])) for a, b in zip(n, n[1:])]
    ratios = [_q(min(8.0, max(0.125, b[1] / a[1])), 1 / 8) for a, b in zip(n, n[1:])]
    return ints, ratios


# --- a variable-order Markov model (PPM-like, interpolated) ---
class Markov:
    def __init__(self, order: int = ORDER):
        self.order = order
        self.counts: Dict[tuple, Counter] = defaultdict(Counter)
        self.alphabet: set = set()

    def learn(self, seq: List[Any]) -> None:
        for i, s in enumerate(seq):
            self.alphabet.add(s)
            for k in range(self.order + 1):
                if i - k < 0:
                    break
                self.counts[tuple(seq[i - k:i])][s] += 1

    def prob(self, ctx: List[Any], s: Any, alphabet: int) -> float:
        p = 1.0 / max(alphabet, 1)                      # order -1: uniform
        for k in range(0, self.order + 1):
            if k > len(ctx):
                break
            c = self.counts.get(tuple(ctx[len(ctx) - k:]) if k else ())
            if not c:
                break
            total = sum(c.values())
            distinct = len(c)
            lam = total / (total + distinct)            # (escape, method C)
            p = lam * c.get(s, 0) / total + (1 - lam) * p
        return max(p, 1e-9)


def information(seq: List[Any], ltm: Markov, alphabet: int) -> List[float]:
    """Information content (bits) of each symbol: long-term and short-term models
    combined by an entropy-weighted mean, as IDyOM does."""
    out = []
    for i, s in enumerate(seq):
        ctx = seq[max(0, i - ORDER):i]
        stm = Markov()
        stm.learn(seq[:i])                              # the tune so far
        pl, ps = ltm.prob(ctx, s, alphabet), stm.prob(ctx, s, alphabet)
        ws = min(1.0, i / 8)                            # (the short-term model needs some notes first)
        out.append(-math.log2((pl + ws * ps) / (1 + ws)))
    return out


# --- features ---
KK_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
KK_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]


def _entropy(xs) -> float:
    c = Counter(xs)
    n = sum(c.values())
    return -sum(v / n * math.log2(v / n) for v in c.values()) if n else 0.0


def _corr(a, b) -> float:
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return num / den if den else 0.0


def features(mel: Dict[str, Any]) -> Dict[str, float]:
    n = mel["notes"]
    pitches = [p for p, _, _ in n]
    durs = [d for _, d, _ in n]
    total = sum(durs)
    ints, _ = symbols(mel)
    beat = mel["beat"]
    long_notes = [(d, pos) for _, d, pos in n if d >= beat - 1e-6]
    on_beat = [abs((pos / beat) - round(pos / beat)) < 1e-3 for d, pos in long_notes]
    grams = [tuple(zip(ints[i:i + 3], [_q(x) for x in durs[i + 1:i + 4]])) for i in range(len(ints) - 2)]
    weights = Counter()
    for p, d, _ in n:
        weights[p % 12] += d
    prof = [weights.get(i, 0) for i in range(12)]
    tonal = max(max(_corr(prof, KK_MAJOR[-k:] + KK_MAJOR[:-k]) for k in range(12)),
                max(_corr(prof, KK_MINOR[-k:] + KK_MINOR[:-k]) for k in range(12)))
    top = max(range(len(pitches)), key=lambda i: (pitches[i], -i))
    return {
        "range": max(pitches) - min(pitches),
        "interval_entropy": _entropy(ints),
        "step_share": sum(1 for i in ints if abs(i) <= 2) / max(1, len(ints)),
        "repeat_share": sum(1 for i in ints if i == 0) / max(1, len(ints)),
        "rhythm_entropy": _entropy(_q(d) for d in durs),
        "held_share": sum(d for d in durs if d >= 2 * beat - 1e-6) / total,
        "long_on_beat": sum(on_beat) / len(on_beat) if on_beat else 1.0,
        "motif_repetition": 1 - len(set(grams)) / max(1, len(grams)),
        "peak_at": sum(durs[:top]) / total,
        "tonalness": tonal,
        "notes_per_beat": len(n) / (total / beat),
    }


# --- the reference distribution and the score ---
_MODEL: Dict[str, Any] = {}


def _model() -> Dict[str, Any]:
    if _MODEL:
        return _MODEL
    tunes = corpus()
    pitch, rhythm = Markov(), Markov()
    for t in tunes:
        a, b = symbols(t)
        pitch.learn(a)
        rhythm.learn(b)
    _MODEL.update(pitch=pitch, rhythm=rhythm, alpha_p=len(pitch.alphabet) + 1, alpha_r=len(rhythm.alphabet) + 1)
    # the corpus's own values (surprise measured on a held-out sample, against a model
    # without it, so the corpus isn't scored on tunes it memorized)
    import random
    rng = random.Random(7)
    sample = rng.sample(tunes, min(300, len(tunes)))
    held = {id(t) for t in sample}
    p2, r2 = Markov(), Markov()
    for t in tunes:
        if id(t) not in held:
            a, b = symbols(t)
            p2.learn(a)
            r2.learn(b)
    ref = defaultdict(list)
    for t in sample:
        a, b = symbols(t)
        ic = information(a, p2, _MODEL["alpha_p"])
        icr = information(b, r2, _MODEL["alpha_r"])
        ref["surprise"].append(sum(ic + icr) / len(ic))
        for k, v in features(t).items():
            ref[k].append(v)
    _MODEL["ref"] = {k: sorted(v) for k, v in ref.items()}
    return _MODEL


def _pct(sorted_vals: List[float], v: float) -> float:
    import bisect
    return 100 * bisect.bisect_left(sorted_vals, v) / max(1, len(sorted_vals))


def score(mel: Dict[str, Any]) -> Dict[str, Any]:
    """{composite (0-10), surprise, features: {name: (value, percentile)}, notes}."""
    m = _model()
    a, b = symbols(mel)
    ic = information(a, m["pitch"], m["alpha_p"])
    icr = information(b, m["rhythm"], m["alpha_r"])
    surprise = sum(ic + icr) / max(1, len(ic))
    feats = features(mel)
    ref = m["ref"]
    report = {"surprise": (round(surprise, 2), round(_pct(ref["surprise"], surprise)))}
    report.update({k: (round(v, 3), round(_pct(ref[k], v))) for k, v in feats.items()})
    points, notes = 0.0, []
    sp = report["surprise"][1]
    points += 3.0 * max(0.0, 1 - abs(sp - 60) / 40)               # a little above the median
    if sp < 25:
        notes.append("very predictable: an unexpected interval or rhythm in the hook would help")
    if sp > 90:
        notes.append("more surprising than almost any folk tune: hard to remember")
    judged = ["range", "interval_entropy", "step_share", "repeat_share", "rhythm_entropy",
              "held_share", "motif_repetition", "tonalness", "notes_per_beat"]
    for k in judged:
        pc = report[k][1]
        points += 6.0 / len(judged) * (1.0 if 10 <= pc <= 90 else 0.5 if 5 <= pc <= 95 else 0.0)
        if not 5 <= pc <= 95:
            notes.append(f"{k.replace('_', ' ')} {report[k][0]} is unusual (percentile {pc} of real tunes)")
    lob = feats["long_on_beat"]
    points += 1.0 * lob
    if lob < 0.9:
        notes.append(f"{round(100 * (1 - lob))}% of its long notes start off the beat")
    return {"composite": round(points, 2), **report, "notes": notes}


# --- our tunes, as melodies ---
def from_leitmotif(tune: Dict[str, Any]) -> Dict[str, Any]:
    """A music_compose.leitmotif() tune (or a hand-written one in its shape)."""
    import music_compose
    meter = tune["meter"]
    ql = 0.5 if meter == "6/8" else 1.0                 # one unit, in quarter notes
    beat = 1.5 if meter == "6/8" else 1.0
    bar = music_compose.METERS[meter] * ql
    pickup = tune.get("pickup", 0) * ql
    notes, t = [], 0.0
    for st, u in tune["notes"]:
        d = u * ql
        notes.append((tune["key"] + st, d, ((t - pickup) % bar)))
        t += d
    return {"notes": notes, "beat": beat, "bar": bar, "tonic": tune["key"] % 12}


def main() -> None:
    ap = argparse.ArgumentParser(description="Score a melody against real tunes.")
    ap.add_argument("seed", nargs="?")
    ap.add_argument("--class", dest="cls", default="")
    ap.add_argument("--minor", action="store_true")
    ap.add_argument("--stage", type=int, default=1)
    ap.add_argument("--gen", type=int, default=None, help="the tune generator's version")
    ap.add_argument("--json", help="a hand-written tune (JSON)")
    ap.add_argument("--build", action="store_true", help="(re)build the corpus")
    a = ap.parse_args()
    if a.build:
        tunes = build()
        print(f"{len(tunes)} tunes -> {CACHE}")
        return
    import music_compose
    if a.json:
        spec = json.loads(Path(a.json).read_text(encoding="utf-8"))
        tune = music_compose.written_tune(spec)
    else:
        extra = {"gen": a.gen} if a.gen else {}
        tune = music_compose.leitmotif(a.seed, "minor" if a.minor else "major", a.cls, stage=a.stage, **extra)
    print(json.dumps(score(from_leitmotif(tune)), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
