"""The host judge: the host's verdicts, the floor for tunes, blind pairs, the decision."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import host_judge as hj  # noqa: E402

GOOD = {"seed": "Test", "meter": "4/4", "mode": "ionian", "hook": 3,
        "motif": [[0, 1], [2, 1], [4, 2], [3, 1], [2, 1], [1, 2]],
        "again": [[0, 1], [2, 1], [4, 2], [5, 1], [4, 1], [2, 2]],
        "climb": [[4, 1], [5, 1], [7, 2], [8, 1], [9, 3], [7, 1], [5, 1]],
        "home": [[0, 1], [2, 1], [4, 2], [2, 1], [1, 1], [0, 4]]}
LATE = dict(GOOD, seed="Late",                                             # long notes half a beat late,
            motif=[[0, 1], [2, .5], [4, 2], [3, 1], [2, 1], [1, 2.5]])    # like the old generator's


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("HOST_TASTE", str(tmp_path / "taste" / "verdicts.json"))
    monkeypatch.setenv("TUNE_CORPUS", str(tmp_path / "no-corpus.json"))
    import tune_score
    monkeypatch.setattr(tune_score, "CACHE", tmp_path / "no-corpus.json")
    return tmp_path


def test_the_hosts_answers_are_kept_with_what_was_judged():
    hj.record(GOOD, LATE, note="the first one")
    hj.record(GOOD, dict(GOOD, seed="Other"), tie=True)
    data = hj.load()
    assert len(data["verdicts"]) == 2 and data["verdicts"][1]["result"] == "tie"
    assert data["items"][data["verdicts"][0]["a"]] == GOOD and data["verdicts"][0]["kind"] == "tune"


def test_the_floor_drops_a_tune_with_long_notes_off_the_beat():
    assert hj.tune_floor(hj.tune_of(GOOD))[1] == []
    assert any("off the beat" in f for f in hj.tune_floor(hj.tune_of(LATE))[1])


def test_blind_pairs_then_a_decision(tmp_path):
    files = []
    for name, spec in (("a", GOOD), ("b", dict(GOOD, seed="Other", climb=[[4, 1], [5, 1], [7, 2], [6, 1], [9, 3], [7, 1], [5, 1]])),
                       ("c", dict(GOOD, seed="Third", again=[[0, 1], [2, 1], [4, 2], [3, 1], [2, 1], [0, 2]])), ("late", LATE)):
        f = tmp_path / f"{name}.json"
        f.write_text(json.dumps(spec))
        files.append(f)
    out = tmp_path / "blind"
    st = hj.prepare_tunes(files, out, seed=1)
    assert str(files[3]) in st["dropped"] and len(st["key"]) == 3            # 3 survivors -> 3 pairs
    for pair in st["key"].values():                                           # the files carry no names
        assert "Test" not in (out / next(k for k, v in st["key"].items() if v == pair) / "X.txt").read_text()
    # the reader prefers a over everything, b over c
    verdicts = {}
    for p, k in st["key"].items():
        rank = {str(files[0]): 2, str(files[1]): 1, str(files[2]): 0}
        verdicts[p] = {"prefer": "X" if rank[k["X"]] > rank[k["Y"]] else "Y", "confidence": 80}
    (out / "verdicts.json").write_text(json.dumps(verdicts))
    d = hj.decide_tunes(out)
    assert [c for c, *_ in d["ranking"]] == [str(files[0]), str(files[1]), str(files[2])]
    assert d["ask_host"] is None
    # a split, unsure reader: too close to call -> ask the host
    (out / "verdicts.json").write_text(json.dumps({p: {"prefer": "X", "confidence": 52} for p in st["key"]}))
    assert hj.decide_tunes(out)["ask_host"] is not None


def test_validate_counts_how_often_the_judges_agree_with_the_host():
    hj.record(GOOD, LATE)
    got = hj.validate()
    assert got["verdicts"] == 1 and got["tune score"] in ("0/0", "1/1")      # (no corpus: the score is 0 for both)
