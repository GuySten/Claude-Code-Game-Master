#!/usr/bin/env python3
"""The host judge: an approximation of the host's own taste in the table's music,
so the host only has to listen when it can't tell.

Tested against the host's verdicts (lib: taste/verdicts.json), the judges that
read the *music* tracked the host and the audio models didn't: Meta's Audiobox
Aesthetics and SongEval agreed with the host about as often as a coin flip, while
the research tune scorer (lib/tune_score.py) and a blind reading of the notes by
a fresh Claude agent matched the host on every tune pair. So:

* Tunes: the tune scorer drops weak candidates (long notes off the beat, droning
  repetition, rhythm with no variety...); the survivors are judged in pairs,
  blind - each pair as anonymous X and Y note listings - by a fresh agent who
  doesn't know which is which; wins decide, the tune score breaks ties.
* Arrangements: the score critic (lib/arrangement.py check) must be clean, and
  the surprise budget balanced (a bold tune plainly set, a simple tune richly
  set: the host's 2x2).
* A close call - the top two candidates within a hair - is asked of the host as
  a quick A/B (two short clips), where "can't tell" is a fine answer. Every
  answer is recorded, and `validate` re-checks the automatic judges against all
  of them, so the judge never drifts from the host's taste.

    host_judge.py tunes prepare a.json b.json c.json --out DIR   (blind pairs for the reader)
    host_judge.py tunes decide DIR                               (-> the two finalists)
    host_judge.py finals prepare a-score.json b-score.json --out DIR   (each finalist arranged)
    host_judge.py finals decide DIR                              (the finished pieces decide)
    host_judge.py clips a.json b.json --out DIR                  (A/B clips to ask the host)
    host_judge.py record WINNER LOSER [--tie] [--note "..."]     (the host's answer)
    host_judge.py validate                                       (the judges vs every verdict)

A candidate tune file is either a hand-written tune (music_compose.written_tune's
shape: "motif", "again", ...) or a generator reference {"seed", "mode", "cls",
"gen"}; an arrangement is a score JSON (lib/arrangement.py).
"""

import argparse
import itertools
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import music_compose  # noqa: E402

CLOSE = 0.25        # a decision this close (share of the pair votes) goes to the host


# --- the host's verdicts ---
def store_path() -> Path:
    """<the campaigns folder>/taste/verdicts.json (HOST_TASTE overrides)."""
    if os.environ.get("HOST_TASTE"):
        return Path(os.environ["HOST_TASTE"])
    try:
        import campaign_manager
        campaign_manager.load_project_env()
        base = campaign_manager.resolve_world_state_base(campaign_manager.DEFAULT_WORLD_STATE)
    except Exception:
        base = os.environ.get("GM_WORLD_STATE_BASE") or "world-state"
    return Path(base) / "taste" / "verdicts.json"


def load() -> Dict[str, Any]:
    p = store_path()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data.setdefault("items", {})
    data.setdefault("verdicts", [])
    return data


def save(data: Dict[str, Any]) -> None:
    p = store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def item_id(spec: Dict[str, Any]) -> str:
    import hashlib
    return hashlib.sha1(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def record(winner: Dict[str, Any], loser: Dict[str, Any], tie: bool = False, note: str = "",
           kind: Optional[str] = None) -> Dict[str, Any]:
    """The host's answer to an A/B: winner over loser (or a tie: "can't tell")."""
    data = load()
    w, l = item_id(winner), item_id(loser)
    data["items"][w], data["items"][l] = winner, loser
    v = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": kind or kind_of(winner), "a": w, "b": l,
         "result": "tie" if tie else "a", **({"note": note} if note else {})}
    data["verdicts"].append(v)
    save(data)
    return v


def kind_of(spec: Dict[str, Any]) -> str:
    return "arrangement" if "melody" in spec or "chords" in spec else "tune"


# --- tunes ---
def tune_of(spec: Dict[str, Any], stage: int = 1) -> Dict[str, Any]:
    """A candidate tune file -> the tune (music_compose's dict)."""
    if "motif" in spec:
        return music_compose.written_tune(spec, stage=stage)
    return music_compose.leitmotif(spec["seed"], spec.get("mode", "major"), spec.get("cls", ""),
                                   stage=stage, gen=int(spec.get("gen", 1)))


