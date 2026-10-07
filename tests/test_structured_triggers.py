"""Tests for structured-trigger-schema.

Consequences gain optional structured triggers (trigger_type/match/expiry) that
the reactivity engine can fire and expire on, additively — legacy free-text
consequences still load and round-trip unchanged.
"""

import json
from pathlib import Path

from lib.consequence_manager import ConsequenceManager


def _consq_path(dcc_world):
    return Path(dcc_world) / "campaigns" / "dungeon-crawler-carl" / "consequences.json"


def test_add_with_structured_trigger(dcc_world):
    cm = ConsequenceManager(dcc_world)
    cid = cm.add_consequence("Guards search the market", "next day",
                             trigger_type="on_location", match="Market", expiry="day 5")
    assert cid
    data = json.loads(_consq_path(dcc_world).read_text(encoding="utf-8"))
    new = next(c for c in data["active"] if c["id"] == cid)
    assert new["trigger_type"] == "on_location"
    assert new["match"] == "Market"
    assert new["expiry"] == "day 5"
    # free-text trigger + description still preserved
    assert new["trigger"] == "next day"
    assert new["consequence"] == "Guards search the market"


def test_legacy_add_omits_structured_fields(dcc_world):
    cm = ConsequenceManager(dcc_world)
    cid = cm.add_consequence("plain consequence", "someday")
    data = json.loads(_consq_path(dcc_world).read_text(encoding="utf-8"))
    new = next(c for c in data["active"] if c["id"] == cid)
    assert "trigger_type" not in new and "match" not in new and "expiry" not in new


def test_fixture_exercises_all_trigger_types_and_a_legacy(dcc_world):
    data = json.loads(_consq_path(dcc_world).read_text(encoding="utf-8"))
    items = data.get("active", []) + data.get("pending", [])
    types = {c.get("trigger_type") for c in items if c.get("trigger_type")}
    assert {"on_location", "on_npc", "on_time", "on_event"}.issubset(types)
    assert any("trigger_type" not in c for c in items), "expected a legacy free-text consequence too"


def test_existing_consequences_round_trip(dcc_world):
    pending = ConsequenceManager(dcc_world).check_pending()
    assert all("consequence" in c and "trigger" in c for c in pending)


def test_expiry_matches_whole_words_not_substrings(dcc_world):
    # Regression: --expiry "dawn" must not self-archive at a place named Dawnhollow.
    cm = ConsequenceManager(dcc_world)
    cid = cm.add_consequence("ambush at first light", "when dawn comes",
                             trigger_type="on_time", match="dawn", expiry="dawn")
    hollow = {"location": "Dawnhollow", "time": "midnight", "present_npcs": [], "events": []}
    assert not cm._is_expired({"expiry": "dawn"}, hollow)
    still_active = [c["id"] for c in cm.check_pending(hollow, limit=10)] + \
                   [c["id"] for c in cm.check_pending()]
    assert cid in still_active

    at_dawn = {"location": "camp", "time": "dawn", "present_npcs": [], "events": []}
    assert cm._is_expired({"expiry": "dawn"}, at_dawn)


def _campaign(tmp_path, name="The Striding Keep"):
    ws = tmp_path / "world-state"
    camp = ws / "campaigns" / "k"
    camp.mkdir(parents=True)
    (ws / "active-campaign.txt").write_text("k")
    (camp / "campaign-overview.json").write_text(json.dumps({"campaign_name": name}))
    return str(ws), camp


def test_free_text_trigger_needs_the_real_time_not_the_campaign_name(tmp_path):
    # A playtest's "Dawn in the Keep" fired two seconds after it was written, at
    # "before dawn": the matcher looked for substrings, and "keep" is in the
    # campaign's own name.
    ws, _ = _campaign(tmp_path)
    cm = ConsequenceManager(ws)
    cm.add_consequence("The Stone reaches for Kestrel", "Dawn in the Keep")
    before = {"location": "The Keep's lower ward", "time": "an hour before dawn", "present_npcs": []}
    assert cm.check_pending(before, limit=10) == []
    at_dawn = {"location": "The Hip", "time": "Dawn", "present_npcs": []}
    assert [c["consequence"] for c in cm.check_pending(at_dawn, limit=10)] == ["The Stone reaches for Kestrel"]


def test_free_text_and_structured_triggers_match_whole_words(tmp_path):
    ws, _ = _campaign(tmp_path, name="Ashes")
    cm = ConsequenceManager(ws)
    cm.add_consequence("The ferryman wants paying", "back at the ship")
    cm.add_consequence("Smugglers wait", "harbour", trigger_type="on_location", match="hip")
    at = {"location": "The Hip of the Worship hall", "time": "noon", "present_npcs": []}
    assert [c["consequence"] for c in cm.check_pending(at, limit=10)] == ["Smugglers wait"]
    ship = {"location": "On the ship", "time": "noon", "present_npcs": []}
    assert [c["consequence"] for c in cm.check_pending(ship, limit=10)] == ["The ferryman wants paying"]
    # A structured on_time "dawn" no longer fires at "before dawn" either.
    cm.add_consequence("Tithe due", "dawn", trigger_type="on_time", match="dawn")
    assert not any(c["consequence"] == "Tithe due" for c in cm.check_pending(
        {"location": "x", "time": "before dawn", "present_npcs": []}, limit=10))


def test_void_strikes_a_mistake_instead_of_resolving_it(tmp_path):
    ws, camp = _campaign(tmp_path)
    cm = ConsequenceManager(ws)
    wrong = cm.add_consequence("[Clock — Kell Ford] The Keep crushes the holdfast", "clock ran out")
    real = cm.add_consequence("Guards hunt the party", "next time")
    cm.resolve(real)
    assert cm.void(wrong, reason="clock ticked by small time steps")
    assert cm.void(real)                      # a mistaken resolve can be voided too
    data = json.loads((camp / "consequences.json").read_text(encoding="utf-8"))
    assert data["active"] == [] and data["resolved"] == []
    voided = {c["id"]: c for c in data["voided"]}
    assert voided[wrong]["void_reason"] == "clock ticked by small time steps"
    assert voided[wrong]["voided_from"] == "active" and voided[real]["voided_from"] == "resolved"
    assert "resolved" not in voided[real]
    assert not cm.void("nope")
