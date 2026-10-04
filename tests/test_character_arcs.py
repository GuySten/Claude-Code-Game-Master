"""A character's story arc (lib/character_arcs.py): moments recorded by the GM, and
what each does to the character's theme."""

import pytest

from lib import character_arcs as arcs


def test_moments_move_the_story_and_the_theme_follows(tmp_path):
    camp = tmp_path
    s = arcs.state_of(camp, "Kestrel")
    assert (s["stage"], s["dark"], s["wound"]) == (0, 0, False)          # a new character: the start
    s = arcs.record(camp, "Kestrel", "growth", "stood alone at the drowned gate")
    assert s["stage"] == 1
    for _ in range(3):
        s = arcs.record(camp, "kestrel", "growth", "again")                 # (any spelling of the name)
    assert s["stage"] == 2                                                  # legendary is the finale's alone
    s = arcs.record(camp, "Kestrel", "wound", "lost her brother")
    assert s["wound"] and arcs.spec(s)["wound"]
    s = arcs.record(camp, "Kestrel", "healing", "buried him at sea")
    assert not s["wound"]
    for _ in range(5):
        s = arcs.record(camp, "Kestrel", "darkness", "took the cursed blade")
    assert s["dark"] == arcs.MAX_DARK
    s = arcs.record(camp, "Kestrel", "light", "gave the blade back")
    assert s["dark"] == arcs.MAX_DARK - 1
    s = arcs.record(camp, "Kestrel", "bond", "swore to guard Pip", other="Pip")
    assert s["bonds"] == ["Pip"] and arcs.spec(s)["warm"]
    s = arcs.record(camp, "Kestrel", "finale", "faced the drowned king")
    assert s["stage"] == 3 and arcs.next_growth(arcs.spec(s)) is None
    assert [m["kind"] for m in arcs.state_of(camp, "KESTREL")["milestones"]][:2] == ["growth", "growth"]
    assert arcs.version(arcs.spec(s)) == "s3-d2-w0-b1"
    with pytest.raises(ValueError):
        arcs.record(camp, "Kestrel", "levelup", "x")


def test_the_next_growth_is_known_ahead(tmp_path):
    sp = arcs.spec(arcs.state_of(tmp_path, "Pip"))
    assert arcs.next_growth(sp) == {**sp, "stage": 1}
    assert arcs.next_growth({**sp, "stage": 2}) is None