def tune_floor(tune: Dict[str, Any], max_range: int = 19) -> Tuple[float, List[str]]:
    """(the research score, its red flags). Red flags drop a candidate: long notes
    off the beat, droning repetition, a rhythm with no variety, broken tune rules.
    (Unusual in the other direction - few repeats, many leaps - is character, not a
    flaw: the host's favourite tunes were bolder than folk tunes.)"""
    import tune_score
    mel = tune_score.from_leitmotif(tune)
    f = tune_score.features(mel)
    flags = []
    if f["long_on_beat"] < .95:                       # (96% of real tunes have none off the beat)
        flags.append(f"{round(100 * (1 - f['long_on_beat']))}% of its long notes start off the beat")
    composite = 0.0
    if tune_score.CACHE.is_file():
        s = tune_score.score(mel)
        composite = s["composite"]
        if s["repeat_share"][1] > 95:
            flags.append(f"drones: repeated notes past the {s['repeat_share'][1]}th percentile of real tunes")
        if s["rhythm_entropy"][1] < 5:
            flags.append("its rhythm has almost no variety")
    t = music_compose.theme_traits(tune)
    if not (t["whole_bars"] and t["ends_home"] and t["range"] <= max_range and t["biggest_jump"] <= 12):
        flags.append("breaks the tune rules (whole bars, ending home, range, leaps)")
    return composite, flags


def versatility(spec: Dict[str, Any]) -> Dict[str, List[str]]:
    """A leitmotif is heard in many forms: its red flags as the seed, heroic and
    legendary versions, darkened, and the villain's (the dark twin). {} = all sound.
    (Raised climaxes may reach 21 semitones: the orchestra, not a singer, plays them.)"""
    out = {}
    for label, mode, kw, rng in (("seed", "major", {"stage": 0}, 19), ("heroic", "major", {"stage": 2}, 21),
                                 ("legendary", "major", {"stage": 3}, 21), ("darkened", "major", {"dark": 2}, 19),
                                 ("villain", "minor", {}, 21)):
        if "motif" in spec:
            tune = music_compose.written_tune(spec, mode, **kw)
        else:
            tune = music_compose.leitmotif(spec["seed"], mode, spec.get("cls", ""), gen=int(spec.get("gen", 1)), **kw)
        flags = tune_floor(tune, rng)[1]
        if flags:
            out[label] = flags
    return out


def describe_tune(tune: Dict[str, Any]) -> str:
    """A note listing for the blind reader (no names, no versions)."""
    import arrangement
    bar = tune["bar"]
    rows = [f"meter {tune['meter']}, tonic {arrangement.name_of(tune['key'])}, "
            f"scale {tune['scale'] if isinstance(tune['scale'], str) else tune['scale']}",
            "at(units) bar.pos note length(units)"]
    u = 0.0
    for st, b in tune["notes"]:
        rows.append(f"{u:g} {int(u // bar) + 1}.{u % bar:g} {arrangement.name_of(tune['key'] + st)} {b:g}")
        u += b
    return "\n".join(rows)


READER = """You are judging melodies blind, from notation only, to predict which of two a
regular listener (a player at a tabletop RPG night, not a musician) would prefer as a
character's theme. Each folder pairNN holds X.txt and Y.txt: a melody listed note by
note (time in units - eighths in 6/8, beats otherwise - bar.position, note, length).
Imagine each on a clarinet over a soft drone. Judge how memorable and characterful the
hook is, whether long notes land on the beat, rhythmic life, the shape and climax, and a
level of surprise that engages without confusing. Read only these files. Write
verdicts.json in this folder: {"pair00": {"prefer": "X" or "Y", "confidence": 50-100,
"why": "..."}, ...}."""


