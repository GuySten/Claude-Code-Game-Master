"""The sampled orchestra: the arrangement of a character's tune (no sound needed)."""
import re
import sys
from pathlib import Path

import math
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


def _chord(np, rate, seconds, amp, seed=1):
    """A sustained stereo chord with a little noise: dense, low crest."""
    t = np.arange(int(rate * seconds)) / rate
    rng = np.random.default_rng(seed)
    x = sum(np.sin(2 * np.pi * f * t + p) for f, p in ((220, 0), (277, 1), (330, 2), (440, 3)))
    x = np.stack([x, np.roll(x, 37)], 1) + 0.3 * rng.standard_normal((len(t), 2))
    return (amp * x / np.abs(x).max()).astype("float32")


def _hits(np, rate, seconds, amp, every=0.5, seed=2):
    """Drum hits: short bursts that die away fast - peaky, a high crest."""
    rng = np.random.default_rng(seed)
    n = int(rate * seconds)
    x = np.zeros((n, 2))
    k = int(rate * 0.25)
    burst = rng.standard_normal((k, 2)) * np.exp(-np.arange(k) / (rate * 0.03))[:, None]
    for at in range(0, n - k, int(rate * every)):
        x[at:at + k] += burst
    return (amp * x / np.abs(x).max()).astype("float32")


def _peaky(np, rate, chord=0.4, hits=0.6, every=1.5):
    """Music with drum hits on it: about 12 dB from its loudness to its peaks."""
    return _chord(np, rate, 12, chord) + _hits(np, rate, 12, hits, every=every)


def _tp_db(np, x, loop=True):
    return 20 * np.log10(orchestra.loop_peak(x, loop))


@pytest.mark.parametrize("loop", [False, True])
def test_mastering_brings_a_piece_to_its_loudness_under_the_true_peak_ceiling(loop):
    np = pytest.importorskip("numpy")
    rate = 8000
    for x in (_chord(np, rate, 12, 0.05), _chord(np, rate, 12, 0.9), _peaky(np, rate),
              _peaky(np, rate, 0.2, 0.3, 0.75)):
        rep = {}
        out = orchestra.master(x, rate, loop=loop, report=rep)
        assert abs(rep["loud_lufs"] - orchestra.MASTER_LUFS) < 0.5, rep
        assert abs(orchestra.loudness(out, rate, loop)["loud"] - orchestra.MASTER_LUFS) < 0.5
        assert _tp_db(np, out, loop) <= orchestra.TRUE_PEAK_DB + 0.05       # never past the ceiling
        assert rep["max_reduction_db"] <= orchestra.LIMIT_DB + 1e-6
        assert len(out) == len(x)                         # (a loop's LOOPSTART still points home)


def test_a_peaky_piece_is_limited_not_turned_down_so_it_matches_a_dense_one():
    np = pytest.importorskip("numpy")
    rate = 8000
    dense = _chord(np, rate, 12, 0.5)
    peaky = _peaky(np, rate)
    a, b = {}, {}
    da, pb = orchestra.master(dense, rate, loop=True, report=a), orchestra.master(peaky, rate, loop=True, report=b)
    assert abs(a["loud_lufs"] - b["loud_lufs"]) < 0.5
    assert 1.0 < b["max_reduction_db"] <= orchestra.LIMIT_DB                # the hits were limited
    for out in (da, pb):
        assert _tp_db(np, out) <= orchestra.TRUE_PEAK_DB + 0.05
    # The old way (gain from the loudest sample) left the peaky piece far quieter:
    old = lambda x: orchestra.loudness(x * (0.89 / np.abs(x).max()), rate, True)["loud"]
    assert old(dense) - old(peaky) > 3


def test_a_hotter_master_is_louder_by_its_step_under_the_same_ceiling():
    np = pytest.importorskip("numpy")
    rate = 8000
    x = _peaky(np, rate)
    one, two = {}, {}
    a = orchestra.master(x, rate, loop=True, report=one)
    b = orchestra.master(x, rate, loop=True, hot_db=2.0, limit_db=8.0, report=two)
    assert abs(two["loud_lufs"] - one["loud_lufs"] - 2.0) < 0.3
    assert two["max_reduction_db"] > one["max_reduction_db"]
    assert max(_tp_db(np, a), _tp_db(np, b)) <= orchestra.TRUE_PEAK_DB + 0.05


def test_a_lone_transient_is_not_limited_past_limit_db_the_piece_is_turned_down():
    np = pytest.importorskip("numpy")
    rate = 8000
    x = _chord(np, rate, 12, 0.02)
    x[rate * 6:rate * 6 + 40] += 0.9                       # one click, 30 dB over the music
    rep = {}
    out = orchestra.master(x, rate, report=rep)
    assert abs(rep["max_reduction_db"] - orchestra.LIMIT_DB) < 0.05
    assert rep["loud_lufs"] < orchestra.MASTER_LUFS - 1
    assert _tp_db(np, out, False) <= orchestra.TRUE_PEAK_DB + 0.05


