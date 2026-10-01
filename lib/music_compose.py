#!/usr/bin/env python3
"""Compose one piece of music with MusicGen, on this computer.

Runs in the composer's own environment (.compose-venv, made by
`bash tools/gm-music-compose.sh setup`), which has a GPU build of PyTorch and
Hugging Face transformers. The game itself stays CPU-only and never imports
this; it starts this script and reads the one JSON line it prints.

    python lib/music_compose.py --prompt "..." --seconds 30 --out music/x.ogg
    python lib/music_compose.py --batch jobs.json   # many pieces, ONE model load
    python lib/music_compose.py --check        # what hardware would be used
    python lib/music_compose.py --benchmark    # time one 30-second piece

The model (facebook/musicgen-small by default; COMPOSE_MODEL to change) is
downloaded from Hugging Face on first use. Its weights are licensed CC-BY-NC
4.0: fine for a home game, not for selling the music.
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

MODEL = os.environ.get("COMPOSE_MODEL", "facebook/musicgen-small")
TOKENS_PER_SECOND = 50          # MusicGen's audio frame rate
MAX_SECONDS = 30                # the model's context: ~1500 tokens


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


def pick_device(wanted: str = "auto") -> str:
    import torch
    if wanted != "auto":
        return wanted
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


_cache = {}


def _load(device: str):
    from transformers import AutoProcessor, MusicgenForConditionalGeneration
    if "processor" not in _cache:
        _cache["processor"] = AutoProcessor.from_pretrained(MODEL)
        _cache["model"] = MusicgenForConditionalGeneration.from_pretrained(MODEL)
    model = _cache["model"].to(device)
    return _cache["processor"], model


def generate(prompt: str, seconds: float, device: str):
    """(samples, sample_rate, device used). Falls back to the CPU when the GPU
    runs out of memory (e.g. while Forge holds an image model)."""
    import torch
    seconds = max(1.0, min(float(seconds), MAX_SECONDS))
    try:
        processor, model = _load(device)
        inputs = processor(text=[prompt], padding=True, return_tensors="pt").to(device)
        with torch.no_grad():
            audio = model.generate(**inputs, do_sample=True, guidance_scale=3.0,
                                   max_new_tokens=int(seconds * TOKENS_PER_SECOND) + 3)
    except RuntimeError as e:          # torch.cuda.OutOfMemoryError is a RuntimeError
        if device == "cpu" or "out of memory" not in str(e).lower():
            raise
        torch.cuda.empty_cache()
        print(f"[compose] the GPU is out of memory; composing on the CPU (slower)", file=sys.stderr)
        return generate(prompt, seconds, "cpu")
    rate = _cache["model"].config.audio_encoder.sampling_rate
    return audio[0, 0].float().cpu().numpy(), rate, device


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
    ap.add_argument("--batch", help="A JSON list of {prompt, seconds, out, loop}: composed in turn "
                                    "with the model loaded once (one JSON line per piece)")
    ap.add_argument("--check", action="store_true", help="Print the hardware that would be used")
    ap.add_argument("--benchmark", action="store_true", help="Time one 30-second piece")
    args = ap.parse_args()

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

    if args.batch:
        jobs = json.loads(Path(args.batch).read_text(encoding="utf-8"))
        for i, job in enumerate(jobs):
            started = time.time()
            try:
                samples, rate, used = generate(job["prompt"], job.get("seconds", 30), device)
                loop = bool(job.get("loop"))
                samples = fade(samples, rate, 0.4 if loop else 0.05, 1.5 if loop else 2.0)
                path = write(samples, rate, Path(job["out"]))
                print(json.dumps({"ok": True, "index": i, "path": str(path),
                                  "seconds": round(len(samples) / rate, 1), "device": used,
                                  "elapsed": round(time.time() - started, 1)}), flush=True)
            except Exception as e:            # one bad piece doesn't sink the rest
                print(json.dumps({"ok": False, "index": i, "error": f"{type(e).__name__}: {e}"}), flush=True)
        return

    if args.benchmark:
        args.prompt = "epic fantasy battle music, thundering drums, brass, strings"
        args.seconds = 30
        args.out = str(Path(tempfile.gettempdir()) / "gm-compose-benchmark.ogg")
    if not args.prompt or not args.out:
        ap.error("--prompt and --out are required")

    started = time.time()
    samples, rate, used = generate(args.prompt, args.seconds, device)
    samples = fade(samples, rate, 0.4 if args.loop else 0.05, 1.5 if args.loop else 2.0)
    path = write(samples, rate, Path(args.out))
    print(json.dumps({"ok": True, "path": str(path), "seconds": round(len(samples) / rate, 1),
                      "device": used, "elapsed": round(time.time() - started, 1)}))


if __name__ == "__main__":
    main()
