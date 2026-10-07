#!/usr/bin/env python3
"""
Threat clocks — felt, mounting pressure (DCC's floor-collapse countdown).

Named segmented clocks that advance on time or events, surfaced in the session
context so stakes are visible and trustworthy. A filled clock is the trigger for a
dramatic beat / book-native milestone. Tone-respecting: a kit/campaign that wants
no doom clock simply declares none. Dramatic choices made at inflection points are
recorded as consequences (via consequence_manager), tying the fork into the
reactive world.

A kit's named tracks (a `named_track` system in ruleset.json: the Hunger, a
Menace, a Dread) are stored here too, as event clocks flagged `"track": true`
that carry the system's thresholds. Unlike a clock they also fall (feeding the
Stone resets the Hunger to 0): `gm-clock.sh track "<name>" <N|+N|-N>`. Crossing a
threshold on the way up fires its consequence into the world, like a clock that
fills.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))

from entity_manager import EntityManager


class ThreatClockManager(EntityManager):
    def __init__(self, world_state_dir: str = None):
        super().__init__(world_state_dir)
        self._wsd = world_state_dir
        self.clocks_file = "threat-clocks.json"

    def _load(self) -> Dict[str, Any]:
        return self.json_ops.load_json(self.clocks_file) or {}

    def add_clock(self, name: str, segments: int, advance_on: str = "time",
                  consequence: str = None, linked_plot: str = None) -> Dict[str, Any]:
        data = self._load()
        entry = {"current": 0, "max": int(segments), "advance_on": advance_on}
        if consequence:
            entry["consequence"] = consequence
        if linked_plot:
            entry["linked_plot"] = linked_plot
        data[name] = entry
        self.json_ops.save_json(self.clocks_file, data)
        return data[name]

    def _fire_if_filled(self, name: str, clock: Dict[str, Any], was_full: bool) -> Optional[str]:
        """Write a clock's stored consequence into the world as it FILLS.

        A clock carried its `consequence` text only as a printed FULL flag, so a
        countdown running out was a line the GM might notice rather than a beat
        that arrived. Firing writes a PENDING consequence — it does not resolve
        it or force the GM's hand, same as every other consequence.

        Firing is the *transition* into full, which is what keeps it to once per
        countdown without a flag to keep in sync: a clock that was already full
        fires nothing, and one reset or extended back below full fires again the
        next time it fills. Mutates `clock` (stamps `consequence_fired` as
        provenance); the caller saves.
        """
        if was_full or int(clock.get("current", 0)) < int(clock.get("max", 1)):
            return None
        text = clock.get("consequence")
        if not text:
            return None
        import contextlib
        from consequence_manager import ConsequenceManager
        # add_consequence announces itself on stdout; this one fires from inside
        # advance/tick-time, whose --json output must stay parseable.
        with contextlib.redirect_stdout(sys.stderr):
            cid = ConsequenceManager(self._wsd).add_consequence(
                f"[Clock — {name}] {text}", trigger=f"the {name} clock ran out")
        clock["consequence_fired"] = cid
        return cid

    def advance(self, name: str, ticks: int = 1) -> Optional[Dict[str, Any]]:
        data = self._load()
        c = data.get(name)
        if not c:
            return None
        was_full = int(c.get("current", 0)) >= int(c.get("max", 1))
        c["current"] = min(c["max"], int(c.get("current", 0)) + int(ticks))
        self._fire_if_filled(name, c, was_full)
        self.json_ops.save_json(self.clocks_file, data)
        return c

    def tick_time_clocks(self, ticks: int = 1) -> Dict[str, Any]:
        """Advance every advance_on=='time' clock that isn't already full.

        The automatic pressure wire: gm-time.sh calls this after each time
        update, passing ticks scaled to elapsed magnitude (--ticks / --duration).
        Default ticks=1 (Dawn→Noon stays +1). Event clocks (advance_on != 'time')
        are untouched — the GM advances those by hand.
        Returns {name: clock} for the clocks that moved.
        """
        data = self._load()
        advanced = {}
        for name, c in data.items():
            if c.get("advance_on", "time") != "time":
                continue
            cur, mx = int(c.get("current", 0)), int(c.get("max", 1))
            if cur >= mx:
                continue
            c["current"] = min(mx, cur + int(ticks))
            self._fire_if_filled(name, c, was_full=False)  # full clocks skipped above
            advanced[name] = c
        if advanced:
            self.json_ops.save_json(self.clocks_file, data)
        return advanced

    # --- set / adjust (clocks and named tracks) ---
    def _key(self, data: Dict[str, Any], name: str) -> Optional[str]:
        want = " ".join(str(name).split()).lower()
        return next((k for k in data if k.lower() == want), None)

    def track_systems(self) -> Dict[str, Dict[str, Any]]:
        """The kit's named tracks (ruleset.json systems, primitive named_track)."""
        ruleset = self.json_ops.load_json("ruleset.json") or {}
        out = {}
        for s in ruleset.get("systems") or []:
            if isinstance(s, dict) and s.get("primitive") == "named_track" and s.get("name"):
                out[str(s["name"])] = s.get("config") or {}
        return out

    def _fire(self, text: str, trigger: str) -> Optional[str]:
        import contextlib
        from consequence_manager import ConsequenceManager
        with contextlib.redirect_stdout(sys.stderr):
            return ConsequenceManager(self._wsd).add_consequence(text, trigger=trigger)

    def change(self, name: str, value: Optional[int] = None, delta: Optional[int] = None,
               reason: Optional[str] = None, create_max: Optional[int] = None) -> Dict[str, Any]:
        """Set (``value``) or move (``delta``, either way) a clock or named track.

        A named track the kit declares but nothing has stored yet is created at 0
        from its config (so its first value persists); ``create_max`` creates any
        other track. Thresholds crossed on the way up fire their consequences, and
        a clock that fills fires its own. Every change is kept in the clock's
        ``history`` with its reason.
        """
        from game_core import named_track
        data = self._load()
        key = self._key(data, name)
        if key is None:
            systems = self.track_systems()
            sys_key = next((k for k in systems if k.lower() == " ".join(str(name).split()).lower()), None)
            if sys_key is None and create_max is None:
                raise ValueError(f"no clock or named track called {name!r} (named tracks: "
                                 f"{', '.join(systems) or 'none in ruleset.json'}; or pass --max N)")
            cfg = systems.get(sys_key) or {}
            key = sys_key or " ".join(str(name).split())
            data[key] = {"current": 0, "max": int(create_max or cfg.get("max") or 6),
                         "advance_on": "event", "track": True}
            if cfg.get("thresholds"):
                data[key]["thresholds"] = cfg["thresholds"]
        c = data[key]
        before, mx = int(c.get("current", 0)), int(c.get("max", 1))
        if value is not None:
            delta = int(value) - before
        res = named_track(before, int(delta or 0), {"max": mx, "thresholds": c.get("thresholds") or []})
        c["current"] = res["after"]
        fired = []
        if res["after"] > before:
            for t in res["crossed"]:
                if isinstance(t, dict) and t.get("consequence"):
                    fired.append(self._fire(f"[{key} at {t['at']}] {t['consequence']}",
                                            f"the {key} reached {t['at']}"))
            cid = self._fire_if_filled(key, c, was_full=before >= mx)
            if cid:
                fired.append(cid)
        if res["after"] != before or reason:
            hist = c.setdefault("history", [])
            hist.append({"at": self.json_ops.get_timestamp(), "from": before, "to": res["after"],
                         **({"reason": reason} if reason else {})})
            del hist[:-20]
        self.json_ops.save_json(self.clocks_file, data)
        return {"name": key, "before": before, "after": res["after"], "max": mx,
                "crossed": [t for t in res["crossed"] if isinstance(t, dict)],
                "rising": res["after"] > before, "fired": [f for f in fired if f]}

    def remove_clock(self, name: str) -> bool:
        data = self._load()
        if name in data:
            del data[name]
            self.json_ops.save_json(self.clocks_file, data)
            return True
        return False

    def get_clocks(self) -> Dict[str, Any]:
        return self._load()

    def is_full(self, name: str) -> bool:
        c = self._load().get(name)
        return bool(c and c.get("current", 0) >= c.get("max", 1))

    def full_clocks(self) -> Dict[str, Any]:
        return {n: c for n, c in self._load().items() if c.get("current", 0) >= c.get("max", 1)}

    def pending_beats(self) -> Dict[str, Any]:
        """Filled clocks = dramatic beats that are due (an inflection point)."""
        return self.full_clocks()

    def record_choice(self, prompt: str, chosen_fork: str, trigger: str = "player choice",
                      trigger_type: str = None, match: str = None) -> str:
        """Record a dramatic-choice fork as a consequence — the fork→reactive-world wire.

        The GM presents `prompt` with stakes-bearing forks at an inflection point;
        the player's chosen fork is written into the consequence engine so it pays
        off later (optionally with a structured trigger). Returns the consequence id.
        """
        from consequence_manager import ConsequenceManager
        cm = ConsequenceManager(self._wsd)
        text = f"[Choice — {prompt}] {chosen_fork}"
        return cm.add_consequence(text, trigger, trigger_type=trigger_type, match=match)

    @staticmethod
    def render(clocks: Dict[str, Any]) -> str:
        """Render clocks as filled/empty segment bars for the GM-visible context."""
        lines = []
        for name, c in clocks.items():
            cur, mx = int(c.get("current", 0)), int(c.get("max", 1))
            bar = "●" * cur + "○" * max(0, mx - cur)
            flag = "  ⚠ FULL" if cur >= mx else ""
            kind = "track" if c.get("track") else f"on {c.get('advance_on', 'time')}"
            lines.append(f"{name}: [{bar}] {cur}/{mx} ({kind}){flag}")
        return "\n".join(lines)