@pytest.mark.parametrize("entry", [0, 3])
def test_a_loop_is_limited_as_it_plays_over_and_over_no_jump_at_its_seam(entry):
    np = pytest.importorskip("numpy")
    rate = 8000
    x = _chord(np, rate, 10, 0.3)
    x[-int(rate * 0.12):-int(rate * 0.1)] *= 3.5           # a hit just before the end: still letting go at the seam
    m = rate * entry
    rep = {}
    out = orchestra.master(x, rate, loop=True, loop_from=m, report=rep)
    assert rep["max_reduction_db"] > 2
    gain = lambda o, i: float(np.median(np.abs(o[i]) / np.maximum(np.abs(x[i, 0]), 1e-9)))
    big = np.abs(x[:, 0]) > 0.1
    end = [i for i in range(len(x) - 40, len(x)) if big[i]]
    head = [i for i in range(m, m + 40) if big[i]]
    jump = 20 * np.log10(gain(out[:, 0], head) / gain(out[:, 0], end))
    assert abs(jump) < 0.05                                 # the gain runs on over the seam
    # ... exactly as in the middle of the loop played three times over:
    body = x[m:]
    long = np.concatenate([x, body, body])
    three = orchestra.master(long, rate, loop=True, loop_from=m)
    assert float(np.abs(three[len(x):len(x) + len(body)] - out[m:]).max()) < 2e-3
    # A piece that ends (no wrap) starts at full gain: the jump a loop must not have.
    once = orchestra.master(x, rate)
    assert gain(once[:, 0], head) / gain(out[:, 0], head) > 1.1 if m == 0 else True


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
    assert set(orchestra.GUITAR) == {"guitar", "guitar_mute", "guitar_lead"}
    for part, art in orchestra.GUITAR.items():
        assert orchestra.PARTS[part][4] == "guitar"
        assert orchestra.PARTS[part][1] == orchestra._guitar_preset(art, 0, 0)     # (its left pass, take 1)
        assert orchestra.FALLBACK[part] == (0, 30)                    # (offline: GM distortion guitar)
        assert orchestra.RANGES[part] == ((40, 79) if part == "guitar_lead" else (35, 76))   # (lead: E2-G5) B1-E5
        assert orchestra.send_db(orchestra.ROOM[part if part == "guitar_lead" else "guitar"]) == -12.0   # mostly dry
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
         "key": "D4", "meter": "4/4", "length": 8, "stage": 2, "chords": [[0, 4, "i"], [4, 8, "bVI"]],
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


def test_the_guitar_is_kept_for_a_bosss_later_stages():
    import arrangement as A
    s = {"tune": {"seed": "Test Hero", "cls": "Fighter"}, "tempo": 120, "statements": [],
         "key": "D4", "meter": "4/4", "length": 8, "chords": [[0, 8, "i"]],
         "harmony": [{"part": "guitar", "play": "root5", "range": ["D2", "D3"], "pattern": "x-  ", "step": 0.5}]}
    kept = lambda sp: [m for lvl, m in A.check(sp, listen=False) if lvl == "warn" and "later stages" in m]
    assert kept(s)                                            # a theme: no
    assert kept(dict(s, role="stage", stage=1))               # a first stage: no
    assert not kept(dict(s, role="stage", stage=2))           # a later stage: yes
    assert not kept(dict(s, role="hit", stage=2))             # a cue of one: yes


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


# --- the rock organ ---
def test_the_rock_organ_is_a_tonewheel_organ_with_its_own_tuning_and_foldback():
    assert "rock_organ" in orchestra.PARTS and orchestra.ORGAN == {"rock_organ"}
    assert len(orchestra.PARTS["rock_organ"]) == 4                     # (no sound set to fetch: synthesized)
    assert orchestra.RANGES["rock_organ"] == (36, 96)                  # a manual: C2-C7
    assert orchestra.send_db(orchestra.ROOM["rock_organ"]) == -12.0    # in front, mostly dry
    assert orchestra._organ_hz(69) == pytest.approx(440.0)             # A: the gears give 440 exactly
    for key in range(36, 97):                                          # the rest: near, not exactly, tempered
        cents = 1200 * __import__("math").log2(orchestra._organ_hz(key) / (440 * 2 ** ((key - 69) / 12)))
        assert abs(cents) < 1.5
    assert any(abs(orchestra._organ_hz(k) / (440 * 2 ** ((k - 69) / 12)) - 1) > 1e-4 for k in range(60, 72))
    assert orchestra._organ_wheel(96 + 36) <= 114 and orchestra._organ_wheel(96 + 36) % 12 == 0   # 1' on C7: folded
    assert orchestra._organ_wheel(36 - 12) == 24                       # 16' on C2: the lowest wheel
    assert orchestra._drawbar_levels("888000000")[:4] == [1.0, 1.0, 1.0, 0.0]
    assert orchestra._drawbar_levels("000000006")[8] == pytest.approx(10 ** (-6 / 20))


