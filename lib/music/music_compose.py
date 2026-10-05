#!/usr/bin/env python3
"""Compose one piece of music with MusicGen, on this computer.

Runs in the composer's own environment (.compose-venv, made by
`bash tools/gm-music-compose.sh setup`), which has a GPU build of PyTorch and
Hugging Face transformers. The game itself stays CPU-only and never imports
this; it starts this script and reads the JSON lines it prints.

    python lib/music_compose.py --prompt "..." --seconds 30 --out music/x.ogg
    python lib/music_compose.py --serve        # stay running, model in RAM (the table uses this)
    python lib/music_compose.py --normalize a.ogg b.ogg   # bring old pieces up to volume
    python lib/music_compose.py --check        # what hardware would be used
    python lib/music_compose.py --benchmark    # time one 30-second piece

The model (facebook/musicgen-small by default; COMPOSE_MODEL to change) is
downloaded from Hugging Face on first use. Its weights are licensed CC-BY-NC
4.0: fine for a home game, not for selling the music.

COMPOSE_MODEL=facebook/musicgen-melody makes the bigger melody model (1.5 B
parameters, half precision on the GPU) the composer for everything.

A piece can have a dark TWIN: the same music, made ominous (a hero's anthem and
the villain theme they'd become). MusicGen-Melody re-composes it on the melody of
the original, changing everything else: with COMPOSE_TWIN=auto (the default) when
it is the composer, or downloaded already (`gm-music-compose.sh setup --melody`)
and there's a GPU. Otherwise, or if that fails, the original recording itself is
darkened: slower and lower, muffled, with a cavernous echo.
"""

import argparse
import faulthandler
import json
import os
import sys
import tempfile
import time
from pathlib import Path

MODEL = os.environ.get("COMPOSE_MODEL", "facebook/musicgen-small")
MELODY_MODEL = os.environ.get("COMPOSE_MELODY_MODEL", "facebook/musicgen-melody")
TWIN = os.environ.get("COMPOSE_TWIN", "auto").strip().lower()        # auto | melody | darken
TOKENS_PER_SECOND = 50          # MusicGen's audio frame rate
MAX_SECONDS = 30                # the model's context: ~1500 tokens
# How loud a finished piece is (gated RMS, dBFS: close to LUFS for music). MusicGen's
# raw output is often 15-20 dB quieter than ordinary music; -14 matches what music
# services play at.
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
    """A villain's weight, whatever the model made of "heavy deep bass": the deep bass
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
    at ``peak_at`` (a fraction of the piece: the tune's climax), then full to the end.
    (The melody model hears only which note leads, not how loud: the build is shaped
    here, on the music itself.)"""
    import numpy as np
    x = np.asarray(samples, dtype="float32")
    t = np.linspace(0.0, 1.0, len(x), dtype="float64")
    p = np.clip(t / max(peak_at, 1e-3), 0.0, 1.0)
    ramp = p * p * (3 - 2 * p)                                 # smoothstep: no sudden swell
    return (x * 10 ** (-depth_db * (1 - ramp) / 20)).astype("float32")


def pick_device(wanted: str = "auto") -> str:
    import torch
    if wanted != "auto":
        return wanted
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


_cache = {}
# With a GPU, the model waits in RAM between pieces (in half precision: half the
# RAM) and is on the card, in full precision, only while it composes, so Forge can
# have the card the rest of the time. COMPOSE_RAM_HALF=0 keeps full precision in RAM.
PARK_HALF = os.environ.get("COMPOSE_RAM_HALF", "1").strip().lower() not in ("0", "no", "off", "false")


def is_melody(name: str) -> bool:
    """Is this checkpoint a MusicGen-Melody one (it needs its own model class)?"""
    from transformers import AutoConfig
    return AutoConfig.from_pretrained(name).model_type == "musicgen_melody"


def _model_class(name: str):
    import transformers
    return (transformers.MusicgenMelodyForConditionalGeneration if is_melody(name)
            else transformers.MusicgenForConditionalGeneration)


def _load():
    """The processor and model, in RAM (read from disk once per process)."""
    from transformers import AutoProcessor
    if "processor" not in _cache:
        _cache["processor"] = AutoProcessor.from_pretrained(MODEL)
        _cache["model"] = _model_class(MODEL).from_pretrained(MODEL).eval()
    return _cache["processor"], _cache["model"]


