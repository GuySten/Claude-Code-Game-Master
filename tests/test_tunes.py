"""Characters' tunes (the leitmotif generator) and the audio helpers the orchestra's
pieces go through (lib/music/music_compose.py)."""

import pytest

from lib import score_music


CLASSES = ["Fighter", "Paladin", "Barbarian", "Rogue", "Bard", "Wizard", "Sorcerer", "Warlock",
           "Cleric", "Druid", "Ranger", "Monk", "Artificer", ""]
PEOPLE = [("Pip", "Rogue"), ("Bram", "Fighter"), ("רן", "Warlock"), ("ג'ון סמיט", ""), ("Zoë", "Bard"),
          ("קסטרל", "Ranger")] + [(f"Hero {i}", CLASSES[i % len(CLASSES)]) for i in range(400)]


def test_only_one_takes_the_graphics_card_at_a_time(tmp_path, monkeypatch):
    import threading
    import time
    import gpu_turn
    monkeypatch.setattr(gpu_turn, "LOCK_PATH", tmp_path / "gpu.lock")
    order = []

    def use(who, hold):
        with gpu_turn.gpu_turn(who):
            order.append(who + " on")
            time.sleep(hold)
            order.append(who + " off")

    t = threading.Thread(target=use, args=("first", 0.5))
    t.start()
    time.sleep(0.1)
    use("pictures", 0)
    t.join()
    assert order == ["first on", "first off", "pictures on", "pictures off"]
    # Never stuck forever: past the wait limit it goes ahead.
    with gpu_turn.gpu_turn("a") as a, gpu_turn.gpu_turn("b", wait=0.3) as b:
        assert a.held and not b.held


def test_a_piece_is_brought_up_to_a_steady_loudness_without_clipping():
    np = pytest.importorskip("numpy")
    from lib import music_compose as mc
    rate = 32000
    t = np.arange(rate * 10) / rate
    quiet = (0.02 * np.sin(2 * np.pi * 220 * t)).astype("float32")     # very quiet
    quiet[rate * 3: rate * 3 + 400] += 0.25                             # with a drum hit
    assert mc.loudness_db(quiet, rate) < -30
    out = mc.normalize(quiet, rate)
    assert -16 < mc.loudness_db(out, rate) < -13                        # ~20 dB louder
    assert float(np.abs(out).max()) <= mc.CEILING + 1e-6                # and never clips
    loud = (0.9 * np.sin(2 * np.pi * 220 * t)).astype("float32")
    assert abs(mc.loudness_db(mc.normalize(loud, rate), rate) - mc.LOUDNESS_DB) < 0.5   # turned down too
    assert not np.abs(mc.normalize(np.zeros(500, "float32"), rate)).any()               # silence stays silent
    theme = mc.finish(quiet, rate, loop=True)
    assert theme[0] == 0 and abs(theme[-1]) < 1e-3                      # still fades at the seam


def test_every_name_gets_its_own_music_file():
    # Hebrew names used to all come out as "piece": three PCs shared one anthem file.
    names = ["קסטרל", "לגולס", "איזרין צל הלילה", "Pip", "Grimaldi the Grey", "Zoë"]
    stems = [score_music.slug(n) for n in names]
    assert len(set(stems)) == len(names)
    assert score_music.slug("Pip") == "pip" and score_music.slug("Grimaldi the Grey") == "grimaldi-the-grey"
    assert score_music.slug("קסטרל") == score_music.slug("קסטרל")          # stable across runs
    assert all(s and all(c.isascii() for c in s) for s in stems)      # still safe in a URL