def _mod_peak(np, x, rate, band, lo, hi):
    """The rate (Hz) the level of ``band`` of x swings at most, between lo and hi Hz."""
    y = orchestra._filter(x, [("hp", band[0], 0.7, 0)] * 2 + [("lp", band[1], 0.7, 0)] * 2, rate)
    k = int(0.01 * rate)
    e = np.convolve(y ** 2, np.ones(k) / k, mode="same")[::rate // 200]
    e = (e - e.mean()) * np.hanning(len(e))
    E = np.abs(np.fft.rfft(e, 8 * len(e)))
    f = np.fft.rfftfreq(8 * len(e), 1 / 200)
    m = (f >= lo) & (f <= hi)
    return float(f[m][np.argmax(E[m])])


def _organ_chord(start=0.0, end=6.0, vel=105):
    return [ev for k in (50, 57, 62, 69) for ev in ((start, 1, "rock_organ", k, vel), (end, 0, "rock_organ", k, 0))]


def test_the_rock_organ_turns_in_its_rotating_speaker():
    np = pytest.importorskip("numpy")
    rate = 44100
    for speed, horn, drum, lo, hi in (("fast", 6.7, 5.8, 3.0, 9.0), ("slow", 0.80, 0.67, 0.5, 1.5)):
        first, stem = orchestra._organ_stem(_organ_chord(), int(7 * rate), rate, {"speaker": speed})
        s = stem.astype("float64")[int(0.5 * rate):int(5.9 * rate)]
        assert stem.shape[1] == 2 and float(abs(s).max()) > 0.01
        assert float(np.corrcoef(s[:, 0], s[:, 1])[0, 1]) < 0.9        # two mics: the speaker decorrelates them
        assert _mod_peak(np, s[:, 0], rate, (1500, 5000), lo, hi) == pytest.approx(horn, abs=0.15 * horn)
        if speed == "fast":                                            # (the drum: slower, under the horn)
            assert _mod_peak(np, s[:, 1], rate, (60, 400), lo, hi) == pytest.approx(drum, abs=0.4)
        P = np.abs(np.fft.rfft(s.mean(axis=1))) ** 2
        f = np.fft.rfftfreq(len(s), 1 / rate)
        assert P[f > 8000].sum() / P.sum() < 0.02                     # the horn rolls the top off


def test_the_rock_organ_speaker_eases_from_slow_to_fast_where_the_score_says():
    np = pytest.importorskip("numpy")
    rate = 44100
    ev = _organ_chord(0.0, 9.0) + [(0.0, 3, "rock_organ", 0, 0), (4.0, 3, "rock_organ", 0, 1)]
    first, stem = orchestra._organ_stem(ev, int(10 * rate), rate)
    s = stem.astype("float64")
    assert _mod_peak(np, s[int(0.2 * rate):int(3.9 * rate), 0], rate, (1500, 5000), 0.3, 9) < 1.2
    assert _mod_peak(np, s[int(5.5 * rate):int(8.9 * rate), 0], rate, (1500, 5000), 0.3, 9) > 5.5
    f = orchestra._rotor_speed([(4 * rate, True)], 6 * rate, rate, orchestra.LESLIE["horn"], False)
    assert f[4 * rate - 1] == pytest.approx(orchestra.LESLIE["horn"]["slow"])
    assert f[int(5.1 * rate)] > 0.9 * orchestra.LESLIE["horn"]["fast"]    # the horn: there in ~1 s
    d = orchestra._rotor_speed([(4 * rate, True)], 6 * rate, rate, orchestra.LESLIE["drum"], False)
    assert d[int(5.1 * rate)] < 0.75 * orchestra.LESLIE["drum"]["fast"]   # the heavy drum: still getting there


def test_the_rock_organ_clicks_at_key_down_and_its_percussion_is_single_triggered():
    np = pytest.importorskip("numpy")
    rate = 44100
    note = lambda t0, t1, k=62: [(t0, 1, "rock_organ", k, 100), (t1, 0, "rock_organ", k, 0)]   # noqa: E731
    first, stem = orchestra._organ_stem(note(0.5, 1.5), int(2.5 * rate), rate)
    m = orchestra._filter(stem.astype("float64").mean(axis=1), [("hp", 2500, 0.7, 0)] * 2, rate)
    on, w = int(0.5 * rate) - first, int(0.008 * rate)
    steady = np.median([(m[on + i:on + i + w] ** 2).mean() for i in range(int(0.1 * rate), int(0.9 * rate), w)])
    assert (m[on:on + w] ** 2).mean() > 10 * steady                    # the click
    # percussion (the third harmonic, decaying): on a note from all keys up, not on one played legato
    ev = note(0.5, 2.5) + note(1.5, 2.5, 69)
    upper = lambda o: orchestra._filter(orchestra._organ_stem(ev, int(3.5 * rate), rate, o)[1].astype("float64")   # noqa: E731
                                        .mean(axis=1), [("hp", 600, 0.7, 0)] * 2, rate)
    plain, perc = upper({}), upper({"percussion": "third"})
    level = lambda x, t: float((x[int(t * rate) - first:int((t + 0.08) * rate) - first] ** 2).mean())   # noqa: E731
    assert level(perc, 0.52) > 1.5 * level(plain, 0.52)               # struck: the first note
    assert level(perc, 1.52) < 1.3 * level(plain, 1.52)               # legato: not again


def test_the_rock_organ_plays_in_the_orchestra_beside_the_guitar(monkeypatch):
    np = pytest.importorskip("numpy")
    pytest.importorskip("tinysoundfont")
    if not orchestra.SF2.is_file():
        pytest.skip("the SoundFont isn't downloaded here")
    monkeypatch.setenv("GM_ORCHESTRA_WORKERS", "1")
    sc = orchestra.Score()
    for k in (50, 57, 62):
        sc.note("rock_organ", k, 0.2, 2.5, 112)
        sc.note("rock_organ:3", k, 3.0, 0.4, 112)                      # (a layer: the same speaker)
    sc.rotate(0.0, False)
    sc.organ = {"drawbars": "888800000"}
    layers = orchestra.play_layers(sc, 4.0, lambda name: name.partition(":")[0], rate=44100)
    out = layers["rock_organ"]
    assert out.shape[1] == 2 and float(abs(out).max()) > 0.01
    body = np.asarray(out[int(0.4 * 44100):int(2.6 * 44100)], dtype="float64")
    assert float(np.corrcoef(body[:, 0], body[:, 1])[0, 1]) < 0.95
    assert float(abs(out.send).max()) < 0.3 * float(abs(out).max())  # mostly dry, like the guitar
    assert orchestra.level_db("rock_organ") == orchestra.level_db("guitar")


def _guitar_solo():
    sc = orchestra.Score()
    for i, (k, d) in enumerate([(66, 0.33), (66, 0.17), (66, 0.17), (67, 1.2), (78, 0.33), (79, 1.6)]):
        sc.note("guitar_lead", k, 0.2 + sum(x for _, x in [(66, 0.33), (66, 0.17), (66, 0.17), (67, 1.2),
                                                             (78, 0.33)][:i]), d * 0.97, 108)
    return sc


def test_the_lead_guitar_is_one_player_near_centre_and_sings(monkeypatch):
    np = pytest.importorskip("numpy")
    pytest.importorskip("tinysoundfont")
    if not orchestra.SF2.is_file():
        pytest.skip("the SoundFont isn't downloaded here")
    if not orchestra.GUITAR_SF2.is_file():
        pytest.skip("the guitar isn't built here (orchestra.fetch_guitar)")
    monkeypatch.setenv("GM_ORCHESTRA_WORKERS", "1")
    rate = 44100
    layers = orchestra.play_layers(_guitar_solo(), 4.5, lambda name: name, rate=rate)
    assert set(layers) == {"guitar_lead"}                              # its own player, not the rhythm's
    out = np.asarray(layers["guitar_lead"], dtype="float64")
    body = out[int(0.3 * rate): int(4.0 * rate)]
    assert float(np.corrcoef(body[:, 0], body[:, 1])[0, 1]) > 0.9      # one pass, not double-tracked
    assert abs(10 * math.log10((body[:, 0] ** 2).sum() / (body[:, 1] ** 2).sum())) < 1.0   # centred
    m = body.mean(axis=1)
    P = np.abs(np.fft.rfft(m)) ** 2
    f = np.fft.rfftfreq(len(m), 1 / rate)
    assert P[(f >= 2000) & (f < 4000)].sum() / P.sum() < 0.1           # no buzz
    assert P[f >= 8000].sum() / P.sum() < 0.002                        # no fizz
    top = out[int(2.6 * rate): int(3.6 * rate)].mean(axis=1)           # G5 (E5 bent up), held: it sings
    rms = [float(np.sqrt((top[i:i + 4410] ** 2).mean())) for i in range(0, len(top) - 4410, 4410)]
    assert min(rms) > 0.5 * max(rms)
    n = 1 << 17
    S = np.abs(np.fft.rfft(top * np.hanning(len(top)), n))
    fr = np.fft.rfftfreq(n, 1 / rate)
    band = (fr > 700) & (fr < 880)
    assert abs(1200 * math.log2(fr[band][S[band].argmax()] / 783.99)) < 30   # in tune, up there
    import arrangement as A
    assert orchestra.RANGES["guitar_lead"][1] == A.pitch("G5")


def test_the_lead_guitar_is_kept_for_later_stages_and_plays_one_note_at_a_time():
    import arrangement as A
    s = {"tune": {"seed": "Test Hero", "cls": "Fighter"}, "tempo": 120, "statements": [],
         "key": "D4", "meter": "4/4", "length": 8, "chords": [[0, 8, "i"]],
         "harmony": [{"part": "guitar", "play": "root5", "range": ["D2", "D3"], "pattern": "x-  ", "step": 0.5}],
         "lines": [{"part": "guitar_lead", "notes": [[0, "D5", 1], [1, "D5", 0.5], [1.5, "D5", 0.5], [2, "Eb5", 2]]}]}
    warns = lambda sp: [m for lvl, m in A.check(sp, listen=False) if lvl == "warn" and "guitar" in m]
    assert any("later stages" in m for m in warns(dict(s, role="stage", stage=1)))   # a first stage: no
    assert not warns(dict(s, role="stage", stage=2))      # a later stage: yes - and no "mud" from its notes
    s["lines"][0]["notes"].append([2, "A4", 2])                         # a second voice
    assert any("one note at a time" in m for m in warns(dict(s, role="stage", stage=2)))
    s["lines"][0]["notes"][-1] = [4, "D5", 2, 0, {"slide": -2}]         # a falling bend: comic
    assert any("comic" in m for m in warns(dict(s, role="stage", stage=2)))



def test_the_loudness_meter_reads_as_bs1770_does():
    np = pytest.importorskip("numpy")
    rate = 48000
    t = np.arange(4 * rate) / rate
    for hz, lufs in ((1000, -20.0), (100, -21.8), (5000, -16.7)):  # (ffmpeg's ebur128, stereo sines)
        y = np.stack([0.1 * np.sin(2 * np.pi * hz * t)] * 2, axis=1)
        assert abs(orchestra.loudness(y, rate)["integrated"] - lufs) < 0.15, hz

# --- the real strings' short notes, the real brass ---
SHORT_PARTS = ["violins", "violins2", "cellos", "basses"]


def test_the_short_string_notes_and_the_brass_play_from_their_own_soundfonts():
    assert orchestra.EXTRA_FONTS["strings_short"] is orchestra.fetch_strings_short
    assert orchestra.EXTRA_FONTS["brass"] is orchestra.fetch_brass
    assert orchestra.EXTRA_FONTS["horn_solo"] is orchestra.fetch_horn_solo
    assert set(orchestra.STRINGS_SHORT) == set(SHORT_PARTS) and "pizzicato" not in orchestra.STRINGS_SHORT
    presets = [p for part in SHORT_PARTS for rr in orchestra.STRINGS_SHORT[part]["presets"] for p in rr]
    assert sorted(presets) == list(range(8))                          # two round-robins a part, each its own
    for part in ("horns", "trombones", "horn_solo"):
        assert orchestra.PARTS[part][4] == orchestra.OWN[part]["font"]
        assert orchestra.FALLBACK[part][0] == 0                       # (offline: the sound set's)
    assert orchestra.FALLBACK["horn_solo"] == orchestra.FALLBACK["horns"] == (0, 60)
    assert orchestra.FALLBACK["trombones"] == (0, 57)
    # the solo horn: a new part, levelled and placed as the horns, its own range
    assert orchestra.level_db("horn_solo") == orchestra.level_db("horns")
    assert orchestra.PARTS["horn_solo"][2:4] == orchestra.PARTS["horns"][2:4]
    assert orchestra.RANGES["horn_solo"] == orchestra.RANGES["horns"]
    # pinned sources, CC-licensed, credited
    assert re.search(r"/[0-9a-f]{40}/$", orchestra.VPO) and re.search(r"/[0-9a-f]{40}/$", orchestra.VSCO2_SFZ)
    credits = (Path(orchestra.__file__).parent / "CREDITS.md").read_text()
    for who in ("Sonatina Symphonic Orchestra", "VSCO 2", "Westlund", "No Budget Orchestra", "CC BY-SA 3.0",
                "CC BY-SA 4.0", "Sampling Plus 1.0", "CC0"):
        assert who in credits


def test_the_brass_sits_drier_than_the_strings():
    for part in ("horns", "horn_solo", "trombones", "tuba", "trumpets"):
        assert orchestra.part_send_db(part) == pytest.approx(orchestra.send_db(orchestra.ROOM.get(part)) - 6.0)
        if part in orchestra.OWN:                                    # (its own recordings: their own room)
            assert orchestra.part_send_db(part, own=True) == pytest.approx(orchestra.OWN[part]["send_db"] - 6.0)
    for part in ("violins", "cellos", "strings", "flutes"):
        assert orchestra.part_send_db(part) == orchestra.send_db(orchestra.ROOM.get(part))


def test_a_string_note_is_short_or_long_by_its_length():
    ev = []
    for t, length in ((0.0, 0.1), (1.0, orchestra.SHORT_S - 0.01), (2.0, orchestra.SHORT_S + 0.01), (3.0, 2.0)):
        ev += [(t, 1, "violins", 72, 100), (t + length, 0, "violins", 72, 0)]
    ev.append((5.0, 1, "violins", 74, 90))                             # never let go: long
    short, long_ = orchestra._split_short(ev)
    assert sorted(e[0] for e in short if e[1] == 1) == [0.0, 1.0]
    assert sorted(e[0] for e in long_ if e[1] == 1) == [2.0, 3.0, 5.0]
    assert len(short) + len(long_) == len(ev)


def _fake_synth(fonts):
    class Syn:                                                         # (records what plays)
        def generate(self, n):
            return bytes(8 * n)
    return lambda rate, sf2, need=(): (Syn(), 0, {f: 1 for f in need if f in fonts})


@pytest.mark.parametrize("have_font", [True, False])
def test_the_length_switch_picks_the_short_recordings_or_the_sustained_ones(monkeypatch, have_font):
    np = pytest.importorskip("numpy")
    played = []

    def stem(syn, sfid, fonts, name, events, total, rate, short=False):
        played.append((name, short, sorted(e[0] for e in events if e[1] == 1)))
        return total, np.zeros((0, 2), dtype="float32")
    monkeypatch.setattr(orchestra, "_synth", _fake_synth({"strings_short"} if have_font else set()))
    monkeypatch.setattr(orchestra, "_stem", stem)
    monkeypatch.setenv("GM_ORCHESTRA_WORKERS", "1")
    sc = orchestra.Score()
    for part in SHORT_PARTS + ["pizzicato", "strings"]:
        sc.note(part, 60, 1.0, 0.15, 100)                              # quick
        sc.note(part, 62, 2.0, 1.0, 100)                               # held
    sc.note("violins:4", 72, 3.0, 0.2, 100)                            # the tune's layer: quick too
    orchestra.play(sc, 4.0, rate=22050)
    got = {(n, s): ts for n, s, ts in played}
    for part in SHORT_PARTS:
        if have_font:
            early = orchestra.STRINGS_SHORT[part]["advance"]
            assert got[(part, True)] == [pytest.approx(1.0 - early)]   # its own, earlier start
            assert got[(part, False)] == [pytest.approx(2.0 - orchestra.ADVANCE.get(part, 0.0))]
        else:                                                          # offline: all sustained, as before
            assert (part, True) not in got and len(got[(part, False)]) == 2
    for part in ("pizzicato", "strings"):                              # (pizzicato stays as it is)
        assert (part, True) not in got and len(got[(part, False)]) == 2
    assert ("violins:4", True) in got if have_font else ("violins:4", False) in got


def test_the_own_brass_starts_as_its_recordings_speak_and_the_stand_in_as_before(monkeypatch):
    np = pytest.importorskip("numpy")
    for have in (True, False):
        played = {}

        def stem(syn, sfid, fonts, name, events, total, rate, short=False):
            played[name] = min(e[0] for e in events if e[1] == 1)
            return total, np.zeros((0, 2), dtype="float32")
        monkeypatch.setattr(orchestra, "_synth", _fake_synth({"brass", "horn_solo"} if have else set()))
        monkeypatch.setattr(orchestra, "_stem", stem)
        monkeypatch.setenv("GM_ORCHESTRA_WORKERS", "1")
        sc = orchestra.Score()
        for part in ("horns", "trombones", "horn_solo"):
            sc.note(part, 60, 1.0, 1.0, 100)
        orchestra.play(sc, 3.0, rate=22050)
        for part in ("horns", "trombones", "horn_solo"):
            early = orchestra.OWN[part]["advance"] if have else orchestra.ADVANCE.get(part, 0.0)
            assert played[part] == pytest.approx(1.0 - early)


@pytest.mark.parametrize("part", ["violins", "cellos", "horns", "trombones", "horn_solo"])
def test_the_new_recordings_fall_back_to_the_sound_set_offline(monkeypatch, capsys, part):
    pytest.importorskip("numpy")
    pytest.importorskip("tinysoundfont")
    if not orchestra.SF2.is_file():
        pytest.skip("the SoundFont isn't downloaded here")
    def offline(**_):
        raise OSError("offline")
    monkeypatch.setattr(orchestra, "EXTRA_FONTS", {k: offline for k in orchestra.EXTRA_FONTS})
    monkeypatch.setattr(orchestra, "_SYNTHS", {})
    monkeypatch.setenv("GM_ORCHESTRA_WORKERS", "1")
    sc = orchestra.Score()
    sc.note(part, 60, 0.2, 0.15, 100)                                  # (a quick note, for the strings)
    sc.note(part, 64, 1.0, 1.0, 100)
    out = orchestra.play(sc, 2.5, rate=22050)
    assert float(abs(out).max()) > 0.001                                # heard, not silent
    font = "strings_short" if part in orchestra.STRINGS_SHORT else orchestra.PARTS[part][4]
    assert f"no {font} (offline)" in capsys.readouterr().err           # said, with a warning


def test_an_sfz_is_read_with_what_its_regions_inherit_and_its_samples_kept_inside():
    import sf2write
    text = """// a comment
<control> default_path=Samples\\Violins\\
<global> volume=2 amp_random=1.5
<group> seq_length=2 seq_position=1 lokey=c4 hikey=d4
<region> sample=a b.wav pitch_keycenter=c#4 volume=4
<group> seq_length=2 seq_position=2
<region> sample=c.wav key=62 transpose=-1
"""
    a, b = sf2write.parse_sfz(text)
    assert a["sample"] == "a b.wav" and a["volume"] == "4" and a["amp_random"] == "1.5" and a["seq_position"] == "1"
    assert a["_default_path"] == "Samples\\Violins\\" and sf2write.sfz_key(a["pitch_keycenter"]) == 61
    assert b["seq_position"] == "2" and "lokey" not in b and b["volume"] == "2"
    assert orchestra._library_path("Strings", "..\\libs\\SSO\\Samples\\1st Violins\\x-PB.flac") == \
        "libs/SSO/Samples/1st Violins/x-PB.flac"
    for bad in ("..\\..\\etc\\passwd", "https://x/y.wav", "a/.hidden.wav", "a/b;rm.wav"):
        with pytest.raises(OSError):
            orchestra._library_path("Strings", bad)


def test_the_short_strings_soundfont_is_built_from_the_sfz_and_its_recordings(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    tsf = pytest.importorskip("tinysoundfont")
    sfmod = pytest.importorskip("soundfile")
    import io
    import sf2write
    rate = 44100

    def wav(freq, secs=0.6):
        t = np.arange(int(secs * rate)) / rate
        x = 0.5 * np.sin(2 * np.pi * freq * t) * np.exp(-4 * t)
        buf = io.BytesIO()
        sfmod.write(buf, np.stack([x, 0.8 * x], 1), rate, format="WAV", subtype="PCM_16")
        return buf.getvalue()
    sfz = """<group> amp_random=1.5 seq_length=2 ampeg_release=2
<region> sample=..\\libs\\S\\a.flac lokey=50 hikey=70 pitch_keycenter=57 seq_position=1 volume=3
<region> sample=..\\libs\\S\\b.flac lokey=50 hikey=70 pitch_keycenter=57 seq_position=2 transpose=-1 lovel=1 hivel=127
"""
    asked = []

    def download(url, cap):
        asked.append(url)
        if url.endswith(".sfz"):
            return sfz.encode()
        return wav(220.0 if "a.flac" in url else 233.08)
    monkeypatch.setattr(orchestra, "_download", download)
    out = orchestra.fetch_strings_short(dest=tmp_path / "s.sf2", quiet=True)
    assert all(u.startswith(orchestra.VPO) for u in asked)
    assert {u.rsplit("/", 1)[-1] for u in asked if not u.endswith(".sfz")} == {"a.flac", "b.flac"}
    samples = sf2write.read_samples(out)
    assert len(samples) == 8 * 2 - 4                                   # stereo pairs (violins, violas), mono (cellos, basses)
    syn = tsf.Synth(samplerate=rate)
    sid = syn.sfload(str(out))
    for preset, freq in ((0, 220.0), (1, 220.0)):                     # rr2: b (A#3) a semitone down, as its SFZ says
        syn.program_select(0, sid, 0, preset)
        syn.noteon(0, 57, 100)
        x = np.frombuffer(syn.generate(rate // 2), dtype="float32").reshape(-1, 2)[:, 0]
        syn.sounds_off(0)
        syn.generate(256)
        spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x))))
        assert abs(np.argmax(spectrum) * rate / len(x) - freq) < 4


