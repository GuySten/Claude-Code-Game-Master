#!/usr/bin/env python3
"""Time management module for GM tools."""

import re
import sys
from pathlib import Path
from typing import Optional

# Add lib directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from campaign_manager import CampaignManager
from json_ops import JsonOperations

# Small elapsed-magnitude map for threat-clock ticks. Not a calendar parser:
# minutes / rounds / under 4 hours → 0 (a scene beat moves no clock)
# 4-23 hours → 1 · N days → N · N weeks → 7*N
# anything else (no unit given) → 1
_DURATION_WEEK = re.compile(r"(\d+)\s*weeks?", re.IGNORECASE)
_DURATION_DAY = re.compile(r"(\d+)\s*days?", re.IGNORECASE)
_DURATION_HOUR = re.compile(r"(\d+)\s*(?:hours?|hrs?)\b", re.IGNORECASE)
_DURATION_SHORT = re.compile(r"\b(?:\d+\s*)?(?:minutes?|mins?|seconds?|rounds?|turns?|moments?)\b"
                             r"|\b(?:an?|half an?)\s+hour\b", re.IGNORECASE)
SHORT_HOURS = 4          # less than this many hours is a scene beat, not a clock tick

# Times of day, in order round the clock. A step inside one of these (Deep night →
# "Deep night, a little later") is a scene beat; moving to the next is a tick.
_PERIODS = (
    ("deep night", ("deep night", "late night", "small hours", "midnight", "witching hour",
                    "pre-dawn", "predawn")),
    ("dawn", ("dawn", "daybreak", "sunrise", "first light", "cockcrow")),
    ("morning", ("morning",)),
    ("midday", ("midday", "noon")),
    ("afternoon", ("afternoon",)),
    ("evening", ("evening", "dusk", "sunset", "sundown", "twilight", "nightfall")),
    ("night", ("night", "nighttime")),
)
PERIOD_ORDER = ("dawn", "morning", "midday", "afternoon", "evening", "night", "deep night")
_CLOCK_TIME = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
_QUALIFIED = re.compile(r"\b(before|after|until|till)\s+(?:the\s+)?(.+)", re.IGNORECASE)


def _bare_period(text: str) -> Optional[str]:
    for period, words in _PERIODS:
        if any(re.search(r"\b" + re.escape(w) + r"\b", text) for w in words):
            return period
    return None


def time_period(text: Optional[str]) -> Optional[str]:
    """The time of day a free-text time names (one of PERIOD_ORDER), else None.

    "before dawn" is the deep night and "after dusk" is night: a qualifier moves
    the named time one step back or forward. A clock time ("21:40") maps by hour.
    """
    s = " ".join(str(text or "").lower().split())
    if not s:
        return None
    q = _QUALIFIED.search(s)
    if q:
        named = _bare_period(q.group(2))
        if named:
            i = PERIOD_ORDER.index(named)
            step = -1 if q.group(1).lower() in ("before", "until", "till") else 1
            return PERIOD_ORDER[(i + step) % len(PERIOD_ORDER)]
    named = _bare_period(s)
    if named:
        return named
    m = _CLOCK_TIME.search(s)
    if m:
        h = int(m.group(1))
        return ("deep night" if h < 5 else "dawn" if h < 7 else "morning" if h < 12
                else "midday" if h < 14 else "afternoon" if h < 17 else "evening" if h < 20
                else "night")
    return None


def _same_text(a: Optional[str], b: Optional[str]) -> bool:
    return " ".join(str(a or "").lower().split()) == " ".join(str(b or "").lower().split())


def crosses_boundary(before_time: Optional[str], before_date: Optional[str],
                     after_time: Optional[str], after_date: Optional[str]) -> bool:
    """Did a time update move to another day, or another time of day?"""
    if not _same_text(before_date, after_date):
        return True
    p1, p2 = time_period(before_time), time_period(after_time)
    if p1 and p2:
        return p1 != p2
    return not _same_text(before_time, after_time)


