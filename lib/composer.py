#!/usr/bin/env python3
"""Composed music for the moments that matter: main villains, bosses, and each
player character's heroic anthem.

The composing happens in a separate environment (.compose-venv, see
lib/music_compose.py and `bash tools/gm-music-compose.sh setup`) so the game
itself keeps its small CPU-only install. Without that environment (or with
MUSIC_COMPOSE=off) nothing here runs and the game keeps its other music:
the library, and the generated themes in the players' browsers.

Composed pieces live in the campaign, in music/themes/ and music/anthems/
(subfolders, so mood matching never picks a villain's theme for a random
fight), listed in music-composed.json:
    {"themes": {"Grimaldi": {"normal": "grimaldi-theme.ogg", "boss": "grimaldi-boss.ogg"}},
     "anthems": {"Pip": {"file": "anthem-pip.ogg", "seconds": 20}}}
"""

import atexit
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gpu_turn import gpu_turn  # noqa: E402
import gpu_remote  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_VENV = PROJECT_ROOT / ".compose-venv"
SCRIPT = Path(__file__).resolve().parent / "music_compose.py"
THEME_SECONDS = 30
ANTHEM_SECONDS = 20


class ComposeError(Exception):
    pass


def _turned_off() -> bool:
    return os.environ.get("MUSIC_COMPOSE", "").strip().lower() in ("off", "0", "no", "false")


def remote() -> bool:
    """Composing on the host laptop's GPU server (lib/gpu_remote.py) instead of here:
    MUSIC_COMPOSE=remote, or a GPU server is set and there's no composer here."""
    if _turned_off() or not gpu_remote.enabled():
        return False
    chosen = os.environ.get("MUSIC_COMPOSE", "").strip().lower()
    return chosen == "remote" or _local_python() is None


def composer_python() -> Optional[Path]:
    """The composer environment's Python, or None (not set up, turned off, or
    composing on the host's laptop instead)."""
    if _turned_off() or remote():
        return None
    return _local_python()


def _python(local: bool = False) -> Optional[Path]:
    """composer_python(), or with ``local`` this machine's composer even when a GPU
    server is set (the GPU server itself composes with this)."""
    if not local:
        return composer_python()
    return None if _turned_off() else _local_python()


def _local_python() -> Optional[Path]:
    for p in (COMPOSE_VENV / "Scripts" / "python.exe", COMPOSE_VENV / "bin" / "python"):
        if p.is_file():
            return p
    return None


def available() -> bool:
    if remote():
        h = gpu_remote.health()
        return bool(h and h.get("composer"))
    return composer_python() is not None


def slug(name: str) -> str:
    """A file-name stem for a piece. A name with letters outside a-z (קסטרל)
    gets a short fingerprint of the whole name, or every Hebrew name would come
    out as the same "piece" and overwrite the others' music."""
    name = str(name)
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40]
    if re.fullmatch(r"[\x00-\x7f]*", name) and base:
        return base
    tag = hashlib.sha1(name.strip().encode("utf-8")).hexdigest()[:8]
    return f"{base}-{tag}" if base else f"piece-{tag}"


