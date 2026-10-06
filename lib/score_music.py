#!/usr/bin/env python3
"""Written music at the table: the GM's scores (lib/arrangement.py), played by the
sampled orchestra (lib/orchestra.py), take the place of AI-composed audio.

A score in the campaign's music/arrangements/ says what it is for with "use":
    {"use": {"as": "anthem", "who": "Kestrel", "stage": 2}}   # a PC at a point of their story
                                                               # (+ "dark", "wound", "warm")
    {"use": {"as": "dark", "who": "Kestrel"}}                 # their dark twin (the villain they'd be)
    {"use": {"as": "theme", "who": "Margrave Ostrec Vane"}}   # a villain's theme (a loop)
    {"use": {"as": "boss", "who": "Dobbin Rusk"}}             # a boss fight (a loop)
    {"use": {"as": "place", "place": "The Hip"}}              # a place's music (a quiet loop)
The table renders each one (again whenever it changes) into music/anthems/,
music/themes/ or music/places/ and lists it in music-composed.json, where the rest of
the table already looks: an anthem plays at a heroic moment, a theme when its foe
appears, a place's music while the party is there.

Until the GM has written a piece, the orchestra still plays: a PC's anthem in the
version their story has reached, arranged by rule from their tune (music/tunes/, the
GM's hand-written tunes; else the generator's), and a place's music from a sketch
(place_sketch: the adventure's signature motif, in the place's colour). What is
still waiting to be written is listed by wanted() (gm-music-compose.sh wanted).

The orchestra needs numpy, soundfile and tinysoundfont (gm-music-compose.sh setup
--orchestra): rendering runs in that environment (lib/orchestra_render.py), here or
on the host laptop's GPU server; this module itself needs nothing but Python.
"""

import base64
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import character_arcs  # noqa: E402
import composer  # noqa: E402
import gpu_remote  # noqa: E402

RENDERER = Path(__file__).resolve().parent / "orchestra_render.py"
SF2 = Path(os.environ.get("ORCHESTRA_SF2") or Path.home() / ".cache" / "gm-orchestra" / "MuseScore_General.sf2")
USES = ("anthem", "dark", "theme", "boss", "place")
WANTED = "music-wanted.json"
SIGNATURE = "signature.json"          # music/tunes/: the adventure's own motif
PLACE_MINUTES = 10                    # play at a place before it earns its music
NO_WINDOW = {"creationflags": 0x08000000} if os.name == "nt" else {}


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _same(a: Any, b: Any) -> bool:
    return " ".join(str(a or "").split()).casefold() == " ".join(str(b or "").split()).casefold()


def slug(name: str) -> str:
    return composer.slug(name)


# --- the tunes and the scores ---
def tunes(campaign_dir) -> Dict[str, Dict[str, Any]]:
    """The GM's hand-written tunes (music/tunes/*.json), by whose they are (their "seed")."""
    out = {}
    for f in sorted((Path(campaign_dir) / "music" / "tunes").glob("*.json")):
        spec = _read(f, None)
        if f.name != SIGNATURE and isinstance(spec, dict) and spec.get("seed") and spec.get("motif"):
            out[spec["seed"]] = spec
    return out


def tune_of(campaign_dir, who: str) -> Optional[Dict[str, Any]]:
    return next((t for seed, t in tunes(campaign_dir).items() if _same(seed, who)), None)