def _gpu_dtype(model):
    """Big models (the 1.5 B melody one) run in half precision on the card."""
    import torch
    return torch.float16 if sum(p.numel() for p in model.parameters()) > 1e9 else torch.float32


def _park(model) -> None:
    """Off the graphics card, into RAM, and give the card's memory back."""
    import torch
    if torch.cuda.is_available():
        model.to("cpu", torch.float16 if PARK_HALF else torch.float32)
        torch.cuda.empty_cache()


def generate(prompt: str, seconds: float, device: str):
    """(samples, sample_rate, device used). The model goes to ``device`` for this
    piece and back to RAM after it. Falls back to the CPU when the GPU runs out
    of memory."""
    import torch
    seconds = max(1.0, min(float(seconds), MAX_SECONDS))
    processor, model = _load()
    step = lambda what: print(f"[compose] {what}", file=sys.stderr, flush=True)  # noqa: E731
    try:
        step(f"moving the model to {device}")
        dtype = _gpu_dtype(model) if device != "cpu" else torch.float32
        model.to(device, dtype)
        inputs = processor(text=[prompt], padding=True, return_tensors="pt").to(device)
        if dtype != torch.float32:
            inputs = {k: (v.to(dtype) if v.is_floating_point() else v) for k, v in inputs.items()}
        step(f"composing {seconds:.0f} s on {device}")
        with torch.no_grad():
            audio = model.generate(**inputs, do_sample=True, guidance_scale=3.0,
                                   max_new_tokens=int(seconds * TOKENS_PER_SECOND) + 3)
        samples = audio[0, 0].float().cpu().numpy()
        step("composed")
    except RuntimeError as e:          # torch.cuda.OutOfMemoryError is a RuntimeError
        if device == "cpu" or "out of memory" not in str(e).lower():
            raise
        _park(model)
        print("[compose] the GPU is out of memory; composing on the CPU (slower)", file=sys.stderr)
        return generate(prompt, seconds, "cpu")
    finally:
        if device != "cpu":
            _park(model)
    return samples, model.config.audio_encoder.sampling_rate, device


# --- a character's leitmotif: a tune of their own, for the melody model to follow ---
# MusicGen left to itself tends to loop one short phrase. Given a melody line, the
# melody model arranges THAT. So each character gets a motif from their name (always
# the same) and their class, built the way film themes are, laid out as a phrase
# that goes somewhere; their dark twin is the same tune turned villainous.
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
    """The tune as a plain synthesized melody line (what the melody model hears):
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


def _load_melody():
    from transformers import AutoProcessor, MusicgenMelodyForConditionalGeneration
    if is_melody(MODEL):                    # the composer IS the melody model: no second copy
        return _load()
    if "melody" not in _cache:
        _cache["melody_processor"] = AutoProcessor.from_pretrained(MELODY_MODEL)
        _cache["melody"] = MusicgenMelodyForConditionalGeneration.from_pretrained(MELODY_MODEL).eval()
    return _cache["melody_processor"], _cache["melody"]


def melody_generate(base, rate: int, prompt: str, seconds: float, device: str):
    """MusicGen-Melody: the description's music, on the melody of ``base``."""
    import numpy as np
    import torch
    processor, model = _load_melody()
    want = processor.feature_extractor.sampling_rate
    audio = np.asarray(base, dtype="float32")
    if rate != want:
        audio = np.interp(np.arange(int(len(audio) * want / rate)) * rate / want,
                          np.arange(len(audio)), audio).astype("float32")
    seconds = max(1.0, min(float(seconds), MAX_SECONDS))
    half = device != "cpu"                  # (1.5 B parameters: half precision on the card)
    try:
        model.to(device, torch.float16 if half else torch.float32)
        inputs = processor(audio=audio, sampling_rate=want, text=[prompt], padding=True,
                           return_tensors="pt").to(device)
        if half:
            inputs = {k: (v.half() if v.is_floating_point() else v) for k, v in inputs.items()}
        with torch.no_grad():
            out = model.generate(**inputs, do_sample=True, guidance_scale=3.0,
                                 max_new_tokens=int(seconds * TOKENS_PER_SECOND) + 3)
        return out[0, 0].float().cpu().numpy(), model.config.audio_encoder.sampling_rate
    finally:
        if device != "cpu":
            _park(model)


