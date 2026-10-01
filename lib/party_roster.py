#!/usr/bin/env python3
"""
Party roster — every player character (PC) at the table.

A campaign always has one LEAD PC in ``character.json`` (the sheet the whole
runtime has always read: statusline, opening seed, images, campaign list). When
more than one human is playing, each additional PC lives in
``players/<slug>.json`` in the same canonical flat shape. Single-player
campaigns never create ``players/`` and behave exactly as before.

These helpers are pure filesystem reads so every manager (player, session,
campaign list, world stats, image gen) resolves PCs the same way.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LEAD_FILE = "character.json"
PLAYERS_DIR = "players"


def slugify(name: str) -> str:
    """File-safe id for a PC name ('Bram Ashford' -> 'bram-ashford')."""
    keep = []
    for ch in str(name or "").strip().lower():
        if ch.isalnum():
            keep.append(ch)
        elif ch in " -_":
            keep.append("-")
    slug = "-".join(part for part in "".join(keep).split("-") if part)
    return slug or "player"


def _same_name(a: Any, b: Any) -> bool:
    return str(a or "").strip().lower() == str(b or "").strip().lower()


def _read(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def lead_path(campaign_dir) -> Path:
    # Absolute, so callers can hand the path to json_ops (which joins relative
    # names onto the campaign dir) without doubling it.
    return Path(campaign_dir).resolve() / LEAD_FILE


def players_dir(campaign_dir) -> Path:
    return Path(campaign_dir).resolve() / PLAYERS_DIR


def extra_pcs(campaign_dir) -> List[Tuple[Path, Dict[str, Any]]]:
    """(path, sheet) for every additional PC, in a stable (filename) order."""
    pdir = players_dir(campaign_dir)
    if not pdir.is_dir():
        return []
    out = []
    for path in sorted(pdir.glob("*.json")):
        data = _read(path)
        if data is not None:
            out.append((path, data))
    return out


def all_pcs(campaign_dir) -> List[Tuple[Path, Dict[str, Any]]]:
    """(path, sheet) for every PC — the lead first, then the extras."""
    out = []
    lead = lead_path(campaign_dir)
    if lead.exists():
        data = _read(lead)
        if data is not None:
            out.append((lead, data))
    return out + extra_pcs(campaign_dir)


def is_multiplayer(campaign_dir) -> bool:
    return bool(extra_pcs(campaign_dir))


def find_pc(campaign_dir, name: str) -> Optional[Path]:
    """Path of the PC sheet named ``name`` (case-insensitive; slug also matches).

    Returns None when no PC carries that name. Callers decide what an unknown
    name means (single-player campaigns historically ignore it).
    """
    if not name:
        return None
    wanted_slug = slugify(name)
    for path, data in all_pcs(campaign_dir):
        if _same_name(data.get("name"), name):
            return path
    for path, data in all_pcs(campaign_dir):
        if slugify(data.get("name", "")) == wanted_slug or path.stem == wanted_slug:
            return path
    return None


def pc_names(campaign_dir) -> List[str]:
    return [data.get("name", path.stem) for path, data in all_pcs(campaign_dir)]


def extra_path_for(campaign_dir, name: str) -> Path:
    return players_dir(campaign_dir) / f"{slugify(name)}.json"