def prepare_tunes(files: List[Path], out: Path, seed: int = 0) -> Dict[str, Any]:
    """Drop the weak, then blind pairs of the rest for a fresh reader."""
    out.mkdir(parents=True, exist_ok=True)
    cands, dropped = {}, {}
    for f in files:
        spec = json.loads(Path(f).read_text(encoding="utf-8"))
        tune = tune_of(spec)
        composite, flags = tune_floor(tune)
        (dropped if flags else cands)[str(f)] = {"spec": spec, "composite": composite, "flags": flags}
    rng = random.Random(seed or int(time.time()))
    key = {}
    for i, (a, b) in enumerate(itertools.combinations(sorted(cands), 2)):
        x, y = (a, b) if rng.random() < .5 else (b, a)
        d = out / f"pair{i:02d}"
        d.mkdir(exist_ok=True)
        (d / "X.txt").write_text(describe_tune(tune_of(cands[x]["spec"])))
        (d / "Y.txt").write_text(describe_tune(tune_of(cands[y]["spec"])))
        key[d.name] = {"X": x, "Y": y}
    (out / "README.txt").write_text(READER)
    state = {"candidates": cands, "dropped": dropped, "key": key}
    (out.parent / f"{out.name}.key.json").write_text(json.dumps(state, indent=1, ensure_ascii=False))
    return state


def decide_tunes(out: Path) -> Dict[str, Any]:
    """Rank the candidates from the blind verdicts (wins weighted by confidence),
    ties broken by the tune score; "ask_host" when the top two are too close."""
    state = json.loads((out.parent / f"{out.name}.key.json").read_text(encoding="utf-8"))
    verdicts = json.loads((out / "verdicts.json").read_text(encoding="utf-8"))
    cands = state["candidates"]
    wins = {c: 0.0 for c in cands}
    games = {c: 0 for c in cands}
    for pair, k in state["key"].items():
        v = verdicts.get(pair)
        if not v:
            continue
        w = (v.get("confidence", 75) - 50) / 50          # 0 (a coin flip) .. 1 (certain)
        win, lose = (k["X"], k["Y"]) if v["prefer"] == "X" else (k["Y"], k["X"])
        wins[win] += .5 + w / 2
        wins[lose] += .5 - w / 2
        games[win] += 1
        games[lose] += 1
    share = {c: wins[c] / games[c] if games[c] else .5 for c in cands}
    ranking = sorted(cands, key=lambda c: (share[c], cands[c]["composite"]), reverse=True)
    close = len(ranking) > 1 and share[ranking[0]] - share[ranking[1]] < CLOSE / 2
    finalists = [c for c in ranking if not versatility(cands[c]["spec"])][:2]
    return {"ranking": [(c, round(share[c], 3), cands[c]["composite"]) for c in ranking],
            "dropped": {c: d["flags"] for c, d in state["dropped"].items()},
            "finalists": finalists,            # (to be arranged and judged as finished pieces)
            "close": close}


# --- arrangements ---
def judge_arrangement(spec: Dict[str, Any]) -> Dict[str, Any]:
    """The critic (errors and warnings must be zero) and the surprise budget."""
    import arrangement
    found = arrangement.check(spec, listen=False)
    ctx = arrangement._build(spec)
    budget = arrangement.surprise_budget(ctx, spec)
    errors = [m for lv, m in found if lv == "error"]
    warns = [m for lv, m in found if lv == "warn"]
    balanced = budget is None or budget[3] == "balanced"
    return {"ok": not errors and not warns, "errors": errors, "warnings": warns,
            "budget": budget[3] if budget else "unmeasured", "score": (0 if errors else 1) + (1 if not warns else 0)
            + (1 if balanced else 0)}


# --- the finals: the finalist tunes, each arranged, judged as finished music ---
SCORE_READER = """You are judging finished orchestral pieces blind, from their scores, to predict
which a regular listener (a player at a tabletop RPG night) would enjoy more as that
character's music. Each folder pairNN holds X.json and Y.json: arrangement scores in the
format documented at the top of lib/arrangement.py (read it; arrangement._build(spec) gives
the tune's notes and the chords). Judge the music as heard: how memorable the tune is in
its setting, whether the orchestration serves it, the development and the build, and a
level of surprise that engages without overloading. Don't render or rate audio. Read only
these files and lib/. Write verdicts.json in this folder: {"pair00": {"prefer": "X" or
"Y", "confidence": 50-100, "why": "..."}, ...}."""


