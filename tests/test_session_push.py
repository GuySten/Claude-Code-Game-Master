"""gm-session.sh push: the campaign repo is updated after a session (the host's rule)."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def push(base: Path, *args):
    env = {**os.environ, "GM_WORLD_STATE_BASE": str(base), "GIT_AUTHOR_NAME": "GM", "GIT_AUTHOR_EMAIL": "gm@example.invalid",
           "GIT_COMMITTER_NAME": "GM", "GIT_COMMITTER_EMAIL": "gm@example.invalid"}
    return subprocess.run(["bash", str(ROOT / "tools" / "gm-session.sh"), "push", *args],
                          cwd=ROOT, env=env, capture_output=True, text=True)


def test_the_session_is_committed_and_pushed_to_the_campaign_repo(tmp_path):
    remote = tmp_path / "remote.git"
    git("init", "-q", "--bare", str(remote), cwd=tmp_path)
    base = tmp_path / "campaigns-repo"
    camp = base / "campaigns" / "keep"
    camp.mkdir(parents=True)
    (base / "active-campaign.txt").write_text("keep")
    (camp / "campaign-overview.json").write_text("{}")
    (base / "campaigns" / "other").mkdir()
    (base / "campaigns" / "other" / "notes.md").write_text("another campaign")
    git("init", "-q", "-b", "main", cwd=base)
    git("remote", "add", "origin", str(remote), cwd=base)

    (camp / "session-log.md").write_text("Session 1: the vault opened.")
    r = push(base, "the vault opened")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Pushed keep to origin/main" in r.stdout
    log = git("log", "--format=%s", "origin/main", cwd=base)
    assert log.startswith("keep: the vault opened")
    files = git("ls-tree", "-r", "--name-only", "origin/main", cwd=base).split()
    assert "campaigns/keep/session-log.md" in files
    assert "campaigns/other/notes.md" not in files            # only the active campaign

    r = push(base, "nothing new")                              # nothing changed: still fine
    assert r.returncode == 0 and "Nothing new" in r.stdout


def test_a_campaigns_folder_that_is_not_a_repo_is_left_alone(tmp_path):
    camp = tmp_path / "campaigns" / "keep"
    camp.mkdir(parents=True)
    (tmp_path / "active-campaign.txt").write_text("keep")
    r = push(tmp_path)
    assert r.returncode == 0 and "isn't a git repo" in r.stdout
