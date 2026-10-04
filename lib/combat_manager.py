#!/usr/bin/env python3
"""
Persisted combat state.

Combat is the one subsystem that used to persist NOTHING — initiative, enemy HP,
conditions, and the round lived only in the model's working memory and drifted
across turns/compaction/resume. This manager keeps it in `combat_state.json` so
combat is resumable and truthful. Combat is OPTIONAL: a narrated skirmish that
never calls `start` still works; this is for fights worth tracking.

Harm/conditions go through the generic game_core (no 5e assumptions).
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from entity_manager import EntityManager
from game_core import apply_harm, heal, add_condition, remove_condition


class CombatManager(EntityManager):
    def __init__(self, world_state_dir: str = None):
        super().__init__(world_state_dir)
        self.combat_file = "combat_state.json"

    def _load(self) -> Dict[str, Any]:
        return self.json_ops.load_json(self.combat_file) or {}

    def _save(self, data: Dict[str, Any]) -> bool:
        return self.json_ops.save_json(self.combat_file, data)

    def is_active(self) -> bool:
        return bool(self._load().get('combatants'))

    def start(self) -> Dict[str, Any]:
        data = {'active': True, 'round': 1, 'turn_index': 0, 'combatants': []}
        self._save(data)
        return data

    def add_combatant(self, name: str, hp: int, ac: int = 10,
                      initiative: int = 0, side: str = 'enemy') -> Dict[str, Any]:
        data = self._load()
        if not data.get('active'):
            data = self.start()
        combatant = {
            'name': name, 'hp_current': int(hp), 'hp_max': int(hp),
            'ac': int(ac), 'conditions': [], 'initiative': int(initiative), 'side': side,
        }
        data.setdefault('combatants', []).append(combatant)
        data['combatants'].sort(key=lambda c: c.get('initiative', 0), reverse=True)
        self._save(data)
        return combatant

    def _find(self, data, name):
        for c in data.get('combatants', []):
            if c['name'].lower() == name.lower():
                return c
        return None

    def modify_hp(self, name: str, delta: int) -> Optional[Dict[str, Any]]:
        data = self._load()
        c = self._find(data, name)
        if c is None:
            return None
        if delta < 0:
            c['hp_current'] = apply_harm(c['hp_current'], -delta)
        else:
            c['hp_current'] = heal(c['hp_current'], c['hp_max'], delta)
        self._save(data)
        return c

    def set_condition(self, name: str, action: str, condition: str) -> Optional[Dict[str, Any]]:
        data = self._load()
        c = self._find(data, name)
        if c is None:
            return None
        c['conditions'] = (add_condition(c['conditions'], condition) if action == 'add'
                           else remove_condition(c['conditions'], condition))
        self._save(data)
        return c

    def next_turn(self) -> Dict[str, Any]:
        data = self._load()
        n = len(data.get('combatants', []))
        if n == 0:
            return data
        data['turn_index'] = (data.get('turn_index', 0) + 1) % n
        if data['turn_index'] == 0:
            data['round'] = data.get('round', 1) + 1
        self._save(data)
        return data

    def end(self) -> Dict[str, Any]:
        data = self._load()
        summary = {
            'rounds': data.get('round', 1),
            'combatants': [c['name'] for c in data.get('combatants', [])],
            'defeated': [c['name'] for c in data.get('combatants', []) if c.get('hp_current', 1) <= 0],
        }
        self._save({})  # clear — combat is over
        return summary

    def header(self) -> str:
        data = self._load()
        if not data.get('combatants'):
            return "(no active combat)"
        lines = [f"⚔ COMBAT — Round {data.get('round', 1)}"]
        for i, c in enumerate(data['combatants']):
            marker = '>' if i == data.get('turn_index', 0) else ' '
            dead = ' 💀' if c.get('hp_current', 1) <= 0 else ''
            cond = f" [{', '.join(c['conditions'])}]" if c.get('conditions') else ""
            lines.append(f"{marker} {c['name']}: {c['hp_current']}/{c['hp_max']} HP, AC {c['ac']}{cond}{dead}")
        return "\n".join(lines)


def main():
    import argparse
    import json
    from cli_output import wants_json, strip_json_flag, emit, emit_error

    parser = argparse.ArgumentParser(description="Persisted combat state")
    sub = parser.add_subparsers(dest='action')
    sub.add_parser('start')
    p = sub.add_parser('add-enemy'); p.add_argument('name'); p.add_argument('hp', type=int)
    p.add_argument('--ac', type=int, default=10); p.add_argument('--init', type=int, default=0)
    p = sub.add_parser('hp'); p.add_argument('name'); p.add_argument('delta', type=int)
    p = sub.add_parser('condition'); p.add_argument('name'); p.add_argument('op', choices=['add', 'remove']); p.add_argument('condition')
    sub.add_parser('next-turn')
    sub.add_parser('header')
    sub.add_parser('status')
    sub.add_parser('end')

    json_mode = wants_json()
    args = parser.parse_args(strip_json_flag(sys.argv[1:]))
    if not args.action:
        parser.print_help(); sys.exit(1)

    m = CombatManager()
    out = None
    if args.action == 'start':
        out = m.start()
    elif args.action == 'add-enemy':
        out = m.add_combatant(args.name, args.hp, ac=args.ac, initiative=args.init)
    elif args.action == 'hp':
        locked = m._find(m._load(), args.name)
        if locked and locked.get('locked'):
            # A foe with a stat block (lib/referee.py): its HP changes only through the
            # referee, in public and in the log.
            sys.exit(f"[ERROR] {locked['name']}'s HP is locked: use gm-referee.sh attack / damage / heal")
        out = m.modify_hp(args.name, args.delta)
    elif args.action == 'condition':
        out = m.set_condition(args.name, args.op, args.condition)
    elif args.action == 'next-turn':
        out = m.next_turn()
    elif args.action == 'end':
        out = m.end()
    elif args.action in ('header', 'status'):
        print(m.header()); return

    if out is None:
        if json_mode:
            sys.exit(emit_error("combatant not found", json_mode=True))
        print("[ERROR] combatant not found", file=sys.stderr); sys.exit(1)
    if json_mode:
        emit(out, json_mode=True)
    else:
        print(json.dumps(out, indent=2))
        print(m.header())


if __name__ == "__main__":
    main()