def main():
    import argparse
    import json
    from cli_output import wants_json, strip_json_flag, emit

    parser = argparse.ArgumentParser(description="Threat clocks")
    sub = parser.add_subparsers(dest="action")
    p = sub.add_parser("add"); p.add_argument("name"); p.add_argument("segments", type=int)
    p.add_argument("--on", default="time")
    p.add_argument("--consequence", help="what happens when it fills (fired into the world)")
    p.add_argument("--linked-plot", dest="linked_plot")
    p = sub.add_parser("advance"); p.add_argument("name"); p.add_argument("--ticks", type=int, default=1)
    p = sub.add_parser("tick-time"); p.add_argument("--ticks", type=int, default=1)
    p = sub.add_parser("set", help="set a clock to N (when the fiction outruns it)")
    p.add_argument("name"); p.add_argument("value", type=int); p.add_argument("--reason")
    p = sub.add_parser("track", help="a named track: show it, set it (N) or move it (+N / -N)")
    p.add_argument("name"); p.add_argument("change", nargs="?")
    p.add_argument("--reason"); p.add_argument("--max", type=int, help="create a track the kit doesn't declare")
    p = sub.add_parser("remove"); p.add_argument("name")
    sub.add_parser("list")
    sub.add_parser("beats")  # filled clocks = beats due
    p = sub.add_parser("choose"); p.add_argument("prompt"); p.add_argument("chosen")
    p.add_argument("--trigger", default="player choice")
    p.add_argument("--trigger-type", dest="trigger_type")
    p.add_argument("--match")

    json_mode = wants_json()
    args = parser.parse_args(strip_json_flag(sys.argv[1:]))
    if not args.action:
        parser.print_help(); sys.exit(1)

    m = ThreatClockManager()
    if args.action == "add":
        out = m.add_clock(args.name, args.segments, advance_on=args.on,
                          consequence=args.consequence, linked_plot=args.linked_plot)
    elif args.action == "advance":
        out = m.advance(args.name, args.ticks)
    elif args.action == "tick-time":
        out = m.tick_time_clocks(args.ticks)
        if not json_mode:
            for n, c in out.items():
                if c.get("current", 0) >= c.get("max", 1):
                    print(f"⚠ {n} is FULL — a dramatic beat is due"
                          + (f": {c['consequence']}" if c.get("consequence") else ""))
    elif args.action in ("set", "track"):
        value = delta = None
        raw = "" if args.action == "set" else (args.change or "")
        if args.action == "set":
            value = args.value
        elif raw:
            try:
                if raw[0] in "+-":
                    delta = int(raw)
                else:
                    value = int(raw)
            except ValueError:
                sys.exit(f"[ERROR] {raw!r}: give N, +N or -N")
        try:
            if args.action == "track" and value is None and delta is None and args.reason is None:
                key = m._key(m.get_clocks(), args.name)
                if key is None:          # first look: store the kit's track at 0
                    out = m.change(args.name, delta=0, create_max=args.max)
                else:
                    c = m.get_clocks()[key]
                    out = {"name": key, "after": c.get("current", 0), "max": c.get("max"),
                           "before": c.get("current", 0), "crossed": [], "rising": False, "fired": []}
            else:
                out = m.change(args.name, value=value, delta=delta, reason=args.reason,
                               create_max=getattr(args, "max", None))
        except ValueError as e:
            sys.exit(f"[ERROR] {e}")
        if not json_mode:
            print(f"{out['name']}: {out['before']} → {out['after']}/{out['max']}"
                  if out["before"] != out["after"] else f"{out['name']}: {out['after']}/{out['max']}")
            for t in out["crossed"]:
                print(f"⚠ {'reached' if out['rising'] else 'fell below'} {t.get('at')}: {t.get('consequence', '')}")
            if out["fired"]:
                print(f"  fired into the world: {', '.join(out['fired'])} (gm-consequence.sh check)")
            return
    elif args.action == "remove":
        out = {"removed": m.remove_clock(args.name)}
    elif args.action == "beats":
        out = m.pending_beats()
    elif args.action == "choose":
        out = {"consequence_id": m.record_choice(
            args.prompt, args.chosen, trigger=args.trigger,
            trigger_type=getattr(args, "trigger_type", None), match=args.match)}
    else:
        out = m.get_clocks()

    if json_mode:
        emit(out, json_mode=True)
    else:
        print(json.dumps(out, indent=2))
        if args.action == "list":
            print(m.render(out))


if __name__ == "__main__":
    main()
