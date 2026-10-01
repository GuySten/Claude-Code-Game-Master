"""Composed music: the bridge to the composer's own environment."""

import json
import sys

import pytest

from lib import composer


def test_compose_runs_the_composer_and_reads_its_answer(tmp_path, monkeypatch):
    fake = tmp_path / "fake_compose.py"
    fake.write_text(
        "import argparse, json, pathlib\n"
        "ap = argparse.ArgumentParser(); ap.add_argument('--prompt'); ap.add_argument('--seconds')\n"
        "ap.add_argument('--out'); ap.add_argument('--loop', action='store_true')\n"
        "a = ap.parse_args(); p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)\n"
        "p.write_bytes(b'OggS'); print('loading model...')\n"
        "print(json.dumps({'ok': True, 'path': str(p), 'seconds': float(a.seconds), 'device': 'cuda',\n"
        "                  'elapsed': 1, 'loop': a.loop, 'prompt': a.prompt}))\n")
    monkeypatch.setattr(composer, "SCRIPT", fake)
    monkeypatch.setattr(composer, "composer_python", lambda: sys.executable)
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

    fake.write_text("import sys; print('CUDA error: no kernel image', file=sys.stderr); sys.exit(1)\n")
    with pytest.raises(composer.ComposeError, match="no kernel image"):
        composer.compose("x", 5, tmp_path / "x.ogg")


def test_no_composer_no_music_jobs(monkeypatch):
    monkeypatch.setenv("MUSIC_COMPOSE", "off")
    assert composer.composer_python() is None and not composer.available()
    with pytest.raises(composer.ComposeError, match="isn't set up"):
        composer.compose("x", 5, composer.PROJECT_ROOT / "nowhere.ogg")


FAKE_BATCH = (
    "import argparse, json, os, pathlib, sys, time\n"
    "ap = argparse.ArgumentParser(); ap.add_argument('--batch'); a = ap.parse_args()\n"
    "log = pathlib.Path(os.environ['FAKE_LOG']); log.write_text(log.read_text() + 'load\\n')  # the model\n"
    "print('loading model...', file=sys.stderr)\n"
    "for i, job in enumerate(json.loads(pathlib.Path(a.batch).read_text(encoding='utf-8'))):\n"
    "    if i and os.environ.get('FAKE_WAIT'):  # the next piece once the caller saw the last: they stream\n"
    "        t = time.time()\n"
    "        while not (log.parent / f'seen-{i - 1}').exists() and time.time() - t < 20: time.sleep(0.05)\n"
    "    if 'FAIL' in job['prompt']:\n"
    "        print(json.dumps({'ok': False, 'index': i, 'error': 'RuntimeError: boom'}), flush=True); continue\n"
    "    p = pathlib.Path(job['out']); p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b'OggS')\n"
    "    print(json.dumps({'ok': True, 'index': i, 'path': str(p), 'seconds': job['seconds'],\n"
    "                      'loop': job['loop'], 'device': 'cuda', 'elapsed': 1}), flush=True)\n")


def fake_batch_composer(tmp_path, monkeypatch):
    fake = tmp_path / "fake_batch.py"
    fake.write_text(FAKE_BATCH)
    log = tmp_path / "loads.txt"
    log.write_text("")
    monkeypatch.setattr(composer, "SCRIPT", fake)
    monkeypatch.setattr(composer, "composer_python", lambda: sys.executable)
    monkeypatch.setenv("FAKE_LOG", str(log))
    return log


def test_a_batch_loads_the_model_once_and_each_piece_lands_as_it_is_done(tmp_path, monkeypatch):
    log = fake_batch_composer(tmp_path, monkeypatch)
    monkeypatch.setenv("FAKE_WAIT", "1")
    camp = tmp_path / "camp"
    camp.mkdir()
    seen = []

    def landed(piece, f):
        seen.append((piece.get("name") or piece["sheet"]["name"], f))
        (tmp_path / f"seen-{len(seen) - 1}").touch()
        # registered already, while the rest are still composing
        assert composer.theme_file(camp, "Grimaldi", True) == "grimaldi-boss.ogg"

    pieces = [{"kind": "theme", "name": "Grimaldi", "boss": True, "look": "a rotting ringmaster"},
              {"kind": "anthem", "sheet": {"name": "Pip", "race": "Halfling", "class": "Rogue"}},
              {"kind": "anthem", "sheet": {"name": "Bram", "race": "Dwarf", "class": "Fighter"}}]
    files = composer.compose_pieces(camp, pieces, landed)
    assert files == ["grimaldi-boss.ogg", "anthem-pip.ogg", "anthem-bram.ogg"]
    assert seen == [("Grimaldi", "grimaldi-boss.ogg"), ("Pip", "anthem-pip.ogg"), ("Bram", "anthem-bram.ogg")]
    assert log.read_text() == "load\n"                                  # ONE model load for all three
    assert composer.anthem(camp, "bram") == {"file": "anthem-bram.ogg", "seconds": 20.0}
    assert composer.has_theme(camp, "Grimaldi", True)

    # One piece failing doesn't sink the rest; all failing is an error.
    monkeypatch.setattr(composer, "theme_prompt", lambda *a: "FAIL")
    got = composer.compose_pieces(camp, [{"kind": "theme", "name": "Lich", "boss": False},
                                         {"kind": "anthem", "sheet": {"name": "Ana"}}])
    assert got == [None, "anthem-ana.ogg"] and not composer.has_theme(camp, "Lich", False)
    with pytest.raises(composer.ComposeError, match="composer failed"):
        composer.compose_pieces(camp, [{"kind": "theme", "name": "Lich", "boss": False}])
    assert composer.compose_many([]) == []