@pytest.fixture
def new_fonts():
    pytest.importorskip("numpy")
    pytest.importorskip("tinysoundfont")
    if not orchestra.SF2.is_file():
        pytest.skip("the SoundFont isn't downloaded here")
    for path, fetch in ((orchestra.STRINGS_SHORT_SF2, "fetch_strings_short"), (orchestra.BRASS_SF2, "fetch_brass"),
                        (orchestra.HORN_SOLO_SF2, "fetch_horn_solo")):
        if not path.is_file():
            pytest.skip(f"{path.name} isn't built here (orchestra.{fetch})")


def _level(np, y, a, b, rate):
    return 20 * np.log10(float(np.sqrt(np.mean(np.asarray(y[int(a * rate):int(b * rate)], dtype="float64") ** 2))) + 1e-12)


def _peak(np, y, t, rate, span=0.6, win=0.05, median=False):
    n = int(win * rate)
    seg = np.asarray(y[int(t * rate):int((t + span) * rate)], dtype="float64")
    e = np.convolve((seg ** 2).sum(axis=1), np.ones(n) / n, mode="valid")
    return 10 * np.log10(float(np.median(e) if median else e.max()) + 1e-20)


@pytest.mark.parametrize("part,key", [("violins", 71), ("violins2", 64), ("cellos", 47), ("basses", 35)])
def test_a_short_string_note_speaks_at_once_and_stands_with_the_long_ones(new_fonts, part, key):
    np = pytest.importorskip("numpy")
    rate = 44100
    def play(length):
        sc = orchestra.Score()
        sc.note(part, key, 0.5, length, 100)
        return np.asarray(orchestra.play(sc, 3.0, rate=rate, align=False))
    short, long_, over = play(0.15), play(2.5), play(orchestra.SHORT_S + 0.05)
    # as loud, at its peak, as a long note holds at the same velocity (the sound set's 0.15 s
    # note: 4.5-8.4 dB under), and within 9 dB of its peak in 0.08 s (the sound set's: 0.16 s)
    assert abs(_peak(np, short, 0.5, rate) - _peak(np, long_, 1.2, rate, 1.2, median=True)) < 2.0
    def speaks(y):
        n = int(0.01 * rate)
        seg = (np.asarray(y[int(0.5 * rate):int(1.1 * rate)], dtype="float64") ** 2).sum(axis=1)
        e = 10 * np.log10(np.convolve(seg, np.ones(n) / n, mode="valid") + 1e-20)
        return int(np.argmax(e >= e.max() - 9)) / rate
    assert speaks(short) < 0.08
    if part == "violins":                                              # (just over: the sustained ones)
        assert speaks(over) > 0.1
    # the same place: L/R balance and width as the long notes', over its range
    def place(length):
        sc = orchestra.Score()
        for i, k in enumerate(range(key - 12, key + 13, 6)):
            sc.note(part, k, 0.5 + 3 * i, length, 100)
        L, R = np.asarray(orchestra.play(sc, 15.5, rate=rate, align=False), dtype="float64").T
        return 10 * np.log10((L ** 2).sum() / (R ** 2).sum()), float((L * R).sum() / np.sqrt((L ** 2).sum() * (R ** 2).sum()))
    (b1, c1), (b2, c2) = place(0.2), place(2.0)
    assert abs(b1 - b2) < 1.5 and abs(c1 - c2) < 0.2                 # (matched over all its range)


