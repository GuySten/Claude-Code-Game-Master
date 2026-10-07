"""Composed music: the bridge to the composer's own environment."""

import json
import os
import sys

import pytest

from lib import composer

# Stands in for `music_compose.py --serve`: "loads the model" once, says it's ready,
# then answers one JSON job per line. It reports whether the graphics-card turn
# was held while it composed.
FAKE_SERVER = (
    "import argparse, json, os, pathlib, sys, time\n"
    "ap = argparse.ArgumentParser(); ap.add_argument('--serve', action='store_true'); ap.parse_args()\n"
    "log = pathlib.Path(os.environ['FAKE_LOG']); log.write_text(log.read_text() + 'load\\n')\n"
    "print('loading model...', file=sys.stderr, flush=True)\n"
    "if os.environ.get('FAKE_BROKEN'):\n"
    "    print('CUDA error: no kernel image is available', file=sys.stderr); sys.exit(1)\n"
    "def card_held():\n"
    "    if os.name == 'nt': return None\n"
    "    import fcntl\n"
    "    with open(os.environ['GPU_LOCK_FILE'], 'a+') as f:\n"
    "        try: fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
    "        except OSError: return True\n"
    "        fcntl.flock(f, fcntl.LOCK_UN); return False\n"
    "device = os.environ.get('COMPOSE_DEVICE') or os.environ.get('FAKE_DEVICE', 'cuda')\n"
    "print(json.dumps({'ready': True, 'device': device}), flush=True)\n"
    "for line in sys.stdin:\n"
    "    job = json.loads(line)\n"
    "    if 'HANG' in job['prompt']: time.sleep(60)\n"
    "    if 'DIE' in job['prompt']: sys.exit(3)\n"
    "    if os.environ.get('CRASH_ON_GPU') and device != 'cpu':\n"
    "        print('[compose] composing 5 s on cuda', file=sys.stderr, flush=True); os._exit(139)\n"
    "    if 'FAIL' in job['prompt']:\n"
    "        print(json.dumps({'ok': False, 'id': job['id'], 'error': 'RuntimeError: boom'}), flush=True); continue\n"
    "    p = pathlib.Path(job['out']); p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b'OggS')\n"
    "    extra = {'melody_from': job.get('melody_from')}\n"
    "    if job.get('twin'):\n"
    "        t = pathlib.Path(job['twin']['out']); t.write_bytes(b'OggS dark')\n"
    "        extra['twin'] = {'path': str(t), 'seconds': 24.0, 'how': 'darkened', 'prompt': job['twin']['prompt']}\n"
    "    print(json.dumps({'ok': True, 'id': job['id'], 'path': str(p), 'seconds': float(job['seconds']),\n"
    "                      'loop': job['loop'], 'prompt': job['prompt'], 'device': 'cuda', 'elapsed': 1,\n"
    "                      'card_held': card_held(), **extra}), flush=True)\n")


def fake_composer(tmp_path, monkeypatch, mod=composer):
    """Point ``mod`` (lib.composer, or the table's own ``composer``) at FAKE_SERVER.
    Returns the file that counts model loads and the list of Forge release calls."""
    import gpu_turn
    fake = tmp_path / "fake_server.py"
    fake.write_text(FAKE_SERVER)
    log = tmp_path / "loads.txt"
    log.write_text("")
    lock = tmp_path / "gpu.lock"
    monkeypatch.setattr(gpu_turn, "LOCK_PATH", lock)
    monkeypatch.setenv("GPU_LOCK_FILE", str(lock))
    monkeypatch.setenv("FAKE_LOG", str(log))
    monkeypatch.setattr(mod, "SCRIPT", fake)
    monkeypatch.setattr(mod, "SERVER_LOG", tmp_path / "composer.log")
    monkeypatch.setattr(mod, "composer_python", lambda: sys.executable)
    monkeypatch.setattr(mod, "_cpu_only", False)
    monkeypatch.delenv("COMPOSE_DEVICE", raising=False)
    released = []
    monkeypatch.setattr(mod, "_free_the_card", lambda: released.append(True))
    mod.stop_server()
    return log, released


