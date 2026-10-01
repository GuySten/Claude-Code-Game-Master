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