def _clean(spec: Dict[str, Any]) -> Dict[str, Any]:
    """A score without anything that names or describes it (titles, notes, a
    written tune's "kind" - its nickname - or "name"): the reader judges the music."""
    spec = json.loads(json.dumps(spec))
    for k in [k for k in spec if k in ("title", "notes", "comment", "about") or k.startswith("_")]:
        spec.pop(k)
    written = (spec.get("tune") or {}).get("written")
    if isinstance(written, dict):
        for k in ("kind", "name", "title", "notes"):
            written.pop(k, None)
    return spec


def prepare_finals(files: List[Path], out: Path, seed: int = 0) -> Dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    cands = {}
    for f in files:
        spec = json.loads(Path(f).read_text(encoding="utf-8"))
        cands[str(f)] = {"spec": spec, "checks": judge_arrangement(spec)}
    rng = random.Random(seed or int(time.time()))
    key = {}
    for i, (a, b) in enumerate(itertools.combinations(sorted(cands), 2)):
        x, y = (a, b) if rng.random() < .5 else (b, a)
        d = out / f"pair{i:02d}"
        d.mkdir(exist_ok=True)
        (d / "X.json").write_text(json.dumps(_clean(cands[x]["spec"]), indent=1, ensure_ascii=False))
        (d / "Y.json").write_text(json.dumps(_clean(cands[y]["spec"]), indent=1, ensure_ascii=False))
        key[d.name] = {"X": x, "Y": y}
    (out / "README.txt").write_text(SCORE_READER)
    state = {"candidates": cands, "key": key}
    (out.parent / f"{out.name}.key.json").write_text(json.dumps(state, indent=1, ensure_ascii=False))
    return state


def decide_finals(out: Path, ask: bool = True) -> Dict[str, Any]:
    """The finished pieces ranked: the critic and the surprise budget first (a piece
    with errors, warnings or an unbalanced budget loses), then the blind reader.
    ``ask=False`` (an important NPC: the host chooses only their own characters'
    tunes): a close call is decided here too, by the ranking."""
    state = json.loads((out.parent / f"{out.name}.key.json").read_text(encoding="utf-8"))
    verdicts = json.loads((out / "verdicts.json").read_text(encoding="utf-8"))
    cands = state["candidates"]
    wins = {c: 0.0 for c in cands}
    games = {c: 0 for c in cands}
    for pair, k in state["key"].items():
        v = verdicts.get(pair)
        if not v:
            continue
        w = (v.get("confidence", 75) - 50) / 50
        win, lose = (k["X"], k["Y"]) if v["prefer"] == "X" else (k["Y"], k["X"])
        wins[win] += .5 + w / 2
        wins[lose] += .5 - w / 2
        games[win] += 1
        games[lose] += 1
    share = {c: wins[c] / games[c] if games[c] else .5 for c in cands}
    ranking = sorted(cands, key=lambda c: (cands[c]["checks"]["score"], share[c]), reverse=True)
    close = (len(ranking) > 1 and cands[ranking[0]]["checks"]["score"] == cands[ranking[1]]["checks"]["score"]
             and share[ranking[0]] - share[ranking[1]] < CLOSE / 2)
    return {"ranking": [(c, round(share[c], 3), cands[c]["checks"]) for c in ranking],
            "ask_host": [ranking[0], ranking[1]] if close and ask else None,
            "winner": None if close and ask else ranking[0], "close": bool(close)}


# --- asking the host ---
def tune_clip(spec: Dict[str, Any], out: Path, bpm: float = 66) -> Path:
    """The tune alone on a clarinet over a soft drone of its keynote and fifth."""
    import orchestra
    tune = tune_of(spec)
    unit = 60 / bpm / (3 if tune["meter"] == "6/8" else 1)
    sc, u, key = orchestra.Score(), 0.0, tune["key"]
    lo = min(key + st for st, _ in tune["notes"])
    shift = 12 if lo < 52 else 0
    for st, b in tune["notes"]:
        sc.note("clarinets", key + st + shift, 1.0 + u * unit, b * unit * .95, 92)
        u += b
    end = 1.0 + u * unit
    for k in (key - 12, key - 5):
        sc.note("strings", k, 0.0, end + .5, 52)
    x = orchestra.master(orchestra.hall(orchestra.play(sc, end + .5)))
    return music_compose.write(x, orchestra.RATE, out)


