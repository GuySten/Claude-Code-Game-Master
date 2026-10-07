"""QA eval for kit-systems-authoring.

The kit can instantiate executable signature-system primitives (a `systems`
block on ruleset.json), and get_full_context surfaces them as a ROLL-these block
distinct from the prose YOUR WORLD'S RULES. Adversarial: malformed entries
dropped, block absent when no systems, named_track config rendered.
"""

import json
from pathlib import Path

from lib.session_manager import SessionManager
from lib.world_kit import WorldKit


def _ruleset_path(world_dir: str) -> Path:
    base = Path(world_dir)
    active = (base / "active-campaign.txt").read_text().strip()
    return base / "campaigns" / active / "ruleset.json"


def _set_systems(world_dir: str, systems) -> None:
    p = _ruleset_path(world_dir)
    rs = json.loads(p.read_text()) if p.exists() else {}
    rs["systems"] = systems
    p.write_text(json.dumps(rs))


def test_worldkit_systems_getter_drops_malformed(dcc_world):
    _set_systems(dcc_world, [
        {"primitive": "named_track", "name": "Menace", "config": {"max": 6}},
        {"primitive": "price_roll", "name": "Sorcery's Price", "config": {}},
        {"name": "no primitive"},          # dropped
        {"primitive": "guarded_payoff"},    # dropped (no name)
        "junk",                              # dropped
    ])
    got = WorldKit(dcc_world).systems()
    assert [s["name"] for s in got] == ["Menace", "Sorcery's Price"]


def test_systems_block_surfaces_in_context(dcc_world):
    _set_systems(dcc_world, [
        {"primitive": "named_track", "name": "Menace",
         "config": {"max": 6, "thresholds": [{"at": 3, "consequence": "they fear you"},
                                             {"at": 6, "consequence": "the city hunts you"}]}},
    ])
    ctx = SessionManager(dcc_world).get_full_context()
    assert "SIGNATURE SYSTEMS (executable" in ctx, "the roll-these block must appear"
    assert "Menace (named_track)" in ctx
    assert "they fear you" in ctx and "the city hunts you" in ctx
    assert "named_track / price_roll / reaction_roll / guarded_payoff" in ctx


def test_no_systems_no_block(dcc_world):
    _set_systems(dcc_world, [])
    assert "SIGNATURE SYSTEMS (executable" not in SessionManager(dcc_world).get_full_context()


def test_write_systems_roundtrips_and_drops_malformed(dcc_world):
    from lib import book_bible
    active = (Path(dcc_world) / "active-campaign.txt").read_text().strip()
    cdir = str(Path(dcc_world) / "campaigns" / active)
    book_bible.write_systems(cdir, [
        {"primitive": "named_track", "name": "Dread", "config": {"max": 4}},
        {"name": "bad — no primitive"},   # dropped
        {"primitive": "price_roll"},        # dropped — no name
    ])
    got = WorldKit(dcc_world).systems()
    assert [s["name"] for s in got] == ["Dread"], "round-trips one, drops the malformed two"
    assert got[0]["config"] == {"max": 4}


def test_named_track_value_persists_and_shows_in_context(dcc_world):
    # A playtest's core house rule (the Hunger) lived only in prose: no tool
    # stored its value. Named tracks are stored as threat clocks marked "track".
    from lib.threat_clocks import ThreatClockManager
    from lib.consequence_manager import ConsequenceManager
    _set_systems(dcc_world, [
        {"primitive": "named_track", "name": "The Hunger",
         "config": {"max": 6, "thresholds": [{"at": 3, "consequence": "the lamps gutter"},
                                             {"at": 6, "consequence": "the Tithe is called"}]}},
    ])
    ctx = SessionManager(dcc_world).get_full_context()
    assert "The Hunger (named_track): NOW 0/6 (not recorded yet)" in ctx
    m = ThreatClockManager(dcc_world)
    out = m.change("the hunger", delta=+3, reason="blood spilled near the Stone")
    assert out["after"] == 3 and [t["at"] for t in out["crossed"]] == [3]
    assert len(out["fired"]) == 1                              # the threshold's consequence
    fired = [c for c in ConsequenceManager(dcc_world).check_pending() if c["id"] == out["fired"][0]]
    assert "the lamps gutter" in fired[0]["consequence"]
    clock = m.get_clocks()["The Hunger"]
    assert clock["track"] and clock["advance_on"] == "event" and clock["current"] == 3
    assert clock["history"][-1]["reason"] == "blood spilled near the Stone"
    m.tick_time_clocks(2)                                      # time never moves a track
    assert m.get_clocks()["The Hunger"]["current"] == 3
    down = m.change("The Hunger", value=0, reason="the Stone was fed")
    assert down["after"] == 0 and down["fired"] == []          # falling fires nothing
    ctx = SessionManager(dcc_world).get_full_context()
    assert "The Hunger (named_track): NOW 0/6." in ctx and "(named track: gm-clock.sh track)" in ctx


def test_named_track_cli(dcc_world):
    import os
    import subprocess
    _set_systems(dcc_world, [{"primitive": "named_track", "name": "Dread", "config": {"max": 4}}])
    root = Path(__file__).resolve().parent.parent
    run = lambda *a: subprocess.run(["bash", str(root / "tools" / "gm-clock.sh"), *a],
                                    capture_output=True, text=True,
                                    env={**os.environ, "GM_WORLD_STATE_BASE": dcc_world})
    assert "Dread: 0 → 2/4" in run("track", "Dread", "+2", "--reason", "a scream").stdout
    assert "Dread: 2 → 1/4" in run("track", "Dread", "-1").stdout
    assert "Dread: 1/4" in run("track", "Dread").stdout
    assert run("track", "Nope", "+1").returncode != 0
    assert "Rumour: 0 → 2/5" in run("track", "Rumour", "2", "--max", "5").stdout
    assert "Dread: 1 → 4/4" in run("set", "Dread", "4").stdout
