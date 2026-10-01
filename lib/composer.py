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

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_VENV = PROJECT_ROOT / ".compose-venv"
SCRIPT = Path(__file__).resolve().parent / "music_compose.py"
THEME_SECONDS = 30
ANTHEM_SECONDS = 20


class ComposeError(Exception):
    pass


def composer_python() -> Optional[Path]:
    """The composer environment's Python, or None (not set up, or turned off)."""
    if os.environ.get("MUSIC_COMPOSE", "").strip().lower() in ("off", "0", "no", "false"):
        return None
    for p in (COMPOSE_VENV / "Scripts" / "python.exe", COMPOSE_VENV / "bin" / "python"):
        if p.is_file():
            return p
    return None


def available() -> bool:
    return composer_python() is not None


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")[:40] or "piece"


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


def compose(prompt: str, seconds: float, out: Path, loop: bool = False,
            timeout: int = 3600) -> Dict[str, Any]:
    """Run the composer (blocking: a minute or two on a GPU, several on a CPU)."""
    py = composer_python()
    if py is None:
        raise ComposeError("the composer isn't set up (bash tools/gm-music-compose.sh setup)")
    cmd = [str(py), str(SCRIPT), "--prompt", prompt, "--seconds", str(seconds), "--out", str(out)]
    if loop:
        cmd.append("--loop")
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              env={**os.environ, "PYTHONUTF8": "1"})
    except subprocess.TimeoutExpired as e:
        raise ComposeError(f"composing took longer than {timeout} s") from e
    lines = [l for l in done.stdout.splitlines() if l.strip().startswith("{")]
    if done.returncode != 0 or not lines:
        tail = (done.stderr or done.stdout or "").strip().splitlines()[-3:]
        raise ComposeError("the composer failed: " + " | ".join(tail))
    return json.loads(lines[-1])


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


def main() -> None:
    """CLI behind tools/gm-music-compose.sh (theme / anthem / status)."""
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