def ticks_from_duration(text: str) -> int:
    """Map a free-text duration to threat-clock ticks (0 for a scene beat)."""
    if not text or not str(text).strip():
        return 1
    s = str(text).strip()
    m = _DURATION_WEEK.search(s)
    if m:
        return max(1, 7 * int(m.group(1)))
    m = _DURATION_DAY.search(s)
    if m:
        return max(1, int(m.group(1)))
    m = _DURATION_HOUR.search(s)
    if m:
        hours = int(m.group(1))
        return 0 if hours < SHORT_HOURS else max(1, hours // 24)
    if _DURATION_SHORT.search(s):
        return 0
    return 1


def ticks_for_elapsed(ticks: Optional[int] = None, duration: Optional[str] = None,
                      before: Optional[tuple] = None, after: Optional[tuple] = None) -> int:
    """Resolve clock ticks for a time advance.

    Explicit ticks win, then duration. Given the (time_of_day, date) before and
    after the update, a step that stays in the same time of day on the same date
    (a scene beat: minutes, a room, a climb) is 0 ticks; a new time of day or a new
    date is 1. With nothing to go on, 1.
    """
    if ticks is not None:
        return max(0, int(ticks))
    if duration:
        return ticks_from_duration(duration)
    if before is not None and after is not None:
        return 1 if crosses_boundary(before[0], before[1], after[0], after[1]) else 0
    return 1


class TimeManager:
    """Manage campaign time state."""

    def __init__(self, world_state_dir: str = "world-state"):
        self.campaign_mgr = CampaignManager(world_state_dir)
        self.campaign_dir = self.campaign_mgr.get_active_campaign_dir()

        if self.campaign_dir is None:
            raise RuntimeError("No active campaign. Run /new-game or /import first.")

        self.json_ops = JsonOperations(str(self.campaign_dir))

    def update_time(self, time_of_day: str, date: str) -> bool:
        """Update the campaign time and date."""
        data = self.json_ops.load_json("campaign-overview.json")

        data['time_of_day'] = time_of_day
        data['current_date'] = date

        if not self.json_ops.save_json("campaign-overview.json", data):
            print(f"[ERROR] Failed to update time")
            return False

        print(f"[SUCCESS] Time updated to: {time_of_day}, {date}")
        return True

    def get_time(self) -> dict:
        """Get current campaign time."""
        data = self.json_ops.load_json("campaign-overview.json")
        return {
            'time_of_day': data.get('time_of_day', 'Unknown'),
            'current_date': data.get('current_date', 'Unknown')
        }


def _parse_ticks_flags(argv):
    """Parse [--ticks N] [--duration TEXT] [--to TIME DATE] from argv."""
    ticks = None
    duration = None
    to = None
    i = 0
    while i < len(argv):
        if argv[i] == "--to":
            if i + 2 >= len(argv):
                print("[ERROR] --to requires a time of day and a date", file=sys.stderr)
                sys.exit(1)
            to = (argv[i + 1], argv[i + 2])
            i += 3
            continue
        if argv[i] == "--ticks":
            if i + 1 >= len(argv):
                print("[ERROR] --ticks requires a number", file=sys.stderr)
                sys.exit(1)
            try:
                ticks = int(argv[i + 1])
            except ValueError:
                print("[ERROR] --ticks must be an integer", file=sys.stderr)
                sys.exit(1)
            i += 2
        elif argv[i] == "--duration":
            if i + 1 >= len(argv):
                print("[ERROR] --duration requires a value", file=sys.stderr)
                sys.exit(1)
            duration = argv[i + 1]
            i += 2
        else:
            print(f"[ERROR] Unknown argument: {argv[i]}", file=sys.stderr)
            sys.exit(1)
    return ticks, duration, to


def main():
    """CLI interface for time management."""
    if len(sys.argv) < 2:
        print("Usage: python lib/time_manager.py update <time_of_day> <date>")
        print("       python lib/time_manager.py get")
        print("       python lib/time_manager.py ticks [--ticks N] [--duration TEXT] [--to TIME DATE]")
        sys.exit(1)

    action = sys.argv[1]

    # ticks is a pure mapping — no campaign, so it can run before TimeManager().
    # With --to (the time about to be set), it compares against the campaign's
    # current time: run it BEFORE update.
    if action == "ticks":
        ticks, duration, to = _parse_ticks_flags(sys.argv[2:])
        before = None
        if to is not None and ticks is None and not duration:
            try:
                now = TimeManager().get_time()
                before = (now['time_of_day'], now['current_date'])
            except RuntimeError:
                before = None
        print(ticks_for_elapsed(ticks=ticks, duration=duration, before=before,
                                after=to if before else None))
        return

    try:
        manager = TimeManager()

        if action == 'update':
            if len(sys.argv) < 4:
                print("Usage: python lib/time_manager.py update <time_of_day> <date>")
                sys.exit(1)
            time_of_day = sys.argv[2]
            date = sys.argv[3]
            if not manager.update_time(time_of_day, date):
                sys.exit(1)

        elif action == 'get':
            time_info = manager.get_time()
            print(f"Time: {time_info['time_of_day']}")
            print(f"Date: {time_info['current_date']}")

        else:
            print(f"Unknown action: {action}")
            sys.exit(1)

    except RuntimeError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
