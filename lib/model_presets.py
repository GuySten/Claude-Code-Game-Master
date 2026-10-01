#!/usr/bin/env python3
"""
Model presets — pick which Claude model plays each part of the game.

The GM is the main Claude Code session; 15 helper agents in .claude/agents/
handle side jobs. A preset sets every helper's ``model:`` (its frontmatter)
and the GM's model (``.claude/settings.local.json`` — personal, not committed),
so one command switches the whole table between cost and quality.

Model names are Claude Code aliases (``opus``, ``sonnet``, ``haiku``), which
always resolve to the newest model of that family; ``inherit`` makes a helper
use whatever model the GM runs on.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = PROJECT_ROOT / ".claude" / "agents"
LOCAL_SETTINGS = PROJECT_ROOT / ".claude" / "settings.local.json"

# Who does what (see the README's Specialist Agents table).
GROUPS: Dict[str, List[str]] = {
    "story": ["plot-weaver", "npc-builder", "world-builder", "dungeon-architect",
              "create-character", "rules-master"],
    "lookup": ["monster-manual", "spell-caster", "gear-master", "loot-dropper",
               "scene-illustrator"],
    "import": ["extractor-items", "extractor-locations", "extractor-npcs", "extractor-plots"],
}
GROUP_LABELS = {
    "story": "story helpers (plots, NPCs, places, characters, rulings)",
    "lookup": "lookup helpers (monsters, spells, gear, loot, image prompts)",
    "import": "book import (one-time extraction of a whole book)",
}

PRESETS: Dict[str, Dict[str, str]] = {
    "recommended": {
        "gm": "opus", "story": "sonnet", "lookup": "haiku", "import": "opus",
        "about": "Best balance: a top-quality GM, quick helpers in the background.",
    },
    "budget": {
        "gm": "sonnet", "story": "haiku", "lookup": "haiku", "import": "sonnet",
        "about": "Cheapest that still plays well: Sonnet GM, Haiku helpers.",
    },
    "premium": {
        "gm": "opus", "story": "opus", "lookup": "sonnet", "import": "opus",
        "about": "Quality first: Opus everywhere it matters. Costs the most.",
    },
    "inherit": {
        "gm": "opus", "story": "inherit", "lookup": "inherit", "import": "opus",
        "about": "Every helper uses whatever model the GM runs on (the original setup).",
    },
}
ALIASES = ("opus", "sonnet", "haiku", "inherit")
FRONTMATTER = re.compile(r"\A---\n(.*?\n)---\n", re.S)


def agent_path(name: str) -> Path:
    return AGENTS_DIR / f"{name}.md"


def read_model(name: str) -> Optional[str]:
    """The model an agent names in its frontmatter (None = inherits the GM's)."""
    try:
        text = agent_path(name).read_text(encoding="utf-8")
    except OSError:
        return None
    m = FRONTMATTER.match(text)
    if not m:
        return None
    found = re.search(r"^model:\s*(\S+)\s*$", m.group(1), re.M)
    return found.group(1) if found else None


def write_model(name: str, model: str) -> bool:
    """Set (or, for 'inherit', remove) an agent's model line. True if changed."""
    path = agent_path(name)
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER.match(text)
    if not m:
        raise ValueError(f"{path.name} has no frontmatter")
    head = m.group(1)
    if model == "inherit":
        new_head = re.sub(r"^model:.*\n", "", head, flags=re.M)
    elif re.search(r"^model:", head, re.M):
        new_head = re.sub(r"^model:.*$", f"model: {model}", head, count=1, flags=re.M)
    elif re.search(r"^tools:.*$", head, re.M):
        new_head = re.sub(r"^(tools:.*\n)", rf"\1model: {model}\n", head, count=1, flags=re.M)
    else:
        new_head = head + f"model: {model}\n"
    if new_head == head:
        return False
    path.write_text(f"---\n{new_head}---\n" + text[m.end():], encoding="utf-8")
    return True


def read_gm_model() -> Optional[str]:
    try:
        return json.loads(LOCAL_SETTINGS.read_text(encoding="utf-8")).get("model")
    except (OSError, ValueError, AttributeError):
        return None


def write_gm_model(model: str) -> None:
    """Personal default model for Claude Code in this project (settings.local.json
    is git-ignored, so each host chooses their own)."""
    try:
        settings = json.loads(LOCAL_SETTINGS.read_text(encoding="utf-8"))
        if not isinstance(settings, dict):
            settings = {}
    except (OSError, ValueError):
        settings = {}
    settings["model"] = model
    LOCAL_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_SETTINGS.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def current_preset() -> Optional[str]:
    for name, preset in PRESETS.items():
        if all((read_model(a) or "inherit") == preset[g]
               for g, agents in GROUPS.items() for a in agents):
            return name
    return None


def show() -> None:
    preset = current_preset()
    print(f"GM (main session): {read_gm_model() or 'not set — Claude Code default'}")
    print(f"Helpers match preset: {preset or 'custom'}")
    for group, agents in GROUPS.items():
        print(f"\n{GROUP_LABELS[group]}:")
        for a in agents:
            print(f"  {a:<20} {read_model(a) or 'inherit (follows the GM)'}")
    print("\nPresets:")
    for name, p in PRESETS.items():
        print(f"  {name:<12} GM {p['gm']:<7} story {p['story']:<8} lookup {p['lookup']:<8} "
              f"import {p['import']:<7} {p['about']}")


def apply(preset_name: str, gm: Optional[str] = None) -> Dict[str, object]:
    preset = PRESETS[preset_name]
    changed = []
    for group, agents in GROUPS.items():
        for a in agents:
            if agent_path(a).exists() and write_model(a, preset[group]):
                changed.append(a)
    gm_model = gm or preset["gm"]
    write_gm_model(gm_model)
    return {"preset": preset_name, "gm": gm_model, "changed": changed}


def main() -> None:
    parser = argparse.ArgumentParser(description="Choose which Claude models run the game")
    parser.add_argument("preset", nargs="?", help=f"one of: {', '.join(PRESETS)} (omit to show)")
    parser.add_argument("--gm", choices=["opus", "sonnet", "haiku"],
                        help="override the GM's model from the preset")
    args = parser.parse_args()

    if not args.preset or args.preset in ("show", "list"):
        return show()
    if args.preset not in PRESETS:
        sys.exit(f"[ERROR] Unknown preset '{args.preset}'. Choose from: {', '.join(PRESETS)}")

    result = apply(args.preset, args.gm)
    p = PRESETS[args.preset]
    print(f"✓ Preset '{args.preset}': {p['about']}")
    print(f"  GM: {result['gm']}  ·  story helpers: {p['story']}  ·  lookup helpers: "
          f"{p['lookup']}  ·  book import: {p['import']}")
    print(f"  Updated {len(result['changed'])} helper agent(s); GM model saved to "
          f".claude/settings.local.json")
    print("  Takes effect in the next Claude Code session. In a running session, switch the "
          f"GM now with: /model {result['gm']}")
    print("  For a live table with friends waiting, /fast makes the GM reply faster "
          "(same model, higher price).")


if __name__ == "__main__":
    main()