@pytest.fixture
def fake(tmp_path, monkeypatch):
    log, released = fake_composer(tmp_path, monkeypatch)
    yield log, released
    composer.stop_server()


def test_compose_runs_the_composer_and_reads_its_answer(tmp_path, fake):
    camp = tmp_path / "camp"
    camp.mkdir()
    (camp / "campaign-overview.json").write_text(json.dumps({"genre": "dark fantasy", "tone": "grim"}))

    f = composer.compose_theme(camp, "Grimaldi", boss=True, look="rotting ringmaster")
    assert f == "grimaldi-boss.ogg" and (camp / "music" / "themes" / f).is_file()
    assert composer.theme_file(camp, "grimaldi", boss=True) == f
    assert composer.theme_file(camp, "Grimaldi", boss=False) == f       # the only one there is
    assert composer.has_theme(camp, "Grimaldi", True) and not composer.has_theme(camp, "Grimaldi", False)

    rec = composer.compose_anthem(camp, {"name": "Pip", "race": "Halfling", "class": "Rogue"})
    assert rec == {"file": "anthem-pip.ogg", "seconds": 16.0, "version": "s0-d0-w0-b0",  # a new character:
                   "versions": {"s0-d0-w0-b0": {"file": "anthem-pip.ogg", "seconds": 16.0}},  # a lone voice
                   "dark": "anthem-pip-dark.ogg", "dark_how": "darkened"}        # (with its dark twin)
    assert composer.anthem(camp, "PIP") == rec

    prompt = composer.theme_prompt("Grimaldi", "rotting ringmaster", composer.flavor(camp), True)
    assert "boss battle" in prompt and "dark fantasy, grim" in prompt and "rotting ringmaster" in prompt
    assert "heroic character theme for Pip, a Halfling Rogue" in composer.anthem_prompt(
        {"name": "Pip", "race": "Halfling", "class": "Rogue"}, "")


def test_the_model_is_read_once_and_waits_in_ram_between_pieces(tmp_path, fake):
    log, released = fake
    camp = tmp_path / "camp"
    camp.mkdir()
    seen = []

    def landed(piece, f):
        seen.append((piece.get("name") or piece["sheet"]["name"], f))
        # registered at once, while the rest are still to come
        assert composer.theme_file(camp, "Grimaldi", True) == "grimaldi-boss.ogg"

    pieces = [{"kind": "theme", "name": "Grimaldi", "boss": True, "look": "a rotting ringmaster"},
              {"kind": "anthem", "sheet": {"name": "Pip", "race": "Halfling", "class": "Rogue"}},
              {"kind": "anthem", "sheet": {"name": "Bram", "race": "Dwarf", "class": "Fighter"}}]
    assert composer.compose_pieces(camp, pieces, landed) == ["grimaldi-boss.ogg", "anthem-pip.ogg",
                                                             "anthem-bram.ogg"]
    assert seen == [("Grimaldi", "grimaldi-boss.ogg"), ("Pip", "anthem-pip.ogg"), ("Bram", "anthem-bram.ogg")]
    assert composer.anthem(camp, "bram")["file"] == "anthem-bram.ogg"
    # Later music: the same composer, the model still in RAM, nothing read from disk.
    composer.compose_theme(camp, "Lich", boss=False)
    assert log.read_text() == "load\n"
    # Each piece had the graphics card to itself, with Forge's model moved off it first.
    assert len(released) == 4
    r = composer.compose("x", 5, tmp_path / "x.ogg")
    if os.name != "nt":
        assert r["card_held"] is True


def test_on_a_cpu_forge_keeps_the_card(tmp_path, fake, monkeypatch):
    _, released = fake
    monkeypatch.setenv("FAKE_DEVICE", "cpu")
    composer.compose("x", 5, tmp_path / "x.ogg")
    assert released == []


