"""The referee (lib/referee.py): every number from a record, every situation from
recorded state, both sides treated alike, and every decision logged."""

import json

import pytest

from lib import referee as ref_mod
from lib.referee import Referee, RefereeError, parse_dc, read_log, report


GOBLIN = {"name": "Grak", "ac": 13, "hp": 7, "abilities": {"str": 8, "dex": 14, "con": 10, "int": 10,
                                                         "wis": 8, "cha": 8},
          "skills": {"stealth": 6}, "passive_perception": 9, "temperament": "cowardly",
          "attacks": [{"name": "Scimitar", "to_hit": 4, "damage": "1d6+2 slashing"},
                      {"name": "Spit", "damage": "1d4 acid", "save": {"ability": "dex", "dc": 12}}]}


class Dice:
    """Scripted dice: each roll takes the next total (the natural is total - bonus)."""

    def __init__(self, *totals):
        self.totals, self.calls = list(totals), []

    def __call__(self, notation, target, label, who, why, announce_only=False):
        self.calls.append({"notation": notation, "target": target, "who": who, "why": why})
        if announce_only:
            return {"total": None, "natural": None, "outcome": None}
        total = self.totals.pop(0)
        nat = total - int(notation.split("+")[1]) if notation and "d20" in notation and "+" in notation \
            else total if notation and "d20" in notation else None
        outcome = None if target is None else ("success" if total >= target else "failure")
        if nat == 20:
            outcome = "success" if target is not None else None
        return {"total": total, "natural": nat, "outcome": outcome, "d20": nat}


@pytest.fixture
def world(tmp_path, monkeypatch):
    base = tmp_path / "world-state"
    camp = base / "campaigns" / "camp"
    camp.mkdir(parents=True)
    (base / "active-campaign.txt").write_text("camp")
    (camp / "campaign-overview.json").write_text(json.dumps({"campaign_name": "Camp"}))
    (camp / "character.json").write_text(json.dumps({
        "name": "Pip", "race": "Halfling", "class": "Rogue", "level": 1, "ac": 14,
        "hp": {"current": 10, "max": 10}, "stats": {"str": 8, "dex": 16, "con": 12, "int": 10,
                                                     "wis": 13, "cha": 14},
        "skills": {"Stealth": 7, "Perception": 3}, "conditions": [],
        "equipment": [{"name": "Shortsword", "damage": "1d6 piercing", "notes": "finesse, light"}]}))
    monkeypatch.setenv("GM_WORLD_STATE_BASE", str(base))
    return {"base": str(base), "camp": camp}


def test_numbers_come_from_the_records_not_the_gm(world):
    dice = Dice(15, 9, 12)
    ref = Referee(world["base"], roller=dice)
    ref.add_enemy(GOBLIN)
    # Pip's Shortsword: finesse, so DEX (+3) + proficiency (+2); damage gets the +3 too.
    out = ref.attack("Pip", "Grak", "shortsword")
    assert dice.calls[0]["notation"] == "1d20+5" and dice.calls[0]["target"] == 13
    assert out["hit"] and dice.calls[1]["notation"] == "1d6+3"
    assert ref.status()["combatants"][0]["hp"] == 0           # 7 - 9: the foe's locked HP
    # A check uses the sheet's own Stealth (+7), and difficulty is a ladder word only.
    ref.check("Pip", "stealth", parse_dc("hard"))
    assert dice.calls[2]["notation"] == "1d20+7" and dice.calls[2]["target"] == 20
    with pytest.raises(RefereeError):
        parse_dc("17")
    with pytest.raises(RefereeError, match="sheet lists no weapon"):
        ref.attack("Pip", "Grak", "Vorpal Sword")