def fingerprint(spec: Dict[str, Any]) -> str:
    """What the music is (not its title or notes): a new one means render it again."""
    body = {k: v for k, v in spec.items() if k not in ("title", "notes", "use", "sketch")}
    return hashlib.sha1(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


def use_of(spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """What a score is for, filled in from its tune (None: not for the table)."""
    use = spec.get("use")
    if not isinstance(use, dict) or use.get("as") not in USES:
        return None
    tune = spec.get("tune") or {}
    out = {"as": use["as"]}
    if use["as"] == "place":
        if not use.get("place"):
            return None
        out["place"] = str(use["place"])
        return out
    who = use.get("who") or tune.get("seed")
    if not who:
        return None
    out["who"] = str(who)
    if use["as"] in ("theme", "boss") and "dark" in use:
        out["descent"] = int(use["dark"])                  # (a villain's theme, as far as they've fallen)
    if use["as"] == "anthem":
        out.update(stage=int(use.get("stage", tune.get("stage", 1))), dark=int(use.get("dark", tune.get("dark", 0))),
                   wound=bool(use.get("wound", False)), warm=bool(use.get("warm", False)))
        out["version"] = character_arcs.version(out)
    return out


def _key(use: Dict[str, Any]) -> str:
    if use["as"] == "place":
        return "place:" + use["place"].casefold()
    return (f"{use['as']}:{use['who'].casefold()}" + (f":{use['version']}" if use["as"] == "anthem" else "")
            + (f":d{use['descent']}" if use.get("descent") is not None else ""))


def index(campaign_dir) -> List[Dict[str, Any]]:
    """Every score meant for the table: {file, spec, use, hash, problem}. problem:
    "tune" - written on another tune than the character's (in music/tunes/), so it
    isn't played; "superseded" - another score is for the same use (the newest wins)."""
    folder = Path(campaign_dir) / "music" / "arrangements"
    found = []
    for f in sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        spec = _read(f, None)
        use = use_of(spec) if isinstance(spec, dict) else None
        if use is None:
            continue
        item = {"file": f, "spec": spec, "use": use, "hash": fingerprint(spec), "problem": None}
        if use["as"] != "place":
            mine = tune_of(campaign_dir, use["who"])
            if mine is not None and (spec.get("tune") or {}).get("written") != mine:
                item["problem"] = "tune"
        found.append(item)
    seen = set()
    for item in found:                      # (newest first)
        if item["problem"]:
            continue
        k = _key(item["use"])
        if k in seen:
            item["problem"] = "superseded"
        seen.add(k)
    return found


def has_score(campaign_dir, kind: str, who: str, version: Optional[str] = None) -> bool:
    """Has the GM written this piece (a score in use, not one set aside)? (A villain's
    theme in any of its versions counts.)"""
    if kind == "place":
        want = _key({"as": "place", "place": who})
        return any(not it["problem"] and _key(it["use"]) == want for it in index(campaign_dir))
    want = _key({"as": kind, "who": who, **({"version": version} if version else {})})
    return any(not it["problem"] and (_key(it["use"]) == want or _key(it["use"]).startswith(want + ":d"))
               for it in index(campaign_dir))


# --- where the rendered music goes, and the registry the table reads ---
def real_title(title: Optional[str]) -> str:
    """The piece's own name, for its file name ("<who>: the Last Waltz (her theme)" ->
    "the-last-waltz"): kept in the file so the host can learn it after the campaign;
    the table never shows it (table_server strips everything after "--")."""
    t = str(title or "")
    t = t.split(":", 1)[1] if ":" in t else ""
    t = re.sub(r"\([^)]*\)", "", t).strip()
    return slug(t)[:60].strip("-") if re.search(r"\w", t) else ""


def target(campaign_dir, use: Dict[str, Any], how: str = "score", title: Optional[str] = None) -> Path:
    music = Path(campaign_dir) / "music"
    named = f"--{real_title(title)}" if real_title(title) else ""
    if use["as"] == "place":
        return music / "places" / f"place-{slug(use['place'])}{named}.ogg"
    who = slug(use["who"])
    if use["as"] == "anthem":
        return music / "anthems" / f"anthem-{who}-{use['version']}-{'score' if how == 'score' else 'orch'}{named}.ogg"
    if use["as"] == "dark":
        return music / "anthems" / f"anthem-{who}-dark-score{named}.ogg"
    d = f"-d{use['descent']}" if use.get("descent") is not None else ""
    return music / "themes" / f"{who}-{'boss' if use['as'] == 'boss' else 'theme'}{d}-score{named}.ogg"


def registry(campaign_dir) -> Dict[str, Any]:
    reg = composer.load_registry(campaign_dir)
    reg.setdefault("places", {})
    return reg


def registered(campaign_dir, use: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """What the registry holds for this use, if its file is there: {file, how, hash, ...}."""
    reg = registry(campaign_dir)
    music = Path(campaign_dir) / "music"
    if use["as"] == "place":
        rec = reg["places"].get(next((k for k in reg["places"] if _same(k, use["place"])), ""), None)
        folder = music / "places"
    elif use["as"] in ("theme", "boss"):
        rec = reg["themes"].get(composer._key(reg["themes"], use["who"]) or "", {})
        kind = "boss" if use["as"] == "boss" else "normal"
        if use.get("descent") is not None:
            v = f"d{use['descent']}"
            f = ((rec.get("versions") or {}).get(kind) or {}).get(v)
            rec = {"file": f, **((rec.get("scores") or {}).get(kind + ":" + v) or {})} if f else None
        else:
            rec = {"file": rec.get(kind), **(rec.get("scores") or {}).get(kind, {})} if rec.get(kind) else None
        folder = music / "themes"
    else:
        rec = reg["anthems"].get(composer._key(reg["anthems"], use["who"]) or "", {})
        if use["as"] == "dark":
            rec = {"file": rec.get("dark"), "how": rec.get("dark_how"), "hash": rec.get("dark_hash")} \
                if rec.get("dark") else None
        else:
            rec = (rec.get("versions") or {}).get(use["version"])
        folder = music / "anthems"
    if rec and rec.get("file") and (folder / rec["file"]).is_file():
        return rec
    return None


def register(campaign_dir, use: Dict[str, Any], path: Path, seconds: float, how: str,
             fp: Optional[str] = None, score: Optional[str] = None) -> None:
    """List a rendered piece where the table looks for it (music-composed.json)."""
    reg = registry(campaign_dir)
    f = Path(path).name
    extra = {"how": how, **({"hash": fp} if fp else {}), **({"score": score} if score else {})}
    if use["as"] == "place":
        key = next((k for k in reg["places"] if _same(k, use["place"])), use["place"])
        reg["places"][key] = {"file": f, "seconds": seconds, **extra}
    elif use["as"] in ("theme", "boss"):
        key = composer._key(reg["themes"], use["who"]) or use["who"]
        kind = "boss" if use["as"] == "boss" else "normal"
        rec = reg["themes"].setdefault(key, {})
        if use.get("descent") is not None:
            v = f"d{use['descent']}"
            rec.setdefault("versions", {}).setdefault(kind, {})[v] = f
            rec.setdefault("scores", {})[kind + ":" + v] = extra
            if not rec.get(kind) or use["descent"] == 0:
                rec[kind] = f
        else:
            rec[kind] = f
            rec.setdefault("scores", {})[kind] = extra
    else:
        key = composer._key(reg["anthems"], use["who"]) or use["who"]
        rec = reg["anthems"].setdefault(key, {})
        if use["as"] == "dark":
            rec.update(dark=f, dark_how=how, dark_hash=fp)
        else:
            rec.setdefault("versions", {})[use["version"]] = {"file": f, "seconds": seconds, **extra}
            if not rec.get("file") or not (Path(campaign_dir) / "music" / "anthems" / rec["file"]).is_file():
                rec.update(file=f, seconds=seconds)
    composer.save_registry(campaign_dir, reg)


# --- rendering: in the orchestra's environment, here or on the host's laptop ---
_HAS: Dict[str, bool] = {}


def _has_module(py: Path, module: str) -> bool:
    k = f"{py}:{module}"
    if k not in _HAS:
        try:
            _HAS[k] = subprocess.run([str(py), "-c", f"import importlib.util, sys; "
                                      f"sys.exit(0 if importlib.util.find_spec({module!r}) else 1)"],
                                     capture_output=True, timeout=60, **NO_WINDOW).returncode == 0
        except (OSError, subprocess.SubprocessError):
            _HAS[k] = False
    return _HAS[k]


def orchestra_python() -> Optional[Path]:
    """A Python with the orchestra's packages (ORCHESTRA_PYTHON, else .compose-venv)."""
    if os.environ.get("MUSIC_ORCHESTRA", "").strip().lower() in ("off", "0", "no", "false"):
        return None
    for p in [os.environ.get("ORCHESTRA_PYTHON")] + [str(x) for x in (
            composer.COMPOSE_VENV / "Scripts" / "python.exe", composer.COMPOSE_VENV / "bin" / "python")]:
        if p and Path(p).is_file() and _has_module(Path(p), "tinysoundfont") and _has_module(Path(p), "numpy"):
            return Path(p)
    return None


def local_ready() -> bool:
    return orchestra_python() is not None and SF2.is_file()


def available() -> bool:
    """Can the table play written music now (here, or on the host's laptop)?"""
    if local_ready():
        return True
    if os.environ.get("MUSIC_ORCHESTRA", "").strip().lower() in ("off", "0", "no", "false"):
        return False
    if gpu_remote.enabled():
        h = gpu_remote.health()
        return bool(h and h.get("orchestra"))
    return False


def render_local(jobs: List[Dict[str, Any]], on_piece: Optional[Callable[[int, Dict[str, Any]], None]] = None,
                 timeout_each: int = 900) -> List[Optional[Dict[str, Any]]]:
    """Render jobs ({kind: score, spec, out} | {kind: theme, seed, written, stage, dark,
    wound, out}) in the orchestra's environment, one process for the lot."""
    py = orchestra_python()
    if py is None:
        raise composer.ComposeError("the orchestra isn't set up (bash tools/gm-music-compose.sh setup --orchestra)")
    results: List[Optional[Dict[str, Any]]] = [None] * len(jobs)
    proc = subprocess.Popen([str(py), str(RENDERER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", **NO_WINDOW,
                            env={**os.environ, "PYTHONUTF8": "1"})
    try:
        for i, job in enumerate(jobs):
            proc.stdin.write(json.dumps({**job, "id": i}, ensure_ascii=False) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            if not line:
                break
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("ok"):
                results[i] = r
                if on_piece is not None:
                    on_piece(i, r)
            else:
                print(f"[orchestra] {Path(job['out']).name}: {r.get('error')}", flush=True)
    finally:
        try:
            proc.stdin.close()
            proc.wait(timeout=10)
        except (OSError, subprocess.SubprocessError):
            proc.kill()
    return results


def render(jobs: List[Dict[str, Any]], on_piece: Optional[Callable[[int, Dict[str, Any]], None]] = None
           ) -> List[Optional[Dict[str, Any]]]:
    """render_local(), or on the host laptop's GPU server when the orchestra is there."""
    if local_ready() or not gpu_remote.enabled():
        return render_local(jobs, on_piece)
    results: List[Optional[Dict[str, Any]]] = [None] * len(jobs)
    for i, job in enumerate(jobs):
        out = Path(job["out"])
        try:
            r = gpu_remote.run("orchestra", {"job": {k: v for k, v in job.items() if k != "out"},
                                             "ext": out.suffix or ".ogg"}, timeout=900)
            path = out.with_suffix(r.get("ext") or out.suffix)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(base64.b64decode(r["audio"]))
        except (gpu_remote.GpuRemoteError, KeyError, ValueError, OSError) as e:
            print(f"[orchestra] {out.name}: {e}", flush=True)
            continue
        results[i] = {"ok": True, "path": str(path), "seconds": r.get("seconds")}
        if on_piece is not None:
            on_piece(i, results[i])
    return results


# --- what to render now ---
def stale(campaign_dir) -> List[Dict[str, Any]]:
    """Scores whose music isn't rendered yet, or was rendered from an older version."""
    out = []
    for item in index(campaign_dir):
        if item["problem"]:
            continue
        rec = registered(campaign_dir, item["use"])
        named = target(campaign_dir, item["use"], title=item["spec"].get("title")).name
        if not rec or rec.get("how") != "score" or rec.get("hash") != item["hash"] or rec.get("file") != named:
            out.append(item)                  # (a new title: a new file name)
    return out


def anthem_job(campaign_dir, name: str, arc: Dict[str, Any], cls: str = "") -> Dict[str, Any]:
    """A PC's anthem at a point of their story, arranged by rule from their tune
    (until the GM writes that version)."""
    use = {"as": "anthem", "who": name, **{k: arc[k] for k in ("stage", "dark", "wound")},
           "warm": bool(arc.get("warm")), "version": character_arcs.version(arc)}
    return {"kind": "theme", "seed": name, "cls": cls, "written": tune_of(campaign_dir, name),
            "stage": arc["stage"], "dark": arc["dark"], "wound": bool(arc["wound"]),
            "out": str(target(campaign_dir, use, "orchestra")), "use": use}


def needs_orchestra(campaign_dir, name: str, arc: Dict[str, Any]) -> bool:
    """Is this version of a PC's anthem still missing, or only the AI's?"""
    rec = registered(campaign_dir, {"as": "anthem", "who": name, "version": character_arcs.version(arc)})
    return not rec or rec.get("how") not in ("score", "orchestra")


def sync(campaign_dir, extra: Optional[List[Dict[str, Any]]] = None,
         on_piece: Optional[Callable[[Dict[str, Any], str], None]] = None) -> List[str]:
    """Render every new or changed score (and ``extra`` rule-arranged jobs, each with
    its "use"), register each as it lands; returns the files made."""
    jobs = [{"kind": "score", "spec": it["spec"], "out": str(target(campaign_dir, it["use"], title=it["spec"].get("title"))),
             "use": it["use"], "hash": it["hash"], "score": it["file"].name} for it in stale(campaign_dir)]
    jobs += list(extra or [])
    if not jobs:
        return []
    made: List[str] = []

    def landed(i: int, r: Dict[str, Any]) -> None:
        job = jobs[i]
        how = "score" if job["kind"] == "score" else "orchestra"
        old = registered(campaign_dir, job["use"])
        if old and old.get("file") and old["file"] != Path(r["path"]).name:     # renamed: the old one goes
            (Path(r["path"]).parent / old["file"]).unlink(missing_ok=True)
        register(campaign_dir, job["use"], Path(r["path"]), r.get("seconds") or 0, how,
                 job.get("hash"), job.get("score"))
        made.append(Path(r["path"]).name)
        if on_piece is not None:
            on_piece(job["use"], Path(r["path"]).name)

    render([{k: v for k, v in j.items() if k not in ("use", "hash", "score")} for j in jobs], landed)
    return made


# --- what the GM still has to write ---
def request(campaign_dir, kind: str, who: str) -> None:
    """The table met a villain (theme) or a boss (boss): their music is wanted."""
    path = Path(campaign_dir) / WANTED
    data = _read(path, {})
    data = data if isinstance(data, dict) else {}
    reqs = data.setdefault("requests", [])
    if not any(r.get("as") == kind and _same(r.get("who"), who) for r in reqs):
        reqs.append({"as": kind, "who": who, "since": time.strftime("%Y-%m-%dT%H:%M:%S")})
        _write(path, data)


def wanted(campaign_dir, pcs: Optional[List[str]] = None, places: Optional[List[str]] = None
           ) -> List[Dict[str, Any]]:
    """What the GM should write next, most pressing first: {what, who/place, why}.
    ``pcs``: the player characters; ``places``: the places that earned music."""
    camp = Path(campaign_dir)
    have = {_key(it["use"]): it for it in index(camp) if not it["problem"]}
    out: List[Dict[str, Any]] = []
    for it in index(camp):
        if it["problem"] == "tune":
            out.append({"what": "rewrite", "file": it["file"].name,
                        "why": f"written on another tune than {it['use'].get('who')}'s (music/tunes/)"})
    for name in pcs or []:
        if tune_of(camp, name) is None:
            out.append({"what": "tune", "who": name, "why": "a main character: their tune is written by hand"})
        arc = character_arcs.spec(character_arcs.state_of(camp, name))
        for a, why in ((arc, "where their story is now"), (character_arcs.next_growth(arc), "their next growth")):
            if a and _key({"as": "anthem", "who": name, "version": character_arcs.version(a)}) not in have:
                out.append({"what": "anthem", "who": name, "version": character_arcs.version(a), "why": why})
        if _key({"as": "dark", "who": name}) not in have:
            out.append({"what": "dark", "who": name, "why": "the villain they could become"})
    for r in (_read(camp / WANTED, {}) or {}).get("requests", []):
        if r.get("as") in ("theme", "boss") and _key({"as": r["as"], "who": r["who"]}) not in have:
            out.append({"what": r["as"], "who": r["who"], "why": "met at the table"})
    for place in places or []:
        it = have.get(_key({"as": "place", "place": place}))
        if it is None or it["spec"].get("sketch"):
            out.append({"what": "place", "place": place,
                        "why": "plays from a sketch" if it else "earned its music"})
    order = {"rewrite": 0, "boss": 1, "theme": 2, "tune": 3, "anthem": 4, "place": 5, "dark": 6}
    return sorted(out, key=lambda w: order.get(w["what"], 9))


# --- places: which earn music, and the sketch that plays until the GM writes one ---
_TRANSIT = re.compile(r"\b(road|path|trail|stair|stairs|ladder|ladders|bridge|corridor|passage|tunnel|hatch|"
                      r"gate|crossing|ford|pass)\b", re.I)


def is_transit(name: str, rec: Optional[Dict[str, Any]] = None) -> bool:
    """A place the party passes through rather than stays at (a road, a stair, a hatch)."""
    rec = rec or {}
    if rec.get("transit") is not None:
        return bool(rec["transit"])
    return bool(_TRANSIT.search(name))


def earns_music(name: str, rec: Optional[Dict[str, Any]], seconds: float, visits: int, opening: bool,
                in_story: bool, minutes: float = PLACE_MINUTES) -> Optional[str]:
    """Why this place has earned its own music (None: not yet). The GM can mark one
    ("music": true in locations.json); else about ten minutes of play there, a return
    (not to a place passed through), the adventure's opening place, or a place a quest
    or plot names."""
    rec = rec or {}
    if rec.get("music") is False:
        return None
    if rec.get("music"):
        return "marked by the GM"
    if seconds >= minutes * 60:
        return f"{int(seconds // 60)} minutes of play there"
    transit = is_transit(name, rec)
    if opening and not transit:
        return "where the adventure opens"
    if visits >= 2 and not transit:
        return "the party came back"
    if in_story and not transit:
        return "a quest or plot names it"
    return None


COLOURS = [   # (words in a place's name or description) -> its colour
    ("sacred", r"temple|shrine|chapel|church|cathedral|altar|holy|sacred|monaster|abbey|tomb|crypt|grave",
     {"mode": "dorian", "tempo": 56, "key": "D4", "lead": ["flutes", "clarinets"], "pad": "organ",
      "choir": True, "motion": "harp"}),
    ("deep", r"cave|cavern|under|deep|pit|mine|dungeon|shaft|cage|cell|prison|locker|chain|iron|sewer|vault|"
             r"dark|black|forge|furnace",
     {"mode": "phrygian", "tempo": 58, "key": "D4", "lead": ["english_horn", "clarinets"], "pad": "strings",
      "choir": False, "motion": "pizzicato"}),
    ("town", r"town|village|market|inn|tavern|square|street|harbou?r|hall|house|home|bunk",
     {"mode": "mixolydian", "tempo": 76, "key": "G4", "lead": ["clarinets", "oboe"], "pad": "strings",
      "choir": False, "motion": "pizzicato"}),
    ("sea", r"sea|ocean|shore|coast|river|lake|ship|deck|dock|bay|wave",
     {"mode": "dorian", "tempo": 64, "key": "E4", "lead": ["horns", "clarinets"], "pad": "strings",
      "choir": False, "motion": "harp"}),
    ("high", r"tower|spire|peak|summit|sky|cloud|wind|high|roof|battlement|gun-?loop|window",
     {"mode": "lydian", "tempo": 62, "key": "F4", "lead": ["flutes", "celesta"], "pad": "strings",
      "choir": False, "motion": "harp"}),
    ("wild", r"forest|wood|grove|hill|field|meadow|moor|marsh|swamp|wild|glade|valley|ash",
     {"mode": "dorian", "tempo": 66, "key": "E4", "lead": ["flutes", "horns"], "pad": "strings",
      "choir": False, "motion": "harp"}),
]
DEFAULT_COLOUR = ("plain", "", {"mode": "dorian", "tempo": 62, "key": "E4", "lead": ["clarinets", "flutes"],
                                "pad": "strings", "choir": False, "motion": "harp"})
SCALES = {"ionian": [0, 2, 4, 5, 7, 9, 11], "lydian": [0, 2, 4, 6, 7, 9, 11],
          "mixolydian": [0, 2, 4, 5, 7, 9, 10], "dorian": [0, 2, 3, 5, 7, 9, 10],
          "aeolian": [0, 2, 3, 5, 7, 8, 10], "phrygian": [0, 1, 3, 5, 7, 8, 10]}
LOOPS = {   # each mode's eight-bar walk (scale degrees, 0 = home), ending ready to begin again
    "ionian": [0, 5, 3, 4, 0, 2, 3, 4], "lydian": [0, 1, 0, 5, 0, 1, 3, 4],
    "mixolydian": [0, 6, 3, 0, 0, 6, 4, 3], "dorian": [0, 3, 0, 6, 0, 3, 2, 6],
    "aeolian": [0, 5, 2, 6, 0, 3, 5, 4], "phrygian": [0, 1, 0, 6, 0, 1, 3, 1],
}
RANGES = {"flutes": (60, 96), "clarinets": (50, 91), "oboe": (58, 91), "english_horn": (52, 81),
          "horns": (41, 77), "celesta": (60, 108), "cellos": (36, 76), "harp": (24, 103)}
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def colour_of(name: str, rec: Optional[Dict[str, Any]] = None) -> tuple:
    text = f"{name} {(rec or {}).get('description') or ''} {(rec or {}).get('position') or ''}".lower()
    best = DEFAULT_COLOUR
    for word, pattern, c in COLOURS:     # the name decides first, then the description
        if re.search(pattern, name.lower()):
            return word, pattern, c
    hits = [(len(re.findall(pattern, text)), i) for i, (_, pattern, _) in enumerate(COLOURS)]
    n, i = max(hits)
    return COLOURS[i] if n else best


def _phrase(rng: random.Random, start: int, end: int) -> List[List[float]]:
    """Two bars of 4/4 in scale degrees: a rhythm, mostly steps, ending long."""
    rhythm = rng.choice([[1, 1, 2, 1, 1, 2], [2, 1, 1, 4], [1.5, 0.5, 1, 1, 4], [1, 1, 1, 1, 4],
                         [2, 2, 1, 1, 2], [1, 0.5, 0.5, 2, 4]])
    notes, d = [], start
    for i, b in enumerate(rhythm):
        if i == len(rhythm) - 1:
            d = end
        elif i:
            d = max(-3, min(7, d + rng.choice([-2, -1, -1, 1, 1, 2, 3, -3] if i == 1 else [-2, -1, 1, 1, 2, -1])))
        notes.append([d, b])
    return notes


def signature(campaign_dir, name: Optional[str] = None) -> Dict[str, Any]:
    """The adventure's own motif (music/tunes/signature.json; made once, from the
    adventure's name, if the GM hasn't written one): heard in every place it plays."""
    path = Path(campaign_dir) / "music" / "tunes" / SIGNATURE
    sig = _read(path, None)
    if isinstance(sig, dict) and sig.get("motif"):
        return sig
    if name is None:
        name = (_read(Path(campaign_dir) / "campaign-overview.json", {}) or {}).get("campaign_name") \
            or Path(campaign_dir).name
    rng = random.Random(hashlib.sha256(("signature:" + str(name)).encode("utf-8")).hexdigest())
    sig = {"seed": str(name), "motif": _phrase(rng, rng.choice([0, 2, 4]), rng.choice([4, 2]))}
    _write(path, sig)
    return sig


def _roman(scale: List[int], deg: int) -> str:
    major = [0, 2, 4, 5, 7, 9, 11]
    third = (scale[(deg + 2) % 7] - scale[deg]) % 12
    fifth = (scale[(deg + 4) % 7] - scale[deg]) % 12
    acc = {-1: "b", 1: "#", 11: "b", -11: "#"}.get(scale[deg] - major[deg], "")
    numeral = ["I", "II", "III", "IV", "V", "VI", "VII"][deg]
    if third == 3:
        numeral = numeral.lower() + ("°" if fifth == 6 else "")
    return acc + numeral


def place_sketch(campaign_dir, name: str, rec: Optional[Dict[str, Any]] = None,
                 adventure: Optional[str] = None) -> Dict[str, Any]:
    """A place's music, sketched by rule (a score in the arrangement format, "sketch":
    true): a quiet two-minute loop in the place's colour, the adventure's signature
    motif and the place's own answer to it, low under the voices. The GM's own piece
    replaces it (orchestrate skill: references/composing.md, places)."""
    word, _, c = colour_of(name, rec)
    rng = random.Random(hashlib.sha256(("place:" + name.casefold()).encode("utf-8")).hexdigest())
    sig = signature(campaign_dir, adventure)["motif"]
    answer = _phrase(rng, rng.choice([2, 4, 1]), 0)
    mode, scale = c["mode"], SCALES[c["mode"]]
    tune = {"seed": f"{name} (place)", "meter": "4/4", "mode": mode, "kind": "place", "key": c["key"],
            "hook": len(sig), "pickup": [], "motif": sig, "again": answer, "climb": [], "home": sig}
    key = 60 + NAMES.index(c["key"][:-1])           # (octave 4)
    walk = LOOPS[mode]
    # The tune is 6 bars (motif, answer, motif): at bar 8 (beat 32), and the motif again at bar 20.
    bars = 32
    melody_at = {32: tune["motif"] + tune["again"] + tune["home"], 80: list(sig)}

    def degree_at(beat: float) -> Optional[int]:
        for at, notes in melody_at.items():
            t = at
            for d, b in notes:
                if t <= beat < t + b:
                    return int(d)
                t += b
        return None

    chords = []
    for bar in range(bars):
        deg = walk[bar % 8]
        held = [degree_at(bar * 4 + k) for k in (0, 2)]
        held = [h for h in held if h is not None]
        if held:                                     # under the tune: a chord that holds its note
            want = held[0] % 7
            fits = [r for r in [deg, 0, 3, 4, 5, 2, 6, 1] if want in (r, (r + 2) % 7, (r + 4) % 7)
                    and not _roman(scale, r).endswith("°")]
            deg = fits[0] if fits else deg
        chords.append([bar * 4, bar * 4 + 4, _roman(scale, deg)])

    def fit(part: str, notes: List[List[float]]) -> int:
        lo, hi = RANGES.get(part, (48, 84))
        semis = [12 * (d // 7) + scale[d % 7] for d, _ in notes]
        for shift in (0, 12, -12, 24):
            if lo <= key + min(semis) + shift and key + max(semis) + shift <= hi:
                return shift
        return 0

    lead, second = c["lead"]
    end = bars * 4
    spec = {
        "title": f"{name} - its music (a sketch: the GM's own piece replaces it)",
        "use": {"as": "place", "place": name}, "sketch": True, "colour": word,
        "tune": {"seed": tune["seed"], "stage": 1, "written": tune},
        "tempo": c["tempo"], "start": -32, "length": end - 32, "loop": True, "role": "place", "lead": 2,
        "statements": [{"at": 0}, {"at": 48, "from": 0, "to": sum(b for _, b in sig)}],
        "dynamics": [[-32, 46], [-30, 52], [0, 60], [20, 64], [32, 58], [56, 54], [64, 52], [96, 52]],
        "melody": [{"from": 0, "to": 24, "parts": {lead: fit(lead, sig + answer)}, "vel": -2, "gain": 5},
                   {"from": 48, "to": 56, "parts": {second: fit(second, sig)}, "vel": -4, "gain": 5}],
        "chords": [[a - 32, b - 32, ch] for a, b, ch in chords],
        "harmony": [
            {"part": c["pad"], "from": -32, "to": end - 32, "play": "chord",
             "range": [f"{NAMES[(key - 12) % 12]}3", f"{NAMES[(key + 5) % 12]}4"], "vel": -28},
            {"part": "basses", "from": -32, "to": end - 32, "play": "bass", "range": ["E1", "D#2"], "vel": -22},
        ],
        "lines": [],
        "patterns": [],
        "hits": [],
    }
    lo3 = f"{NAMES[key % 12]}2"
    hi3 = f"{NAMES[(key - 1) % 12]}3" if key % 12 else "B2"
    if c["motion"] == "harp":
        spec["harmony"].append({"part": "harp", "from": -32, "to": end - 32, "play": "chord",
                                "range": [f"{NAMES[key % 12]}3", f"{NAMES[(key + 7) % 12]}4"],
                                "pattern": "o o o o ", "step": 0.5, "vel": -22})
    else:
        spec["harmony"].append({"part": "pizzicato", "from": -32, "to": end - 32, "play": "root",
                                "range": [lo3, hi3], "pattern": " o o", "vel": -20})
    spec["harmony"].append({"part": "cellos", "from": 24, "to": 48, "play": "third",
                            "range": ["C3", "B3"], "pattern": "o---", "vel": -22})
    if c["choir"]:
        spec["harmony"].append({"part": "choir", "from": -16, "to": 24, "play": "chord",
                                "range": [f"{NAMES[key % 12]}3", f"{NAMES[(key + 4) % 12]}4"], "vel": -20})
    return spec


def ensure_sketch(campaign_dir, name: str, rec: Optional[Dict[str, Any]] = None) -> Optional[Path]:
    """Write a place's sketch into music/arrangements/ unless a score for it exists."""
    if any(it["use"]["as"] == "place" and _same(it["use"]["place"], name) for it in index(campaign_dir)):
        return None
    out = Path(campaign_dir) / "music" / "arrangements" / f"place-{slug(name)}.json"
    _write(out, place_sketch(campaign_dir, name, rec))
    return out


def place_file(campaign_dir, name: str) -> Optional[str]:
    rec = registered(campaign_dir, {"as": "place", "place": name})
    return rec["file"] if rec else None


# --- the CLI behind gm-music-compose.sh scores / wanted / place ---
def main() -> None:
    import argparse
    from campaign_manager import CampaignManager
    import party_roster
    from character_schema import to_flat
    ap = argparse.ArgumentParser(description="Written music at the table")
    sub = ap.add_subparsers(dest="action", required=True)
    sub.add_parser("scores", help="The scores meant for the table, and what is rendered")
    sub.add_parser("render", help="Render every new or changed score now")
    sub.add_parser("wanted", help="What is still waiting to be written")
    p = sub.add_parser("place", help="Sketch a place's music now (the table does it once a place earns it)")
    p.add_argument("name")
    args = ap.parse_args()
    camp = CampaignManager(os.environ.get("GM_WORLD_STATE_BASE", "world-state")).get_active_campaign_dir()
    if camp is None:
        sys.exit("[ERROR] No active campaign.")
    if args.action == "scores":
        for it in index(camp):
            u = it["use"]
            what = u["as"] + " " + (u.get("place") or u.get("who")) + (f" {u['version']}" if u.get("version") else "")
            rec = registered(camp, u)
            state = it["problem"] or ("rendered" if rec and rec.get("hash") == it["hash"] else "to render")
            print(f"  {it['file'].name:34} {what:44} {state}{' (sketch)' if it['spec'].get('sketch') else ''}")
        print(f"Orchestra: {'ready' if available() else 'not set up (gm-music-compose.sh setup --orchestra)'}")
    elif args.action == "render":
        made = sync(camp)
        print("\n".join(f"  [SUCCESS] {f}" for f in made) or "Nothing new to render.")
    elif args.action == "wanted":
        pcs = [to_flat(raw).get("name") or path.stem for path, raw in party_roster.all_pcs(camp)]
        places = _read(Path(camp) / "table" / "places.json", {}).get("music", [])
        for w in wanted(camp, pcs, places):
            who = w.get("who") or w.get("place") or w.get("file")
            print(f"  {w['what']:8} {who}{' ' + w['version'] if w.get('version') else ''}: {w['why']}")
    elif args.action == "place":
        import image_gen
        found = image_gen.find_location(args.name, camp)
        out = ensure_sketch(camp, found[1] if found else args.name, found[2] if found else None)
        print(f"[SUCCESS] {out}" if out else "That place already has a score.")


if __name__ == "__main__":
    main()
