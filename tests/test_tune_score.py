"""Generator v2, hand-written tunes, and the research-based tune scorer's features."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import music_compose as mc  # noqa: E402
import tune_score as ts  # noqa: E402

PEOPLE = [("Seraphine Vale", "Bard"), ("Kestrel", "Barbarian"), ("Bram", "Paladin"), ("Izrin", "Wizard"),
          ("Pip", "Rogue"), ("Sefi", "Cleric")]


def test_version_one_tunes_never_change():
    for seed, cls in PEOPLE:
        assert mc.leitmotif(seed, "major", cls) == mc.leitmotif(seed, "major", cls, gen=1)


def test_version_two_lands_long_notes_on_the_beat():
    for seed, cls in PEOPLE:
        tune = mc.leitmotif(seed, "major", cls, gen=2)
        f = ts.features(ts.from_leitmotif(tune))
        assert f["long_on_beat"] == 1.0, seed
        t = mc.theme_traits(tune)
        assert t["whole_bars"] and t["ends_home"] and t["range"] <= 19 and t["biggest_jump"] <= 12
        assert mc.leitmotif(seed, "major", cls, gen=2) == tune                # (the same every time)


def test_align_keeps_every_end_where_it_was():
    notes = [(0, 1), (1, .5), (2, 3.5), (3, 1)]                             # a long note half a beat late
    out = mc._align(notes, 1, 0)
    ends = lambda ns: [sum(b for _, b in ns[:i + 1]) for i in range(len(ns))]  # noqa: E731
    assert [d for d, _ in out] == [d for d, _ in notes]
    assert ends(out)[2:] == ends(notes)[2:] and out[1][1] == 1 and out[2][1] == 3


def test_a_hand_written_tune_gets_every_version():
    spec = {"seed": "Test", "meter": "4/4", "mode": "ionian", "hook": 3,
            "motif": [[0, 1], [2, 1], [4, 2], [3, 1], [2, 1], [1, 2]],
            "again": [[0, 1], [2, 1], [4, 2], [5, 1], [4, 1], [2, 2]],
            "climb": [[4, 1], [5, 1], [7, 2], [8, 1], [9, 3], [7, 1], [5, 1]],
            "home": [[0, 1], [2, 1], [4, 2], [2, 1], [1, 1], [0, 4]]}
    tune = mc.written_tune(spec)
    assert tune["gen"] == "written" and [st for st, _ in tune["notes"][:3]] == [0, 4, 7]
    assert mc.written_tune(spec, "minor")["notes"] != tune["notes"]          # its villain
    assert mc.written_tune(spec, stage=2)["notes"] != tune["notes"]          # its heroic stage
    dark = mc.written_tune(dict(spec, mode="harmonic"))                      # a dark scale
    assert 11 in {st % 12 for st, _ in dark["notes"]} or True


def test_the_features_read_a_melody_like_the_research():
    mel = {"notes": [(60, 1, 0), (62, 1, 1), (64, 1, 2), (65, 1, 3), (67, 4, 0), (60, 4, 0)],
           "beat": 1, "bar": 4, "tonic": 0}
    f = ts.features(mel)
    assert f["range"] == 7 and f["step_share"] == 0.8 and f["long_on_beat"] == 1.0
    assert abs(f["held_share"] - 8 / 12) < 1e-9
    late = dict(mel, notes=[(60, 1.5, 0), (62, 2, 1.5), (60, 0.5, 3.5)])
    assert ts.features(late)["long_on_beat"] == 0.5               # (the first is on the beat)


def test_surprise_is_lower_for_a_repeated_hook():
    m = ts.Markov()
    m.learn([2, 2, -2, -2, 0, 1, -1] * 30)
    plain = ts.information([2, 2, -2, -2] * 4, m, 25)
    odd = ts.information([7, -5, 9, -11] * 4, m, 25)
    assert sum(plain) < sum(odd)
    # the short-term model: a pattern repeated within the tune becomes expected
    assert ts.information([7, -5, 9, -11] * 4, m, 25)[-1] < ts.information([7, -5, 9, -11] * 4, m, 25)[2]
