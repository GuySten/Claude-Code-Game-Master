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
    """Loudness, then soft edges (a looping theme gets short fades both ends)."""
    return fade(normalize(samples, rate), rate, 0.4 if loop else 0.05, 1.5 if loop else 2.0)


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


def _load():
    """The processor and model, in RAM (read from disk once per process)."""
    from transformers import AutoProcessor, MusicgenForConditionalGeneration
    if "processor" not in _cache:
        _cache["processor"] = AutoProcessor.from_pretrained(MODEL)
        _cache["model"] = MusicgenForConditionalGeneration.from_pretrained(MODEL).eval()
    return _cache["processor"], _cache["model"]


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
        model.to(device, torch.float32)
        inputs = processor(text=[prompt], padding=True, return_tensors="pt").to(device)
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


def run_job(job: dict, device: str) -> dict:
    """Compose one {prompt, seconds, out, loop} job -> its JSON answer."""
    started = time.time()
    try:
        samples, rate, used = generate(job["prompt"], job.get("seconds", 30), device)
        samples = finish(samples, rate, bool(job.get("loop")))
        path = write(samples, rate, Path(job["out"]))
        return {"ok": True, "path": str(path), "seconds": round(len(samples) / rate, 1),
                "device": used, "elapsed": round(time.time() - started, 1)}
    except Exception as e:                # one bad piece doesn't sink the rest
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def write(samples, rate: int, out: Path) -> Path:
    """OGG when this soundfile build can (small files), else WAV."""
    import soundfile as sf
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        sf.write(str(out), samples, rate)
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