def clips(files: List[Path], out: Path) -> List[Path]:
    """A/B clips for the host: a tune alone, or an arrangement rendered."""
    import arrangement
    out.mkdir(parents=True, exist_ok=True)
    made = []
    for label, f in zip("AB", files):
        spec = json.loads(Path(f).read_text(encoding="utf-8"))
        if kind_of(spec) == "tune":
            made.append(tune_clip(spec, out / f"{label}.ogg"))
        else:
            x, r = arrangement.render(spec)
            made.append(music_compose.write(x, r, out / f"{label}.ogg"))
    return made


# --- keeping the judge honest ---
def validate() -> Dict[str, Any]:
    """The automatic judges vs every verdict of the host's: how often they agree."""
    data = load()
    out = {"tune score": [0, 0], "arrangement checks": [0, 0]}
    for v in data["verdicts"]:
        if v["result"] == "tie":
            continue
        a, b = data["items"][v["a"]], data["items"][v["b"]]
        if v["kind"] == "tune":
            sa, sb = tune_floor(tune_of(a))[0], tune_floor(tune_of(b))[0]
            key = "tune score"
        else:
            sa, sb = judge_arrangement(a)["score"], judge_arrangement(b)["score"]
            key = "arrangement checks"
        if sa == sb:
            continue
        out[key][0] += sa > sb
        out[key][1] += 1
    return {k: f"{r}/{n}" for k, (r, n) in out.items()} | {"verdicts": len(data["verdicts"])}


def main() -> None:
    ap = argparse.ArgumentParser(description="The host judge: the host's taste, approximated.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tunes")
    t.add_argument("step", choices=["prepare", "decide"])
    t.add_argument("files", nargs="*")
    t.add_argument("--out", required=False)
    fz = sub.add_parser("finals", help="the finalists, each arranged: judged as finished pieces")
    fz.add_argument("step", choices=["prepare", "decide"])
    fz.add_argument("files", nargs="*")
    fz.add_argument("--out", required=False)
    fz.add_argument("--no-host", action="store_true",
                    help="an important NPC: decide close calls too (the host picks only their own characters')")
    c = sub.add_parser("clips")
    c.add_argument("files", nargs=2)
    c.add_argument("--out", required=True)
    r = sub.add_parser("record")
    r.add_argument("winner")
    r.add_argument("loser")
    r.add_argument("--tie", action="store_true", help="the host couldn't tell them apart")
    r.add_argument("--note", default="")
    sub.add_parser("validate")
    a = ap.parse_args()
    if a.cmd == "tunes":
        if a.step == "prepare":
            st = prepare_tunes([Path(f) for f in a.files], Path(a.out))
            print(json.dumps({"pairs": len(st["key"]), "dropped": {k: v["flags"] for k, v in st["dropped"].items()},
                              "next": f"a fresh agent reads {a.out}/README.txt and writes {a.out}/verdicts.json"},
                             indent=1, ensure_ascii=False))
        else:
            print(json.dumps(decide_tunes(Path(a.out or a.files[0])), indent=1, ensure_ascii=False))
    elif a.cmd == "finals":
        if a.step == "prepare":
            st = prepare_finals([Path(f) for f in a.files], Path(a.out))
            print(json.dumps({"pairs": len(st["key"]), "checks": {k: v["checks"] for k, v in st["candidates"].items()},
                              "next": f"a fresh agent reads {a.out}/README.txt and writes {a.out}/verdicts.json"},
                             indent=1, ensure_ascii=False))
        else:
            print(json.dumps(decide_finals(Path(a.out or a.files[0]), ask=not a.no_host), indent=1, ensure_ascii=False))
    elif a.cmd == "clips":
        print("\n".join(str(p) for p in clips([Path(f) for f in a.files], Path(a.out))))
    elif a.cmd == "record":
        w = json.loads(Path(a.winner).read_text(encoding="utf-8"))
        lo = json.loads(Path(a.loser).read_text(encoding="utf-8"))
        print(json.dumps(record(w, lo, a.tie, a.note), ensure_ascii=False))
    else:
        print(json.dumps(validate(), indent=1))


if __name__ == "__main__":
    main()
