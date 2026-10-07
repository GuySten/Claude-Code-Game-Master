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


def test_a_loop_with_an_entry_plays_it_once_and_loops_back_to_the_body(tmp_path):
    # A boss stage opens strong once (the stage change's climax), then loops its body.
    sp = spec(loop=True, length=16, start=-4, loop_from=0)
    assert A.loop_start(sp) == round(4 * 60 / 80 * orchestra.RATE)    # after the 4-beat entry
    assert A.loop_start(spec(loop=True, length=16)) is None             # a plain loop: from the top
    with pytest.raises(A.ArrangementError):
        A.build(spec(loop=True, length=16, loop_from=20))
    np = pytest.importorskip("numpy")
    pytest.importorskip("soundfile")
    out = music_compose.write(np.zeros((4800, 2), dtype="float32"), 48000, tmp_path / "s.ogg", loop_start=1234,
                              landing=2400)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
    import table_server
    assert table_server.loop_start(out) == pytest.approx(1234 / 48000)
    assert table_server.loop_start(out, "LANDING") == pytest.approx(0.05)     # where a sting lands
    plain = music_compose.write(np.zeros((4800, 2), dtype="float32"), 48000, tmp_path / "p.ogg")
    assert table_server.loop_start(plain) is None


def test_the_critic_wants_a_stage_entry_strong_and_judges_the_climax_on_the_body():
    import arrangement
    parts = ["violins", "violins2", "cellos", "basses", "horns", "trombones", "flutes", "clarinets",
             "bassoons", "trumpets", "tuba", "oboe"]

    def piece(entry_parts):
        lines = []
        for i, part in enumerate(parts):
            lo, _ = orchestra.RANGES[part]
            notes = [[u, lo + 7, 4] for u in range(-8, 0, 4)] if i < entry_parts else []   # the entry
            notes += [[u, lo + 7, 4] for u in range(0, 64, 4) if i < 5 or u >= 48]      # the body builds
            lines.append({"part": part, "notes": notes})
        return {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "statements": [], "start": -8,
                "length": 64, "loop": True, "loop_from": 0, "role": "battle", "chords": [[-8, 64, "i"]],
                "dynamics": [[-8, 118], [0, 80], [44, 90], [48, 120], [60, 80]], "lines": lines}
    strong = [m for _, m in arrangement.check(piece(12), listen=False)]
    weak = [m for _, m in arrangement.check(piece(3), listen=False)]
    assert not [m for m in strong if "entry" in m and "parts" in m]
    assert not [m for m in strong if "nothing left to arrive" in m]        # (the entry isn't the body)
    assert [m for m in weak if "start strong" in m]
    assert [m for m in strong if "loop body is" in m]                     # 64 beats: far too short
    long = piece(12)
    long.update(length=320, lines=[{**l, "notes": l["notes"] + [[u, l["notes"][-1][1], 4] for u in range(64, 320, 4)]}
                                   for l in long["lines"] if l["notes"]])
    assert not [m for _, m in arrangement.check(long, listen=False) if "loop body is" in m]


def test_a_statement_can_be_stretched_and_a_bar_of_two_is_a_meter():
    # A chant over a fast engine: the tune augmented at the piece's own tempo (the Ashen
    # Saint's composer had to write "tempo": 35 for a piece at 140 to get it).
    def horns(sp):
        score, _, _ = A.build(sp)
        return sorted((t, k) for t, on, p, k, _ in score.events if on and p == "horns:4")
    plain, slow = horns(spec()), horns(spec(statements=[{"at": 0, "stretch": 4}]))
    assert [k for _, k in slow] == [k for _, k in plain]
    assert [t for t, _ in slow] == pytest.approx([4 * t for t, _ in plain])
    with pytest.raises(A.ArrangementError, match="stretch"):
        A.build(spec(statements=[{"at": 0, "stretch": 0}]))
    sketch = {"tune": {"seed": "sketch", "key": "D4", "meter": "2/4"}, "statements": [], "length": 8,
              "chords": [[0, 8, "i"]], "harmony": [{"part": "strings", "play": "chord", "range": ["D3", "D4"]}]}
    assert A.build(sketch)[1] > 0