def test_conditions_apply_to_both_sides_from_the_record(world):
    dice = Dice(10, 10, 10)
    ref = Referee(world["base"], roller=dice)
    ref.add_enemy(GOBLIN)
    ref.combat.set_condition("Grak", "add", "prone")
    ref.attack("Pip", "Grak", "shortsword")                    # melee vs prone: advantage
    assert dice.calls[0]["notation"].startswith("2d20kh1") and "Grak is prone" in dice.calls[0]["why"]
    ref.attack("Grak", "Pip", "Scimitar")                      # and the prone foe attacks at disadvantage
    assert dice.calls[1]["notation"] == "2d20kl1+4" and "Grak is prone" in dice.calls[1]["why"]
    # Pip's own sheet says poisoned: his checks are at disadvantage, by the same rule.
    sheet = json.loads((world["camp"] / "character.json").read_text())
    (world["camp"] / "character.json").write_text(json.dumps({**sheet, "conditions": ["poisoned"]}))
    ref.check("Pip", "perception", parse_dc("easy"))
    assert dice.calls[2]["notation"] == "2d20kl1+3" and "Pip is poisoned" in dice.calls[2]["why"]


def test_a_battlefield_effect_hits_everyone_unless_a_recorded_trait(world):
    dice = Dice(10, 10, 10)
    ref = Referee(world["base"], roller=dice)
    ref.add_enemy(GOBLIN)
    ref.add_enemy({**GOBLIN, "name": "Mole", "traits": ["Tremorsense"]})
    ref.add_field("Shaking floor", ["dis:attack"], unless="tremorsense")
    ref.attack("Pip", "Grak", "shortsword")
    ref.attack("Grak", "Pip", "Scimitar")
    ref.attack("Mole", "Pip", "Scimitar")
    assert "Shaking floor" in dice.calls[0]["why"] and dice.calls[0]["notation"].startswith("2d20kl1")
    assert "Shaking floor" in dice.calls[1]["why"]                     # the foe too
    assert "Shaking floor" not in dice.calls[2]["why"]                 # only its recorded trait spares it
    with pytest.raises(RefereeError):
        ref.add_field("Bad", ["+2:attack"])                             # no free numbers


def test_hidden_is_earned_and_spent(world):
    dice = Dice(14, 10)
    ref = Referee(world["base"], roller=dice)
    ref.add_enemy(GOBLIN)
    ref.hide("Pip")                                            # Stealth +7 vs Grak's passive 9
    assert dice.calls[0]["target"] == 9 and ref.status()["combatants"][1]["states"].get("hidden")
    ref.attack("Pip", "Grak", "shortsword")
    assert "Pip is hidden" in dice.calls[1]["why"] and dice.calls[1]["notation"].startswith("2d20kh1")
    assert not ref.status()["combatants"][1]["states"].get("hidden")   # attacking gave him away


def test_saves_use_recorded_dcs_and_cover(world):
    dice = Dice(11)
    ref = Referee(world["base"], roller=dice)
    ref.add_enemy(GOBLIN)
    ref.set_cover("Pip", "half")
    ref.save("Pip", "dex", 12, "Grak's Spit")
    assert dice.calls[0]["notation"] == "1d20+5" and "half cover" in dice.calls[0]["why"]  # +3 dex, +2 cover


def test_every_decision_is_logged_and_reported(world):
    dice = Dice(25, 4, 12)
    ref = Referee(world["base"], roller=dice)
    ref.add_enemy(GOBLIN)
    ref.attack("Pip", "Grak", "shortsword")                    # natural 20: dice doubled
    assert dice.calls[1]["notation"] == "2d6+3"
    ref.check("Pip", "perception", parse_dc("medium"))
    entries = read_log(world["camp"])
    actions = [e["action"] for e in entries]
    assert actions[:3] == ["enemy", "attack", "damage"] and "check" in actions
    attack = entries[1]
    assert attack["to_hit"] == 5 and attack["ac"] == 13 and attack["crit"] is True
    r = report(entries)
    assert r["party"]["rolls"] == 2 and r["party"]["crits"] == 1 and r["party"]["average_d20"] == 14.5
    assert ref_mod.describe_entry(attack).count("Pip") == 1


def test_a_free_roll_is_logged_as_one(world, monkeypatch):
    import sys
    from lib import dice as dice_mod
    monkeypatch.setattr(sys, "argv", ["dice.py", "1d20+9", "--dc", "10", "--for", "Grak", "--local"])
    dice_mod.main()
    free = [e for e in read_log(world["camp"]) if e["kind"] == "free"]
    assert free and free[0]["notation"] == "1d20+9" and free[0]["who"] == "Grak"
    assert "free rolls (GM, outside the referee)" in report(read_log(world["camp"]))
