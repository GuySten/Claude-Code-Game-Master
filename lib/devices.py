#!/usr/bin/env python3
"""Character devices that are written by rule (see the orchestrate skill's
references/devices.md): they take an arrangement and add a device to it.

    madness(spec, windows)   a solo violin plays the tune along with the orchestra and,
                             in each window, breaks - too high, off pitch, off the beat -
                             with the string section following it ("unhinge"); the piece
                             begins with it alone, composed, and ends with it alone,
                             unravelled.

Run in the orchestra's environment (it reads the tune from lib/arrangement.py).
"""

import copy
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import arrangement  # noqa: E402

STRINGS = ("strings", "violins", "violins2", "cellos", "tremolo", "pizzicato", "basses")


def _line(spec: Dict[str, Any], windows: Sequence[Tuple[float, float]], wild: float, seed: int,
          top: int, along: float, climax: Optional[Tuple[float, float]]) -> List[list]:
    """The violin: the tune an octave up, and in each window, broken."""
    ctx = arrangement._build({**spec, "lines": [l for l in spec.get("lines") or [] if l["part"] != "solo_violin"]})
    rnd = random.Random(seed)
    out = []
    for u, b, k in ctx["played"]:
        w = next((w for w in windows if w[0] <= u < w[1]), None)
        base = k + 12
        while base > top:
            base -= 12
        if w is None:
            lift = 6 if climax and climax[0] <= u < climax[1] else 0     # (over a full orchestra)
            out.append([round(u, 3), base, round(b, 3), along + lift])
            continue
        f = (u - w[0]) / max(1e-6, w[1] - w[0])
        up = 12 if f < 0.35 / wild else (19 if f < 0.7 / wild else 24)  # too high, sooner when wilder
        p = base + up
        while p > top:
            p -= 12
        jit = rnd.uniform(-0.28, 0.18) * b if b < 2 else rnd.uniform(-0.2, 0.1)   # rushing, dragging
        vel = rnd.choice([-12, -4, 6, 14, 18])
        how = {"wobble": round(rnd.uniform(0.25, 0.7) * wild, 2), "slide": round(rnd.uniform(-2.5, 1.0) * wild, 2)}
        if b >= 1 and rnd.random() < 0.5:                                # stuck on a note
            n = rnd.randint(2, 4)
            step = b / (n + 1)
            for i in range(n):
                out.append([round(u + jit + i * step, 3), p + (1 if i % 2 else 0), round(step * 0.8, 3), vel + 4 * i])
            out.append([round(u + jit + n * step, 3), p, round(step, 3), vel, how])
        elif rnd.random() < 0.04:                                        # a note dropped
            continue
        else:
            out.append([round(u + jit, 3), p, round(b * rnd.uniform(0.85, 1.1), 3), vel, how])
    return out


def madness(spec: Dict[str, Any], windows: Sequence[Tuple[float, float]], *, wild: float = 1.0,
            follow: Sequence[str] = STRINGS, seed: int = 7, gain: float = 10.0, top: int = 98,
            opening: Optional[List[list]] = None, ending: Optional[List[list]] = None,
            fill: Optional[List[list]] = None, climax: Optional[Tuple[float, float]] = None,
            stumble: Sequence[Tuple[float, float]] = ()) -> Dict[str, Any]:
    """The arrangement with the madness device: ``windows`` are the breaks (in the tune's
    units: keep them short - about a beat - and growing); ``wild`` how far each goes;
    ``follow`` the parts that go with it (the strings); ``opening``/``ending``: the
    violin's notes alone before the piece / after the tune ([at, pitch, units, vel,
    {how}]); ``fill``: its notes where the tune rests; ``climax``: (from, to) where it
    plays a little louder over the full orchestra; ``stumble``: where the plucked pulse
    drops out with it."""
    s = copy.deepcopy(spec)
    s["lines"] = [l for l in s.get("lines") or [] if l["part"] != "solo_violin"]
    notes = _line(s, windows, wild, seed, top, 0, climax) + list(opening or []) + list(ending or []) + list(fill or [])
    notes.sort(key=lambda n: float(n[0]))
    for a, b in zip(notes, notes[1:]):                       # one violin: a note ends where the next begins
        a[2] = round(max(0.05, min(float(a[2]), float(b[0]) - float(a[0]) - 0.02)), 3)
    s["lines"].append({"part": "solo_violin", "vel": 0, "gain": gain, "notes": notes})
    s["unhinge"] = [{"parts": [p for p in follow], "from": a, "to": b + 0.25,
                     "drift": round(0.55 * wild, 2), "wobble": round(0.28 * wild, 2), "seed": i}
                    for i, (a, b) in enumerate(windows)]
    for a, b in stumble:
        kept = []
        for h in s.get("harmony") or []:
            if h["part"] == "pizzicato" and h["from"] < b and h["to"] > a:
                if h["from"] < a:
                    kept.append({**h, "to": a})
                if h["to"] > b:
                    kept.append({**h, "from": b})
            else:
                kept.append(h)
        s["harmony"] = kept
    return s
