"""The sampled orchestra: the arrangement of a character's tune (no sound needed)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import music_compose  # noqa: E402
import orchestra  # noqa: E402

PEOPLE = [("Kestrel", "Barbarian"), ("Izrin", "Wizard"), ("Bram", "Paladin"), ("Pip", "Rogue"),
          ("Sefi", "Cleric"), ("Ammet", "Monk")]


@pytest.mark.parametrize("name,cls", PEOPLE)
def test_the_harmony_fits_the_tune_moves_and_ends_home(name, cls):
    tune = music_compose.leitmotif(name, "major", cls, stage=3)
    prog = orchestra.harmonize(tune)
    assert prog[-1][2] == 0                                       # home: the tonic
    assert len({d for _, _, d, _ in prog}) >= 3                   # it moves
    runs, run = [], 1
    for (_, _, a, _), (_, _, b, _) in zip(prog, prog[1:]):
        run = run + 1 if a == b else 1
        runs.append(run)
    assert max(runs, default=1) <= 4
    # The strong notes (those that start a span) are in their chord, nearly always.
    starts = {round(t, 6): st for t, st in ((sum(b for _, b in tune["notes"][:i]), s)
                                            for i, (s, _) in enumerate(tune["notes"]))}
    fits = [starts[round(a, 6)] % 12 in pcs for a, _, _, pcs in prog if round(a, 6) in starts]
    assert sum(fits) >= 0.8 * len(fits)


@pytest.mark.parametrize("stage", [0, 1, 2, 3])
def test_the_orchestra_grows_with_the_story(stage):
    tune = music_compose.leitmotif("Kestrel", "major", "Barbarian", stage=stage)
    score, seconds = orchestra.arrange(tune, stage)
    parts = {p.partition(":")[0] for _, _, p, _, _ in score.events}
    assert parts <= orchestra.LAYERS[stage]
    assert all(0 <= t <= seconds + 3.5 and 0 <= v <= 127 for t, _, _, _, v in score.events)
    assert sum(1 for e in score.events if e[1]) == sum(1 for e in score.events if not e[1])
    if stage == 0:
        assert parts == {"horns"}                                  # a lone voice
    if stage == 3:
        assert {"trumpets", "choir", "timpani", "kit", "flutes"} <= parts


def test_the_tune_is_the_characters_own():
    tune = music_compose.leitmotif("Kestrel", "major", "Barbarian", stage=3)
    score, _ = orchestra.arrange(tune, 3)
    played = [k for _, on, p, k, _ in sorted(score.events) if on and p == "violins:4"]
    assert played == [tune["key"] + st for st, _ in tune["notes"]]


def test_it_sounds_when_the_instruments_are_here(tmp_path):
    pytest.importorskip("numpy")
    pytest.importorskip("tinysoundfont")
    if not orchestra.SF2.is_file():
        pytest.skip("the SoundFont isn't downloaded here")
    samples, rate = orchestra.render("Kestrel", "Barbarian", 1)
    assert samples.ndim == 2 and samples.shape[1] == 2 and len(samples) > 10 * rate
    assert 0.1 < float(abs(samples).max()) <= 0.9


def test_an_instrument_built_from_recordings_plays_at_its_pitch(tmp_path):
    np = pytest.importorskip("numpy")
    tsf = pytest.importorskip("tinysoundfont")
    import sf2write
    rate = 44100
    t = np.arange(rate * 2) / rate
    tone = (np.sin(2 * np.pi * 220.0 * t) * 12000).astype("int16")      # A3, two seconds
    audio, ls, le = sf2write.crossfade_loop(np.stack([tone, tone], 1), rate, start_s=0.5, fade_s=0.2)
    zone = dict(audio=audio, rate=rate, key=57, lo=40, hi=70, ls=ls, le=le)
    sf2write.write(tmp_path / "t.sf2", [("A", [zone]), ("B", [zone])], "test")
    assert sf2write.read_samples(tmp_path / "t.sf2")[0][3] == 57
    assert len(sf2write.read_samples(tmp_path / "t.sf2")) == 2           # shared, stored once (L, R)
    syn = tsf.Synth(samplerate=rate)
    sid = syn.sfload(str(tmp_path / "t.sf2"))
    syn.program_select(0, sid, 0, 1)
    syn.noteon(0, 69, 100)                                              # A4: an octave up
    out = np.frombuffer(syn.generate(rate * 4), dtype="float32").reshape(-1, 2)[rate * 3:, 0]
    assert float(abs(out).max()) > 0.01                                 # still sounding, looped
    spectrum = np.abs(np.fft.rfft(out * np.hanning(len(out))))
    assert abs(np.argmax(spectrum) * rate / len(out) - 440.0) < 3


@pytest.mark.parametrize("part", ["men_choir", "chorus", "choir_oo", "choir_oh", "gong", "bass_drum", "anvil",
                                  "brake_drum"])
def test_the_real_choirs_fall_back_to_the_sound_sets_choir_when_they_cant_be_had(monkeypatch, part):
    pytest.importorskip("numpy")
    pytest.importorskip("tinysoundfont")
    if not orchestra.SF2.is_file():
        pytest.skip("the SoundFont isn't downloaded here")
    def offline(**_):
        raise OSError("offline")
    monkeypatch.setattr(orchestra, "EXTRA_FONTS", {k: offline for k in orchestra.EXTRA_FONTS})
    sc = orchestra.Score()
    sc.note(part, 57, 0.0, 2.0, 100)
    out = orchestra.play(sc, 2.5)
    assert float(abs(out).max()) > 0.001                                # heard, not silent


def test_the_parts_played_in_parallel_sound_as_played_one_by_one(monkeypatch):
    np = pytest.importorskip("numpy")
    pytest.importorskip("tinysoundfont")
    if not orchestra.SF2.is_file():
        pytest.skip("the SoundFont isn't downloaded here")
    sc = orchestra.Score()
    for i, part in enumerate(["violins", "cellos", "horns", "flutes", "timpani"]):
        sc.note(part, 48 + 5 * i, 0.3 * i, 1.0, 100)
    sc.note("violins:4", 72, 2.0, 1.0, 100)                          # a layer: the tune
    played = {}
    for workers in ("1", "3"):
        monkeypatch.setenv("GM_ORCHESTRA_WORKERS", workers)
        played[workers] = orchestra.play(sc, 4.0, rate=22050)
    one, many = played["1"], played["3"]
    assert float(abs(one).max()) > 0.01
    assert float(abs(one - many).max()) < 1e-2 * float(abs(one).max())
    assert float(abs(one.send - many.send).max()) < 1e-2 * float(abs(one.send).max())
    layers = orchestra.play_layers(sc, 4.0, lambda n: "tune" if ":" in n else "rest", rate=22050)
    assert set(layers) == {"tune", "rest"}
    assert float(abs(layers["tune"] + layers["rest"] - one).max()) < 1e-2 * float(abs(one).max())
    assert float(abs(layers["tune"][: 22050]).max()) == 0.0               # (the tune starts at 2 s)


def test_mastering_keeps_a_climax_above_what_led_to_it():
    np = pytest.importorskip("numpy")
    rate = 8000
    t = np.arange(rate * 8) / rate
    quiet = 0.05 * np.sin(2 * np.pi * 220 * t[: rate * 6])
    loud = 0.4 * np.sin(2 * np.pi * 220 * t[: rate * 2])             # 18 dB above: the climax
    x = np.concatenate([quiet, loud]).astype("float32")
    out = orchestra.master(np.stack([x, x], 1), rate, loop=True)
    level = lambda a: 20 * np.log10(np.sqrt(np.mean(a ** 2)))
    q, l = level(out[rate: rate * 5, 0]), level(out[rate * 6 + 400:, 0])
    assert l - q > 16.5                                             # the limiter took at most ~1.5 dB
    assert np.abs(out).max() <= 0.9


def test_a_loop_with_an_entry_rings_over_its_loop_point_not_its_first_sample():
    np = pytest.importorskip("numpy")
    rate = 8000
    dry = np.zeros((rate * 3, 2), dtype="float32")
    dry[int(rate * 1.9):int(rate * 2.0)] = 0.5                   # a hit just before the end
    wet = orchestra.hall(dry, rate, rt60=1.0, loop_at=rate * 2, loop_from=rate)
    assert len(wet) == rate * 2
    head = float(np.abs(wet[:rate // 4]).max())                  # the entry: untouched
    at_loop = float(np.abs(wet[rate:rate + rate // 4]).max())    # the tail rings on here
    assert head < 1e-6 < at_loop


PERC_PARTS = ["gong", "bass_drum", "anvil", "brake_drum"]


def test_the_real_percussion_parts_play_from_their_own_soundfont():
    assert orchestra.EXTRA_FONTS["perc"] is orchestra.fetch_percussion
    for part in PERC_PARTS:
        assert orchestra.PARTS[part][4] == "perc"
        p = orchestra.PERC[part]
        assert orchestra.PARTS[part][1] == p["preset"]
        assert orchestra.RANGES[part] == (p["lo"], p["hi"]) and p["lo"] <= p["key"] <= p["hi"]
        assert p["hi"] + orchestra.RR_KEYS * (len(p["layers"][0][1]) - 1) <= 127   # (its round-robins fit)
        assert [top for top, _ in p["layers"]][-1] == 127
        assert orchestra.FALLBACK[part][0] == 128                     # (offline: the GM kit's nearest)
    assert len(orchestra.PERC["bass_drum"]["layers"]) == 7 and len(orchestra.PERC["bass_drum"]["layers"][0][1]) == 2
    assert {p["preset"] for p in orchestra.PERC.values()} == {0, 1, 2, 3}
    assert all(u.startswith("https://raw.githubusercontent.com/sgossner/") for p in orchestra.PERC.values()
               for _, takes in p["layers"] for u in takes)


def test_a_struck_instrument_built_from_recordings_has_layers_and_rings_once(tmp_path):
    np = pytest.importorskip("numpy")
    tsf = pytest.importorskip("tinysoundfont")
    import sf2write
    rate = 44100
    t = np.arange(rate) / rate
    def stroke(freq):
        x = (np.sin(2 * np.pi * freq * t) * np.exp(-3 * t) * 20000).astype("int16")
        return np.stack([x, x], 1)
    soft, loud = stroke(200.0), stroke(800.0)
    zones = [dict(audio=a, rate=rate, key=50, lo=48, hi=52, vlo=lo, vhi=hi, loop=False, ls=8,
                  le=len(a) - 8, excl=1) for a, lo, hi in ((soft, 1, 64), (loud, 65, 127))]
    sf2write.write(tmp_path / "p.sf2", [("Hit", zones)], "test")
    syn = tsf.Synth(samplerate=rate)
    sid = syn.sfload(str(tmp_path / "p.sf2"))
    def hit(vel):
        syn.program_select(0, sid, 0, 0)
        syn.noteon(0, 50, vel)
        out = np.frombuffer(syn.generate(rate * 2), dtype="float32").reshape(-1, 2)[:, 0]
        syn.sounds_off(0)
        syn.generate(256)
        return out
    for vel, freq in ((40, 200.0), (120, 800.0)):                   # the velocity picks the layer
        out = hit(vel)[: rate // 2]
        spectrum = np.abs(np.fft.rfft(out * np.hanning(len(out))))
        assert abs(np.argmax(spectrum) * rate / len(out) - freq) < 5
    out = hit(120)
    assert float(abs(out[rate + 2000:]).max()) < 1e-4                 # played once: not looped


@pytest.fixture
def perc_font():
    pytest.importorskip("numpy")
    pytest.importorskip("tinysoundfont")
    if not orchestra.SF2.is_file():
        pytest.skip("the SoundFont isn't downloaded here")
    if not orchestra.PERC_SF2.is_file():
        pytest.skip("the percussion isn't built here (orchestra.fetch_percussion)")


def test_the_real_percussion_sounds_rings_and_takes_turns(perc_font):
    np = pytest.importorskip("numpy")
    rate = 22050
    for part in PERC_PARTS:
        sc = orchestra.Score()
        key = orchestra.PERC[part]["key"]
        sc.note(part, key, 0.1, 0.3, 90)
        sc.note(part, key, 1.6, 0.3, 90)
        out = np.asarray(orchestra.play(sc, 3.0, rate=rate))
        assert float(abs(out).max()) > 0.005, part
        a, b = out[int(0.1 * rate): int(0.6 * rate), 0], out[int(1.6 * rate): int(2.1 * rate), 0]
        if len(orchestra.PERC[part]["layers"][0][1]) > 1:            # its round-robins, in turn
            assert float(np.corrcoef(a, b)[0, 1]) < 0.99, part
    sc = orchestra.Score()
    sc.note("gong", orchestra.PERC["gong"]["key"], 0.1, 0.5, 100)    # a short note: it rings on
    out = np.asarray(orchestra.play(sc, 12.0, rate=rate))
    level = lambda x: float(np.sqrt(np.mean(x ** 2)))
    assert level(out[int(10 * rate): int(11 * rate)]) > 0.05 * level(out[int(0.2 * rate): int(1.2 * rate)])


def test_an_arrangement_plays_the_real_percussion(perc_font):
    import arrangement as A
    s = {"tune": {"seed": "Test Hero", "cls": "Fighter"}, "tempo": 120, "statements": [],
         "key": "C4", "meter": "4/4", "length": 8, "chords": [[0, 8, "I"]],
         "patterns": [{"part": "bass_drum", "note": "bd", "from": 0, "to": 4, "pattern": "x"},
                      {"part": "anvil", "from": 0, "to": 4, "pattern": " x x"}],
         "hits": [{"part": "brake_drum", "at": 4, "vel": 100}, {"part": "gong", "note": "gong", "at": 6, "vel": 110}]}
    score, _, _ = A.build(s)
    keys = {(p, k) for _, on, p, k, _ in score.events if on}
    assert keys == {(p, orchestra.PERC[p]["key"]) for p in PERC_PARTS}
    assert not [m for lvl, m in A.check(s, listen=False) if lvl == "error"]
    samples, rate = A.render(s, rate=22050)
    assert float(abs(samples).max()) > 0.05


# --- the electric guitar ---
def test_the_guitar_parts_play_one_instrument_from_its_own_soundfont():
    assert orchestra.EXTRA_FONTS["guitar"] is orchestra.fetch_guitar
    assert set(orchestra.GUITAR) == {"guitar", "guitar_mute"}
    for part, art in orchestra.GUITAR.items():
        assert orchestra.PARTS[part][4] == "guitar"
        assert orchestra.PARTS[part][1] == orchestra._guitar_preset(art, 0, 0)     # (its left pass, take 1)
        assert orchestra.FALLBACK[part] == (0, 30)                    # (offline: GM distortion guitar)
        assert orchestra.RANGES[part] == (35, 76)                     # B1-E5
        assert orchestra.send_db(orchestra.ROOM["guitar"]) == -12.0   # mostly dry
    presets = {orchestra._guitar_preset(a, s, t) for a in (0, 1) for s in (0, 1)
               for t in range(orchestra.GUITAR_TAKES)}
    assert presets == set(range(4 * orchestra.GUITAR_TAKES))
    assert orchestra.GUITAR_URL.startswith("https://drive.usercontent.google.com/")


def _fake_guitar_library(root, np, soundfile):
    """A stand-in for the unpacked library: a short stereo tone for every note and take."""
    names = ["c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b"]
    rate = 44100
    t = np.arange(int(0.4 * rate)) / rate
    for folder in ("Sus_Down", "Mute_Down"):
        (root / "Samples" / folder).mkdir(parents=True)
        for key in range(orchestra.GUITAR_KEYS[0], orchestra.GUITAR_KEYS[1] + 1):
            f = 440 * 2 ** ((key - 69) / 12)
            for take in range(1, orchestra.GUITAR_TAKES + 2):          # (one more than kept)
                x = 0.5 * np.sin(2 * np.pi * f * t + take) * np.exp(-3 * t)
                y = np.stack([x, np.roll(x, 17 * take)], 1)            # (left and right: other takes)
                name = f"{names[key % 12]}{key // 12 - 1}_{folder}{take}.flac"
                soundfile.write(str(root / "Samples" / folder / name), y, rate)


def test_the_guitar_soundfont_is_built_from_the_unpacked_library(tmp_path):
    np = pytest.importorskip("numpy")
    soundfile = pytest.importorskip("soundfile")
    tsf = pytest.importorskip("tinysoundfont")
    _fake_guitar_library(tmp_path / "lib", np, soundfile)
    out = orchestra.fetch_guitar(dest=tmp_path / "guitar.sf2", quiet=True, src=tmp_path / "lib")
    syn = tsf.Synth(samplerate=44100)
    sid = syn.sfload(str(out))
    for preset in range(4 * orchestra.GUITAR_TAKES):
        syn.program_select(0, sid, 0, preset)
        syn.noteon(0, 35, 100)                                         # B1: E2's recording, pitched down
        x = np.frombuffer(syn.generate(4410), dtype="float32").reshape(-1, 2)[:, 0]
        syn.sounds_off(0)
        syn.generate(256)
        assert float(abs(x).max()) > 1e-3, preset


def test_the_guitar_wont_download_what_it_cant_unpack(tmp_path, monkeypatch):
    monkeypatch.setattr(orchestra, "_rar_tools", lambda: [])
    monkeypatch.delenv("ORCHESTRA_GUITAR_SRC", raising=False)
    def no_download(*a, **k):
        raise AssertionError("downloaded 716 MB it then couldn't unpack")
    monkeypatch.setattr(orchestra.urllib.request, "urlopen", no_download)
    with pytest.raises(OSError, match="7-Zip"):
        orchestra.fetch_guitar(dest=tmp_path / "guitar.sf2", quiet=True)
    assert not (tmp_path / "guitar.sf2").exists()


def test_a_third_on_the_distorted_guitar_is_flagged_power_chords_are_not():
    import arrangement as A
    s = {"tune": {"seed": "Test Hero", "cls": "Fighter"}, "tempo": 120, "statements": [],
         "key": "D4", "meter": "4/4", "length": 8, "chords": [[0, 4, "i"], [4, 8, "bVI"]],
         "harmony": [{"part": "guitar", "play": "root5", "range": ["D2", "D3"], "pattern": "x-  ", "step": 0.5,
                      "legato": 1.0},
                     {"part": "guitar_mute", "play": "root5", "range": ["D2", "D3"], "pattern": "  oo", "step": 0.5}]}
    found = A.check(s, listen=False)
    assert not [m for lvl, m in found if lvl == "error"]
    assert not [m for _, m in found if "guitar" in m]
    s["harmony"].append({"part": "guitar", "play": "chord", "range": ["D3", "D4"], "from": 0, "to": 2})
    assert [m for lvl, m in A.check(s, listen=False) if lvl == "warn" and "turns to mud" in m]


def _guitar_riff():
    sc = orchestra.Score()
    for i in range(8):                                                 # open chords, chugs between
        t = 0.2 + 0.25 * i
        if i % 4 == 0:
            sc.note("guitar", 38, t, 0.5, 112); sc.note("guitar", 45, t, 0.5, 112)
        elif i % 4 > 1:
            sc.note("guitar_mute", 38, t, 0.18, 96); sc.note("guitar_mute", 45, t, 0.18, 96)
    return sc


def _heard_like_a_rhythm_guitar(np, out, rate):
    out = np.asarray(out, dtype="float64")
    assert float(abs(out).max()) > 0.01
    body = out[int(0.2 * rate): int(2.2 * rate)]
    corr = float(np.corrcoef(body[:, 0], body[:, 1])[0, 1])
    assert corr < 0.9                                                  # two passes, left and right
    m = body.mean(axis=1)
    P = np.abs(np.fft.rfft(m)) ** 2
    f = np.fft.rfftfreq(len(m), 1 / rate)
    assert P[(f >= 2000) & (f < 4000)].sum() / P.sum() < 0.15          # no buzz (GM sample alone: 28%)


def test_the_guitar_sounds_through_its_amp_double_tracked(monkeypatch):
    np = pytest.importorskip("numpy")
    pytest.importorskip("tinysoundfont")
    if not orchestra.SF2.is_file():
        pytest.skip("the SoundFont isn't downloaded here")
    if not orchestra.GUITAR_SF2.is_file():
        pytest.skip("the guitar isn't built here (orchestra.fetch_guitar)")
    monkeypatch.setenv("GM_ORCHESTRA_WORKERS", "1")
    sc = _guitar_riff()
    layers = orchestra.play_layers(sc, 3.0, lambda name: name, rate=44100)
    assert set(layers) == {"guitar"}                                   # one instrument, one amp
    _heard_like_a_rhythm_guitar(np, layers["guitar"], 44100)
    assert float(abs(layers["guitar"].send).max()) < 0.3 * float(abs(layers["guitar"]).max())   # mostly dry


def test_the_guitar_falls_back_to_the_gm_guitar_through_a_cabinet(monkeypatch, capsys):
    np = pytest.importorskip("numpy")
    pytest.importorskip("tinysoundfont")
    if not orchestra.SF2.is_file():
        pytest.skip("the SoundFont isn't downloaded here")
    def offline(**_):
        raise OSError("offline")
    monkeypatch.setattr(orchestra, "EXTRA_FONTS", {**orchestra.EXTRA_FONTS, "guitar": offline})
    monkeypatch.setattr(orchestra, "_SYNTHS", {})
    monkeypatch.setenv("GM_ORCHESTRA_WORKERS", "1")
    out = orchestra.play(_guitar_riff(), 3.0, rate=44100)
    assert "no guitar" in capsys.readouterr().err                      # said, not silent
    _heard_like_a_rhythm_guitar(np, out, 44100)
