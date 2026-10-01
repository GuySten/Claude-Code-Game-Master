#!/usr/bin/env python3
"""
Fields for the status-line HUD (tools/gm-statusline.sh), as tab-separated lines.
Replaces the jq filters it used, so the HUD works without jq (e.g. on Windows).

  hud_fields.py char FILE    name race class level ac gold hp hp_max xp xp_next location
  hud_fields.py conds FILE   conditions, lower-case, comma-separated
  hud_fields.py over FILE    current_date time_of_day current_location
"""

import json
import sys


def first(data, *paths, default=""):
    """The first path whose value is set (jq's `a // b // default`)."""
    for path in paths:
        value = data
        for key in path.split("."):
            value = value.get(key) if isinstance(value, dict) else None
        if value not in (None, False):
            return value
    return default


def cell(value) -> str:
    if isinstance(value, dict):
        value = value.get("current", "")
    return str(value).replace("\t", " ").replace("\n", " ")


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    kind, path = sys.argv[1], sys.argv[2]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    if kind == "char":
        row = [first(data, "name", "identity.name", default="?"),
               first(data, "race", "identity.race", default="?"),
               first(data, "class", "identity.class", default="?"),
               first(data, "level", "progression.level", default=1),
               first(data, "ac", "vitals.ac", default="?"),
               first(data, "gold", "inventory.gold", default=0),
               first(data, "hp.current", "vitals.hp.current", "hp", default=0),
               first(data, "hp.max", "vitals.hp.max", "hp", default=0),
               first(data, "xp.current", "progression.xp.current", "xp", default=0),
               first(data, "xp.next_level", "progression.xp.next_level", default=0),
               first(data, "current_location", "details.current_location", default="?")]
        print("\t".join(cell(v) for v in row))
    elif kind == "conds":
        conds = data.get("conditions") or []
        print(", ".join(str(c).lower() for c in conds if c) if isinstance(conds, list) else "")
    elif kind == "over":
        row = [first(data, "current_date"), first(data, "time_of_day"),
               first(data, "player_position.current_location")]
        print("\t".join(cell(v) for v in row))
    else:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
