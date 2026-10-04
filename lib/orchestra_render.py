#!/usr/bin/env python3
"""The orchestra's renderer for the table (lib/score_music.py runs it in the
orchestra's environment): one JSON job per line on stdin, one JSON answer per line
on stdout.

    {"kind": "score", "spec": {...an arrangement...}, "out": "x.ogg"}
    {"kind": "theme", "seed": "Kestrel", "cls": "Barbarian", "written": {...} | null,
     "stage": 1, "dark": 0, "wound": false, "out": "x.ogg"}     (arranged by rule)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import arrangement  # noqa: E402
import music_compose  # noqa: E402
import orchestra  # noqa: E402


def run(job: dict) -> dict:
    if job["kind"] == "score":
        samples, rate = arrangement.render(job["spec"])
    elif job["kind"] == "theme":
        stage = 0 if job.get("wound") else int(job.get("stage", 1))   # (a wound: a lone voice, a lament)
        tune = music_compose.leitmotif(job["seed"], "major", job.get("cls") or "", stage=stage,
                                       dark=int(job.get("dark", 0)), gen=2, written=job.get("written"))
        score, seconds = orchestra.arrange(tune, stage, int(job.get("dark", 0)))
        rate = orchestra.RATE
        samples = orchestra.master(orchestra.hall(orchestra.play(score, seconds), rate), rate)
    else:
        raise ValueError(f"unknown job kind {job['kind']!r}")
    path = music_compose.write(samples, rate, Path(job["out"]))
    return {"ok": True, "path": str(path), "seconds": round(len(samples) / rate, 1)}


def main() -> None:
    if not orchestra.SF2.is_file():
        orchestra.fetch(quiet=True)
    for line in sys.stdin:
        try:
            job = json.loads(line)
        except ValueError:
            continue
        try:
            out = run(job)
        except Exception as e:                     # one bad piece doesn't sink the rest
            out = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        print(json.dumps({**out, "id": job.get("id")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