def test_the_dark_twin_is_the_same_music_slower_lower_and_muffled():
    np = pytest.importorskip("numpy")
    from lib import music_compose as mc
    rate = 32000
    t = np.arange(rate * 2) / rate
    tune = (0.3 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.sin(2 * np.pi * 6000 * t)).astype("float32")
    dark = mc.darken(tune, rate)
    assert abs(len(dark) / rate - 2 / 0.84) < 0.05                    # slower
    spec = np.abs(np.fft.rfft(dark[: rate])); freqs = np.fft.rfftfreq(rate, 1 / rate)
    assert abs(freqs[spec.argmax()] - 440 * 0.84) < 5                   # lower: ~3 semitones down
    peak = lambda s, f, hz: s[(f > hz - 30) & (f < hz + 30)].max()      # noqa: E731
    before = np.abs(np.fft.rfft(tune[: rate]))
    was = peak(before, freqs, 6000) / peak(before, freqs, 440)          # the bright overtone, before
    now = peak(spec, freqs, 6000 * 0.84) / peak(spec, freqs, 440 * 0.84)
    assert now < was / 10                                               # muffled


def test_every_heroes_tune_is_built_like_a_film_heroes_theme():
    """A rise of a 5th or more to the opening's peak, gap-fill after it, a held
    climax around two-thirds in, a singable range, home to the tonic on a bar line."""
    from lib import music_compose as mc
    for name, cls in PEOPLE:
        t = mc.theme_traits(mc.leitmotif(name, "major", cls))
        assert t["rise"] >= 5 and t["gap_fill"], (name, cls, t)
        assert 0.4 <= t["climax_at"] <= 0.75 and t["climax_held"], (name, cls, t)
        assert t["range"] <= 19 and t["biggest_jump"] <= 12, (name, cls, t)
        assert t["ends_home"] and t["whole_bars"], (name, cls, t)
        assert t["hook_repeats"] >= 5 and t["single_climax"], (name, cls, t)   # memorable: A A B A
    assert mc.leitmotif("Pip", "major", "Rogue")["notes"] == mc.leitmotif(" pip ", "major", "Rogue")["notes"]


def test_every_villains_tune_is_the_same_tune_turned_menacing():
    """Minor, a march of repeated notes, half-step sighs, a tritone, falling home
    through the minor 2nd; and still the hero's tune: the same motif, key and meter."""
    from lib import music_compose as mc
    for name, cls in PEOPLE:
        hero, dark = mc.leitmotif(name, "major", cls), mc.leitmotif(name, "minor", cls)
        t = mc.theme_traits(dark)
        assert t["minor"] and t["repeated"] and t["tritone"] and t["sighs"] >= 3, (name, cls, t)
        assert t["falls_home"] and t["ends_home"] and dark["notes"][-2][0] == 1, (name, cls, t)
        assert t["range"] <= 19 and t["biggest_jump"] <= 12 and t["whole_bars"], (name, cls, t)
        assert 0.4 <= t["climax_at"] <= 0.75 and t["hook_repeats"] >= 3, (name, cls, t)
        assert dark["shape"] == hero["shape"] and (dark["key"], dark["meter"]) == (hero["key"], hero["meter"])


def test_no_two_characters_share_a_tune():
    """Different kinds, meters and modes: the tunes of different characters differ in
    their shape and their rhythm (the first version gave 60 names 18 shapes)."""
    import difflib
    import itertools
    from lib import music_compose as mc

    def shape(name, cls):
        notes = mc.leitmotif(name, "major", cls)["notes"]
        p = [x for x, _ in notes]
        contour = tuple("U" if b - a > 2 else "u" if b > a else "=" if b == a else "d" if a - b <= 2 else "D"
                        for a, b in zip(p, p[1:]))
        return contour, tuple(round(b, 2) for _, b in notes), tuple(b - a for a, b in zip(p, p[1:]))
    people = PEOPLE[:60]
    shapes = [shape(*p) for p in people]
    assert len({(i, r) for _, r, i in shapes}) == len(people)                 # no two the same tune (any key)
    shapes = [(c, r) for c, r, _ in shapes]
    assert len({c for c, _ in shapes}) >= 50                                  # nor mostly the same shape
    alike = [(difflib.SequenceMatcher(None, a[0], b[0]).ratio(), difflib.SequenceMatcher(None, a[1], b[1]).ratio())
             for a, b in itertools.combinations(shapes, 2)]
    assert sum(c for c, _ in alike) / len(alike) < 0.6 and sum(r for _, r in alike) / len(alike) < 0.5