def melody_ready() -> bool:
    """Can a twin be re-composed on the melody without a download? (auto mode)"""
    try:
        if is_melody(MODEL):
            return True
        from huggingface_hub import try_to_load_from_cache
        return isinstance(try_to_load_from_cache(MELODY_MODEL, "config.json"), str)
    except Exception:
        return False


def twin_mode(device: str) -> str:
    if TWIN in ("melody", "darken"):
        return TWIN
    return "melody" if device != "cpu" and melody_ready() else "darken"


def twin_from(base, rate: int, prompt: str, seconds: float, device: str):
    """(samples, rate, how): the dark twin of ``base``."""
    if twin_mode(device) == "melody":
        try:
            samples, out_rate = melody_generate(base, rate, prompt, seconds, device)
            return samples, out_rate, "melody"
        except Exception as e:             # not downloaded, offline, out of memory...
            print(f"[compose] the melody model failed ({type(e).__name__}: {e}); "
                  "darkening the recording instead", file=sys.stderr, flush=True)
    return darken(base, rate), rate, "darkened"


def _leitmotif_piece(job: dict, device: str):
    """(samples, rate) composed on the job's leitmotif by the melody model, or None
    (no melody model here, or it failed: the caller composes as before)."""
    lm = job["leitmotif"]
    if twin_mode(device) != "melody":
        return None
    try:
        seconds = max(1.0, min(float(job.get("seconds", 30)), MAX_SECONDS))
        score = render_leitmotif(lm["seed"], lm.get("mode", "major"), seconds, cls=lm.get("cls") or "",
                                 **{k: lm[k] for k in ("stage", "dark") if k in lm})
        return melody_generate(score, 32000, job["prompt"], seconds, device)
    except Exception as e:
        print(f"[compose] the leitmotif piece failed ({type(e).__name__}: {e}); composing freely",
              file=sys.stderr, flush=True)
        return None


def run_job(job: dict, device: str) -> dict:
    """Compose one {prompt, seconds, out, loop} job -> its JSON answer."""
    started = time.time()
    try:
        extra = {}
        lm = job.get("leitmotif")
        score = _leitmotif_piece(job, device) if lm else None
        if score is not None:               # a character's own tune, arranged by the melody model
            samples, rate = score
            used, extra = device, {"how": "leitmotif"}
        elif job.get("melody_from"):        # this piece IS a twin: of a piece already made
            import soundfile as sf
            base, base_rate = sf.read(job["melody_from"], dtype="float32", always_2d=False)
            if getattr(base, "ndim", 1) > 1:
                base = base.mean(axis=1)
            samples, rate, how = twin_from(base, base_rate, job["prompt"], job.get("seconds", 30), device)
            used, extra = device, {"how": how}
        else:
            samples, rate, used = generate(job["prompt"], job.get("seconds", 30), device)
        raw = samples
        if extra.get("how") == "leitmotif" and not job.get("loop"):          # an anthem: build to its climax
            arc = {k: lm[k] for k in ("stage", "dark") if k in lm}
            peak = theme_traits(leitmotif(lm["seed"], lm.get("mode", "major"), lm.get("cls") or "", **arc))["climax_at"]
            gentle = lm.get("stage", 1) == 0 or lm.get("wound")                 # (a lone voice, a lament)
            samples = crescendo(samples, rate, peak, 3.0 if gentle else 7.0)
        if job.get("heavy"):                # a villain theme: its weight, for certain
            samples = heavy(samples, rate)
        samples = finish(samples, rate, bool(job.get("loop")))
        path = write(samples, rate, Path(job["out"]))
        twin = job.get("twin")
        t_score = _leitmotif_piece({**twin, "seconds": twin.get("seconds", job.get("seconds", 30))}, device) \
            if twin and twin.get("leitmotif") else None
        if t_score is not None:             # the same tune in the minor: the dark twin
            (t_samples, t_rate), how = t_score, "leitmotif"
        elif twin:                          # and its dark twin, from the same music
            t_samples, t_rate, how = twin_from(raw, rate, twin["prompt"], twin.get("seconds", job.get("seconds", 30)), device)
        if twin:                            # (a twin is always the dark one: heavy)
            t_samples = finish(heavy(t_samples, t_rate), t_rate, bool(twin.get("loop")))
            t_path = write(t_samples, t_rate, Path(twin["out"]))
            extra["twin"] = {"path": str(t_path), "seconds": round(len(t_samples) / t_rate, 1), "how": how}
        return {"ok": True, "path": str(path), "seconds": round(len(samples) / rate, 1),
                "device": used, "elapsed": round(time.time() - started, 1), **extra}
    except Exception as e:                # one bad piece doesn't sink the rest
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def write(samples, rate: int, out: Path) -> Path:
    """OGG when this soundfile build can (small files), else WAV."""
    import soundfile as sf
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        # In blocks: libsndfile's OGG encoder can crash on one very long write.
        channels = 1 if getattr(samples, "ndim", 1) == 1 else samples.shape[1]
        with sf.SoundFile(str(out), "w", samplerate=rate, channels=channels) as f:
            for i in range(0, len(samples), 1 << 16):
                f.write(samples[i:i + (1 << 16)])
        return out
    except Exception:
        wav = out.with_suffix(".wav")
        sf.write(str(wav), samples, rate)
        return wav


