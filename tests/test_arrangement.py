"""Arrangements: a piece written as notes for the sampled orchestra."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import arrangement as A  # noqa: E402
import music_compose  # noqa: E402
import orchestra  # noqa: E402

C4 = 60


@pytest.mark.parametrize("symbol,notes,bass", [
    ("I", ["C", "E", "G"], "C"), ("vi7", ["A", "C", "E", "G"], "A"), ("bVII", ["A#", "D", "F"], "A#"),
    ("IVadd9", ["F", "A", "C", "G"], "F"), ("I/E", ["C", "E", "G"], "E"), ("V7", ["G", "B", "D", "F"], "G"),
    ("bII", ["C#", "F", "G#"], "C#"), ("vii°", ["B", "D", "F"], "B"), ("Vsus4", ["G", "C", "D"], "G"),
    ("I5", ["C", "G"], "C"), ("bVI7", ["G#", "C", "D#", "F#"], "G#"), ("i", ["C", "D#", "G"], "C"),
])
def test_chords_are_read_as_a_composer_writes_them(symbol, notes, bass):
    c = A.chord(symbol, C4)
    assert [A.NAMES[p] for p in c["pcs"]] == notes and A.NAMES[c["bass"]] == bass


def test_pitches_and_bad_input():
    assert A.pitch("C4") == 60 and A.pitch("E#4") == 65 and A.pitch("Bb2") == 46 and A.pitch(61) == 61
    for bad in ("H4", "C", "4C"):
        with pytest.raises(A.ArrangementError):
            A.pitch(bad)
    with pytest.raises(A.ArrangementError):
        A.chord("IX", C4)


def spec(**more):
    base = {"tune": {"seed": "Test Hero", "cls": "Fighter"}, "tempo": 80,
            "dynamics": [[0, 80], [8, 110]],
            "melody": [{"from": 0, "to": 1000, "parts": {"horns": 0, "violins": 12}}],
            "chords": [[0, 4, "I"], [4, 8, "IV"], [8, 1000, "V7"]],
            "harmony": [{"part": "strings", "play": "chord", "range": ["G3", "G4"]},
                        {"part": "cellos", "play": "bass", "range": ["C2", "B2"], "pattern": "x-o "}],
            "patterns": [{"part": "timpani", "note": "root", "from": 0, "to": 8, "pattern": "x   "}],
            "hits": [{"part": "kit", "note": "crash", "at": 0, "vel": 120}]}
    base.update(more)
    return base


def test_the_tune_is_played_exactly_by_the_parts_named():
    tune = music_compose.leitmotif("Test Hero", "major", "Fighter")
    score, seconds, loop = A.build(spec())
    horns = [k for t, on, p, k, _ in sorted(score.events) if on and p == "horns:4"]   # (the lead layer)
    assert horns == [tune["key"] + st for st, _ in tune["notes"]]
    violins = [k for t, on, p, k, _ in sorted(score.events) if on and p == "violins:4"]
    assert violins == [k + 12 for k in horns]
    assert loop is None and seconds > 0


def test_chords_sound_their_own_notes_and_patterns_keep_time():
    score, _, _ = A.build(spec())
    tune = music_compose.leitmotif("Test Hero", "major", "Fighter")
    unit = 60 / 80 / (3 if tune["meter"] == "6/8" else 1)
    for t, on, p, k, _ in score.events:
        if on and p == "strings":
            c = A.chord("I" if t < 4 * unit - 1e-6 else "IV" if t < 8 * unit - 1e-6 else "V7", tune["key"])
            assert k % 12 in c["pcs"]
            assert A.pitch("G3") <= k <= A.pitch("G4")
    cellos = sorted((t, k) for t, on, p, k, _ in score.events if on and p == "cellos")
    gaps = {round(b[0] - a[0], 6) for a, b in zip(cellos, cellos[1:])}
    assert gaps <= {round(2 * unit, 6)}                         # "x-o ": every 2 units, held 2
    timp = [t for t, on, p, *_ in score.events if on and p == "timpani"]
    assert len(timp) == 2                                       # "x   " over 8 units


def test_mistakes_are_named():
    with pytest.raises(A.ArrangementError, match="no such part"):
        A.build(spec(harmony=[{"part": "kazoo", "play": "chord"}]))
    with pytest.raises(A.ArrangementError, match="not a chord"):
        A.build(spec(chords=[[0, 8, "I7b13"]]))
    with pytest.raises(A.ArrangementError, match="no chord there"):
        A.build(spec(chords=[], harmony=[]))
    with pytest.raises(A.ArrangementError, match="seed"):
        A.build({"tune": {}})


def test_a_loop_stops_at_its_length_and_slows_for_nothing():
    score, seconds, loop = A.build(spec(loop=True, length=8, start=-4, ritard={"from": 4, "amount": 0.5}))
    assert loop == seconds
    assert all(t < seconds for t, on, *_ in score.events if on)
    first = min(t for t, on, p, *_ in score.events if on and p.startswith("horns"))
    assert first == pytest.approx(4 * 60 / 80)                  # the tune, after a 4-beat intro


def test_the_tune_listing_shows_every_note():
    text = A.describe("Test Hero", cls="Fighter")
    tune = music_compose.leitmotif("Test Hero", "major", "Fighter")
    assert len(text.splitlines()) == 2 + len(tune["notes"])


def test_a_loop_has_no_seam(tmp_path):
    np = pytest.importorskip("numpy")
    pytest.importorskip("tinysoundfont")
    if not orchestra.SF2.is_file():
        pytest.skip("the SoundFont isn't downloaded here")
    x, rate = A.render(spec(loop=True, length=16))
    assert x.shape[1] == 2
    rms = lambda s: float(np.sqrt((s ** 2).mean()))           # noqa: E731
    assert abs(20 * np.log10(rms(x[-rate // 4:]) / rms(x[:rate // 4]))) < 6
    assert float(np.abs(x[0] - x[-1]).max()) < 0.1
    out = music_compose.write(x, rate, tmp_path / "loop.ogg")
    assert out.stat().st_size > 1000


def test_the_tune_is_mixed_over_the_rest_and_parts_are_evened_out():
    score, _, _ = A.build(spec(lead=6, melody=[{"from": 0, "to": 1000, "parts": {"horns": 0}, "gain": 2}]))
    assert {p for _, _, p, _, _ in score.events if p.startswith("horns")} == {"horns:8"}
    # the quiet choir recording is turned up, the loud horns down; a piece can adjust
    assert orchestra.level_db("choir") > orchestra.level_db("horns") + 10
    assert orchestra.level_db("choir", {"choir": -3}) == orchestra.level_db("choir") - 3