def test_the_peak_is_judged_against_the_bodys_first_half_minute_not_sixteen_slow_bars():
    import arrangement
    parts = ["violins", "violins2", "cellos", "basses", "horns", "trombones", "flutes", "clarinets",
             "bassoons", "trumpets", "tuba", "oboe"]

    def piece(tempo, all_from_start):
        lines = []
        for i, part in enumerate(parts):
            lo, _ = orchestra.RANGES[part]
            notes = [[u, lo + 7, 4] for u in range(-8, 0, 4)]                      # a strong entry
            notes += [[u, lo + 7, 4] for u in range(0, 96, 4) if all_from_start or i < 5 or 56 <= u < 68]
            lines.append({"part": part, "notes": notes})
        return {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "statements": [], "start": -8,
                "length": 96, "loop": True, "loop_from": 0, "role": "battle", "tempo": tempo,
                "chords": [[-8, 96, "i"]], "dynamics": [[-8, 118], [0, 80], [56, 124], [68, 80]], "lines": lines}
    def flagged(sp):
        return [m for _, m in arrangement.check(sp, listen=False) if "brings nothing" in m]
    assert not flagged(piece(40, False))        # 16 bars here are 96 s: the old window swallowed the peak
    assert flagged(piece(40, True))             # a peak with nothing new is still caught


def test_a_boss_stage_states_its_tune_whole():
    base = spec(loop=True, start=-4, loop_from=0, length=64, role="battle")
    tune_len = A._build(base)["tune_len"]
    frag = {**base, "statements": [{"at": 0, "from": 0, "to": tune_len / 2}, {"at": 32, "from": tune_len / 2}]}
    whole = {**base, "statements": [{"at": 0}, {"at": 32, "shift": 3}]}
    assert [m for _, m in A.check(frag, listen=False) if "never states the boss's tune whole" in m]
    assert not [m for _, m in A.check(whole, listen=False) if "never states the boss's tune whole" in m]


def test_the_tune_listing_shows_every_note():
    text = A.describe("Test Hero", cls="Fighter")
    tune = music_compose.leitmotif("Test Hero", "major", "Fighter")
    notes = [l for l in text.splitlines() if not l.startswith(("chords", "  bar"))]
    assert len(notes) == 2 + len(tune["notes"])
    menu = [l for l in text.splitlines() if l.startswith("  bar")]          # a chord menu per bar
    assert menu and all(len(l.split(":", 1)[1].split()) >= 1 for l in menu)