def test_a_failed_piece_a_crash_or_a_hang_doesnt_sink_the_rest(tmp_path, fake):
    log, _ = fake
    out = lambda n: str(tmp_path / f"{n}.ogg")                          # noqa: E731
    got = composer.compose_many([{"prompt": "FAIL", "seconds": 5, "out": out("a"), "loop": False},
                                 {"prompt": "fine", "seconds": 5, "out": out("b"), "loop": False}])
    assert got[0] is None and got[1]["path"] == out("b")
    # The composer dies mid-way: it's started again for the next piece.
    got = composer.compose_many([{"prompt": "DIE", "seconds": 5, "out": out("c"), "loop": False},
                                 {"prompt": "fine", "seconds": 5, "out": out("d"), "loop": False}])
    # (the dead piece got one more try on the CPU, in vain: three loads)
    assert got[0] is None and got[1]["path"] == out("d") and log.read_text() == "load\nload\nload\n"
    assert composer._cpu_only is True
    # It hangs: stopped after the time limit, and the next piece still comes.
    got = composer.compose_many([{"prompt": "HANG", "seconds": 5, "out": out("e"), "loop": False},
                                 {"prompt": "fine", "seconds": 5, "out": out("f"), "loop": False}],
                                timeout_each=2)
    assert got[0] is None and got[1]["path"] == out("f")
    with pytest.raises(composer.ComposeError, match="boom"):
        composer.compose("FAIL", 5, tmp_path / "x.ogg")
    assert composer.compose_many([]) == []


def test_a_composer_that_dies_on_the_graphics_card_carries_on_on_the_cpu(tmp_path, fake, monkeypatch, capsys):
    log, _ = fake
    monkeypatch.setenv("CRASH_ON_GPU", "1")
    got = composer.compose_many([{"prompt": "a waltz", "seconds": 5, "out": str(tmp_path / "a.ogg"), "loop": False},
                                 {"prompt": "a march", "seconds": 5, "out": str(tmp_path / "b.ogg"), "loop": False}])
    assert got[0] and got[1] and got[0]["path"] == str(tmp_path / "a.ogg")   # both came, on the CPU
    assert composer._cpu_only is True and log.read_text() == "load\nload\n"  # restarted once
    said = capsys.readouterr().err
    assert "stopped while composing piece 1" in said and "composing on the CPU from now on" in said


def test_a_broken_composer_says_why(tmp_path, fake, monkeypatch):
    monkeypatch.setenv("FAKE_BROKEN", "1")
    with pytest.raises(composer.ComposeError, match="no kernel image"):
        composer.compose("x", 5, tmp_path / "x.ogg")


def test_no_composer_no_music_jobs(monkeypatch):
    monkeypatch.setenv("MUSIC_COMPOSE", "off")
    assert composer.composer_python() is None and not composer.available()
    assert composer.start_server() is False
    with pytest.raises(composer.ComposeError, match="isn't set up"):
        composer.compose("x", 5, composer.PROJECT_ROOT / "nowhere.ogg")


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

    t = threading.Thread(target=use, args=("music", 0.5))
    t.start()
    time.sleep(0.1)
    use("pictures", 0)
    t.join()
    assert order == ["music on", "music off", "pictures on", "pictures off"]
    # Never stuck forever: past the wait limit it goes ahead.
    with gpu_turn.gpu_turn("a") as a, gpu_turn.gpu_turn("b", wait=0.3) as b:
        assert a.held and not b.held


def test_composed_music_is_brought_up_to_a_steady_loudness_without_clipping():
    np = pytest.importorskip("numpy")
    from lib import music_compose as mc
    rate = 32000
    t = np.arange(rate * 10) / rate
    quiet = (0.02 * np.sin(2 * np.pi * 220 * t)).astype("float32")     # MusicGen-quiet
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
    stems = [composer.slug(n) for n in names]
    assert len(set(stems)) == len(names)
    assert composer.slug("Pip") == "pip" and composer.slug("Grimaldi the Grey") == "grimaldi-the-grey"
    assert composer.slug("קסטרל") == composer.slug("קסטרל")          # stable across runs
    assert all(s and all(c.isascii() for c in s) for s in stems)      # still safe in a URL


