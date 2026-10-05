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


def test_the_critic_reads_a_score_for_what_a_listener_would_notice():
    found = A.check(spec(), listen=False)
    assert not [m for lv, m in found if lv == "error"]
    # out of range, quick notes on a slow instrument with no quick doubling, a buried tune
    bad = spec(lines=[{"part": "horns", "notes": [[0, "C2", 2]]},
                      {"part": "violins2", "notes": [[float(i) / 2, "C5", 0.25] for i in range(16)]}],
               chords=[[0, 40, "I"]], dynamics=[[0, 90]])
    found = A.check(bad, listen=False)
    text = " | ".join(f"{lv}: {m}" for lv, m in found)
    assert "error: horns: 1 note(s) out of its range" in text
    assert "warn: violins2: 15 of 16 notes are shorter than it takes to speak" in text   # (the horn doubles one)
    assert "only move 0 velocity points" in text and "one chord holds" in text
    # a quick instrument doubling the same notes takes the warning away
    doubled = dict(bad, lines=bad["lines"] + [{"part": "clarinets", "notes": [[float(i) / 2, "C4", 0.25] for i in range(16)]}])
    assert not any("violins2" in m for _, m in A.check(doubled, listen=False))


def test_the_critic_hears_a_buried_tune(tmp_path):
    pytest.importorskip("numpy")
    pytest.importorskip("tinysoundfont")
    if not orchestra.SF2.is_file():
        pytest.skip("the SoundFont isn't downloaded here")
    buried = spec(lead=-12, melody=[{"from": 0, "to": 1000, "parts": {"violins": 0}}],
                  harmony=[{"part": "brass", "play": "chord", "range": ["G3", "G4"], "vel": 20}])
    assert any(lv == "error" and "buried" in m for lv, m in A.check(buried))


def test_a_key_change_reads_its_chords_in_the_new_key():
    tune = music_compose.leitmotif("Test Hero", "major", "Fighter")
    s = spec(statements=[{"at": 0}, {"at": 100, "shift": 2}], keys=[{"from": 100, "shift": 2}],
             chords=[[0, 100, "I"], [100, 1000, "I"]], harmony=[{"part": "strings", "play": "bass", "range": ["C2", "B2"]}])
    score, _, _ = A.build(s)
    basses = sorted((t, k) for t, on, p, k, _ in score.events if on and p == "strings")
    assert (basses[1][1] - basses[0][1]) % 12 == 2                 # home, a step up
    horns = [k for t, on, p, k, _ in sorted(score.events) if on and p == "horns:4"]
    n = len(tune["notes"])
    assert [b - a for a, b in zip(horns[:n], horns[n:])] == [2] * n


def test_the_critic_hears_a_thin_battle_and_a_static_theme():
    held = spec(chords=[[0, 1000, "I"]], harmony=[{"part": "strings", "play": "chord", "range": ["G3", "G4"]}],
                patterns=[], hits=[])
    assert any("only the tune moves" in m for _, m in A.check(held, listen=False))
    battle = dict(held, role="battle", loop=True)
    assert any("battle or loop texture" in m for _, m in A.check(battle, listen=False))
    busy = dict(battle, harmony=held["harmony"] + [
        {"part": p, "play": "root", "range": ["C2", "B3"], "pattern": "xo"} for p in ("cellos", "bassoons", "pizzicato")])
    assert not any("texture" in m or "only the tune" in m for _, m in A.check(busy, listen=False))


def test_the_surprise_budget_pairs_a_tune_with_its_setting(monkeypatch, tmp_path):
    import tune_score
    corpus = tmp_path / "corpus.json"
    corpus.write_text("[]")
    monkeypatch.setattr(tune_score, "CACHE", corpus)
    plain = spec(chords=[[0, 1000, "I"]])
    rich = spec(chords=[[0, 8, "I"], [8, 1000, "bVI"]], keys=[{"from": 8, "shift": 2}])
    for pct, s, verdict in ((95, rich, "both"), (95, plain, "balanced"), (60, plain, "neither"), (60, rich, "balanced")):
        monkeypatch.setattr(tune_score, "score", lambda mel, p=pct: {"surprise": (0, p)})
        got = A.surprise_budget(A._build(s), s)
        assert got[3] == verdict, (pct, got)


def test_a_falling_bend_on_brass_is_flagged_as_comic_and_a_sliding_part_with_chords_as_sagging():
    import arrangement
    spec = {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "statements": [], "length": 8,
            "chords": [[0, 8, "i"]],
            "harmony": [{"part": "trombones", "from": 0, "to": 8, "play": "chord", "range": ["D3", "A4"]}],
            "lines": [{"part": "trumpets", "notes": [[0, "D5", 2, 0, {"slide": -7}]]},
                      {"part": "trombones", "notes": [[4, "A3", 2, 0, {"slide": -3}]]},
                      {"part": "violins", "notes": [[4, "A5", 2, 0, {"slide": -2}]]}]}
    found = [m for _, m in arrangement.check(spec, listen=False)]
    assert any(m.startswith("trumpets:") and "comic" in m for m in found)
    assert any(m.startswith("trombones:") and "sag" in m for m in found)
    assert not any(m.startswith("violins:") for m in found)          # a string slide is fine
    spec["role"] = "comic"
    assert not any("comic" in m for _, m in arrangement.check(spec, listen=False))