def flavor(campaign_dir) -> str:
    """The campaign's genre and tone, as a few words for the music prompt."""
    try:
        o = json.loads((Path(campaign_dir) / "campaign-overview.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    bits = []
    for k in ("genre", "tone"):
        v = o.get(k)
        if isinstance(v, str) and v.strip():
            bits.append(v.strip().rstrip(".")[:80])
    return ", ".join(bits)


def theme_prompt(name: str, look: str, style: str, boss: bool) -> str:
    who = f"{name}" + (f" ({look.strip().rstrip('.')[:120]})" if look else "")
    setting = f", {style}" if style else ""
    if boss:
        return (f"epic orchestral boss battle theme for {who}{setting}, thundering war drums, "
                "roaring brass, dark choir, driving strings, intense and relentless, 150 bpm")
    return (f"ominous villain leitmotif for {who}{setting}, low strings, menacing brass, "
            "dark and brooding, slow build, cinematic")


def anthem_prompt(sheet: Dict[str, Any], style: str) -> str:
    name = sheet.get("name", "the hero")
    who = " ".join(str(sheet.get(k) or "") for k in ("race", "class")).strip()
    concept = str(sheet.get("concept") or "").strip().rstrip(".")
    setting = f", {style}" if style else ""
    return (f"heroic triumphant anthem for {name}" + (f", a {who}" if who else "")
            + (f", {concept[:100]}" if concept else "") + f"{setting}, soaring brass fanfare, "
            "uplifting strings, pounding timpani, glorious and inspiring")


# --- the composer process: started once, keeps the model in RAM ---
SERVER_LOG = Path(tempfile.gettempdir()) / "gm-composer.log"
_server: Optional[subprocess.Popen] = None
_server_device = ""
_server_lock = threading.RLock()


# No console window for it on Windows: the table runs in the background, so Windows
# would open one, and closing that window kills the composer without a word.
NO_WINDOW = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if os.name == "nt" else {}
# After composing on the graphics card crashed, the rest of the session composes on
# the CPU (slower, but the music comes).
_cpu_only = False


def _spawn(local: bool = False) -> Optional[subprocess.Popen]:
    global _server, _server_device
    if _server is not None and _server.poll() is None:
        return _server
    py = _python(local)
    if py is None:
        return None
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONFAULTHANDLER": "1"}
    if _cpu_only:
        env["COMPOSE_DEVICE"] = "cpu"
    with open(SERVER_LOG, "w", encoding="utf-8", errors="replace") as log:
        _server = subprocess.Popen([str(py), str(SCRIPT), "--serve"], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=log, text=True, encoding="utf-8",
                                   errors="replace", env=env, **NO_WINDOW)
    _server_device = ""
    return _server


# How a process that died says why (Windows exit codes, and signals elsewhere).
EXIT_MEANINGS = {
    3221225477: "it crashed inside a native library (access violation, 0xC0000005)",
    3221226505: "it crashed inside a native library (0xC0000409: often CUDA / the graphics driver)",
    3221225495: "Windows refused it memory (0xC0000017: RAM and page file full)",
    3221225725: "it crashed (stack overflow, 0xC00000FD)",
    3221225786: "it was stopped (its window was closed, or Ctrl+C, 0xC000013A)",
    1: "it stopped with an error (see the composer's log)",
    -9: "it was killed (out of memory?)", 137: "it was killed (out of memory?)",
    -11: "it crashed inside a native library (segmentation fault)",
}


def _why_it_died(proc: subprocess.Popen) -> str:
    code = proc.poll()
    if code is None:
        return "it stopped answering"
    return EXIT_MEANINGS.get(code, f"it stopped (exit code {code})")


def _log_tail() -> str:
    try:
        return " | ".join(SERVER_LOG.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-3:])
    except OSError:
        return ""


def _read(proc: subprocess.Popen, want, timeout: float) -> Optional[Dict[str, Any]]:
    """The composer's next JSON line that ``want(line)`` accepts; None if it died
    or took longer than ``timeout`` (then it's stopped)."""
    watchdog = threading.Timer(timeout, proc.kill)
    watchdog.daemon = True
    watchdog.start()
    try:
        for line in proc.stdout:
            if line.strip().startswith("{"):
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if want(r):
                    return r
        return None
    finally:
        watchdog.cancel()


def start_server(timeout: float = 1800, local: bool = False) -> bool:
    """Start the composer and let it read the model into RAM (once). Blocks until
    it's ready; True if it is. The table calls this in the background at start."""
    global _server_device
    if not local and remote():
        try:
            return bool(gpu_remote.run("compose-start", timeout=timeout).get("ok"))
        except gpu_remote.GpuRemoteError:
            return False
    with _server_lock:
        proc = _spawn(local)
        if proc is None:
            return False
        if _server_device:
            return True
        r = _read(proc, lambda r: "ready" in r, timeout)
        if r is None:
            stop_server()
            return False
        _server_device = r.get("device") or "cpu"
        return True


def stop_server() -> None:
    global _server, _server_device
    with _server_lock:
        proc, _server, _server_device = _server, None, ""
    if proc is None:
        return
    try:
        proc.stdin.close()               # it finishes when its input ends
        proc.wait(timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        proc.kill()
        proc.wait()


atexit.register(stop_server)


def _free_the_card() -> None:
    """Pictures' model off the graphics card (into RAM) before music uses it."""
    try:
        import image_gen
        image_gen.release_gpu()
    except Exception:
        pass


def compose_many(jobs: List[Dict[str, Any]], on_piece: Optional[Callable[[int, Dict[str, Any]], None]] = None,
                 timeout_each: int = 1800, local: bool = False) -> List[Optional[Dict[str, Any]]]:
    """Compose pieces ({prompt, seconds, out, loop}) with the running composer: its
    model stays in RAM, so it's read from disk only once. Each piece takes its turn
    on the graphics card (pictures wait for it, and it for them), with Forge's model
    moved off the card first. ``on_piece(index, result)`` is called as each one
    lands. Returns one result per job (None where that piece failed)."""
    global _cpu_only
    if not jobs:
        return []
    if not local and remote():
        return _compose_remote(jobs, on_piece, timeout_each)
    if _python(local) is None:
        raise ComposeError("the composer isn't set up (bash tools/gm-music-compose.sh setup)")
    results: List[Optional[Dict[str, Any]]] = [None] * len(jobs)
    errors: List[str] = []
    with _server_lock:
        for i, job in enumerate(jobs):
            if not start_server(local=local):        # (re)started if it isn't running
                errors.append(_log_tail() or "it didn't start")
                break
            proc = _server
            with gpu_turn("music"):
                if _server_device != "cpu":
                    _free_the_card()
                try:
                    proc.stdin.write(json.dumps({**job, "id": i}, ensure_ascii=False) + "\n")
                    proc.stdin.flush()
                    r = _read(proc, lambda r: r.get("id") == i, timeout_each)
                except OSError:
                    r = None
            if r is None:                            # it died, or hung and was stopped
                why = "it took too long" if proc.poll() is None else _why_it_died(proc)
                errors.append(f"the composer stopped: {why}. Its log ends: {_log_tail()}")
                print(f"[compose] the composer stopped while composing piece {i + 1}: {why}"
                      f" (log: {SERVER_LOG})", file=sys.stderr, flush=True)
                gpu = _server_device not in ("", "cpu")
                stop_server()
                if gpu and not _cpu_only:            # crashed on the graphics card: CPU from now on
                    _cpu_only = True
                    print("[compose] composing on the CPU from now on (slower)", file=sys.stderr, flush=True)
                    try:
                        retry = compose_many([job], timeout_each=timeout_each, local=local)[0]
                    except ComposeError as e:
                        errors.append(str(e))
                        retry = None
                    if retry:
                        results[i] = retry
                        if on_piece is not None:
                            on_piece(i, retry)
                continue
            if not r.get("ok"):
                errors.append(r.get("error") or "that piece failed")
                continue
            results[i] = r
            if on_piece is not None:
                on_piece(i, r)
    if not any(results):
        raise ComposeError("the composer failed: " + (errors[-1] if errors else "no answer"))
    return results


def _compose_remote(jobs: List[Dict[str, Any]], on_piece, timeout_each: int
                    ) -> List[Optional[Dict[str, Any]]]:
    """compose_many() on the host laptop's GPU server: the piece comes back as
    bytes and is written where the job asked, the same as a local one."""
    results: List[Optional[Dict[str, Any]]] = [None] * len(jobs)
    errors: List[str] = []
    for i, job in enumerate(jobs):
        out = Path(job["out"])
        try:
            r = gpu_remote.run("compose", {"prompt": job["prompt"], "seconds": job.get("seconds", 30),
                                           "loop": bool(job.get("loop")), "ext": out.suffix or ".ogg"},
                               timeout=timeout_each)
            path = out.with_suffix(r.get("ext") or out.suffix)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(base64.b64decode(r["audio"]))
        except (gpu_remote.GpuRemoteError, KeyError, ValueError, OSError) as e:
            errors.append(str(e))
            continue
        results[i] = {"ok": True, "path": str(path), "seconds": r.get("seconds"),
                      "device": r.get("device"), "elapsed": r.get("elapsed"), "id": i}
        if on_piece is not None:
            on_piece(i, results[i])
    if not any(results):
        raise ComposeError("the host's composer failed: " + (errors[-1] if errors else "no answer"))
    return results


def compose(prompt: str, seconds: float, out: Path, loop: bool = False,
            timeout: int = 3600, local: bool = False) -> Dict[str, Any]:
    """Compose one piece (blocking: a minute or two on a GPU, several on a CPU).
    ``local``: on this machine's composer even when a GPU server is set."""
    return compose_many([{"prompt": prompt, "seconds": seconds, "out": str(out), "loop": loop}],
                        timeout_each=timeout, local=local)[0]


# --- what has been composed for this campaign ---
def registry_path(campaign_dir) -> Path:
    return Path(campaign_dir) / "music-composed.json"


def load_registry(campaign_dir) -> Dict[str, Any]:
    try:
        data = json.loads(registry_path(campaign_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("themes", {})
    data.setdefault("anthems", {})
    return data


def save_registry(campaign_dir, data: Dict[str, Any]) -> None:
    path = registry_path(campaign_dir)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _key(table: Dict[str, Any], name: str) -> Optional[str]:
    return next((k for k in table if k.strip().lower() == str(name).strip().lower()), None)


def theme_file(campaign_dir, name: str, boss: bool) -> Optional[str]:
    """The composed theme for this foe (the boss one when asked, else the other)."""
    reg = load_registry(campaign_dir)["themes"]
    rec = reg.get(_key(reg, name)) or {}
    order = ("boss", "normal") if boss else ("normal", "boss")
    for kind in order:
        f = rec.get(kind)
        if f and (Path(campaign_dir) / "music" / "themes" / f).is_file():
            return f
    return None


def has_theme(campaign_dir, name: str, boss: bool) -> bool:
    reg = load_registry(campaign_dir)["themes"]
    f = (reg.get(_key(reg, name)) or {}).get("boss" if boss else "normal")
    return bool(f and (Path(campaign_dir) / "music" / "themes" / f).is_file())


def anthem(campaign_dir, name: str) -> Optional[Dict[str, Any]]:
    reg = load_registry(campaign_dir)["anthems"]
    rec = reg.get(_key(reg, name))
    if rec and (Path(campaign_dir) / "music" / "anthems" / rec.get("file", "")).is_file():
        return rec
    return None


def compose_pieces(campaign_dir, pieces: List[Dict[str, Any]],
                   on_piece: Optional[Callable[[Dict[str, Any], str], None]] = None) -> List[Optional[str]]:
    """Compose themes ({kind: theme, name, boss, look}) and anthems ({kind: anthem,
    sheet}) together, with ONE model load. Each is registered (and ``on_piece(piece,
    file)`` called) as soon as it lands. Returns the file names (None where a piece failed)."""
    camp = Path(campaign_dir)
    style = flavor(camp)
    jobs = []
    for p in pieces:
        if p["kind"] == "theme":
            out = camp / "music" / "themes" / f"{slug(p['name'])}-{'boss' if p['boss'] else 'theme'}.ogg"
            jobs.append({"prompt": theme_prompt(p["name"], p.get("look", ""), style, p["boss"]),
                         "seconds": THEME_SECONDS, "out": str(out), "loop": True})
        else:
            name = p["sheet"].get("name", "hero")
            out = camp / "music" / "anthems" / f"anthem-{slug(name)}.ogg"
            jobs.append({"prompt": anthem_prompt(p["sheet"], style), "seconds": ANTHEM_SECONDS,
                         "out": str(out), "loop": False})
    files: List[Optional[str]] = [None] * len(pieces)

    def landed(i: int, r: Dict[str, Any]) -> None:
        p, f = pieces[i], Path(r["path"]).name
        reg = load_registry(camp)
        if p["kind"] == "theme":
            key = _key(reg["themes"], p["name"]) or p["name"]
            reg["themes"].setdefault(key, {})["boss" if p["boss"] else "normal"] = f
        else:
            name = p["sheet"].get("name", "hero")
            key = _key(reg["anthems"], name) or name
            reg["anthems"][key] = {"file": f, "seconds": r.get("seconds", ANTHEM_SECONDS)}
        save_registry(camp, reg)
        files[i] = f
        if on_piece is not None:
            on_piece(p, f)

    compose_many(jobs, landed)
    return files


def compose_theme(campaign_dir, name: str, boss: bool, look: str = "") -> str:
    out = Path(campaign_dir) / "music" / "themes" / f"{slug(name)}-{'boss' if boss else 'theme'}.ogg"
    got = compose(theme_prompt(name, look, flavor(campaign_dir), boss), THEME_SECONDS, out, loop=True)
    reg = load_registry(campaign_dir)
    key = _key(reg["themes"], name) or name
    reg["themes"].setdefault(key, {})["boss" if boss else "normal"] = Path(got["path"]).name
    save_registry(campaign_dir, reg)
    return Path(got["path"]).name


def compose_anthem(campaign_dir, sheet: Dict[str, Any]) -> Dict[str, Any]:
    name = sheet.get("name", "hero")
    out = Path(campaign_dir) / "music" / "anthems" / f"anthem-{slug(name)}.ogg"
    got = compose(anthem_prompt(sheet, flavor(campaign_dir)), ANTHEM_SECONDS, out)
    reg = load_registry(campaign_dir)
    key = _key(reg["anthems"], name) or name
    reg["anthems"][key] = {"file": Path(got["path"]).name, "seconds": got.get("seconds", ANTHEM_SECONDS)}
    save_registry(campaign_dir, reg)
    return reg["anthems"][key]


def normalize_files(campaign_dir) -> List[Dict[str, Any]]:
    """Bring this campaign's composed pieces to the standard loudness (pieces
    composed before the composer did that by itself are often very quiet)."""
    py = composer_python()
    if py is None:
        raise ComposeError("the composer isn't set up (bash tools/gm-music-compose.sh setup)")
    music = Path(campaign_dir) / "music"
    files = sorted(str(f) for sub in ("themes", "anthems") for f in (music / sub).glob("*")
                   if f.suffix.lower() in (".ogg", ".wav"))
    if not files:
        return []
    done = subprocess.run([str(py), str(SCRIPT), "--normalize", *files], capture_output=True, text=True, **NO_WINDOW,
                          encoding="utf-8", errors="replace", timeout=600, env={**os.environ, "PYTHONUTF8": "1"})
    got = [json.loads(l) for l in done.stdout.splitlines() if l.strip().startswith("{")]
    if not got:
        tail = (done.stderr or done.stdout or "").strip().splitlines()[-3:]
        raise ComposeError("the composer failed: " + " | ".join(tail))
    return got


def main() -> None:
    """CLI behind tools/gm-music-compose.sh (theme / anthem / normalize / status)."""
    import argparse
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from campaign_manager import CampaignManager
    ap = argparse.ArgumentParser(description="Composed music for villains, bosses and heroes")
    sub = ap.add_subparsers(dest="action", required=True)
    t = sub.add_parser("theme", help="Compose a villain's theme (--boss: their boss battle theme)")
    t.add_argument("name")
    t.add_argument("--boss", action="store_true")
    t.add_argument("--look", default="", help="What they're like (shapes the music)")
    a = sub.add_parser("anthem", help="Compose a player character's heroic anthem")
    a.add_argument("name")
    sub.add_parser("normalize", help="Bring this campaign's composed music up to the standard loudness")
    sub.add_parser("status", help="Is the composer set up? What has been composed?")
    args = ap.parse_args()

    camp = CampaignManager(os.environ.get("GM_WORLD_STATE_BASE", "world-state")).get_active_campaign_dir()
    if args.action == "status":
        print(f"Composer: {'ready (' + str(composer_python()) + ')' if available() else 'not set up'}")
        if camp:
            reg = load_registry(camp)
            for n, rec in reg["themes"].items():
                print(f"  theme  {n}: {', '.join(f'{k} {v}' for k, v in rec.items())}")
            for n, rec in reg["anthems"].items():
                print(f"  anthem {n}: {rec['file']} ({rec.get('seconds')} s)")
        return
    if camp is None:
        sys.exit("[ERROR] No active campaign.")
    try:
        if args.action == "normalize":
            got = normalize_files(camp)
            if not got:
                print("Nothing composed in this campaign yet.")
            for r in got:
                name = Path(r["path"]).name
                print(f"  [SUCCESS] {name}: {r['before_db']} -> {r['after_db']} dB" if r.get("ok")
                      else f"  [FAILED]  {name}: {r.get('error')}")
            return
        if args.action == "theme":
            f = compose_theme(camp, args.name, args.boss, args.look)
            print(f"[SUCCESS] {args.name}'s {'boss ' if args.boss else ''}theme: music/themes/{f}")
        else:
            import party_roster
            from character_schema import to_flat
            path = party_roster.find_pc(camp, args.name)
            if path is None:
                sys.exit(f"[ERROR] No player character named {args.name}.")
            rec = compose_anthem(camp, to_flat(json.loads(path.read_text(encoding="utf-8"))))
            print(f"[SUCCESS] {args.name}'s anthem: music/anthems/{rec['file']} ({rec['seconds']} s)")
    except ComposeError as e:
        sys.exit(f"[ERROR] {e}")


if __name__ == "__main__":
    main()
