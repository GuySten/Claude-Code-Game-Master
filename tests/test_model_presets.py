"""Model presets: one command sets every helper agent's model and the GM's."""

import json
import shutil

import pytest

from lib import model_presets as mp


@pytest.fixture
def project(tmp_path, monkeypatch):
    agents = tmp_path / ".claude" / "agents"
    shutil.copytree(mp.AGENTS_DIR, agents)
    monkeypatch.setattr(mp, "AGENTS_DIR", agents)
    monkeypatch.setattr(mp, "LOCAL_SETTINGS", tmp_path / ".claude" / "settings.local.json")
    return tmp_path


def test_every_agent_belongs_to_a_group(project):
    grouped = {a for agents in mp.GROUPS.values() for a in agents}
    on_disk = {p.stem for p in mp.AGENTS_DIR.glob("*.md")}
    assert grouped == on_disk


@pytest.mark.parametrize("name", list(mp.PRESETS))
def test_each_preset_applies_and_is_recognised(project, name):
    mp.apply(name)
    assert mp.current_preset() == name
    preset = mp.PRESETS[name]
    for group, agents in mp.GROUPS.items():
        for a in agents:
            assert (mp.read_model(a) or "inherit") == preset[group]
    assert json.loads(mp.LOCAL_SETTINGS.read_text())["model"] == preset["gm"]


def test_switching_keeps_the_rest_of_the_frontmatter_and_settings(project):
    mp.LOCAL_SETTINGS.write_text(json.dumps({"permissions": {"allow": ["Bash(bash tools/*)"]}}))
    import re
    original = (mp.AGENTS_DIR / "plot-weaver.md").read_text()
    without_model = re.sub(r"^model:.*\n", "", original, flags=re.M)
    mp.apply("budget", gm="opus")
    mp.apply("inherit")
    # Only the model line ever changes: name, description, tools, color and body stay.
    assert (mp.AGENTS_DIR / "plot-weaver.md").read_text() == without_model
    settings = json.loads(mp.LOCAL_SETTINGS.read_text())
    assert settings["permissions"] == {"allow": ["Bash(bash tools/*)"]}
    assert settings["model"] == "opus"
