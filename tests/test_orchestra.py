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


@pytest.mark.parametrize("part", ["men_choir", "chorus", "choir_oo", "choir_oh"])
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
