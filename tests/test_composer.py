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
    "    print(json.dumps({'ok': True, 'id': job['id'], 'path': str(p), 'seconds': float(job['seconds']),\n"
    "                      'loop': job['loop'], 'prompt': job['prompt'], 'device': 'cuda', 'elapsed': 1,\n"
    "                      'card_held': card_held()}), flush=True)\n")


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
    assert rec == {"file": "anthem-pip.ogg", "seconds": 20.0}
    assert composer.anthem(camp, "PIP") == rec

    prompt = composer.theme_prompt("Grimaldi", "rotting ringmaster", composer.flavor(camp), True)
    assert "boss battle" in prompt and "dark fantasy, grim" in prompt and "rotting ringmaster" in prompt
    assert "heroic triumphant anthem for Pip, a Halfling Rogue" in composer.anthem_prompt(
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
    assert composer.anthem(camp, "bram") == {"file": "anthem-bram.ogg", "seconds": 20.0}
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
