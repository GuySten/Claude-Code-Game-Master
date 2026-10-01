#!/usr/bin/env python3
"""
Starter music library for the online table.

``music/library.json`` lists freely licensed tracks, each tagged with the scene
mood it fits. ``fetch`` downloads the ones that are missing into ``music/``,
named ``<mood>-<title>.mp3`` so the table's automatic music (``say --mood``)
picks them up with no further setup, and writes ``music/CREDITS.md`` — the
attribution the licenses ask for. The table page also shows each track's
credit while it plays.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MUSIC_DIR = PROJECT_ROOT / "music"
LIBRARY = MUSIC_DIR / "library.json"
MIN_BYTES = 50 * 1024          # anything smaller is an error page, not a song
USER_AGENT = "gm-claude-music-library/1.0 (+https://github.com/Sstobo/Claude-Code-Game-Master)"


def load_library(path: Path = LIBRARY) -> List[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    tracks = data.get("tracks", []) if isinstance(data, dict) else []
    return [t for t in tracks if isinstance(t, dict) and t.get("file") and t.get("url")]


def credit_line(track: Dict[str, Any]) -> str:
    """'"Five Armies" by Kevin MacLeod (incompetech.com) — CC BY 4.0'"""
    source = str(track.get("source", "")).replace("https://", "").replace("http://", "").rstrip("/")
    who = track.get("artist", "Unknown artist") + (f" ({source})" if source else "")
    return f"\"{track.get('title', track['file'])}\" by {who} — {track.get('license', '')}".rstrip(" —")


def credit_for(file_name: str, path: Path = LIBRARY) -> Optional[str]:
    for track in load_library(path):
        if track["file"].lower() == str(file_name).lower():
            return credit_line(track)
    return None


def write_credits(tracks: List[Dict[str, Any]], music_dir: Path = MUSIC_DIR) -> Path:
    have = [t for t in tracks if (music_dir / t["file"]).is_file()]
    lines = ["# Music credits", "",
             "Tracks fetched from music/library.json for the online table.", ""]
    for t in have:
        lic = t.get("license", "")
        if t.get("license_url"):
            lic = f"[{lic}]({t['license_url']})"
        lines.append(f"- `{t['file']}` — \"{t.get('title')}\" by {t.get('artist')} "
                     f"({t.get('source', '')}), licensed under {lic}")
    path = music_dir / "CREDITS.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def fetch_one(track: Dict[str, Any], music_dir: Path = MUSIC_DIR, timeout: int = 60) -> str:
    """Download one track. Returns 'have', 'ok', or an error description."""
    dest = music_dir / track["file"]
    if dest.is_file() and dest.stat().st_size >= MIN_BYTES:
        return "have"
    req = urllib.request.Request(track["url"], headers={"User-Agent": USER_AGENT})
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ctype = resp.headers.get("Content-Type", "")
            if "text/html" in ctype:
                return f"not an audio file ({ctype})"
            with open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
    except urllib.error.HTTPError as e:
        tmp.unlink(missing_ok=True)
        return f"HTTP {e.code}"
    except (urllib.error.URLError, OSError) as e:
        tmp.unlink(missing_ok=True)
        return f"could not download ({getattr(e, 'reason', e)})"
    if tmp.stat().st_size < MIN_BYTES:
        tmp.unlink(missing_ok=True)
        return "download too small to be a song"
    tmp.replace(dest)
    return "ok"


def main() -> None:
    parser = argparse.ArgumentParser(description="Starter music library for the online table")
    sub = parser.add_subparsers(dest="action")
    sub.add_parser("list", help="Show the library and which tracks are already downloaded")
    f = sub.add_parser("fetch", help="Download the missing tracks into music/")
    f.add_argument("--mood", help="Only tracks for this mood")
    args = parser.parse_args()

    tracks = load_library()
    if not tracks:
        sys.exit(f"[ERROR] No tracks in {LIBRARY}")
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)

    if args.action in (None, "list"):
        by_mood: Dict[str, List[Dict[str, Any]]] = {}
        for t in tracks:
            by_mood.setdefault(t.get("mood", "?"), []).append(t)
        for mood, items in by_mood.items():
            print(f"{mood}:")
            for t in items:
                mark = "✓" if (MUSIC_DIR / t["file"]).is_file() else " "
                print(f"  [{mark}] {t['file']:<44} {credit_line(t)}")
        print("\nDownload the missing ones with: bash tools/gm-music-library.sh fetch")
        return

    if args.action == "fetch":
        chosen = [t for t in tracks if not args.mood or t.get("mood") == args.mood]
        got = have = 0
        failed = []
        for i, t in enumerate(chosen, 1):
            print(f"[{i}/{len(chosen)}] {t['file']} ... ", end="", flush=True)
            result = fetch_one(t)
            print({"have": "already here", "ok": "downloaded"}.get(result, f"FAILED: {result}"))
            if result == "ok":
                got += 1
            elif result == "have":
                have += 1
            else:
                failed.append((t, result))
        credits = write_credits(tracks)
        print(f"\n{got} downloaded, {have} already here, {len(failed)} failed. "
              f"Credits: {credits.relative_to(PROJECT_ROOT)}")
        if failed:
            print("Failed tracks fall back to the built-in sounds for their mood. If a link has "
                  "moved, fix its url in music/library.json and run fetch again.")
            sys.exit(1 if not (got or have) else 0)
        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