def test_an_anthem_comes_with_its_dark_twin_ready_for_a_fall(tmp_path, fake):
    camp = tmp_path / "camp"
    camp.mkdir()
    composer.compose_pieces(camp, [{"kind": "anthem", "sheet": {"name": "Pip", "class": "Rogue"}}])
    rec = composer.anthem(camp, "Pip")
    assert rec["file"] == "anthem-pip.ogg" and rec["dark"] == "anthem-pip-dark.ogg" and rec["dark_how"] == "darkened"
    assert composer.dark_anthem(camp, "Pip").read_bytes() == b"OggS dark"
    # Pip falls (lost to madness): the dark twin is their villain theme, at once.
    assert composer.villain_theme_from_anthem(camp, "Pip") == "pip-theme.ogg"
    assert composer.theme_file(camp, "Pip", False) == "pip-theme.ogg"
    assert composer.villain_theme_from_anthem(camp, "Nobody") is None


def test_a_dark_anthem_made_later_is_the_twin_of_the_heroic_one(tmp_path, fake):
    camp = tmp_path / "camp"
    (camp / "music" / "anthems").mkdir(parents=True)
    (camp / "music" / "anthems" / "anthem-bram.ogg").write_bytes(b"OggS heroic")
    composer.save_registry(camp, {"themes": {}, "anthems": {"Bram": {"file": "anthem-bram.ogg", "seconds": 20}}})
    got = []
    composer.compose_pieces(camp, [{"kind": "dark_anthem", "name": "Bram", "sheet": {"name": "Bram"}}],
                            lambda p, f: got.append(f))
    assert got == ["bram-theme.ogg"] and composer.theme_file(camp, "Bram", False) == "bram-theme.ogg"
    rec = composer.compose("x", 5, camp / "x.ogg", melody_from=str(camp / "music" / "anthems" / "anthem-bram.ogg"))
    assert rec["melody_from"].endswith("anthem-bram.ogg")            # the heroic one's music, made dark


def test_the_laptop_composes_the_twin_too(tmp_path, monkeypatch):
    import base64
    import gpu_remote
    sent = []

    def run(kind, payload, timeout=0):
        sent.append(payload)
        return {"audio": base64.b64encode(b"hero").decode(), "ext": ".ogg", "seconds": 20,
                "twin_audio": base64.b64encode(b"villain").decode(), "twin_ext": ".ogg", "twin_how": "melody"}
    monkeypatch.setattr(gpu_remote, "run", run)
    monkeypatch.setattr(composer, "remote", lambda: True)
    src = tmp_path / "old.ogg"
    src.write_bytes(b"old anthem")
    r = composer.compose_many([{"prompt": "hero", "seconds": 20, "out": str(tmp_path / "a.ogg"), "loop": False,
                                "twin": {"prompt": "dark", "out": str(tmp_path / "a-dark.ogg")},
                                "melody_from": str(src)}])[0]
    assert sent[0]["twin_prompt"] == "dark" and base64.b64decode(sent[0]["melody_audio"]) == b"old anthem"
    assert (tmp_path / "a-dark.ogg").read_bytes() == b"villain" and r["twin"]["how"] == "melody"


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


