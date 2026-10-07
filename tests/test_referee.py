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


def test_a_natural_one_or_twenty_is_automatic_only_on_an_attack():
    import dice
    one = {"notation": "1d20+15", "total": 16, "rolls": [1]}   # a natural 1 with +15
    twenty = {"notation": "1d20+2", "total": 22, "rolls": [20]}
    assert dice.judge(one, 15, "AC") == "failure"         # an attack: a 1 misses
    assert dice.judge(one, 15, "DC") == "success"         # a check: its total (with a complication)
    assert dice.judge(one, 15) == "success"
    assert dice.judge(twenty, 25, "AC") == "success"      # an attack: a 20 hits
    assert dice.judge(twenty, 25, "DC") == "failure"      # a check: still short


def _sheet(world):
    return json.loads((world["camp"] / "character.json").read_text())


def test_death_saves_are_tallied_on_the_sheet(world):
    ref = Referee(world["base"], roller=Dice(12, 1, 15, 3, 14))
    ref.damage("Pip", "10", "a falling portcullis")
    pip = _sheet(world)
    assert pip["status"] == "dying" and pip["death_saves"] == {"successes": 0, "failures": 0}
    assert ref.death_save("Pip")["death"]["death_saves"] == {"successes": 1, "failures": 0}
    assert ref.death_save("Pip")["death"]["death_saves"] == {"successes": 1, "failures": 2}   # a natural 1
    assert ref.death_save("Pip")["death"]["death_saves"] == {"successes": 2, "failures": 2}
    # Damage at 0 HP is a failure: the third one kills.
    ref.damage("Pip", "1", "a stray arrow")
    assert _sheet(world)["status"] == "dead" and "death_saves" not in _sheet(world)
    with pytest.raises(RefereeError, match="is dead, not dying"):
        ref.death_save("Pip")
    saves = [e for e in read_log(world["camp"]) if e["action"] == "death-save"]
    assert [e["result"] for e in saves] == ["success", "failure", "success"]


def test_three_successes_are_stable_and_a_twenty_wakes(world):
    ref = Referee(world["base"], roller=Dice(10, 11, 19, 20))
    ref.damage("Pip", "10", "a trap")
    for _ in range(3):
        out = ref.death_save("Pip")
    assert out["death"]["outcome"] == "stable"
    pip = _sheet(world)
    assert pip["status"] == "stable" and "death_saves" not in pip and "stable" not in pip["conditions"]
    with pytest.raises(RefereeError, match="stable, not dying"):
        ref.death_save("Pip")
    # A crit while down: two failures, and stable is over.
    from lib.player_manager import PlayerManager
    PlayerManager(world["base"]).modify_hp("Pip", -2, crit=True)
    assert _sheet(world)["status"] == "dying" and _sheet(world)["death_saves"]["failures"] == 2
    assert ref.death_save("Pip")["death"]["outcome"] == "revived"          # natural 20
    pip = _sheet(world)
    assert pip["hp"]["current"] == 1 and pip["status"] == "alive" and "death_saves" not in pip


def test_healing_clears_the_tally_and_stable_is_never_a_condition_beside_dying(world):
    from lib.player_manager import PlayerManager, life_tag
    pm = PlayerManager(world["base"])
    pm.modify_hp("Pip", -10)
    pm.modify_hp("Pip", -1)
    assert _sheet(world)["death_saves"]["failures"] == 1
    pm.modify_condition("Pip", "add", "stable")                 # the old way: becomes the status
    pip = _sheet(world)
    assert pip["status"] == "stable" and "stable" not in pip["conditions"]
    pm.modify_hp("Pip", 3)
    pip = _sheet(world)
    assert pip["status"] == "alive" and "death_saves" not in pip
    # A legacy sheet written as dying + condition stable reads as stable.
    assert life_tag({"status": "dying", "conditions": ["unconscious", "stable"],
                     "hp": {"current": 0, "max": 9}}) == " | STABLE"