def test_a_loop_has_no_seam(tmp_path):
    np = pytest.importorskip("numpy")
    pytest.importorskip("tinysoundfont")
    if not orchestra.SF2.is_file():
        pytest.skip("the SoundFont isn't downloaded here")
    x, rate = A.render(spec(loop=True, length=16))
    assert x.shape[1] == 2
    rms = lambda s: float(np.sqrt((s ** 2).mean()))           # noqa: E731
    assert abs(20 * np.log10(rms(x[-rate // 4:]) / rms(x[:rate // 4]))) < 6.5   # (6.0 dB; 5.8 before the
                                                     # brass went drier, BRASS_DRY_DB: less hall rings over the seam)
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
                      {"part": "tremolo", "notes": [[float(i) / 2, "C5", 0.25] for i in range(16)]}],
               chords=[[0, 40, "I"]], dynamics=[[0, 90]])
    found = A.check(bad, listen=False)
    text = " | ".join(f"{lv}: {m}" for lv, m in found)
    assert "error: horns: 1 note(s) out of its range" in text
    assert "warn: tremolo: 15 of 16 notes are shorter than it takes to speak" in text   # (the horn doubles one)
    assert "only move 0 velocity points" in text and "one chord holds" in text
    # a quick instrument doubling the same notes takes the warning away
    doubled = dict(bad, lines=bad["lines"] + [{"part": "clarinets", "notes": [[float(i) / 2, "C4", 0.25] for i in range(16)]}])
    assert not any("tremolo" in m for _, m in A.check(doubled, listen=False))


def test_quick_string_notes_play_their_short_recordings_and_need_no_double():
    # 0.19 s notes (a quarter of a beat at 80): under SHORT_S - the short-note recordings, which
    # speak at once; 0.375 s ones (half a beat): too long for those, too short for the sustained
    quick = spec(lines=[{"part": "violins2", "notes": [[float(i) / 2, "C5", 0.25] for i in range(16)]}],
                 chords=[[0, 40, "I"]])
    assert 0.25 * 60 / 80 < orchestra.SHORT_S
    assert not any(m.startswith("violins2:") for _, m in A.check(quick, listen=False))
    middling = spec(lines=[{"part": "violins2", "notes": [[float(i), "C5", 0.5] for i in range(16)]}],
                    chords=[[0, 40, "I"]])
    text = " | ".join(m for _, m in A.check(middling, listen=False))
    assert "violins2: 16 of 16 notes are shorter than it takes to speak" in text
    assert f"under {orchestra.SHORT_S:.2f}s" in text


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


def test_the_critic_hears_a_static_theme():
    held = spec(chords=[[0, 1000, "I"]], harmony=[{"part": "strings", "play": "chord", "range": ["G3", "G4"]}],
                patterns=[], hits=[])
    assert any("only the tune moves" in m for _, m in A.check(held, listen=False))
    battle = dict(held, role="battle", loop=True)
    # (no count of moving lines any more: it came from the audio rater, not the host)
    assert not any("battle or loop texture" in m for _, m in A.check(battle, listen=False))
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


def test_a_motif_is_written_once_and_placed_transformed():
    import arrangement
    spec = {"motifs": {"call": [[0, "D4", 1], [1, "A4", 1], [2, "D5", 2]]},
            "lines": [{"part": "horns", "motif": "call", "at": 8},
                      {"part": "trombones", "motif": "call", "at": 16, "shift": -12, "stretch": 2,
                       "alter": {"1": -1}, "repeat": 2, "every": 8, "vel": -4},
                      {"part": "violins", "motif": "call", "at": 0, "invert": True, "take": [0, 2]},
                      {"part": "cellos", "motif": "call", "at": 0, "retro": True, "octave": -1,
                       "notes": [[6, "D3", 1]]}]}
    lines = arrangement.expand_motifs(spec)["lines"]
    assert lines[0]["notes"] == [[8.0, 62, 1.0], [9.0, 69, 1.0], [10.0, 74, 2.0]]
    tb = lines[1]["notes"]
    assert [n[0] for n in tb] == [16.0, 18.0, 20.0, 24.0, 26.0, 28.0]          # twice as slow, twice
    assert [n[1] for n in tb[:3]] == [50, 56, 62]                              # an octave down, the fifth bent to a tritone
    assert lines[1]["vel"] == -4 and "motif" not in lines[1]
    assert lines[2]["notes"] == [[0.0, 62, 1.0], [1.0, 55, 1.0]]                # mirrored: up a fifth becomes down a fifth
    assert [n[1] for n in lines[3]["notes"]] == [62, 57, 50, "D3"]              # backwards, an octave down, plus a note
    assert lines[3]["notes"][0][0] == 0.0 and lines[3]["notes"][-1] == [6, "D3", 1]


def test_a_misnamed_motif_is_an_error_that_names_the_ones_there_are():
    import arrangement, pytest as _pt
    with _pt.raises(arrangement.ArrangementError, match="call"):
        arrangement.expand_motifs({"motifs": {"call": [[0, "D4", 1]]}, "lines": [{"part": "horns", "motif": "cal"}]})


def test_a_score_written_with_motifs_checks_and_builds():
    import arrangement
    spec = {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "statements": [], "length": 16,
            "chords": [[0, 16, "i"]],
            "harmony": [{"part": "strings", "from": 0, "to": 16, "play": "chord", "range": ["D3", "A4"]}],
            "motifs": {"call": [[0, "D4", 1], [1, "A4", 1], [2, "D5", 2]]},
            "lines": [{"part": "horns", "motif": "call", "at": 0, "repeat": 4, "every": 4}]}
    ctx = arrangement._build(spec)
    horns = [e for e in ctx["score"].events if e[1] and e[2].partition(":")[0] == "horns"]
    assert len(horns) == 12
    assert not [m for lvl, m in arrangement.check(spec, listen=False) if lvl == "error"]


def test_a_line_is_doubled_by_naming_the_other_parts_once():
    import arrangement
    spec = {"motifs": {"m": [[0, "C5", 1], [1, "D5", 1]]},
            "lines": [{"part": "violins", "vel": -2, "notes": [[0, "C5", 2]],
                       "double": [{"part": "chorus", "octave": -1, "vel": -4}]},
                      {"part": "trombones", "motif": "m", "at": 4, "octave": -2, "double": [{"part": "men_choir"}]}]}
    lines = arrangement.expand_motifs(spec)["lines"]
    assert [l["part"] for l in lines] == ["violins", "chorus", "trombones", "men_choir"]
    assert lines[1]["notes"] == [[0, 60, 2]] and lines[1]["vel"] == -6 and "double" not in lines[0]
    assert [n[1] for n in lines[3]["notes"]] == [48, 50] and lines[3]["notes"][0][0] == 4.0


def test_a_progression_is_written_as_one_string_of_chords():
    import arrangement
    got = arrangement.progression_chords({"progression": [{"at": 0, "chords": "i bVI | iv*2", "repeat": 2},
                                                          {"at": 32, "chords": "V", "every": 2}]}, 4)
    assert got == [[0, 4, "i"], [4, 8, "bVI"], [8, 16, "iv"], [16, 20, "i"], [20, 24, "bVI"], [24, 32, "iv"],
                   [32, 34, "V"]]
    spec = {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "statements": [], "length": 8,
            "progression": {"chords": "i iv"},
            "harmony": [{"part": "strings", "from": 0, "to": 8, "play": "chord", "range": ["D3", "A4"]}]}
    ctx = arrangement._build(spec)
    assert ctx["chord_at"](1)["symbol"] == "i" and ctx["chord_at"](5)["symbol"] == "iv"


def test_a_written_tune_can_be_read_note_by_note():
    import arrangement
    tune = {"seed": "Ashen Saint", "key": "C4", "meter": "4/4", "mode": "aeolian",
            "motif": [[0, 1], [0, 1], [4, 2]], "again": [[2, 4]], "climb": [], "home": [[0, 4]]}
    out = arrangement.describe("Ashen Saint", written=tune)
    assert "C4" in out and "G4" in out and "4/4" in out


def test_the_tune_listing_counts_bars_from_the_first_downbeat_as_grid_does():
    import arrangement
    from music import music_compose
    written = {"seed": "Picked", "key": "D4", "meter": "3/4", "mode": "aeolian", "pickup": [[4, 1]],
               "motif": [[7, 3], [6, 2], [4, 1]], "again": [[7, 3], [6, 3]], "climb": [], "home": [[0, 3]]}
    t = music_compose.leitmotif("Picked", "major", written=written)
    assert t["pickup"] == 1
    menu = arrangement.fitting_chords(t)
    assert [label for label, _ in menu[:2]] == ["pickup", "bar 1"]
    rows = [l.split() for l in arrangement.describe("Picked", written=written).splitlines()]
    assert ["0", "0.2"] == rows[3][:2] and ["1", "1.0"] == rows[4][:2]     # the pickup, then bar 1
    moved = arrangement.describe("Picked", written=written, key="F4").splitlines()
    assert "tonic F4" in moved[0] and moved[4].split()[2] == "F5"            # D5 (the octave) -> F5
    assert moved[4].endswith("(the hook)")


def test_fix_moves_notes_into_range_and_doubles_quick_notes_on_slow_strings():
    import arrangement
    spec = {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "statements": [], "length": 16, "tempo": 120,
            "chords": [[0, 16, "i"]],
            "harmony": [{"part": "basses", "from": 0, "to": 16, "play": "root", "range": ["C1", "C2"]}],
            "lines": [{"part": "trumpets", "notes": [[0, "D7", 2], [2, "A6", 2]]},          # all too high: one shift
                      {"part": "bells", "notes": [[0, "C2", 4], [4, "C4", 4]]},             # one note too low
                      {"part": "violins", "notes": [[i * 0.75, "D5", 0.75] for i in range(20)]}],   # (0.375 s)
            "patterns": [{"part": "timpani", "note": "D1", "from": 0, "to": 8, "pattern": "x"}]}
    fixed, changes = arrangement.fix(spec, listen=False)
    assert not [m for lv, m in arrangement.check(fixed, listen=False) if lv == "error"]
    assert fixed["lines"][0]["notes"][0][1] == "D5"                  # the trumpets' line, an octave... or two down
    assert fixed["lines"][1]["notes"][0][1] == "C4"
    assert fixed["lines"][2]["double"][0]["part"] in ("flutes", "clarinets")
    assert pitch_ok(fixed["harmony"][0]["range"])
    assert len(changes) >= 4


def pitch_ok(rng):
    import arrangement, orchestra
    lo, hi = orchestra.RANGES["basses"]
    return lo <= arrangement.pitch(rng[0]) <= arrangement.pitch(rng[1]) <= hi


def test_a_climax_with_nothing_left_to_arrive_is_flagged_and_a_built_one_is_not():
    import arrangement
    def piece(opening_parts):
        parts = ["violins", "violins2", "cellos", "basses", "horns", "trombones", "flutes", "clarinets",
                 "bassoons", "trumpets", "tuba", "oboe"]
        lines = []
        for i, part in enumerate(parts):
            lo, _ = __import__("orchestra").RANGES[part]
            start = 0 if i < opening_parts else 12          # the rest enter at the climax
            lines.append({"part": part, "notes": [[u, lo + 7, 1] for u in range(start, 16)]})
        return {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "statements": [], "length": 64,
                "chords": [[0, 64, "i"]], "dynamics": [[0, 70], [44, 90], [48, 120], [60, 80]],
                "lines": [{**l, "notes": [[n[0] * 4, n[1], 4] for n in l["notes"]]} for l in lines]}
    flat = [m for _, m in arrangement.check(piece(12), listen=False) if "nothing left to arrive" in m]
    built = [m for _, m in arrangement.check(piece(5), listen=False) if "nothing left to arrive" in m]
    assert flat and not built


def test_fix_puts_the_tune_on_top_with_the_gain_the_critic_names(monkeypatch):
    sp = spec(melody=[{"from": 0, "to": 16, "parts": {"horns": 0}}, {"from": 16, "to": 32, "parts": {"horns": 0}, "gain": 2}])
    said = [("warn", 'the tune is barely over the rest at bar 1-bar 4: +0 dB (melody entry #0 "gain": 3 would put it at +3)'),
            ("error", 'the tune is buried at bar 5-bar 8: -3 dB under the rest (give melody entry #1 "gain": 8)')]
    monkeypatch.setattr(A, "check", lambda s, listen=True: said)
    fixed, changes = A.fix(sp)
    assert [m.get("gain") for m in fixed["melody"]] == [3.0, 8.0]
    assert len(changes) == 2 and sp["melody"][0].get("gain") is None       # (the original untouched)


def test_a_figure_is_written_once_and_played_in_many_sections():
    sp = spec(figures={"waltz": [{"play": "bass", "range": ["D2", "C#3"], "pattern": "x--"},
                                 {"play": "chord", "range": ["A3", "F4"], "pattern": " oo", "vel": -6}]},
              harmony=[{"figure": "waltz", "part": "cellos", "spans": [[0, 12], [24, 36]], "vel": -10, "octave": 1},
                       {"part": "strings", "play": "chord", "spans": [[0, 6], [12, 18]], "vel": -20}])
    out = A.expand_figures(sp)["harmony"]
    assert len(out) == 4 + 2
    assert out[0] == {"play": "bass", "range": ["D3", "C#4"], "pattern": "x--", "from": 0, "to": 12,
                      "part": "cellos", "vel": -10.0}
    assert out[1]["vel"] == -16.0 and out[3]["from"] == 24
    assert [(e["from"], e["to"]) for e in out[4:]] == [(0, 6), (12, 18)]
    A.build(sp)                                                     # (it plays)
    with pytest.raises(A.ArrangementError):
        A.expand_figures(spec(harmony=[{"figure": "nope", "part": "cellos", "spans": [[0, 4]]}]))


def test_a_line_marked_lead_is_measured_like_the_tune():
    pytest.importorskip("numpy")
    pytest.importorskip("tinysoundfont")
    if not orchestra.SF2.is_file():
        pytest.skip("the SoundFont isn't downloaded here")
    sp = {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "statements": [], "length": 16,
          "chords": [[0, 16, "i"]], "dynamics": [[0, 100]],
          "harmony": [{"part": "strings", "from": 0, "to": 16, "play": "chord", "range": ["D3", "D5"], "vel": 10}],
          "lines": [{"part": "flutes", "lead": True, "vel": -40,
                     "notes": [[u, "A5", 2] for u in range(0, 16, 2)]}]}
    assert [m for _, m in A.check(sp) if "lead line (flutes)" in m]
    fixed, changes = A.fix(sp)                               # make sets its gain, as for the tune
    assert fixed["lines"][0]["gain"] > 0 and any("lead line #0" in c for c in changes)
    assert not [m for _, m in A.check(fixed) if "lead line (flutes)" in m]


def _seam_loop(entry: bool, end_at: int = 32):
    """A loop of steady strings (to ``end_at``, then nothing); ``entry``: an ff brass chord
    from the entry held two bars into the body - heard on the first pass only."""
    harmony = [{"part": "strings", "from": 0, "to": end_at, "play": "chord", "range": ["D3", "D5"],
                "pattern": "xxxx"}]
    if entry:
        harmony.append({"part": "brass", "from": -4, "to": 4, "play": "chord", "range": ["D3", "D5"],
                        "pattern": "x-------", "vel": 20})
    return {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "statements": [], "length": 32,
            "tempo": 120, "loop": True, "start": -4 if entry else 0, "loop_from": 0,
            "chords": [[-4, 32, "i"]], "dynamics": [[-4, 120], [0, 90], [32, 90]], "harmony": harmony}


def test_the_loop_seam_is_heard_as_on_a_repeat_not_through_the_entry():
    pytest.importorskip("numpy")
    pytest.importorskip("tinysoundfont")
    if not orchestra.SF2.is_file():
        pytest.skip("the SoundFont isn't downloaded here")
    seam = lambda sp: [m for _, m in A.check(sp) if "loop's seam" in m]
    assert not seam(_seam_loop(entry=True))                  # the entry's chord isn't there on a repeat
    assert seam(_seam_loop(entry=False, end_at=24))          # the music stops two bars before the end


def test_steady_pieces_written_to_their_recipe_pass_the_critic():
    # composing.md: a pre-end is intense with no development; a turn cue and a place hold a
    # steady texture. The critic's climax and stage checks are for themes and stages only.
    parts = ["violins", "violins2", "cellos", "basses", "horns", "trombones", "flutes", "clarinets", "bassoons"]
    def steady(role, **extra):
        lines = [{"part": p, "notes": [[u, orchestra.RANGES[p][0] + 7, 4] for u in range(0, 64, 4)]} for p in parts]
        return {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "statements": [], "length": 64,
                "loop": True, "role": role, "chords": [[0, 64, "i"]], "dynamics": [[0, 110], [64, 110]],
                "lines": lines, **extra}
    for role in ("pre_end", "turn", "place"):
        found = [m for _, m in A.check(steady(role), listen=False)]
        assert not [m for m in found if "nothing left to arrive" in m or "loop body is" in m], (role, found)
    # a theme loop with a played-once intro is not a stage either
    intro = steady("theme", start=-4, loop_from=0)
    assert not [m for _, m in A.check(intro, listen=False) if "loop body is" in m]


def test_several_parts_and_several_hits_are_written_once():
    sp = spec(harmony=[{"parts": ["strings", "horns"], "play": "chord", "range": ["G3", "G4"], "from": 0, "to": 8}],
              hits=[{"parts": ["timpani", "trombones"], "at": [0, 8, 16], "note": "root", "len": 1}])
    out = A.expand_figures(sp)
    assert [h["part"] for h in out["harmony"]] == ["strings", "horns"]
    assert sorted((h["part"], h["at"]) for h in out["hits"]) == [("timpani", 0), ("timpani", 8), ("timpani", 16),
                                                                 ("trombones", 0), ("trombones", 8), ("trombones", 16)]
    A.build(sp)


def test_the_grid_does_the_arithmetic():
    tune = {"bar": 3, "meter": "3/4", "pickup": 1, "notes": [(0, 1)] + [(0, 3)] * 20}
    g = A.grid(tune, 168, entry_bars=4, body_seconds=150)
    assert "1 bar = 3 units = 1.07 s" in g and "(1 pickup + 20 bars)" in g
    assert '"start": -12' in g and '"length": 432' in g                    # 144 bars >= 150 s
    assert '"at": 23 -> bars 9-28' in g


def test_an_arpeggio_plays_one_chord_tone_per_hit_and_flows_across_chords():
    import arrangement
    spec = {"tune": {"seed": "sketch", "key": "F4", "meter": "4/4"}, "statements": [], "length": 8,
            "tempo": 120, "chords": [[0, 4, "i"], [4, 8, "bVI"]],
            "harmony": [{"part": "pizzicato", "play": "arpeggio", "from": 0, "to": 8, "range": ["F3", "C5"],
                         "pattern": "xxxxxxxx", "step": 0.5}]}
    score, _, _ = arrangement.build(spec)
    keys = [k for t, on, p, k, _ in sorted(score.events) if on and p == "pizzicato"]
    names = [arrangement.name_of(k) for k in keys]
    assert names[:5] == ["F3", "G#3", "C4", "F4", "G#4"]                 # up through F minor's tones
    assert set(keys[8:]) <= {k for k in range(53, 73) if k % 12 in (1, 5, 8)}   # then Db major's
    down = arrangement.build({**spec, "harmony": [{**spec["harmony"][0], "order": "down"}]})[0]
    assert arrangement.name_of(next(k for t, on, p, k, _ in sorted(down.events) if on)) == "C5"
    with pytest.raises(arrangement.ArrangementError):
        arrangement.build({**spec, "harmony": [{**spec["harmony"][0], "pattern": None}]})


def test_a_written_tunes_listing_says_written_not_a_generated_mode():
    import arrangement
    tune = {"seed": "Ashen Saint", "key": "C4", "meter": "4/4", "mode": "aeolian",
            "motif": [[0, 1], [0, 1], [4, 2]], "again": [[2, 4]], "climb": [], "home": [[0, 4]]}
    head = arrangement.describe("Ashen Saint", written=tune).splitlines()[0]
    assert "(written)" in head and "major" not in head


def test_the_tune_on_brass_alone_is_flagged_but_a_blend_is_not():
    import arrangement
    base = {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "length": 16, "tempo": 100,
            "chords": [[0, 16, "I"]], "statements": [{"at": 0}]}
    alone = {**base, "melody": [{"from": 0, "to": 16, "parts": {"horns": 0}}]}
    blend = {**base, "melody": [{"from": 0, "to": 16, "parts": {"horns": 0}},
                                {"from": 0, "to": 16, "parts": {"violins": 0}}]}       # (another entry, same time)
    flagged = lambda sp: [m for _, m in arrangement.check(sp, listen=False) if "rule 13" in m]
    assert flagged(alone) and not flagged(blend)


def test_a_lead_line_on_horns_doubled_by_woods_is_not_exposed():
    import arrangement
    base = {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "length": 8, "tempo": 100,
            "chords": [[0, 8, "I"]], "statements": [],
            "lines": [{"part": "horns", "lead": True, "notes": [[0, "D4", 4], [4, "A4", 4]]}]}
    exposed = lambda sp: [m for _, m in arrangement.check(sp, listen=False) if "is exposed" in m]
    assert exposed(base)
    doubled = {**base, "lines": [{**base["lines"][0], "double": [{"part": "clarinets"}]}]}
    assert not exposed(doubled)


def test_timpani_roots_sit_in_the_drums_lowest_octave():
    import arrangement
    spec = {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "length": 8, "tempo": 100,
            "chords": [[0, 4, "I"], [4, 8, "IV"]], "statements": [],
            "patterns": [{"part": "timpani", "note": "root", "from": 0, "to": 8, "pattern": "x---"}]}
    score, _, _ = arrangement.build(spec)
    keys = sorted({k for t, on, p, k, _ in score.events if on and p == "timpani"})
    assert [arrangement.name_of(k) for k in keys] == ["D2", "G2"]


def test_a_later_boss_stage_is_mastered_louder_than_the_one_before():
    np = pytest.importorskip("numpy")
    pytest.importorskip("tinysoundfont")
    if not orchestra.SF2.is_file():
        pytest.skip("the SoundFont isn't downloaded here")
    import arrangement
    spec = {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "statements": [], "length": 16,
            "tempo": 120, "loop": True, "role": "stage", "chords": [[0, 16, "i"]],
            "harmony": [{"part": "strings", "from": 0, "to": 16, "play": "chord", "range": ["D3", "D5"],
                         "pattern": "xxxx"},
                        {"part": "brass", "from": 0, "to": 16, "play": "chord", "range": ["D3", "D4"],
                         "pattern": "x-x-"}],
            "hits": [{"part": "timpani", "note": "D2", "at": 8, "len": 1, "vel": 120}]}
    one, rate = arrangement.render({**spec, "stage": 1})
    two, _ = arrangement.render({**spec, "stage": 2})
    level = lambda x: orchestra.loudness(x, rate, loop=True)["loud"]
    assert abs(level(one) - orchestra.MASTER_LUFS) < 0.5
    assert abs(level(two) - level(one) - arrangement.STAGE_STEP_DB) < 0.3   # the step, all of it
    for x in (one, two):                                                     # under the same ceiling
        assert 20 * np.log10(orchestra.loop_peak(x, True)) <= orchestra.TRUE_PEAK_DB + 0.05


def test_a_choir_on_quick_notes_is_flagged_but_held_choir_notes_are_not():
    import arrangement
    base = {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "length": 16, "tempo": 126,
            "chords": [[0, 16, "i"]], "statements": []}
    quick = {**base, "lines": [{"part": "chorus", "notes": [[i / 2, "D4" if i % 2 else "F4", 0.5] for i in range(16)]}]}
    held = {**base, "lines": [{"part": "chorus", "notes": [[i * 2, "D4" if i % 2 else "F4", 2] for i in range(8)]}]}
    flagged = lambda sp: [m for _, m in arrangement.check(sp, listen=False) if "changes notes" in m]
    assert flagged(quick) and not flagged(held)


def test_many_short_brass_stabs_are_flagged_but_a_few_are_not():
    import arrangement
    base = {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "length": 32, "tempo": 120,
            "chords": [[0, 32, "i"]], "statements": []}
    stabs = {**base, "lines": [{"part": "brass", "notes": [[i + 0.5, "D3", 0.5] for i in range(32)]}]}
    few = {**base, "lines": [{"part": "brass", "notes": [[i * 8 + 0.5, "D3", 0.5] for i in range(4)]}]}
    flagged = lambda sp: [m for _, m in arrangement.check(sp, listen=False) if "stabs (" in m]
    assert flagged(stabs) and not flagged(few)


def test_constant_semitone_dissonance_is_flagged_but_a_passing_grind_is_not():
    import arrangement
    base = {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "length": 16, "tempo": 100,
            "chords": [[0, 16, "i"]], "statements": []}
    grind = {**base, "lines": [{"part": "strings", "notes": [[0, "D4", 16], [0, "D#4", 16]]}]}
    passing = {**base, "lines": [{"part": "strings", "notes": [[0, "D4", 16], [14, "D#4", 1]]}]}
    flagged = lambda sp: [m for _, m in arrangement.check(sp, listen=False) if "clash sounds" in m]
    assert flagged(grind) and not flagged(passing)


def test_a_mens_choir_above_e4_is_flagged():
    import arrangement
    base = {"tune": {"seed": "sketch", "key": "D4", "meter": "4/4"}, "length": 8, "tempo": 80,
            "chords": [[0, 8, "i"]], "statements": []}
    high = {**base, "lines": [{"part": "men_choir", "notes": [[0, "D3", 4], [4, "G#4", 4]]}]}
    low = {**base, "lines": [{"part": "men_choir", "notes": [[0, "D3", 4], [4, "D#4", 4]]}]}
    flagged = lambda sp: [m for _, m in arrangement.check(sp, listen=False) if "above E4" in m]
    assert flagged(high) and not flagged(low)
