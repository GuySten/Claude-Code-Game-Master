#!/usr/bin/env python3
"""The referee: checks, saves and attacks resolved from the RECORDS, never from the
Game Master's say-so.

A GM who picks numbers in the moment can't help leaning on them: a modifier here,
a forgotten penalty there, a hazard that only bites one side. The referee takes
those choices away:

- **No numbers from the GM.** Bonuses come from the sheets (PCs) and the locked
  stat blocks (foes); a difficulty is a word from the standard ladder (easy=10 …
  nearly-impossible=30) or a number a record states (a spell's save DC, a foe's
  ability). There is no "+2 because" argument anywhere.
- **Situations are recorded state, not per-roll choices.** Conditions (prone,
  poisoned, restrained…), cover, being hidden, being helped and battlefield
  effects (a shaking floor, thick fog) are written onto the fight once and then
  apply to EVERY roll they touch, on both sides, until they end. A foe is exempt
  from a battlefield effect only through a trait its stat block lists.
- **Hidden is earned.** `hide` rolls Stealth against the best passive Perception
  of the other side; only a success records it, and attacking ends it.
- **Everything is shown.** Each roll goes to the open table's public dice log,
  with every advantage, disadvantage and cover named ("⚖ Pip — Shortsword vs
  Grak · advantage: Grak is prone").
- **Foes' hit points are locked.** A foe's HP changes only through the referee
  (attacks, `damage`, `heal`), never by hand.
- **Everything is logged.** Each decision goes to the campaign's referee-log.jsonl:
  who, which record every number came from, each advantage/disadvantage and why,
  the difficulty and the result. Dice rolled OUTSIDE the referee (lib/dice.py) are
  logged there too, as free rolls. `gm-referee.sh log` reads it, `report` sums it
  up per side, so the players can check that the GM is fair.

Combat state lives in the campaign's combat_state.json (lib/combat_manager.py);
the PCs' own sheets stay the record for PCs (HP, conditions).
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))

import dice  # noqa: E402
from combat_manager import CombatManager  # noqa: E402
from player_manager import PlayerManager, death_saves, life_status  # noqa: E402

ABILITIES = ("str", "dex", "con", "int", "wis", "cha")
ABILITY_NAMES = {"strength": "str", "dexterity": "dex", "constitution": "con",
                 "intelligence": "int", "wisdom": "wis", "charisma": "cha"}
SKILLS = {
    "acrobatics": "dex", "animal handling": "wis", "arcana": "int", "athletics": "str",
    "deception": "cha", "history": "int", "insight": "wis", "intimidation": "cha",
    "investigation": "int", "medicine": "wis", "nature": "int", "perception": "wis",
    "performance": "cha", "persuasion": "cha", "religion": "int", "sleight of hand": "dex",
    "stealth": "dex", "survival": "wis",
}
# The standard difficulty ladder: the only free choice the GM has, and it's coarse.
DC_LADDER = {"very-easy": 5, "easy": 10, "medium": 15, "hard": 20, "very-hard": 25,
             "nearly-impossible": 30}
CASTING = {"warlock": "cha", "sorcerer": "cha", "bard": "cha", "paladin": "cha",
           "wizard": "int", "artificer": "int", "cleric": "wis", "druid": "wis",
           "ranger": "wis", "monk": "wis"}

# Conditions (5e SRD) and what they do to rolls, applied from the record.
ATTACKER_ADV = {"invisible"}
ATTACKER_DIS = {"blinded", "frightened", "poisoned", "prone", "restrained"}
TARGET_GIVES_ADV = {"blinded", "paralyzed", "petrified", "restrained", "stunned", "unconscious"}
TARGET_GIVES_DIS = {"invisible"}
MELEE_AUTO_CRIT = {"paralyzed", "unconscious"}
CHECK_DIS = {"poisoned", "frightened", "cursed"}   # (cursed: the table's punishment, until atonement)
AUTO_FAIL_STR_DEX_SAVES = {"paralyzed", "petrified", "stunned", "unconscious"}
COVER_AC = {"half": 2, "three-quarters": 5}
# The same check of the same skill against the same DC by the same character in
# one scene (within this many hours, among this many recent log entries) is
# flagged to the GM as a repeat roll. A note, never a block.
REPEAT_HOURS = 6
REPEAT_WINDOW = 400
# Battlefield effects: what an effect may change, nothing else.
EFFECT_KINDS = {"adv", "dis"}
EFFECT_ROLLS = {"attack", "check", "save"}


class RefereeError(Exception):
    pass


LOG_NAME = "referee-log.jsonl"


def audit(campaign_dir: Optional[Path], entry: Dict[str, Any]) -> None:
    """Append one decision to the campaign's referee log (never fails the game)."""
    if campaign_dir is None:
        return
    import datetime
    entry = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), **entry}
    try:
        with open(Path(campaign_dir) / LOG_NAME, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def active_campaign_dir() -> Optional[Path]:
    try:
        from campaign_manager import CampaignManager
        import os
        camp = CampaignManager(os.environ.get("GM_WORLD_STATE_BASE", "world-state")).get_active_campaign_dir()
        return Path(camp) if camp else None
    except Exception:
        return None


def mod(score: Any) -> int:
    try:
        return (int(score) - 10) // 2
    except (TypeError, ValueError):
        return 0


def _norm(s: Any) -> str:
    return " ".join(str(s or "").replace("_", " ").split()).lower()


def ability_key(name: str) -> Optional[str]:
    n = _norm(name)
    if n in ABILITIES:
        return n
    return ABILITY_NAMES.get(n)


def parse_dc(dc: str) -> int:
    """A ladder word only ("hard"), or a number a record states (use --dc-from)."""
    word = _norm(dc).replace(" ", "-")
    if word in DC_LADDER:
        return DC_LADDER[word]
    raise RefereeError(f"difficulty must be one of: {', '.join(DC_LADDER)} (a number only comes "
                       f"from a record: --vs-passive, --vs-spell-of, --vs-ability)")


class Combatant:
    """One side's numbers, from the PC's sheet or the foe's locked stat block."""

    def __init__(self, name: str, record: Dict[str, Any], kind: str, state: Dict[str, Any]):
        self.name, self.record, self.kind, self.state = name, record, kind, state

    # --- what the record says ---
    @property
    def level(self) -> int:
        try:
            return int(self.record.get("level") or 1)
        except (TypeError, ValueError):
            return 1

    @property
    def prof(self) -> int:
        if self.kind == "enemy":
            return int(self.record.get("proficiency_bonus") or 2)
        try:
            return int(self.record.get("proficiency_bonus"))
        except (TypeError, ValueError):
            return 2 + (self.level - 1) // 4

    def score(self, ab: str) -> int:
        stats = self.record.get("abilities") or self.record.get("stats") or {}
        for k, v in stats.items():
            if ability_key(k) == ab:
                return v if isinstance(v, int) else int(v) if str(v).lstrip("-").isdigit() else 10
        return 10

    def ab_mod(self, ab: str) -> int:
        return mod(self.score(ab))

    def _listed(self, table: str, name: str) -> Optional[int]:
        """A bonus the record states outright (a sheet's "Stealth": 7, a block's skills)."""
        entries = self.record.get(table) or {}
        if isinstance(entries, list):
            return self.prof + 0 if any(_norm(e) == name for e in entries if isinstance(e, str)) else None
        for k, v in entries.items():
            if _norm(k) == name:
                if isinstance(v, bool):
                    return self.prof if v else None
                if isinstance(v, dict):
                    if "bonus" in v:
                        return int(v["bonus"])
                    return self.prof if v.get("proficient") else None
                try:
                    return int(v)
                except (TypeError, ValueError):
                    return None
        return None

    def skill_bonus(self, skill: str) -> Tuple[int, str]:
        skill = _norm(skill)
        if skill in SKILLS:
            listed = self._listed("skills", skill)
            if listed is not None:
                # A list entry means "proficient": ability + proficiency.
                if isinstance(self.record.get("skills"), list):
                    return self.ab_mod(SKILLS[skill]) + listed, skill.title()
                return listed, skill.title()
            return self.ab_mod(SKILLS[skill]), skill.title()
        ab = ability_key(skill)
        if ab:
            return self.ab_mod(ab), ab.upper()
        raise RefereeError(f"not a skill or ability: {skill}")

    def save_bonus(self, ab: str) -> int:
        listed = self._listed("saves", ab)
        if listed is None:
            for k, v in (self.record.get("saves") or {}).items() if isinstance(self.record.get("saves"), dict) else []:
                if ability_key(k) == ab:
                    listed = int(v) if not isinstance(v, bool) else (self.prof if v else None)
        if isinstance(self.record.get("saves"), list) and listed is not None:
            return self.ab_mod(ab) + listed
        return listed if listed is not None else self.ab_mod(ab)

    def passive_perception(self) -> int:
        if self.record.get("passive_perception"):
            return int(self.record["passive_perception"])
        return 10 + self.skill_bonus("perception")[0]

    def ac(self) -> int:
        try:
            return int(self.record.get("ac") or 10)
        except (TypeError, ValueError):
            return 10

    def spell_dc(self) -> int:
        if self.record.get("spell_save_dc"):
            return int(self.record["spell_save_dc"])
        ab = CASTING.get(_norm(self.record.get("class")))
        if not ab:
            raise RefereeError(f"{self.name}'s record has no spellcasting (class or spell_save_dc)")
        return 8 + self.prof + self.ab_mod(ab)

    def traits(self) -> List[str]:
        out = [str(t) for t in (self.record.get("traits") or []) if t]
        out += [str(f) for f in (self.record.get("features") or []) if isinstance(f, str)]
        return [_norm(t) for t in out]

    def conditions(self) -> List[str]:
        out = [_norm(c) for c in (self.record.get("conditions") or [])] + \
              [_norm(c) for c in (self.state.get("conditions") or [])]
        if self.kind == "pc" and life_status(self.record) in ("dying", "stable") \
                and "unconscious" not in out:
            out.append("unconscious")          # (at 0 HP: unconscious, by the rules)
        return [c for c in out if c != "stable"]

    def states(self) -> Dict[str, Any]:
        return self.state.setdefault("states", {})

    # --- the attacks the record lists ---
    def attack(self, name: str) -> Dict[str, Any]:
        want = _norm(name)
        if self.kind == "enemy":
            for a in self.record.get("attacks") or []:
                if _norm(a.get("name")) == want:
                    return {"name": a["name"], "to_hit": int(a["to_hit"]),
                            "damage": str(a["damage"]), "ranged": bool(a.get("ranged"))}
            raise RefereeError(f"{self.name}'s stat block has no attack named {name}")
        for item in (self.record.get("equipment") or []) + (self.record.get("weapons") or []):
            if not isinstance(item, dict) or _norm(item.get("name")) != want or not item.get("damage"):
                continue
            notes = _norm(" ".join(str(item.get(k, "")) for k in ("notes", "properties", "range", "name")))
            ranged = bool(item.get("ranged")) or "range" in notes and "thrown" not in notes \
                or any(w in notes for w in ("bow", "crossbow", "dart", "sling", "throwing"))
            finesse = "finesse" in notes or ranged
            ab = "dex" if ranged or (finesse and self.ab_mod("dex") > self.ab_mod("str")) else "str"
            to_hit = item.get("to_hit", item.get("attack_bonus"))
            to_hit = int(to_hit) if to_hit is not None else self.ab_mod(ab) + self.prof
            dmg = str(item["damage"])
            if not re.search(r"\d+d\d+\s*[+-]\s*\d+", dmg):     # no modifier written: add the ability's
                m = self.ab_mod(ab)
                dmg = re.sub(r"(\d+d\d+)", lambda x: x.group(1) + (f"{m:+d}" if m else ""), dmg, count=1)
            return {"name": item["name"], "to_hit": to_hit, "damage": dmg, "ranged": ranged}
        for sp in (self.record.get("spells") or []) + (self.record.get("cantrips") or []):
            text = sp if isinstance(sp, str) else " ".join(str(v) for v in (sp or {}).values())
            if want in _norm(text) and re.search(r"\d+d\d+", text):
                ab = CASTING.get(_norm(self.record.get("class")), "cha")
                return {"name": name, "to_hit": self.prof + self.ab_mod(ab),
                        "damage": re.search(r"\d+d\d+(\s*[+-]\s*\d+)?", text).group(0), "ranged": True,
                        "spell": True}
        raise RefereeError(f"{self.name}'s sheet lists no weapon or attack spell named {name} "
                           f"(record it on the sheet first: gm-player.sh)")


class Referee:
    def __init__(self, world_state_dir: Optional[str] = None, roller=None):
        self.combat = CombatManager(world_state_dir)
        self.players = PlayerManager(world_state_dir)
        self.roller = roller or table_roll

    # --- the fight's record ---
    def _data(self) -> Dict[str, Any]:
        data = self.combat._load()
        data.setdefault("combatants", [])
        data.setdefault("fields", [])
        return data

    @staticmethod
    def _in_fight(data: Dict[str, Any]) -> bool:
        return bool(data.get("active"))

    def _save(self, data: Dict[str, Any]) -> None:
        """Write the fight. Outside a fight, a PC's entry is only a holder for a
        recorded situation (helped, hidden, cover) and never a combatant: a check
        in the corridor writes no combat_state.json unless something is recorded."""
        outside = [e for e in data.get("outside") or [] if e.get("states")]
        if outside:
            data["outside"] = outside
        else:
            data.pop("outside", None)
        if not (self._in_fight(data) or data.get("combatants") or data.get("fields") or outside):
            camp = getattr(self.combat, "campaign_dir", None)
            if camp is None or not (Path(camp) / self.combat.combat_file).exists():
                return                          # nothing to record, and no file to clear
            data = {}
        self.combat._save(data)

    def _log(self, action: str, **fields) -> None:
        audit(getattr(self.combat, "campaign_dir", None), {"kind": "referee", "action": action, **fields})

    def _entry(self, data: Dict[str, Any], name: str, create_pc: bool = True,
               join: bool = False) -> Dict[str, Any]:
        """The fight's entry for ``name``. A PC not yet in it joins the fight only
        while one is on (or when ``join``: initiative); outside a fight the PC
        gets a holder entry that is never a combatant."""
        for c in data["combatants"]:
            if _norm(c["name"]) == _norm(name):
                return c
        sheet = self._sheet(name)
        if sheet and create_pc:
            outside = data.setdefault("outside", [])
            held = next((e for e in outside if _norm(e["name"]) == _norm(name)), None)
            if self._in_fight(data) or join:
                if held is not None:
                    outside.remove(held)
                entry = held or {"name": sheet.get("name", name), "side": "party", "kind": "pc",
                                 "initiative": 0, "conditions": [], "states": {}}
                data["combatants"].append(entry)
                return entry
            if held is None:
                held = {"name": sheet.get("name", name), "side": "party", "kind": "pc",
                        "conditions": [], "states": {}}
                outside.append(held)
            return held
        raise RefereeError(f"no combatant or player character named {name}")

    def _sheet(self, name: str) -> Optional[Dict[str, Any]]:
        """That PC's sheet, by its exact name (never another PC's)."""
        sheet = self.players.get_player(name)
        return sheet if sheet and _norm(sheet.get("name")) == _norm(name) else None

    def who(self, data: Dict[str, Any], name: str) -> Combatant:
        entry = self._entry(data, name)
        if entry.get("kind") == "enemy":
            return Combatant(entry["name"], entry.get("block") or {}, "enemy", entry)
        return Combatant(entry["name"], self._sheet(entry["name"]) or {}, "pc", entry)

    # --- foes: locked stat blocks ---
    def add_enemy(self, block: Dict[str, Any], side: str = "enemy") -> Dict[str, Any]:
        for key in ("name", "ac", "hp", "abilities", "attacks"):
            if key not in block:
                raise RefereeError(f"a stat block needs {key} (name, ac, hp, abilities, attacks)")
        for a in block["attacks"]:
            if not {"name", "damage"} <= set(a) or ("to_hit" not in a and "save" not in a):
                raise RefereeError("each attack needs name, damage and to_hit (or a save)")
        data = self._data()
        if any(_norm(c["name"]) == _norm(block["name"]) for c in data["combatants"]):
            raise RefereeError(f"{block['name']} is already in the fight (give each foe its own name)")
        data["active"] = True
        data.setdefault("round", 1)
        data.setdefault("turn_index", 0)
        entry = {"name": block["name"], "side": side, "kind": "enemy", "locked": True,
                 "hp_current": int(block["hp"]), "hp_max": int(block["hp"]), "ac": int(block["ac"]),
                 "initiative": 0, "conditions": [], "states": {}, "block": block}
        data["combatants"].append(entry)
        self._save(data)
        self._log("enemy", name=block["name"], block=block)
        return entry

    def initiative(self) -> List[Dict[str, Any]]:
        data = self._data()
        for name in [p.get("name") for p in self.players.get_all_players() if p.get("status") != "dead"]:
            self._entry(data, name, join=True)
        out = []
        for c in data["combatants"]:
            who = self.who(data, c["name"])
            bonus = int(who.record.get("initiative", who.ab_mod("dex"))) if who.kind == "enemy" \
                else who.ab_mod("dex")
            r = self.roller(f"1d20{bonus:+d}" if bonus else "1d20", None, None, c["name"],
                            "⚖ Initiative")
            c["initiative"] = r["total"]
            out.append({"name": c["name"], "initiative": r["total"]})
        data["combatants"].sort(key=lambda c: c["initiative"], reverse=True)
        data.update(active=True, round=1, turn_index=0)
        self._save(data)
        self._log("initiative", order=out)
        return out

    # --- recorded situations ---
    def set_cover(self, name: str, cover: str) -> str:
        cover = _norm(cover).replace(" ", "-")
        if cover not in ("none", *COVER_AC):
            raise RefereeError("cover is none, half or three-quarters")
        data = self._data()
        states = self._entry(data, name).setdefault("states", {})
        states.pop("cover", None) if cover == "none" else states.update(cover=cover)
        self._save(data)
        self._log("cover", who=self._entry(data, name)["name"], cover=cover)
        return cover

    def help(self, helper: str, name: str) -> None:
        data = self._data()
        self._entry(data, helper)
        self._entry(data, name).setdefault("states", {})["helped_by"] = helper
        self._save(data)
        self._log("help", who=helper, helps=name)

    def add_field(self, name: str, effects: List[str], unless: Optional[str] = None) -> Dict[str, Any]:
        """A battlefield effect: it applies to EVERY combatant; only a recorded trait
        (``unless``) exempts one."""
        parsed = []
        for e in effects:
            kind, _, what = _norm(e).partition(":")
            roll, _, ab = what.partition("-")
            if kind not in EFFECT_KINDS or roll not in EFFECT_ROLLS or (ab and ab not in ABILITIES):
                raise RefereeError(f"an effect is adv|dis:attack|check|save[-ability] (e.g. dis:check-dex), not {e}")
            parsed.append({"kind": kind, "roll": roll, "ability": ab or None})
        data = self._data()
        field = {"name": name, "effects": parsed, "unless": _norm(unless) if unless else None}
        data["fields"] = [f for f in data["fields"] if _norm(f["name"]) != _norm(name)] + [field]
        self._save(data)
        self._log("field", name=name, effects=effects, applies_to="everyone",
                  unless_trait=field["unless"])
        return field

    def end_field(self, name: str) -> None:
        data = self._data()
        data["fields"] = [f for f in data["fields"] if _norm(f["name"]) != _norm(name)]
        self._save(data)

    # --- what applies to a roll ---
    def _field_effects(self, data, who: Combatant, roll: str, ab: Optional[str]) -> List[Tuple[str, str]]:
        out = []
        for f in data["fields"]:
            if f.get("unless") and any(f["unless"] in t for t in who.traits()):
                continue
            for e in f["effects"]:
                if e["roll"] == roll and (not e["ability"] or e["ability"] == ab):
                    out.append((e["kind"], f["name"]))
        return out

    @staticmethod
    def _notation(bonus: int, adv: List[str], dis: List[str]) -> Tuple[str, str]:
        tail = f"{bonus:+d}" if bonus else ""
        note = []
        if adv:
            note.append("advantage: " + "; ".join(adv))
        if dis:
            note.append("disadvantage: " + "; ".join(dis))
        if adv and not dis:
            return f"2d20kh1{tail}", " · ".join(note)
        if dis and not adv:
            return f"2d20kl1{tail}", " · ".join(note)
        return f"1d20{tail}", " · ".join(note) + (" (they cancel)" if adv and dis else "")

    # --- the rolls ---
    def _scene(self) -> str:
        """Where and when the party is (location | time of day | date): a scene."""
        camp = getattr(self.combat, "campaign_dir", None)
        try:
            o = json.loads((Path(camp) / "campaign-overview.json").read_text(encoding="utf-8")) if camp else {}
        except (OSError, ValueError):
            o = {}
        pos = o.get("player_position") if isinstance(o.get("player_position"), dict) else {}
        return " | ".join(str(x or "") for x in (pos.get("current_location"), o.get("time_of_day"),
                                                  o.get("current_date")))

    def _earlier_tries(self, who: str, skill: str, dc: Optional[int], scene: str) -> List[Dict[str, Any]]:
        """The same character's checks of the same skill against the same DC in this
        scene (and within REPEAT_HOURS): the smell of rolling until it works."""
        import datetime
        camp = getattr(self.combat, "campaign_dir", None)
        if camp is None:
            return []
        now = datetime.datetime.now(datetime.timezone.utc)
        out = []
        for e in read_log(Path(camp))[-REPEAT_WINDOW:]:
            if (e.get("action") != "check" or e.get("voided") or e.get("scene") != scene
                    or e.get("who") != who or e.get("skill") != skill or e.get("dc") != dc):
                continue
            try:
                age = now - datetime.datetime.fromisoformat(e.get("at", ""))
            except ValueError:
                continue
            if age.total_seconds() <= REPEAT_HOURS * 3600:
                out.append(e)
        return out

    def check(self, name: str, skill: str, dc: Optional[int] = None, why: str = "",
              warn_repeat: bool = True) -> Dict[str, Any]:
        data = self._data()
        who = self.who(data, name)
        bonus, label = who.skill_bonus(skill)
        scene = self._scene()
        if warn_repeat:
            earlier = self._earlier_tries(who.name, label, dc, scene)
            if earlier:
                failed = sum(e.get("outcome") == "failure" for e in earlier)
                print(f"⚠ REPEAT ROLL (a note, not a block): {who.name} has already rolled {label} vs DC {dc} "
                      f"{len(earlier)}× in this scene ({failed} failed). A route once crossed stays crossed; "
                      f"party movement is one group check; a failed move costs time or position, "
                      f"HP only when a fall was the stated stake.")
        ab = SKILLS.get(_norm(skill)) or ability_key(skill)
        adv, dis = [], []
        for c in who.conditions():
            if c in CHECK_DIS:
                dis.append(f"{who.name} is {c}")
        if who.states().pop("helped_by", None):
            adv.append(f"helped")
        for kind, field in self._field_effects(data, who, "check", ab):
            (adv if kind == "adv" else dis).append(field)
        notation, note = self._notation(bonus, adv, dis)
        r = self.roller(notation, dc, "DC", who.name, "⚖ " + " · ".join(x for x in (label, why, note) if x))
        self._save(data)
        self._log("check", who=who.name, side=who.state.get("side", "party"), skill=label,
                  bonus=bonus, bonus_from=f"{who.kind} record", advantage=adv, disadvantage=dis,
                  dc=dc, why=why, notation=notation, scene=scene, **_result(r))
        return r

    def save(self, name: str, ability: str, dc: int, source: str) -> Dict[str, Any]:
        data = self._data()
        who = self.who(data, name)
        ab = ability_key(ability)
        if not ab:
            raise RefereeError(f"not an ability: {ability}")
        conds = who.conditions()
        if ab in ("str", "dex") and any(c in AUTO_FAIL_STR_DEX_SAVES for c in conds):
            bad = next(c for c in conds if c in AUTO_FAIL_STR_DEX_SAVES)
            out = {"ok": True, "total": None, "outcome": "failure", "auto": f"{who.name} is {bad}"}
            self._log("save", who=who.name, side=who.state.get("side", "party"), ability=ab, dc=dc,
                      source=source, outcome="failure", automatic=f"{who.name} is {bad}")
            self.roller(None, dc, "DC", who.name, f"⚖ {ab.upper()} save vs {source}: automatic failure "
                                                   f"({who.name} is {bad})", announce_only=True)
            return out
        bonus = who.save_bonus(ab)
        adv, dis = [], []
        if ab == "dex" and "restrained" in conds:
            dis.append(f"{who.name} is restrained")
        cover = who.states().get("cover")
        if ab == "dex" and cover:
            bonus += COVER_AC[cover]
        for kind, field in self._field_effects(data, who, "save", ab):
            (adv if kind == "adv" else dis).append(field)
        notation, note = self._notation(bonus, adv, dis)
        extra = f" · {cover} cover +{COVER_AC[cover]}" if ab == "dex" and cover else ""
        r = self.roller(notation, dc, "DC", who.name,
                        f"⚖ {ab.upper()} save vs {source}" + (f" · {note}" if note else "") + extra)
        self._log("save", who=who.name, side=who.state.get("side", "party"), ability=ab, bonus=bonus,
                  advantage=adv, disadvantage=dis, cover=cover if ab == "dex" else None, dc=dc,
                  source=source, notation=notation, **_result(r))
        return r

    def _dying_pc(self, name: str) -> Dict[str, Any]:
        sheet = self._sheet(name)
        if not sheet:
            raise RefereeError(f"no player character named {name} (death saves are for PCs)")
        status = life_status(sheet)
        if status != "dying":
            raise RefereeError(f"{sheet.get('name', name)} is {status}, not dying")
        return sheet

    def death_save(self, name: str) -> Dict[str, Any]:
        """A flat d20 against 10: no bonus can touch it. Recorded on the sheet: a
        natural 20 regains 1 HP, a natural 1 is two failures, three successes are
        stable, three failures are death."""
        sheet = self._dying_pc(name)
        who = sheet.get("name", name)
        r = self.roller("1d20", 10, "DC", who, "⚖ Death save")
        nat = r.get("natural") if r.get("natural") is not None else r.get("total")
        res = self.players.record_death_save(who, int(nat or 0), r.get("outcome") == "success")
        if not res.get("success"):
            raise RefereeError(res.get("error") or f"could not record {who}'s death save")
        self._log("death-save", who=who, side="party", dc=10, notation="1d20", **_result(r),
                  result=res["outcome"], tally=res.get("death_saves"), status=res.get("status"))
        return {**r, "death": res}

    def stabilize(self, name: str, by: Optional[str] = None, source: Optional[str] = None) -> Dict[str, Any]:
        """Stop a dying PC's death saves: a Medicine check (DC 10) by ``by``, or no
        roll at all for a ``source`` that just works (Spare the Dying, a healer's
        kit). Logged either way."""
        sheet = self._dying_pc(name)
        who = sheet.get("name", name)
        if source:
            res = self.players.stabilize(who, how=source + (f" ({by})" if by else ""))
            self._log("stabilize", who=who, side="party", by=by, source=source, roll=None,
                      outcome="stable")
            return {"stable": res.get("success", False), "check": None}
        if not by:
            raise RefereeError("stabilize needs --by <who tends them> (Medicine DC 10) or "
                               "--source \"<spell or healer's kit>\" (no roll)")
        r = self.check(by, "medicine", 10, why=f"stabilize {who}", warn_repeat=False)
        stable = r.get("outcome") == "success"
        if stable:
            self.players.stabilize(who, how=f"Medicine {r.get('total')} ({by})")
        self._log("stabilize", who=who, side="party", by=by, source="Medicine DC 10",
                  roll=r.get("total"), outcome="stable" if stable else "still dying")
        return {"stable": stable, "check": r}

    def hide(self, name: str) -> Dict[str, Any]:
        """Stealth against the best passive Perception on the other side."""
        data = self._data()
        who = self.who(data, name)
        side = who.state.get("side", "party")
        foes = [self.who(data, c["name"]) for c in data["combatants"]
                if c.get("side", "party") != side and c.get("hp_current", 1) != 0]
        if not foes:
            raise RefereeError("nobody on the other side to hide from (add the foes first)")
        best = max(foes, key=lambda f: f.passive_perception())
        dc = best.passive_perception()
        r = self.check(name, "stealth", dc, why=f"hide from {best.name} (passive Perception {dc})",
                       warn_repeat=False)
        data = self._data()
        entry = self._entry(data, name)
        self._log("hide", who=entry["name"], against=best.name, passive_perception=dc,
                  hidden=r.get("outcome") == "success")
        if r.get("outcome") == "success":
            entry.setdefault("states", {})["hidden"] = True
        else:
            entry.setdefault("states", {}).pop("hidden", None)
        self._save(data)
        return r

    def attack(self, attacker: str, target: str, weapon: str, long_range: bool = False,
               within_5ft: bool = True) -> Dict[str, Any]:
        data = self._data()
        a, t = self.who(data, attacker), self.who(data, target)
        atk = a.attack(weapon)
        ranged = atk["ranged"]
        adv, dis = [], []
        ac = t.ac()
        if t.kind == "enemy":
            ac = int(t.state.get("ac") or ac)
        for c in a.conditions():
            if c in ATTACKER_ADV:
                adv.append(f"{a.name} is {c}")
            if c in ATTACKER_DIS:
                dis.append(f"{a.name} is {c}")
        if a.states().pop("hidden", None):
            adv.append(f"{a.name} is hidden")
        if a.states().pop("helped_by", None):
            adv.append("helped")
        tconds = t.conditions()
        for c in tconds:
            if c in TARGET_GIVES_ADV:
                adv.append(f"{t.name} is {c}")
            if c in TARGET_GIVES_DIS:
                dis.append(f"{t.name} is {c}")
            if c == "prone":
                (adv if not ranged and within_5ft else dis).append(f"{t.name} is prone")
        if t.states().get("hidden"):
            dis.append(f"{t.name} is hidden")
        if long_range:
            dis.append("long range")
        for kind, field in self._field_effects(data, a, "attack", None):
            (adv if kind == "adv" else dis).append(field)
        cover = t.states().get("cover")
        cover_note = ""
        if cover:
            ac += COVER_AC[cover]
            cover_note = f" · {t.name} has {cover} cover (+{COVER_AC[cover]} AC)"
        notation, note = self._notation(atk["to_hit"], adv, dis)
        why = f"⚖ {atk['name']} vs {t.name}" + (f" · {note}" if note else "") + cover_note
        r = self.roller(notation, ac, "AC", a.name, why)
        out = {"attack": r, "hit": r.get("outcome") == "success", "damage": None}
        crit = r.get("natural") == 20 or (out["hit"] and not ranged and within_5ft
                                          and any(c in MELEE_AUTO_CRIT for c in tconds))
        self._save(data)
        self._log("attack", who=a.name, side=a.state.get("side", "party"), target=t.name,
                  weapon=atk["name"], to_hit=atk["to_hit"], to_hit_from=f"{a.kind} record",
                  advantage=adv, disadvantage=dis, ac=ac, cover=cover, long_range=long_range,
                  notation=notation, crit=crit, **_result(r))
        if out["hit"]:
            out["damage"] = self.damage(t.name, atk["damage"], f"{atk['name']} ({a.name})", crit=crit)
        return out

    def damage(self, target: str, notation: str, source: str, crit: bool = False,
               heal: bool = False) -> Dict[str, Any]:
        """Damage (or healing) from a stated source, rolled in public and applied to
        the record: the foe's locked HP, or the PC's sheet."""
        m = re.match(r"\s*(\d+)d(\d+)\s*([+-]\s*\d+)?\s*(.*)", notation)
        if m:
            count = int(m.group(1)) * (2 if crit else 1)
            dice_n = f"{count}d{m.group(2)}" + (m.group(3) or "").replace(" ", "")
            kind = m.group(4).strip()
            r = self.roller(dice_n, None, None, None,
                            f"⚖ {'healing' if heal else 'damage'}: {source}"
                            + (f" ({kind})" if kind else "") + (" · critical: dice doubled" if crit else ""))
            amount = max(0, r["total"])
        elif notation.strip().isdigit():
            amount = int(notation)
            self.roller(None, None, None, None, f"⚖ {amount} {'healing' if heal else 'damage'}: {source}",
                        announce_only=True)
        else:
            raise RefereeError(f"not a damage roll: {notation}")
        data = self._data()
        entry = self._entry(data, target)
        if entry.get("kind") == "enemy":
            before = {"hp": entry["hp_current"]}
            entry["hp_current"] = min(entry["hp_max"], entry["hp_current"] + amount) if heal \
                else max(0, entry["hp_current"] - amount)
            left = {"hp": entry["hp_current"], "hp_max": entry["hp_max"]}
            self._save(data)
        else:
            sheet = self._sheet(entry["name"]) or {}
            before = {"hp": (sheet.get("hp") or {}).get("current"), "status": life_status(sheet),
                      "death_saves": sheet.get("death_saves")}
            res = self.players.modify_hp(entry["name"], amount if heal else -amount, crit=crit and not heal)
            left = {"hp": res.get("current_hp"), "hp_max": res.get("max_hp"), "status": res.get("status")}
            if res.get("death_saves"):
                left["death_saves"] = res["death_saves"]
        self._log("heal" if heal else "damage", target=entry["name"], side=entry.get("side", "party"),
                  amount=amount, notation=notation, crit=crit, source=source, before=before, **left)
        return {"amount": amount, "target": entry["name"], **left}

    # --- a mistaken ruling, struck from the record ---
    def void(self, line: int, reason: str) -> Dict[str, Any]:
        """Void the referee-log entry on ``line`` (as `log` numbers them): it stays
        in the log, marked voided, and leaves the report. Its hit-point effect is
        reversed (an attack: the damage it dealt) to the state before it, instead
        of a made-up heal. Nothing else in the fight is touched."""
        camp = getattr(self.combat, "campaign_dir", None)
        entries = read_log(Path(camp)) if camp else []
        by_line = {e["_line"]: e for e in entries}
        e = by_line.get(int(line))
        if e is None or e.get("kind") != "referee":
            raise RefereeError(f"no referee decision on line {line} (gm-referee.sh log shows the numbers)")
        if e.get("action") == "void":
            raise RefereeError("that line is itself a void")
        if e.get("voided"):
            raise RefereeError(f"line {line} is already voided ({e['voided']})")
        hits = [e] if e.get("action") in ("damage", "heal") else []
        if e.get("action") == "attack":
            src = f"{e.get('weapon')} ({e.get('who')})"
            hits = [x for x in entries if e["_line"] < x["_line"] <= e["_line"] + 4
                    and x.get("action") == "damage" and x.get("target") == e.get("target")
                    and x.get("source") == src and not x.get("voided")][:1]
        restored = []
        for h in hits:
            restored.append(self._undo_hp(h))
        lines = [e["_line"]] + [h["_line"] for h in hits if h is not e]
        self._log("void", voids=lines, reason=reason, restored=restored)
        return {"voided": lines, "restored": restored}

    def _undo_hp(self, h: Dict[str, Any]) -> Dict[str, Any]:
        """Put one damage/heal entry's target back as it was before it."""
        amount = int(h.get("amount") or 0)
        sign = 1 if h.get("action") == "damage" else -1
        before = h.get("before") or {}
        data = self._data()
        foe = next((c for c in data["combatants"] if _norm(c["name"]) == _norm(h.get("target"))
                    and c.get("kind") == "enemy"), None)
        if foe is not None:
            unchanged = foe["hp_current"] == h.get("hp") and before.get("hp") is not None
            foe["hp_current"] = int(before["hp"]) if unchanged else \
                max(0, min(foe["hp_max"], foe["hp_current"] + sign * amount))
            self._save(data)
            return {"target": foe["name"], "hp": foe["hp_current"]}
        sheet = self._sheet(h.get("target"))
        if sheet:
            hp = sheet.get("hp") or {}
            unchanged = hp.get("current") == h.get("hp") and before.get("hp") is not None
            if unchanged:
                new_hp, status, tally = int(before["hp"]), before.get("status"), before.get("death_saves")
            else:
                new_hp = max(0, min(int(hp.get("max") or 0), int(hp.get("current") or 0) + sign * amount))
                status, tally = None, None
            res = self.players.restore_vitals(sheet["name"], new_hp, status, tally)
            return {"target": sheet["name"], "hp": res.get("current_hp"), "status": res.get("status")}
        return {"target": h.get("target"), "hp": None, "note": "no longer in the fight: nothing to restore"}

    def status(self) -> Dict[str, Any]:
        """The whole fight, as the combat referee sees it: no story, no plans."""
        data = self._data()
        out = {"round": data.get("round", 1), "turn": None, "fields": data["fields"], "combatants": []}
        for i, c in enumerate(data["combatants"]):
            who = self.who(data, c["name"])
            entry = {"name": c["name"], "side": c.get("side", "party"), "kind": who.kind,
                     "initiative": c.get("initiative"), "ac": who.ac(),
                     "conditions": who.conditions(), "states": dict(c.get("states") or {})}
            if who.kind == "enemy":
                entry.update(hp=c["hp_current"], hp_max=c["hp_max"],
                             attacks=c["block"].get("attacks"), temperament=c["block"].get("temperament"),
                             traits=c["block"].get("traits"))
            else:
                hp = who.record.get("hp") or {}
                entry.update(hp=hp.get("current"), hp_max=hp.get("max"))
            out["combatants"].append(entry)
            if i == data.get("turn_index", 0):
                out["turn"] = c["name"]
        return out


def _result(r: Dict[str, Any]) -> Dict[str, Any]:
    return {"total": r.get("total"), "natural": r.get("natural"), "d20": r.get("d20"),
            "outcome": r.get("outcome")}


def read_log(campaign_dir: Path) -> List[Dict[str, Any]]:
    """The log's entries, each with its ``_line`` number; an entry a later `void`
    struck carries ``voided`` (the reason)."""
    out = []
    try:
        for n, line in enumerate((Path(campaign_dir) / LOG_NAME).read_text(encoding="utf-8").splitlines(), 1):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if isinstance(e, dict):
                e["_line"] = n
                out.append(e)
    except OSError:
        pass
    voided = {}
    for e in out:
        if e.get("action") == "void":
            for n in e.get("voids") or []:
                voided[n] = e.get("reason") or "voided"
    for e in out:
        if e["_line"] in voided:
            e["voided"] = voided[e["_line"]]
    return out


def describe_entry(e: Dict[str, Any]) -> str:
    """One log line, for people."""
    text = _describe(e)
    return f"✗ VOIDED ({e['voided']}): {text}" if e.get("voided") else text


def _describe(e: Dict[str, Any]) -> str:
    at = e.get("at", "")[11:16]
    a = e.get("action")
    def edges():
        bits = []
        if e.get("advantage"):
            bits.append("adv: " + "; ".join(e["advantage"]))
        if e.get("disadvantage"):
            bits.append("dis: " + "; ".join(e["disadvantage"]))
        return (" [" + " | ".join(bits) + "]") if bits else ""
    res = f" → {e.get('total')} {e.get('outcome') or ''}".rstrip() if e.get("total") is not None else ""
    if e.get("kind") == "free":
        return (f"{at} ⚠ FREE ROLL (not the referee) {e.get('who') or 'GM'}: {e.get('notation')}"
                f" {e.get('why') or ''}" + (f" vs {e.get('label')} {e['target']}" if e.get("target") is not None else "")
                + res + (" (secret)" if e.get("secret") else ""))
    if a == "check":
        return f"{at} {e['who']} ({e['side']}) {e['skill']} {e['bonus']:+d} vs DC {e['dc']}{edges()}{res}"
    if a == "save":
        if e.get("automatic"):
            return f"{at} {e['who']} ({e['side']}) {e['ability'].upper()} save vs {e['source']}: automatic failure ({e['automatic']})"
        return f"{at} {e['who']} ({e['side']}) {e['ability'].upper()} save {e['bonus']:+d} vs DC {e['dc']} ({e['source']}){edges()}{res}"
    if a == "attack":
        return (f"{at} {e['who']} ({e['side']}) attacks {e['target']} with {e['weapon']} {e['to_hit']:+d} "
                f"vs AC {e['ac']}{edges()}{res}" + (" CRIT" if e.get("crit") else ""))
    if a in ("damage", "heal"):
        return f"{at}   {a} {e['amount']} to {e['target']} ({e['source']}) → {e.get('hp')}/{e.get('hp_max')} HP"
    if a == "field":
        return f"{at} battlefield: {e['name']} {', '.join(e['effects'])} for EVERYONE" + \
            (f" except trait '{e['unless_trait']}'" if e.get("unless_trait") else "")
    if a == "enemy":
        b = e.get("block") or {}
        return f"{at} foe locked in: {e['name']} AC {b.get('ac')} HP {b.get('hp')}"
    if a == "hide":
        return f"{at} {e['who']} hides from {e['against']} (passive {e['passive_perception']}): {'hidden' if e['hidden'] else 'seen'}"
    if a == "death-save":
        t = e.get("tally") or {}
        result = e.get("result")
        return (f"{at} {e['who']} death save{res}" + ("" if result in ("success", "failure") else f" → {result}")
                + (f" ({t.get('successes', 0)}✓ {t.get('failures', 0)}✗)" if t else ""))
    if a == "stabilize":
        how = e.get("source") + (f" by {e['by']}" if e.get("by") else "") if e.get("source") else e.get("by")
        return f"{at} {e['who']} stabilize: {how}" + (f" → {e['roll']}" if e.get("roll") is not None else "") \
            + f" → {e.get('outcome')}"
    if a == "void":
        return f"{at} VOID lines {', '.join(map(str, e.get('voids') or []))}: {e.get('reason')}"
    return f"{at} {a}: " + json.dumps({k: v for k, v in e.items() if k not in ('at', 'kind', 'action', '_line')},
                                      ensure_ascii=False)


def report(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Per side: how the dice and the edges fell, and how many rolls skipped the referee."""
    sides: Dict[str, Dict[str, Any]] = {}
    for e in entries:
        if e.get("voided"):
            continue
        if e.get("kind") == "free":
            s = sides.setdefault("free rolls (GM, outside the referee)", {"rolls": 0})
            s["rolls"] += 1
            continue
        if e.get("action") not in ("check", "save", "attack"):
            continue
        s = sides.setdefault(e.get("side", "party"), {"rolls": 0, "naturals": [], "advantage": 0,
                                                       "disadvantage": 0, "successes": 0, "crits": 0})
        s["rolls"] += 1
        if e.get("d20"):
            s["naturals"].append(e["d20"])
        s["advantage"] += bool(e.get("advantage"))
        s["disadvantage"] += bool(e.get("disadvantage"))
        s["successes"] += e.get("outcome") == "success"
        s["crits"] += bool(e.get("crit"))
    for s in sides.values():
        nat = s.pop("naturals", None)
        if nat is not None:
            s["average_d20"] = round(sum(nat) / len(nat), 1) if nat else None
    return sides


# ------------------------------------------------------------------ rolling ----
def table_roll(notation: Optional[str], target: Optional[int], label: Optional[str],
               who: Optional[str], why: str, announce_only: bool = False) -> Dict[str, Any]:
    """Roll at the open table (every player sees it), else here. Returns
    {total, natural, outcome}."""
    try:
        from table_server import roll_at_table
    except ImportError:
        roll_at_table = None
    if announce_only:                       # no dice: said here, and kept in the log
        print(why)
        return {"total": None, "natural": None, "outcome": None}
    shown = roll_at_table({"notation": notation, "target": target, "target_label": label or "DC",
                           "pc": who, "why": why}) if roll_at_table else None
    if shown and shown.get("ok"):
        roll = shown.get("roll") or {}
        kept = roll.get("rolls") or []
        out = {"total": roll.get("total"), "natural": roll.get("natural"), "outcome": roll.get("outcome"),
               "d20": kept[0] if "d20" in str(notation) and len(kept) == 1 else None}
    else:
        r = dice.DiceRoller().roll(notation)
        kept = r.get("kept") or r.get("rolls") or []
        out = {"total": r["total"], "natural": dice.natural(r), "outcome": dice.judge(r, target, label or "DC"),
               "d20": kept[0] if "d20" in notation and len(kept) == 1 else None}
    print(f"{why}: {notation} = {out['total']}"
          + (f" vs {label or 'DC'} {target} — {'✓' if out['outcome'] == 'success' else '✗'} {out['outcome']}"
             if target is not None else ""))
    return out


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="The referee: rolls from the records, never from the GM")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check", help="An ability check: check <who> <skill|ability> --dc <ladder>")
    p.add_argument("who"); p.add_argument("skill")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--dc", help=", ".join(f"{k}={v}" for k, v in DC_LADDER.items()))
    g.add_argument("--vs-passive", nargs=2, metavar=("WHO", "SKILL"),
                   help="against someone's passive score (10 + their bonus)")
    p.add_argument("--why", default="")
    p = sub.add_parser("save", help="A saving throw against a recorded source")
    p.add_argument("who"); p.add_argument("ability")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--vs-spell-of", metavar="CASTER", help="the caster's spell save DC, from their record")
    g.add_argument("--dc", help="a ladder word (environmental hazards)")
    g.add_argument("--vs-ability", nargs=2, metavar=("FOE", "ABILITY"), help="a save DC the foe's stat block lists")
    p.add_argument("--source", default="")
    p = sub.add_parser("attack", help="attack <attacker> <target> <weapon|attack|spell on the record>")
    p.add_argument("attacker"); p.add_argument("target"); p.add_argument("weapon")
    p.add_argument("--long-range", action="store_true")
    p.add_argument("--not-adjacent", action="store_true", help="a melee-only bonus doesn't apply (target prone, 5+ ft away)")
    p = sub.add_parser("damage", help="Damage from a stated source: damage <target> <dice> --source '...'")
    p.add_argument("target"); p.add_argument("notation"); p.add_argument("--source", required=True)
    p = sub.add_parser("heal", help="heal <target> <dice|N> --source '...'")
    p.add_argument("target"); p.add_argument("notation"); p.add_argument("--source", required=True)
    p = sub.add_parser("death-save", help="A flat d20 vs 10, recorded on the sheet (nat 20: 1 HP; "
                                          "nat 1: two failures; 3 successes stable, 3 failures dead)")
    p.add_argument("who")
    p = sub.add_parser("stabilize", help="stabilize <dying PC> --by <who tends them> (Medicine DC 10) "
                                         "| --source \"Spare the Dying\" (no roll)")
    p.add_argument("who"); p.add_argument("--by"); p.add_argument("--source")
    p = sub.add_parser("void", help="void <line> --reason '...': strike a mistaken ruling and undo its HP")
    p.add_argument("line", type=int); p.add_argument("--reason", required=True)
    p = sub.add_parser("hide", help="Stealth vs the other side's best passive Perception; success records hidden")
    p.add_argument("who")
    p = sub.add_parser("help", help="help <helper> <who>: advantage on their next roll")
    p.add_argument("helper"); p.add_argument("who")
    p = sub.add_parser("cover", help="cover <who> none|half|three-quarters (applies until changed)")
    p.add_argument("who"); p.add_argument("cover")
    p = sub.add_parser("field", help="A battlefield effect for EVERYONE: field '<name>' --effect dis:attack ...")
    p.add_argument("name"); p.add_argument("--effect", action="append", required=True)
    p.add_argument("--unless-trait", help="only a stat block / sheet trait containing this exempts")
    p = sub.add_parser("end-field"); p.add_argument("name")
    p = sub.add_parser("enemy", help="Add a foe with a locked stat block (JSON file or text)")
    p.add_argument("block"); p.add_argument("--side", default="enemy")
    sub.add_parser("initiative", help="Roll initiative for everyone in the fight and every PC")
    sub.add_parser("status", help="The fight as JSON (what the combat referee agent reads)")
    p = sub.add_parser("log", help="Every referee decision and free roll, for people to check")
    p.add_argument("--last", type=int, default=40)
    sub.add_parser("report", help="Per side: dice, advantages, disadvantages, successes; free rolls")
    args = ap.parse_args()

    ref = Referee()
    try:
        if args.cmd == "check":
            data = ref._data()
            if args.vs_passive:
                other = ref.who(data, args.vs_passive[0])
                bonus, label = other.skill_bonus(args.vs_passive[1])
                dc, why = 10 + bonus, f"vs {other.name}'s passive {label} {10 + bonus}"
            else:
                dc, why = parse_dc(args.dc), f"{_norm(args.dc)} DC"
            ref.check(args.who, args.skill, dc, why=" · ".join(x for x in (args.why, why) if x))
        elif args.cmd == "save":
            data = ref._data()
            if args.vs_spell_of:
                dc, src = ref.who(data, args.vs_spell_of).spell_dc(), args.source or f"{args.vs_spell_of}'s spell"
            elif args.vs_ability:
                foe = ref.who(data, args.vs_ability[0])
                found = next((a for a in foe.record.get("attacks") or []
                              if _norm(a.get("name")) == _norm(args.vs_ability[1]) and a.get("save")), None)
                if not found:
                    raise RefereeError(f"{foe.name}'s stat block lists no save for {args.vs_ability[1]}")
                dc, src = int(found["save"]["dc"]), f"{foe.name}'s {found['name']}"
            else:
                dc, src = parse_dc(args.dc), args.source or "a hazard"
            ref.save(args.who, args.ability, dc, src)
        elif args.cmd == "attack":
            out = ref.attack(args.attacker, args.target, args.weapon, args.long_range, not args.not_adjacent)
            if out["damage"]:
                d = out["damage"]
                print(f"→ {d['target']}: {d['amount']} damage, {d['hp']}/{d['hp_max']} HP left")
        elif args.cmd in ("damage", "heal"):
            d = ref.damage(args.target, args.notation, args.source, heal=args.cmd == "heal")
            print(f"→ {d['target']}: {d['hp']}/{d['hp_max']} HP")
        elif args.cmd == "death-save":
            r = ref.death_save(args.who)
            d, nat = r["death"], r.get("natural")
            t = d.get("death_saves") or {}
            print("→ " + {"revived": "natural 20: 1 HP, conscious",
                          "stable": "third success: STABLE (no more death saves)",
                          "dead": "third failure: DEAD (gm-player.sh / the Death Protocol)"}.get(
                d["outcome"], ("natural 1: two failures" if nat == 1 else d["outcome"])
                + f" — {t.get('successes', 0)}✓ {t.get('failures', 0)}✗"))
        elif args.cmd == "stabilize":
            out = ref.stabilize(args.who, by=args.by, source=args.source)
            print(f"→ {args.who} is " + ("STABLE" if out["stable"] else "still dying"))
        elif args.cmd == "void":
            out = ref.void(args.line, args.reason)
            print(f"→ voided line(s) {', '.join(map(str, out['voided']))}"
                  + "".join(f"; {x['target']} back to {x['hp']} HP" for x in out["restored"] if x.get("hp") is not None))
        elif args.cmd == "hide":
            r = ref.hide(args.who)
            print(f"→ {args.who} is {'HIDDEN' if r.get('outcome') == 'success' else 'not hidden'}")
        elif args.cmd == "help":
            ref.help(args.helper, args.who); print(f"→ {args.who} has advantage on their next roll")
        elif args.cmd == "cover":
            print(f"→ {args.who}: cover {ref.set_cover(args.who, args.cover)}")
        elif args.cmd == "field":
            f = ref.add_field(args.name, args.effect, args.unless_trait)
            print(f"→ battlefield: {f['name']} for everyone" + (f" (except a '{f['unless']}' trait)" if f["unless"] else ""))
        elif args.cmd == "end-field":
            ref.end_field(args.name); print(f"→ {args.name} is over")
        elif args.cmd == "enemy":
            text = Path(args.block).read_text(encoding="utf-8") if Path(args.block).is_file() else args.block
            e = ref.add_enemy(json.loads(text), args.side)
            print(f"→ {e['name']} joins the fight: {e['hp_max']} HP, AC {e['ac']} (locked)")
        elif args.cmd == "initiative":
            for x in ref.initiative():
                print(f"  {x['name']}: {x['initiative']}")
        elif args.cmd == "status":
            print(json.dumps(ref.status(), ensure_ascii=False, indent=1))
        elif args.cmd == "log":
            for e in read_log(ref.combat.campaign_dir)[-args.last:]:
                print(f"#{e['_line']} " + describe_entry(e))
        elif args.cmd == "report":
            for side, s in report(read_log(ref.combat.campaign_dir)).items():
                print(f"{side}: " + ", ".join(f"{k} {v}" for k, v in s.items()))
    except RefereeError as e:
        sys.exit(f"[REFEREE] {e}")


if __name__ == "__main__":
    main()
