"""Tests for session-identity-metadata: pair-based session count + structured footer."""

from pathlib import Path

from lib.session_manager import SessionManager


def _log(dcc_world):
    return Path(dcc_world) / "campaigns" / "dungeon-crawler-carl" / "session-log.md"


def test_session_number_uses_pairs_not_raw_starts(dcc_world):
    text = _log(dcc_world).read_text(encoding="utf-8")
    ended = text.count("### Session Ended:")
    started = text.count("## Session Started:")
    expected = ended + (1 if started > ended else 0)
    n = SessionManager(dcc_world)._get_session_number()
    assert n == expected
    # The pre-fix bug counted raw starts (DCC had ~20 starts for ~13 sessions).
    assert n < started


def test_end_writes_structured_footer(dcc_world):
    SessionManager(dcc_world).end_session(
        "Tested ending.", cliffhanger="A shadow moves at the door.",
        open_threads=["Find the key", "Warn the village"])
    text = _log(dcc_world).read_text(encoding="utf-8")
    assert "**Cliffhanger:** A shadow moves at the door." in text
    assert "**Open threads:** Find the key; Warn the village" in text
    assert "**Session:**" in text and "**Location:**" in text


def test_cliffhanger_and_threads_surface_in_context(dcc_world):
    sm = SessionManager(dcc_world)
    sm.end_session("done", cliffhanger="The door creaks open.", open_threads=["Escape the dungeon"])
    ctx = sm.get_full_context()
    assert "WHERE WE PAUSED: The door creaks open." in ctx
    assert "OPEN THREADS: Escape the dungeon" in ctx


def test_legacy_log_without_footer_still_works(dcc_world):
    # Before any structured end, context still assembles (best-effort cliffhanger).
    assert "PREVIOUSLY ON" in SessionManager(dcc_world).get_full_context()


def test_end_numbers_the_session_it_ends_even_without_a_start(tmp_path):
    # A playtest never ran `start`: its two sessions were numbered 0 and 1 and
    # session_count stayed 0.
    import json
    ws = tmp_path / "world-state"
    camp = ws / "campaigns" / "k"
    camp.mkdir(parents=True)
    (ws / "active-campaign.txt").write_text("k")
    (camp / "campaign-overview.json").write_text(json.dumps({"campaign_name": "K", "session_count": 0}))
    (camp / "session-log.md").write_text("# Session Log - K\n\n---\n")
    sm = SessionManager(str(ws))
    sm.end_session("The lottery night.", cliffhanger="An hour before dawn.")
    sm.end_session("Dawn; the Keep knelt.")
    text = (camp / "session-log.md").read_text(encoding="utf-8")
    assert "**Session:** 1\n" in text and "**Session:** 2\n" in text and "**Session:** 0" not in text
    assert json.loads((camp / "campaign-overview.json").read_text())["session_count"] == 2
    summaries = sm._recent_session_summaries()
    assert len(summaries) == 2 and summaries[0].startswith("The lottery night.")
    sm.start_session()
    sm.end_session("Third.")
    assert "**Session:** 3\n" in (camp / "session-log.md").read_text(encoding="utf-8")
