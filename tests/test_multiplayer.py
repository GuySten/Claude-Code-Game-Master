"""Multiplayer: several player characters at one table.

The lead PC stays in character.json; every other player's PC lives in
players/<slug>.json. Single-player campaigns keep the historical behavior
(an unknown name still resolves to the lead), while a multiplayer campaign
refuses an unknown name so one player's damage never lands on another.
"""

import json

from lib.identity_onboarding import IdentityOnboarding
from lib.player_manager import PlayerManager
from lib.session_manager import SessionManager


def _world(tmp_path):
    world = tmp_path / "world-state"
    camp = world / "campaigns" / "camp"
    camp.mkdir(parents=True)
    (world / "active-campaign.txt").write_text("camp")
    (camp / "campaign-overview.json").write_text(json.dumps({
        "campaign_name": "Camp",
        "opening_matched_to_pc": True,
        "player_position": {"current_location": "The Rusty Tankard"},
    }))
    return world, camp


def _load(path):
    return json.loads(path.read_text())


def _table(tmp_path):
    world, camp = _world(tmp_path)
    onboarding = IdentityOnboarding(str(world))
    assert onboarding.onboard("original", name="Pip", concept="a halfling rogue")["success"]
    joined = onboarding.join("original", name="Bram", concept="a dwarf cleric")
    assert joined["success"] and joined["seat"] == "player"
    return world, camp


def test_join_seats_a_second_pc_without_touching_the_lead(tmp_path):
    world, camp = _table(tmp_path)
    assert _load(camp / "character.json")["name"] == "Pip"
    bram = _load(camp / "players" / "bram.json")
    assert bram["name"] == "Bram"
    assert bram["current_location"] == "The Rusty Tankard"
    assert _load(camp / "campaign-overview.json")["current_character"] == "Pip"


def test_join_without_a_lead_becomes_the_lead(tmp_path):
    world, camp = _world(tmp_path)
    result = IdentityOnboarding(str(world)).join("original", name="Pip")
    assert result["success"] and result["seat"] == "lead"
    assert _load(camp / "character.json")["name"] == "Pip"
    assert not (camp / "players").exists()


def test_join_refuses_a_duplicate_name_but_numbers_nameless_strangers(tmp_path):
    world, camp = _table(tmp_path)
    onboarding = IdentityOnboarding(str(world))
    assert not onboarding.join("original", name="pip")["success"]
    first = onboarding.join("nameless")
    second = onboarding.join("nameless")
    assert first["character"]["name"] != second["character"]["name"]


def test_named_changes_land_on_the_named_pc(tmp_path):
    world, camp = _table(tmp_path)
    pm = PlayerManager(str(world))
    assert pm.modify_hp("bram", -4)["current_hp"] == 6
    assert pm.modify_gold("Bram", 12)["current_gold"] == 12
    assert pm.modify_inventory("Pip", "add", "Lockpicks")["success"]
    bram, pip = _load(camp / "players" / "bram.json"), _load(camp / "character.json")
    assert bram["hp"]["current"] == 6 and bram["gold"] == 12
    assert pip["hp"]["current"] == 10 and pip["equipment"] == ["Lockpicks"]


def test_unknown_name_is_refused_only_in_multiplayer(tmp_path):
    world, camp = _world(tmp_path)
    IdentityOnboarding(str(world)).onboard("original", name="Pip")
    pm = PlayerManager(str(world))
    # Single player: the historical contract — the name is ignored.
    assert pm.modify_hp("whoever", -1)["success"]
    IdentityOnboarding(str(world)).join("original", name="Bram")
    assert not PlayerManager(str(world)).modify_hp("whoever", -1)["success"]


def test_set_swaps_the_lead_and_keeps_both_sheets(tmp_path):
    world, camp = _table(tmp_path)
    pm = PlayerManager(str(world))
    pm.modify_hp("Bram", -4)
    assert pm.set_current_player("Bram")
    assert _load(camp / "character.json")["hp"]["current"] == 6
    assert _load(camp / "players" / "pip.json")["name"] == "Pip"
    assert not (camp / "players" / "bram.json").exists()
    assert _load(camp / "campaign-overview.json")["current_character"] == "Bram"


def test_leave_archives_a_player_but_never_the_lead(tmp_path):
    world, camp = _table(tmp_path)
    pm = PlayerManager(str(world))
    assert not pm.remove_player("Pip")["success"]
    assert pm.remove_player("Bram")["success"]
    assert not (camp / "players" / "bram.json").exists()
    assert _load(camp / "departed" / "bram.json")["name"] == "Bram"
    assert [p["name"] for p in pm.get_all_players()] == ["Pip"]


def test_become_for_a_fallen_player_replaces_only_their_seat(tmp_path):
    world, camp = _table(tmp_path)
    (camp / "npcs.json").write_text(json.dumps({"Mira": {
        "is_party_member": True,
        "character_sheet": {"name": "Mira", "level": 2, "hp": {"current": 14, "max": 14}},
    }}))
    pm = PlayerManager(str(world))
    pm.kill_character("Bram", "crossbow bolt")
    result = pm.become("Mira", for_pc="Bram")
    assert result["success"] and result["seat"] == "player"
    assert _load(camp / "character.json")["name"] == "Pip"
    assert _load(camp / "players" / "mira.json")["hp"]["current"] == 14
    assert not (camp / "players" / "bram.json").exists()
    assert list((camp / "fallen").glob("bram-*.json"))
    assert _load(camp / "campaign-overview.json")["current_character"] == "Pip"


def test_move_and_context_cover_every_pc(tmp_path):
    world, camp = _table(tmp_path)
    sm = SessionManager(str(world))
    sm.move_party("The Old Mill")
    assert _load(camp / "players" / "bram.json")["current_location"] == "The Old Mill"
    assert _load(camp / "character.json")["current_location"] == "The Old Mill"
    ctx = sm.get_full_context()
    assert "--- PLAYER CHARACTERS (2 players at the table) ---" in ctx
    assert "[lead] Pip" in ctx and "[player] Bram" in ctx


def test_single_player_context_is_unchanged(tmp_path):
    world, camp = _world(tmp_path)
    IdentityOnboarding(str(world)).onboard("original", name="Pip")
    ctx = SessionManager(str(world)).get_full_context()
    assert "--- CHARACTER ---" in ctx and "PLAYER CHARACTERS" not in ctx
    assert "[lead]" not in ctx


def test_save_restore_round_trips_the_whole_table(tmp_path):
    world, camp = _table(tmp_path)
    sm = SessionManager(str(world))
    assert sm.create_save("table")
    IdentityOnboarding(str(world)).join("original", name="Zed")
    PlayerManager(str(world)).modify_hp("Bram", -3)
    assert sm.restore_save("table")
    assert sorted(p.name for p in (camp / "players").glob("*.json")) == ["bram.json"]
    assert _load(camp / "players" / "bram.json")["hp"]["current"] == 10