def test_the_own_brass_and_the_solo_horn_sound_where_the_horns_stood(new_fonts):
    np = pytest.importorskip("numpy")
    rate = 44100
    for part, key in (("horns", 62), ("trombones", 50), ("horn_solo", 66)):
        sc = orchestra.Score()
        sc.note(part, key, 0.3, 1.5, 100)
        y = orchestra.play(sc, 3.0, rate=rate)
        L, R = np.asarray(y, dtype="float64").T
        assert float(abs(np.asarray(y)).max()) > 0.01, part
        assert float(np.corrcoef(L, R)[0, 1]) > 0.99, part              # one microphone, panned
        pan = orchestra.PARTS[part][2]
        assert (L ** 2).sum() < (R ** 2).sum() if pan > 64 else True, part
        # its hall: the brass drier (the send under the dry mix)
        assert float(np.abs(y.send).max()) < float(np.abs(np.asarray(y)).max()), part


def test_an_arrangement_plays_the_solo_horn_over_the_brass(new_fonts):
    import arrangement as A
    s = {"tune": {"seed": "Test Hero", "cls": "Fighter"}, "tempo": 100, "length": 8,
         "melody": [{"from": 0, "to": 8, "parts": {"horn_solo": 0}}],
         "chords": [[0, 1000, "I"]], "harmony": [{"part": "trombones", "play": "chord", "range": ["C3", "C4"]}]}
    score, _, _ = A.build(s)
    assert any(p.startswith("horn_solo:") for _, _, p, _, _ in score.events)   # the tune's lift, as any carrier
    assert not [m for lvl, m in A.check(s, listen=False) if lvl == "error"]
    samples, rate = A.render(s, rate=22050)
    assert float(abs(samples).max()) > 0.05