def main() -> None:
    ap = argparse.ArgumentParser(description="Compose music with MusicGen (local)")
    ap.add_argument("--prompt", help="What the music should sound like")
    ap.add_argument("--seconds", type=float, default=30)
    ap.add_argument("--out", help="Where to write it (.ogg)")
    ap.add_argument("--loop", action="store_true", help="A looping theme: short fades both ends")
    ap.add_argument("--device", default=os.environ.get("COMPOSE_DEVICE", "auto"),
                    help="auto (GPU if there is one), cuda, or cpu")
    ap.add_argument("--serve", action="store_true",
                    help="Keep running with the model in RAM: JSON jobs on stdin, answers on stdout")
    ap.add_argument("--normalize", nargs="+", metavar="FILE",
                    help="Bring already-composed pieces to the standard loudness, in place")
    ap.add_argument("--check", action="store_true", help="Print the hardware that would be used")
    ap.add_argument("--benchmark", action="store_true", help="Time one 30-second piece")
    ap.add_argument("--class", dest="cls", default="", help="With --leitmotif: the character's class")
    ap.add_argument("--leitmotif", metavar="NAME",
                    help="Write NAME's leitmotif (and its dark twin) as plain melody files to --out's folder")
    ap.add_argument("--fetch-melody", action="store_true",
                    help="Download the melody model (for COMPOSE_TWIN=melody) and exit")
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

    if args.fetch_melody:
        _load_melody()
        print(json.dumps({"ok": True, "model": MELODY_MODEL}))
        return

    import torch
    device = pick_device(args.device)
    if args.check:
        info = {"ok": True, "torch": torch.__version__, "device": device, "model": MODEL,
                "cuda": torch.cuda.is_available()}
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            info.update(gpu=props.name, vram_gb=round(props.total_memory / 2**30, 1),
                        capability=f"{props.major}.{props.minor}")
        print(json.dumps(info))
        return

    if args.serve:
        # A crash inside torch/CUDA kills the process with no Python error at all:
        # this writes where it happened to the log (stderr), Windows crashes included.
        faulthandler.enable(file=sys.stderr, all_threads=True)
        # Stay running: the model is read from disk ONCE and waits in RAM. One JSON
        # job per line in, one JSON answer per line out (with the job's "id").
        _, model = _load()
        if device != "cpu":
            _park(model)
        print(json.dumps({"ready": True, "device": device, "model": MODEL}), flush=True)
        for line in sys.stdin:
            try:
                job = json.loads(line)
            except ValueError:
                continue
            print(json.dumps({**run_job(job, device), "id": job.get("id")}), flush=True)
        return

    if args.benchmark:
        args.prompt = "epic fantasy battle music, thundering drums, brass, strings"
        args.seconds = 30
        args.out = str(Path(tempfile.gettempdir()) / "gm-compose-benchmark.ogg")
    if not args.prompt or not args.out:
        ap.error("--prompt and --out are required")

    started = time.time()
    samples, rate, used = generate(args.prompt, args.seconds, device)
    samples = finish(samples, rate, args.loop)
    path = write(samples, rate, Path(args.out))
    print(json.dumps({"ok": True, "path": str(path), "seconds": round(len(samples) / rate, 1),
                      "device": used, "elapsed": round(time.time() - started, 1)}))


if __name__ == "__main__":
    main()
