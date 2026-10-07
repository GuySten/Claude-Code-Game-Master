#!/usr/bin/env python3
"""Rate music with Meta's Audiobox Aesthetics (an open model that listens to audio
and predicts how people would rate it, 1-10):

  CE  content enjoyment      how much a listener enjoys it
  CU  content usefulness     how usable it is (as a soundtrack, a cue...)
  PC  production complexity  how much is going on (many layers -> higher)
  PQ  production quality     how clean and professional the sound is

    python3 lib/music_rate.py a.ogg b.mp3 ...           (a table, best enjoyment first)
    python3 lib/music_rate.py --json a.ogg               (one JSON line per file)

A second opinion beside the score critic (lib/arrangement.py check): the critic
reads the notes and measures what can be measured; this listens to the finished
sound. It judges recordings, not compositions - a real orchestra will outscore the
sampled one on PQ whatever the notes - so compare like with like, and trust the
host's ears over both. Needs torch, torchaudio, soundfile and audiobox_aesthetics
(gm-music.sh setup --rater); the model (~1 GB) downloads on first use.
"""

import argparse
import json
import sys
from typing import Dict, List

AXES = ("CE", "CU", "PC", "PQ")


def rate(paths: List[str]) -> List[Dict[str, float]]:
    import soundfile as sf
    import torch
    from audiobox_aesthetics.infer import AesPredictor
    pred = AesPredictor(checkpoint_pth=None, precision="float32")
    out = []
    for path in paths:
        x, sr = sf.read(path, always_2d=True, dtype="float32")
        r = pred.forward([{"path": torch.from_numpy(x.T.copy()), "sample_rate": sr}])[0]
        out.append({"file": path, **{k: round(float(r[k]), 2) for k in AXES}})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Rate music with Meta's Audiobox Aesthetics.")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rows = rate(a.files)
    if a.json:
        for r in rows:
            print(json.dumps(r, ensure_ascii=False))
        return
    print(f"{'file':40} {'enjoy':>6} {'useful':>6} {'complex':>7} {'quality':>7}")
    for r in sorted(rows, key=lambda r: -r["CE"]):
        name = r["file"].replace("\\", "/").rsplit("/", 1)[-1]
        print(f"{name[:40]:40} {r['CE']:6.2f} {r['CU']:6.2f} {r['PC']:7.2f} {r['PQ']:7.2f}")


if __name__ == "__main__":
    sys.exit(main())