def test_a_composer_job_writes_the_piece_and_its_twin(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    from lib import music_compose as mc
    rate = 32000
    tone = (0.2 * np.sin(2 * np.pi * 330 * np.arange(rate * 3) / rate)).astype("float32")
    monkeypatch.setattr(mc, "generate", lambda prompt, seconds, device: (tone, rate, device))
    monkeypatch.setattr(mc, "TWIN", "melody")
    monkeypatch.setattr(mc, "_load_melody", lambda: (_ for _ in ()).throw(OSError("not downloaded")))
    r = mc.run_job({"prompt": "hero", "seconds": 3, "out": str(tmp_path / "h.wav"),
                    "twin": {"prompt": "dark", "out": str(tmp_path / "d.wav"), "loop": True}}, "cpu")
    assert r["ok"] and r["twin"]["how"] == "darkened"                  # the melody model failed: darkened
    assert sf.info(r["twin"]["path"]).duration > sf.info(r["path"]).duration
    again = mc.run_job({"prompt": "dark", "seconds": 3, "out": str(tmp_path / "v.wav"), "loop": True,
                        "melody_from": r["path"]}, "cpu")
    assert again["ok"] and again["how"] == "darkened"


def test_twins_use_the_melody_model_only_when_its_there_and_on_a_gpu(monkeypatch):
    from lib import music_compose as mc
    monkeypatch.setattr(mc, "TWIN", "auto")
    monkeypatch.setattr(mc, "melody_ready", lambda: True)
    assert mc.twin_mode("cuda") == "melody" and mc.twin_mode("cpu") == "darken"
    monkeypatch.setattr(mc, "melody_ready", lambda: False)             # not downloaded: no surprise download
    assert mc.twin_mode("cuda") == "darken"
    monkeypatch.setattr(mc, "TWIN", "melody")
    assert mc.twin_mode("cpu") == "melody"                              # asked for: always tried


CLASSES = ["Fighter", "Paladin", "Barbarian", "Rogue", "Bard", "Wizard", "Sorcerer", "Warlock",
           "Cleric", "Druid", "Ranger", "Monk", "Artificer", ""]
PEOPLE = [("Pip", "Rogue"), ("Bram", "Fighter"), ("רן", "Warlock"), ("ג'ון סמיט", ""), ("Zoë", "Bard"),
          ("קסטרל", "Ranger")] + [(f"Hero {i}", CLASSES[i % len(CLASSES)]) for i in range(400)]


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


def test_anthems_are_composed_on_the_leitmotif_with_the_melody_model(tmp_path, fake):
    camp = tmp_path / "camp"
    camp.mkdir()
    seen = []
    real = composer.compose_many
    composer.compose_many = lambda jobs, *a, **k: seen.extend(jobs) or real(jobs, *a, **k)
    try:
        composer.compose_pieces(camp, [{"kind": "anthem", "sheet": {"name": "Pip", "class": "Rogue"}}])
    finally:
        composer.compose_many = real
    assert seen[0]["leitmotif"] == {"seed": "Pip", "mode": "major", "cls": "Rogue", "stage": 1, "dark": 0,
                                    "wound": False}
    assert seen[0]["twin"]["leitmotif"] == {"seed": "Pip", "mode": "minor", "cls": "Rogue"}
    assert "memorable melody" in seen[0]["prompt"]


def test_a_composer_job_follows_the_leitmotif_or_composes_freely(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    pytest.importorskip("soundfile")
    from lib import music_compose as mc
    tone = np.zeros(32000 * 2, "float32") + 0.1
    monkeypatch.setattr(mc, "generate", lambda prompt, seconds, device: (tone, 32000, device))
    heard = []
    monkeypatch.setattr(mc, "melody_generate",
                        lambda base, rate, prompt, seconds, device: heard.append((prompt, len(base))) or (tone, 32000))
    job = {"prompt": "hero", "seconds": 2, "out": str(tmp_path / "h.wav"), "leitmotif": {"seed": "Pip"},
           "twin": {"prompt": "dark", "out": str(tmp_path / "d.wav"), "leitmotif": {"seed": "Pip", "mode": "minor"}}}
    monkeypatch.setattr(mc, "twin_mode", lambda device: "melody")
    r = mc.run_job(job, "cuda")
    assert r["how"] == "leitmotif" and r["twin"]["how"] == "leitmotif" and [p for p, _ in heard] == ["hero", "dark"]
    monkeypatch.setattr(mc, "twin_mode", lambda device: "darken")         # no melody model: as before
    r = mc.run_job(job, "cpu")
    assert "how" not in r and r["twin"]["how"] == "darkened"


def test_an_anthem_builds_to_its_climax_and_ends_on_its_chord(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    from lib import music_compose as mc
    rate = 32000
    tone = (0.2 * np.sin(2 * np.pi * 220 * np.arange(rate * 10) / rate)).astype("float32")
    # The swell: quieter at the start, full from the climax on.
    built = mc.crescendo(tone, rate, 0.5)
    level = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)))           # noqa: E731
    assert level(built[: rate]) < level(built[6 * rate: 7 * rate]) - 5
    assert abs(level(built[8 * rate: 9 * rate]) - level(tone[8 * rate: 9 * rate])) < 0.1
    # The end: an anthem keeps its final chord (a short tail), a loop still fades at its seam.
    end = mc.finish(tone, rate, loop=False)
    assert level(end[-rate // 2: -rate // 4]) > level(end[rate * 5: rate * 6]) - 3
    # A composer job on the tune: the anthem is shaped; the villain twin gets a theme's length.
    seconds_asked = []
    monkeypatch.setattr(mc, "twin_mode", lambda device: "melody")
    monkeypatch.setattr(mc, "melody_generate", lambda base, r, prompt, seconds, device:
                        seconds_asked.append((prompt, seconds)) or (np.tile(tone, 4)[: int(seconds * rate)], rate))
    r = mc.run_job({"prompt": "hero", "seconds": 10, "out": str(tmp_path / "h.wav"),
                    "leitmotif": {"seed": "Kestrel", "cls": "Barbarian"},
                    "twin": {"prompt": "dark", "out": str(tmp_path / "d.wav"), "loop": True, "seconds": 30,
                             "leitmotif": {"seed": "Kestrel", "mode": "minor", "cls": "Barbarian"}}}, "cuda")
    assert r["how"] == "leitmotif" and seconds_asked == [("hero", 10), ("dark", 30)]
    hero, _ = sf.read(r["path"], dtype="float32")
    assert level(hero[: rate]) < level(hero[7 * rate: 8 * rate]) - 4                 # it builds
    assert sf.info(r["twin"]["path"]).duration == pytest.approx(30, abs=0.1)


def test_the_prompts_ask_for_tempo_weight_and_the_build():
    hero = composer.anthem_prompt({"name": "Kestrel", "class": "Barbarian"}, "")
    dark = composer.dark_anthem_prompt({"name": "Kestrel"}, "")
    assert "110 bpm" in hero and "climax" in hero and "held" in hero
    assert "70 bpm" in dark and "low brass" in dark and "bass" in dark


def test_a_villain_theme_is_made_heavy_whatever_the_model_did(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    from lib import music_compose as mc
    rate = 32000
    t = np.arange(rate * 4) / rate
    mix = (0.2 * np.sin(2 * np.pi * 60 * t) + 0.2 * np.sin(2 * np.pi * 1000 * t)
           + 0.2 * np.sin(2 * np.pi * 6000 * t) + 0.2 * np.sin(2 * np.pi * 12 * t)).astype("float32")
    band = lambda x, hz: np.abs(np.fft.rfft(x))[int(hz * len(x) / rate)]          # noqa: E731
    db = lambda a, b: 20 * np.log10(a / b)                                         # noqa: E731
    out = mc.heavy(mix, rate)
    assert len(out) == len(mix)
    assert db(band(out, 60) / band(out, 1000), band(mix, 60) / band(mix, 1000)) > 5      # deep bass up
    assert db(band(out, 6000) / band(out, 1000), band(mix, 6000) / band(mix, 1000)) < -2  # highs softened
    assert band(out, 12) < band(mix, 12) / 10                                       # rumble cut
    # In a job: the dark twin comes out heavy; the hero doesn't.
    monkeypatch.setattr(mc, "generate", lambda prompt, seconds, device: (mix, rate, device))
    monkeypatch.setattr(mc, "twin_mode", lambda device: "darken")
    r = mc.run_job({"prompt": "hero", "seconds": 4, "out": str(tmp_path / "h.wav"),
                    "twin": {"prompt": "dark", "out": str(tmp_path / "d.wav"), "loop": True}}, "cpu")
    hero, _ = sf.read(r["path"], dtype="float32")
    dark, _ = sf.read(r["twin"]["path"], dtype="float32")
    bass_share = lambda x: (np.abs(np.fft.rfft(x))[: int(150 * len(x) / rate)] ** 2).sum() / (np.abs(np.fft.rfft(x)) ** 2).sum()  # noqa: E731
    assert bass_share(dark) > bass_share(mix) * 1.5 and abs(bass_share(hero) - bass_share(mix)) < 0.02


def test_a_dark_anthem_made_later_asks_for_its_weight_too(tmp_path, fake):
    camp = tmp_path / "camp"
    camp.mkdir()
    seen = []
    real = composer.compose_many
    composer.compose_many = lambda jobs, *a, **k: seen.extend(jobs) or real(jobs, *a, **k)
    try:
        composer.compose_pieces(camp, [{"kind": "dark_anthem", "name": "Bram", "sheet": {"name": "Bram"}},
                                       {"kind": "judgment", "name": composer.JUDGMENT}])
    finally:
        composer.compose_many = real
    assert seen[0]["heavy"] is True and not seen[1].get("heavy")


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


def test_each_point_of_the_story_has_its_own_anthem(tmp_path, fake):
    from lib import character_arcs as arcs
    camp = tmp_path / "camp"
    camp.mkdir()
    sheet = {"name": "Kestrel", "class": "Barbarian"}
    composer.compose_pieces(camp, [{"kind": "anthem", "sheet": sheet,
                                    "spec": arcs.spec(arcs.state_of(camp, "Kestrel"))}])
    assert composer.anthem(camp, "Kestrel")["version"] == "s0-d0-w0-b0"     # a lone voice, to begin
    arcs.record(camp, "Kestrel", "growth", "stood alone at the drowned gate")
    now = arcs.spec(arcs.state_of(camp, "Kestrel"))
    assert not composer.has_version(camp, "Kestrel", now)
    assert composer.anthem(camp, "Kestrel")["file"] == "anthem-kestrel.ogg"  # (until the new one is ready)
    seen = []
    real = composer.compose_many
    composer.compose_many = lambda jobs, *a, **k: seen.extend(jobs) or real(jobs, *a, **k)
    try:
        composer.compose_pieces(camp, [{"kind": "anthem_version", "sheet": sheet, "spec": now}])
    finally:
        composer.compose_many = real
    assert seen[0]["leitmotif"]["stage"] == 1 and "twin" not in seen[0]
    assert composer.has_version(camp, "Kestrel", now)
    assert composer.anthem(camp, "Kestrel")["file"] == "anthem-kestrel-s1-d0-w0-b0.ogg"
    assert composer.anthem(camp, "Kestrel")["dark"] == "anthem-kestrel-dark.ogg"   # (the villain twin stays)


def test_the_anthem_is_described_for_where_the_story_is():
    sheet = {"name": "Kestrel", "class": "Barbarian"}
    p = lambda **a: composer.anthem_prompt(sheet, "", {"stage": 1, "dark": 0, "wound": False, "warm": False, **a})  # noqa: E731
    assert "solo" in p(stage=0) and "orchestra" not in p(stage=0)
    assert "choir" in p(stage=3) and "legendary" in p(stage=3)
    assert "lament" in p(wound=True) and "70 bpm" in p(wound=True)
    assert "shadow" in p(dark=1) and "tormented" in p(dark=3) and "warm" in p(warm=True)
    assert composer.anthem_seconds({"stage": 0}) < composer.anthem_seconds({"stage": 1}) < \
        composer.anthem_seconds({"stage": 3}) <= 30