def test_the_class_picks_the_kind_of_theme():
    from lib import music_compose as mc
    wizards = [mc.leitmotif(f"Mage {i}", "major", "Wizard") for i in range(30)]
    assert all(w["scale"] == "lydian" for w in wizards)                 # wonder: the raised 4th
    assert any(6 in {p % 12 for p, _ in w["notes"]} for w in wizards)
    assert all(mc.leitmotif(f"Rogue {i}", "major", "Rogue")["meter"] == "6/8" for i in range(30))
    assert {mc.leitmotif(f"Knight {i}", "major", "Fighter")["kind"] for i in range(30)} <= {"fanfare", "bugle"}
    kinds = {mc.leitmotif(f"Someone {i}")["kind"] for i in range(60)}          # no class: any kind
    assert kinds == set(mc.KINDS)


def test_a_tune_renders_as_a_melody_line():
    pytest.importorskip("numpy")
    from lib import music_compose as mc
    for mode, s in (("major", 20), ("minor", 30)):
        line = mc.render_leitmotif("Pip", mode, s)
        assert abs(len(line) / 32000 - s) < 0.01 and float(abs(line).max()) > 0.1


def test_one_of_the_most_memorable_candidate_tunes_is_kept():
    """Each character's tune is one of the best of twelve on memorability (its hook
    heard again and again, a strong opening rise, an arch to one climax, mostly
    steps), and keeps every hard rule."""
    import hashlib
    import random
    from lib import music_compose as mc
    for name, cls in PEOPLE[:40]:
        tune = mc.leitmotif(name, "major", cls)
        seed_hex = hashlib.sha256(name.strip().lower().encode("utf-8")).hexdigest()
        rng = random.Random(seed_hex)
        rng.randrange(10)
        kinds, meters, modes = mc._style(cls)
        found = mc._candidates(seed_hex, rng.choice(kinds), rng.choice(meters), rng.choice(modes))
        best = max(sc for sc, _, _ in found)
        assert len(found) == mc.CANDIDATES and tune["memorability"] >= best - .5 - 1e-9, (name, tune["memorability"], best)
        assert tune["memorability"] >= 7, (name, cls, tune["memorability"])


def test_the_theme_follows_the_characters_story():
    """The hook never changes; the stage reshapes the tune (a lone voice, the theme,
    heroic, legendary); dark deeds borrow darker notes, one by one."""
    from lib import music_compose as mc
    for name, cls in PEOPLE[:30]:
        by_stage = [mc.leitmotif(name, "major", cls, stage=s) for s in range(4)]
        traits = [mc.theme_traits(t) for t in by_stage]
        for t in traits:
            assert t["whole_bars"] and t["ends_home"] and t["biggest_jump"] <= 12 and t["range"] <= 22, (name, t)
        seed, full = by_stage[0], by_stage[1]
        hook_at, hook_len = full["hook"]
        assert seed["notes"][hook_at:hook_at + hook_len] == full["notes"][hook_at:hook_at + hook_len]  # same hook
        assert traits[0]["hook_repeats"] >= 2 and len(seed["notes"]) < len(full["notes"])          # a lone voice
        assert max(p for p, _ in by_stage[2]["notes"]) > max(p for p, _ in full["notes"])         # reaching higher
        assert sum(b for _, b in by_stage[3]["notes"]) > sum(b for _, b in by_stage[2]["notes"])   # the legend's end
        pcs = [{p % 12 for p, _ in mc.leitmotif(name, "major", cls, stage=1, dark=d)["notes"]} for d in range(4)]
        darker = [len(pc & {1, 3, 8, 10}) for pc in pcs]                    # the dark notes it uses
        assert darker == sorted(darker) and darker[3] > darker[0], (name, cls, darker)