def test_stabilize_rolls_medicine_or_uses_a_source(world):
    (world["camp"] / "players").mkdir()
    (world["camp"] / "players" / "ammet.json").write_text(json.dumps({
        "name": "Ammet", "class": "Cleric", "level": 1, "hp": {"current": 8, "max": 8},
        "stats": {"wis": 14}, "skills": {"Medicine": 4}, "conditions": []}))
    ref = Referee(world["base"], roller=Dice(8, 13))
    ref.damage("Pip", "10", "a trap")
    with pytest.raises(RefereeError, match="--by"):
        ref.stabilize("Pip")
    assert ref.stabilize("Pip", by="Ammet")["stable"] is False             # Medicine 8 vs DC 10
    assert _sheet(world)["status"] == "dying"
    assert ref.stabilize("Pip", by="Ammet")["stable"] is True
    assert _sheet(world)["status"] == "stable"
    log = read_log(world["camp"])
    assert [e["outcome"] for e in log if e["action"] == "stabilize"] == ["still dying", "stable"]
    assert [e["dc"] for e in log if e["action"] == "check"] == [10, 10]
    ref.damage("Pip", "1", "a kick")                                        # dying again
    assert ref.stabilize("Pip", source="Spare the Dying", by="Ammet")["stable"] is True
    assert len([e for e in read_log(world["camp"]) if e["action"] == "check"]) == 2   # no roll


def test_a_check_outside_a_fight_creates_no_combatants(world):
    ref = Referee(world["base"], roller=Dice(12, 12, 12))
    ref.check("Pip", "athletics", parse_dc("easy"))
    assert not (world["camp"] / "combat_state.json").exists()
    ref.help("Pip", "Pip")                                       # a recorded situation is kept...
    state = json.loads((world["camp"] / "combat_state.json").read_text())
    assert state["combatants"] == [] and state["outside"][0]["states"]["helped_by"] == "Pip"
    ref.check("Pip", "athletics", parse_dc("easy"))              # ...until spent
    assert json.loads((world["camp"] / "combat_state.json").read_text()) == {}
    # In a fight, the PC joins it.
    ref.add_enemy(GOBLIN)
    ref.check("Pip", "athletics", parse_dc("easy"))
    assert [c["name"] for c in ref.status()["combatants"]] == ["Grak", "Pip"]


def test_void_strikes_a_ruling_and_undoes_its_damage(world):
    dice = Dice(15, 5, 14, 4)
    ref = Referee(world["base"], roller=dice)
    ref.add_enemy(GOBLIN)
    ref.attack("Grak", "Pip", "Scimitar")                      # hits for 5: Pip 10 -> 5
    assert _sheet(world)["hp"]["current"] == 5
    attack = next(e for e in read_log(world["camp"]) if e["action"] == "attack")
    out = ref.void(attack["_line"], "Pip was 15 ft up the chain, out of reach")
    assert _sheet(world)["hp"]["current"] == 10 and len(out["voided"]) == 2
    log = read_log(world["camp"])
    assert all(e.get("voided") for e in log if e["action"] in ("attack", "damage"))
    assert report(log) == {}                                    # a voided roll leaves the report
    assert ref_mod.describe_entry(attack | {"voided": "x"}).startswith("✗ VOIDED")
    ref.attack("Pip", "Grak", "shortsword")                    # 14 hits, 4 damage: Grak 7 -> 3
    dmg = [e for e in read_log(world["camp"]) if e["action"] == "damage"][-1]
    ref.void(dmg["_line"], "wrong target")
    assert ref.status()["combatants"][0]["hp"] == 7
    with pytest.raises(RefereeError, match="already voided"):
        ref.void(dmg["_line"], "again")


def test_a_repeat_roll_is_flagged_never_blocked(world, capsys):
    ref = Referee(world["base"], roller=Dice(5, 6, 15))
    ref.check("Pip", "athletics", 10, why="climb the shaft")
    assert "REPEAT ROLL" not in capsys.readouterr().out
    ref.check("Pip", "athletics", 10, why="climb the shaft again")
    out = capsys.readouterr().out
    assert "REPEAT ROLL" in out and "1× in this scene (1 failed)" in out
    r = ref.check("Pip", "athletics", 15, why="a harder wall")          # another DC: another task
    assert "REPEAT ROLL" not in capsys.readouterr().out and r["outcome"] == "success"
