"""The madness device: the violin plays the tune along, breaks in its windows, the strings follow."""
import json
import pytest

np = pytest.importorskip("numpy")


def test_madness_adds_a_breaking_violin_and_the_strings_follow():
    from lib import devices
    tune = {"seed": "T", "meter": "3/4", "mode": "harmonic", "hook": 3, "pickup": [],
            "motif": [[0, 1], [2, 1], [4, 1]], "again": [[4, 1], [2, 1], [1, 1]],
            "climb": [[2, 1], [4, 1], [6, 1]], "home": [[4, 1], [1, 1], [0, 3]]}
    spec = {"tune": {"seed": "T", "written": tune}, "tempo": 84, "start": -3, "length": 15,
            "chords": [[-3, 15, "i"]], "lines": [],
            "harmony": [{"part": "pizzicato", "from": -3, "to": 15, "play": "chord", "range": ["E3", "C#4"], "pattern": " oo"}]}
    out = devices.madness(spec, [(6.0, 7.0)], stumble=[(6.0, 7.0)], opening=[[-3.0, "C#6", 1.0, -12]])
    vio = next(l for l in out["lines"] if l["part"] == "solo_violin")
    calm = [n for n in vio["notes"] if 0 <= n[0] < 5.5]          # (a rushed break note may start a little early)
    broken = [n for n in vio["notes"] if 5.5 <= n[0] < 7]
    assert calm and all(len(n) == 4 for n in calm)                      # along: in tune, in time
    assert broken and max(n[1] for n in broken) > max(n[1] for n in calm)   # too high
    assert out["unhinge"][0]["parts"][0] == "strings" and out["unhinge"][0]["from"] == 6.0
    assert [h["to"] for h in out["harmony"] if h["part"] == "pizzicato"][0] == 6.0   # the pulse stumbles
    assert vio["notes"][0][0] == -3.0
    assert spec["lines"] == []                                           # (the input is left alone)
