"""load_project_env: a script run directly finds what .env names, like the wrappers."""
import os
from pathlib import Path

from lib.campaign_manager import load_project_env

ROOT = Path(__file__).resolve().parent.parent


def test_the_environment_wins_over_dot_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GM_WORLD_STATE_BASE", str(tmp_path))
    load_project_env()
    assert os.environ["GM_WORLD_STATE_BASE"] == str(tmp_path)


def test_a_relative_base_is_anchored_at_the_project_root(monkeypatch):
    monkeypatch.setenv("GM_WORLD_STATE_BASE", "some-campaigns")
    load_project_env()
    assert os.environ["GM_WORLD_STATE_BASE"] == str(ROOT / "some-campaigns")
