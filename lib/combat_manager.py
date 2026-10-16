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
                      initiative: int = 0, side: str = 'enemy',
                      zone: Optional[str] = None) -> Dict[str, Any]:
        data = self._load()
        if not data.get('active'):
            data = self.start()
        combatant = {
            'name': name, 'hp_current': int(hp), 'hp_max': int(hp),
            'ac': int(ac), 'conditions': [], 'initiative': int(initiative), 'side': side,
        }
        if zone:
            combatant['zone'] = " ".join(str(zone).split())
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

    def set_zone(self, name: str, zone: Optional[str]) -> Optional[Dict[str, Any]]:
        """Where a combatant is ("on the chain, 15 ft up", "at the grate"): reach and
        range are judged from it. A PC not yet in the fight joins it (while one is
        on). An empty zone clears it."""
        data = self._load()
        c = self._find(data, name)
        if c is None:
            import party_roster
            path = party_roster.find_pc(self.campaign_dir, name) if data.get('active') else None
            if path is None:
                return None
            sheet = party_roster._read(path) or {}
            c = {'name': sheet.get('name', name), 'side': 'party', 'kind': 'pc',
                 'initiative': 0, 'conditions': [], 'states': {}}
            data.setdefault('combatants', []).append(c)
        zone = " ".join(str(zone or "").split())
        if zone:
            c['zone'] = zone
        else:
            c.pop('zone', None)
        self._save(data)
        return c

    @staticmethod
    def takes_turns(c: Dict[str, Any]) -> bool:
        """An object (a vein, a plate: a stat block with no attacks) and a foe at 0 HP
        have no turn; a PC always does (at 0 HP it makes death saves)."""
        if c.get('kind') == 'pc' or c.get('side') == 'party':
            return True
        if isinstance(c.get('block'), dict) and not c['block'].get('attacks'):
            return False
        return c.get('hp_current', 1) > 0

    def next_turn(self) -> Dict[str, Any]:
        """The next combatant who takes a turn (objects and fallen foes are passed by);
        past the last one, the next round."""
        data = self._load()
        cs = data.get('combatants', [])
        if not cs or not any(self.takes_turns(c) for c in cs):
            return data
        i = data.get('turn_index', 0)
        for _ in range(len(cs)):
            i += 1
            if i >= len(cs):
                i = 0
                data['round'] = data.get('round', 1) + 1
            if self.takes_turns(cs[i]):
                break
        data['turn_index'] = i
        self._save(data)
        return data

    def catch_up(self, name: str) -> Optional[str]:
        """``name`` acts (an attack, a hide, a death save): make it their turn, so the
        record (and the players' panel) follows the fight even when next-turn was never
        run. Someone later in the order: the turns between are passed; someone earlier:
        a new round. Returns a line saying what moved, or None (already their turn, or
        no fight). A reaction (an opportunity attack) must not call this."""
        data = self._load()
        cs = data.get('combatants', [])
        if not data.get('active') or not cs:
            return None
        idx = next((k for k, c in enumerate(cs) if c['name'].lower() == name.lower()), None)
        cur = data.get('turn_index', 0)
        if idx is None or idx == cur:
            return None
        if idx < cur:
            data['round'] = data.get('round', 1) + 1
        passed = [c['name'] for c in (cs[cur:idx] if idx > cur else cs[cur:] + cs[:idx])
                  if self.takes_turns(c)]
        data['turn_index'] = idx
        self._save(data)
        return (f"↻ turn: {cs[idx]['name']}, round {data.get('round', 1)}"
                + (f" (passed: {', '.join(passed)})" if passed else ""))

    def remove(self, name: str) -> Optional[Dict[str, Any]]:
        """Take someone out of the fight who is no longer in it (a freed captive, a foe
        who surrendered or fled): off the order and off the players' panel. The turn
        stays with whoever has it."""
        data = self._load()
        cs = data.get('combatants', [])
        idx = next((k for k, c in enumerate(cs) if c['name'].lower() == name.lower()), None)
        if idx is None:
            return None
        gone = cs.pop(idx)
        cur = data.get('turn_index', 0)
        if idx < cur:
            data['turn_index'] = cur - 1
        elif idx == cur and cs:
            data['turn_index'] = cur % len(cs)  # (the next one is up)
        self._save(data)
        return gone

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
            cond = f" [{', '.join(map(str, c['conditions']))}]" if c.get('conditions') else ""
            if 'hp_current' in c:
                hp = f"{c['hp_current']}/{c['hp_max']} HP, AC {c.get('ac', '?')}"
            else:                      # a PC (the referee's): HP lives on the sheet
                hp = "PC (HP on the sheet)"
            zone = f" @ {c['zone']}" if c.get('zone') else ""
            lines.append(f"{marker} {c['name']}: {hp}{cond}{zone}{dead}")
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
    p.add_argument('--zone', help='where it stands ("on the chain, 15 ft up")')
    p = sub.add_parser('zone', help='set where a combatant (or a PC) is; no zone clears it')
    p.add_argument('name'); p.add_argument('zone', nargs='?', default='')
    p = sub.add_parser('hp'); p.add_argument('name'); p.add_argument('delta', type=int)
    p = sub.add_parser('condition'); p.add_argument('name'); p.add_argument('op', choices=['add', 'remove']); p.add_argument('condition')
    sub.add_parser('next-turn')
    p = sub.add_parser('remove', help='take someone out of the fight (a freed captive, a foe who surrendered or fled)')
    p.add_argument('name')
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
        out = m.add_combatant(args.name, args.hp, ac=args.ac, initiative=args.init, zone=args.zone)
    elif args.action == 'zone':
        out = m.set_zone(args.name, args.zone)
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
    elif args.action == 'remove':
        out = m.remove(args.name)
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
