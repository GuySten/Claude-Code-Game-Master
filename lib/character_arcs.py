#!/usr/bin/env python3
"""A character's story arc: the moments that changed them, recorded by the GM when
the story earns them (never by level or any other count), and what each does to
the character's theme (lib/music_compose.py), which follows them unannounced:

  growth   - a fear faced, a purpose found, a choice that defines them: the theme
             grows (a lone voice -> the theme as written -> the full orchestra)
  bond     - a friendship, a love, a sworn companion: a warmer arrangement
  wound    - a loss, a failure, grief: a lament, until healed
  healing  - the wound closes: the lament lifts
  darkness - a cruel choice, a temptation taken: the tune borrows a darker note
             (up to three: it slides toward the villain they could become)
  light    - atonement, mercy, sacrifice: one dark note given back
  finale   - the campaign's climax: the legendary version

The table says only that the character changed; the music shows how.
Kept in the campaign's character-arcs.json.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

FILE = "character-arcs.json"
KINDS = ("growth", "bond", "wound", "healing", "darkness", "light", "finale")
STAGES = ("seed", "theme", "heroic", "legendary")   # 0: a lone voice ... 3: the finale
MAX_DARK = 3


def _path(campaign_dir) -> Path:
    return Path(campaign_dir) / FILE


def load(campaign_dir) -> Dict[str, Any]:
    try:
        data = json.loads(_path(campaign_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    return data if isinstance(data, dict) else {}


def save(campaign_dir, data: Dict[str, Any]) -> None:
    path = _path(campaign_dir)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _key(data: Dict[str, Any], name: str) -> str:
    return next((k for k in data if k.strip().casefold() == name.strip().casefold()), name.strip())


def state_of(campaign_dir, name: str) -> Dict[str, Any]:
    """Where this character's story is (a new character: at the start of it)."""
    data = load(campaign_dir)
    got = data.get(_key(data, name)) or {}
    return {"stage": int(got.get("stage", 0)), "dark": int(got.get("dark", 0)),
            "wound": bool(got.get("wound", False)), "bonds": list(got.get("bonds") or []),
            "milestones": list(got.get("milestones") or [])}


def apply(state: Dict[str, Any], kind: str, other: Optional[str] = None) -> Dict[str, Any]:
    """What one moment does to the arc."""
    if kind not in KINDS:
        raise ValueError(f"a moment is one of: {', '.join(KINDS)}")
    s = {**state, "bonds": list(state.get("bonds") or [])}
    if kind == "growth":
        s["stage"] = min(2, s["stage"] + 1)              # (legendary is the finale's alone)
    elif kind == "finale":
        s["stage"] = 3
    elif kind == "wound":
        s["wound"] = True
    elif kind == "healing":
        s["wound"] = False
    elif kind == "darkness":
        s["dark"] = min(MAX_DARK, s["dark"] + 1)
    elif kind == "light":
        s["dark"] = max(0, s["dark"] - 1)
    elif kind == "bond" and other and other not in s["bonds"]:
        s["bonds"].append(other)
    return s


def record(campaign_dir, name: str, kind: str, what: str, other: Optional[str] = None) -> Dict[str, Any]:
    """The GM records a moment that changed this character. Returns the new state."""
    data = load(campaign_dir)
    key = _key(data, name)
    state = apply(state_of(campaign_dir, name), kind, other)
    state["milestones"] = state["milestones"] + [{"t": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                                  "kind": kind, "what": what,
                                                  **({"with": other} if other else {})}]
    data[key] = state
    save(campaign_dir, data)
    return state


def spec(state: Dict[str, Any]) -> Dict[str, Any]:
    """What the theme needs to know: {stage, dark, wound, warm}."""
    return {"stage": state["stage"], "dark": state["dark"], "wound": state["wound"],
            "warm": bool(state.get("bonds"))}


def version(sp: Dict[str, Any]) -> str:
    """A name for one version of a theme, e.g. "s2-d1-w0-b1"."""
    return f"s{sp['stage']}-d{sp['dark']}-w{int(sp['wound'])}-b{int(sp.get('warm', False))}"


def next_growth(sp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The version the next growth would bring (composed ahead, to be ready)."""
    if sp["stage"] >= 2:
        return None
    return {**sp, "stage": sp["stage"] + 1}
