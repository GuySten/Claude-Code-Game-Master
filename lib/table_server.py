#!/usr/bin/env python3
"""
The online table — let every player join from their own computer.

One host runs Claude Code as the GM. ``gm-table.sh start`` launches this small
web server (standard library only, no extra installs). Each player opens the
link in a browser, enters the table code, and either takes an existing player
character or creates a new one (seated via the same ``join`` path as
``gm-player.sh join``). Players type actions; the GM reads them with
``gm-table.sh wait`` / ``inbox`` and posts narration back with
``gm-table.sh say``. Every browser sees the story live.

Voice: the page uses the browser's own speech engines (Web Speech API) — players
can speak their actions (push-to-talk) and hear the narration read aloud, in
English or Hebrew. Each player's language travels with their actions so the GM
can answer in it; ``say --lang he|en`` posts a language-specific version of a
beat (each browser shows only its own language's version; untagged = everyone).
Players' actions are translated too: the GM sends translations with
``gm-table.sh translate`` (``wait`` lists what needs it), and each browser shows
every action in its player's language, with the original a tap away.

Music: ``gm-table.sh music <track>`` sets one shared background track for the
whole table — an audio file from ``music/`` (project-wide) or ``<campaign>/music/``,
a direct https link to an audio file, or a built-in generated ambience
(``ambient:wind`` …). Every browser plays it from the same point; each player
controls only their own volume / mute.

Automatic music: the GM tags narration with the scene's mood
(``say --mood combat``). The server picks a track for that mood — a file from
``music/`` whose name carries one of the mood's keywords (``battle-drums.mp3``
-> combat) or is listed in ``music/moods.json``, else the mood's built-in
ambience — and switches only when the mood actually changes.

Enemy themes: a special enemy (named villain, boss, recurring foe) gets their
own music with ``say --theme "Grimaldi"``: a file assigned to them
(``music theme "Grimaldi" clown-waltz.mp3``, kept in ``<campaign>/music-themes.json``),
else a file named after them (``grimaldi.mp3``), else a leitmotif the browser
generates from their name — the same tune every time they return. The theme
holds through combat/boss/dread moods and gives way when the scene moves on.
``--boss`` (or a later ``--mood boss``) plays the boss version of the theme:
the same tune, but fast and thundering (or ``<name>-boss.mp3`` if there is one).

The server is the ONLY writer of the table log, so the GM-side commands talk
to it over localhost (authenticated with a host key kept in
``<campaign>/table/server.json``) rather than touching files directly.

Files (all under ``<campaign>/table/``):
  log.jsonl     every message (player actions, GM narration, joins)
  seats.json    browser seat token -> player character name
  gm-cursor     id of the last message the GM has read
  langs.json    player character name -> language they play in (en / he)
  music.json    the shared background track (what, volume, loop, when it started, mood)
  settings.json table settings (auto_music on/off)
  turn-times.json how long the GM's last turns took (drives the players' progress bar)
  server.json   port, table code, host key, pid (written by `serve`)
"""

import argparse
import hashlib
import hmac
import json
import os
import secrets
import signal
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).parent))

import composer
import party_roster
import table_tts
from campaign_manager import CampaignManager
from character_schema import to_flat

MAX_TEXT = 4000            # longest single message (GM narration can be long)
MAX_PLAYER_TEXT = 1200     # longest player action
MAX_BODY = 16 * 1024
DEFAULT_PORT = 8765
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".webp": "image/webp", ".gif": "image/gif"}
LANGS = {"en": "English", "he": "Hebrew"}
AUDIO_TYPES = {".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".oga": "audio/ogg",
               ".opus": "audio/ogg", ".m4a": "audio/mp4", ".aac": "audio/aac",
               ".wav": "audio/wav", ".flac": "audio/flac", ".webm": "audio/webm"}
# Generated in the browser (Web Audio) — no files needed. Keep in sync with
# AMBIENCES in table_page.html.
AMBIENT = {
    "wind": "Howling wind (travel, mountains, open plains)",
    "rain": "Steady rain (camp, city at night, melancholy)",
    "cave": "Low drone with dripping water (caves, ruins, the underdark)",
    "fire": "Crackling hearth (tavern, camp fire, safe rest)",
    "dungeon": "Dark pulsing drone (dread, a monster near, the boss lair)",
    "storm": "Rain with rolling thunder (danger outdoors, sea, climax)",
    "peaceful": "Soft slow chords (calm, rest, a safe town, a hard-won victory)",
    "battle": "War drums and a driving bass (combat, chases, the boss fight)",
    "mystery": "Shimmering tones over a low hum (magic, secrets, investigation)",
    "epic": "Boss battle (fast and thundering: double-time drums, racing bass, brass hits)",
}
# Scene moods the GM tags narration with. Each picks a music file whose name
# holds one of its keywords (or one listed under it in music/moods.json), else
# its built-in ambience. "silence" fades the music out.
MOODS = {
    "calm": {"ambient": "peaceful", "volume": 0.35,
             "keywords": ["calm", "peaceful", "peace", "village", "town", "rest", "morning",
                          "gentle", "relax", "home", "pastoral"],
             "use": "safe places, rest, quiet conversation, morning in town"},
    "tavern": {"ambient": "fire", "volume": 0.4,
               "keywords": ["tavern", "inn", "pub", "festive", "feast", "drinking", "bard",
                            "lute", "folk"],
               "use": "taverns, inns, feasts, a lively market"},
    "travel": {"ambient": "wind", "volume": 0.4,
               "keywords": ["travel", "journey", "road", "adventure", "exploration", "explore",
                            "wilderness", "forest", "overworld", "field", "mountain"],
               "use": "the road, wilderness, exploring the open world"},
    "mystery": {"ambient": "mystery", "volume": 0.4,
                "keywords": ["mystery", "mysterious", "magic", "arcane", "investigation",
                             "puzzle", "ruins", "enchanted", "wonder", "secret"],
                "use": "magic, secrets, ancient ruins, investigating a clue"},
    "dread": {"ambient": "dungeon", "volume": 0.45,
              "keywords": ["dread", "horror", "creepy", "eerie", "suspense", "tension",
                           "haunted", "ominous", "dark", "scary"],
              "use": "something is wrong, a monster is near, horror, stealth"},
    "dungeon": {"ambient": "cave", "volume": 0.45,
                "keywords": ["dungeon", "cave", "crypt", "underground", "tomb", "catacomb",
                             "mine", "sewer", "underdark"],
                "use": "caves, crypts, dungeons, anything underground"},
    "combat": {"ambient": "battle", "volume": 0.55,
               "keywords": ["combat", "battle", "fight", "action", "war", "skirmish", "drums",
                            "chase"],
               "use": "a fight breaks out, a chase, a desperate escape"},
    "boss": {"ambient": "epic", "volume": 0.7,
             "keywords": ["boss", "epic", "climax", "final", "showdown", "dragon"],
             "use": "the big villain, a dragon, the climax of the arc"},
    "sad": {"ambient": "rain", "volume": 0.35,
            "keywords": ["sad", "melancholy", "grief", "funeral", "loss", "sorrow", "lament",
                         "tragic"],
            "use": "a death, a loss, a farewell, grief"},
    "storm": {"ambient": "storm", "volume": 0.5,
              "keywords": ["storm", "thunder", "sea", "ocean", "sailing", "ship", "tempest"],
              "use": "storms, the sea, nature turned dangerous"},
    "victory": {"ambient": "peaceful", "volume": 0.45,
                "keywords": ["victory", "triumph", "celebration", "heroic", "fanfare", "win",
                             "glory"],
                "use": "the fight is won, a triumph, a celebration"},
}
SILENCE = "silence"
# What the GM can be doing during a turn (reported by .claude/hooks/table-progress.sh
# as the GM's tools run). Browsers word each one in their own language.
STAGES = ("reading", "lore", "dice", "sheets", "moving", "threads", "image", "translating")
DEFAULT_TURN_SECONDS = 45      # the estimate before this table has any history
TURN_HISTORY = 12              # turns the estimate is based on
STALE_TURN_SECONDS = 20 * 60   # a turn the GM never answered stops counting
# While an enemy's theme plays, these moods mean "still the same encounter".
THEME_HOLDS_THROUGH = {"combat", "boss", "dread"}
NAME_STOPWORDS = {"the", "of", "a", "an", "and", "lord", "lady", "sir"}
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CODE_WORDS = ["ember", "raven", "lantern", "goblin", "dragon", "tavern", "rune",
              "owlbear", "mimic", "dagger", "torch", "crypt", "griffin", "potion"]


def table_dir(campaign_dir) -> Path:
    return Path(campaign_dir).resolve() / "table"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


# ------------------------------------------------- rolling a character ----
# Joining players can roll one: 4d6, drop the lowest, for each of the campaign's
# abilities (its ruleset's stat_schema; the classic six by default). With the
# classic six, a race and a class that suits the best scores are suggested too,
# with level-1 HP and AC. All of it is a starting point the GM builds on.
CLASSIC_SIX = ["str", "dex", "con", "int", "wis", "cha"]
RACES = {"Human": "אדם", "Elf": "אלף", "Dwarf": "גמד", "Halfling": "בן־גמד",
         "Gnome": "גנום", "Half-Elf": "חצי־אלף", "Half-Orc": "חצי־אורק",
         "Tiefling": "טיפלינג", "Dragonborn": "בן־דרקון"}
# class -> (Hebrew, hit die, the abilities it leans on)
CLASSES = {"Barbarian": ("ברברי", 12, ["str", "con"]), "Bard": ("פייטן", 8, ["cha"]),
           "Cleric": ("כוהן", 8, ["wis"]), "Druid": ("דרואיד", 8, ["wis"]),
           "Fighter": ("לוחם", 10, ["str", "dex"]), "Monk": ("נזיר", 8, ["dex", "wis"]),
           "Paladin": ("פלדין", 10, ["str", "cha"]), "Ranger": ("סייר", 10, ["dex", "wis"]),
           "Rogue": ("נוכל", 8, ["dex"]), "Sorcerer": ("מכשף", 6, ["cha"]),
           "Warlock": ("קוסם אופל", 8, ["cha"]), "Wizard": ("קוסם", 6, ["int"])}
NAMES = [("Bram", "בראם"), ("Tamsin", "תמסין"), ("Orrin", "אורין"), ("Liora", "ליאורה"),
         ("Kestrel", "קסטרל"), ("Doran", "דורן"), ("Ysolde", "איזולדה"), ("Fenn", "פן"),
         ("Marek", "מארק"), ("Seren", "סרן"), ("Halden", "הלדן"), ("Wren", "רן"),
         ("Thorne", "ת'ורן"), ("Isra", "איסרה"), ("Galen", "גאלן"), ("Nyra", "נירה"),
         ("Corwin", "קורווין"), ("Elsbeth", "אלסבת"), ("Ruk", "רוק"), ("Talia", "טליה")]
MAX_PENDING_ROLLS = 200
# A round: once the first player acts, the GM waits until every seated player has
# acted, or this many seconds (gm-table.sh round <seconds|off>).
ROUND_SECONDS = 60
# The players' side chat: kept in memory only, never on disk and never in any
# GM endpoint, so the GM (and Claude, who can read the campaign's files) can't
# see it. It clears when the table restarts.
CHAT_KEEP = 500
CHAT_TEXT = 500
# A PC in one of these states can't act, so a round never waits for them.
CANT_ACT = ("dead", "dying", "unconscious", "incapacitated", "paralyzed", "paralysed",
            "petrified", "stunned", "asleep", "sleeping", "knocked out", "comatose")


def cant_act(sheet: Dict[str, Any]) -> Optional[str]:
    """Why this PC can't act right now (their status, a condition, 0 HP), else None."""
    status = str(sheet.get("status") or "alive").strip().lower()
    if status not in ("", "alive", "ok", "active"):
        return status
    for cond in sheet.get("conditions") or []:
        text = str(cond.get("name") if isinstance(cond, dict) else cond).strip().lower()
        if any(word in text for word in CANT_ACT):
            return text
    hp = sheet.get("hp")
    current = hp.get("current") if isinstance(hp, dict) else None
    if isinstance(current, (int, float)) and current <= 0 and (hp or {}).get("max"):
        return "0 hp"
    return None
# Portraits: a PC without one gets one drawn in the background. The worker waits
# this long for the GM to write the character's look (so the portrait matches
# every later picture of them), and retries a failed one after a while.
PORTRAIT_GRACE = 180
PORTRAIT_RETRY = 900
# Ability score increases (5e): every class at these levels, plus a few extras.
ASI_LEVELS = {4, 8, 12, 16, 19}
ASI_EXTRA = {"Fighter": {6, 14}, "Rogue": {10}}


def _mod(score: int) -> int:
    return (score - 10) // 2


# ============================================================ table state ====

class TableState:
    """Messages + seats for one campaign table. Thread-safe; single process."""

    def __init__(self, campaign_dir: Path, world_state_base: str):
        self.campaign_dir = Path(campaign_dir).resolve()
        self.base = world_state_base
        self.dir = table_dir(self.campaign_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.dir / "log.jsonl"
        self.seats_path = self.dir / "seats.json"
        self.cursor_path = self.dir / "gm-cursor"
        self.lock = threading.RLock()       # re-entrant: party() runs inside turn bookkeeping
        self.messages: List[Dict[str, Any]] = []
        self.rev = 0          # bumps on every new message AND every translation
        if self.log_path.exists():
            by_id: Dict[int, Dict[str, Any]] = {}
            for line in self.log_path.read_text(encoding="utf-8").splitlines():
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                self.rev += 1
                if "patch" in entry:          # a later edit or translation
                    target = by_id.get(entry.get("patch"))
                    if target is not None:
                        if "text" in entry:   # the player corrected it: old translations go
                            target["text"] = entry["text"]
                            target["edited"] = entry.get("edited") or True
                            target.pop("tr", None)
                        if entry.get("tr"):
                            target.setdefault("tr", {}).update(entry["tr"])
                        target["rev"] = self.rev
                    continue
                entry["rev"] = self.rev
                self.messages.append(entry)
                by_id[entry.get("id")] = entry
        self.seats: Dict[str, str] = self._read_json(self.seats_path, {})
        self.langs_path = self.dir / "langs.json"
        self.langs: Dict[str, str] = self._read_json(self.langs_path, {})
        self.music_path = self.dir / "music.json"
        self.music: Dict[str, Any] = self._read_json(self.music_path, {})
        self.settings_path = self.dir / "settings.json"
        self.settings: Dict[str, Any] = self._read_json(self.settings_path, {})
        self.turn_times_path = self.dir / "turn-times.json"
        times = self._read_json(self.turn_times_path, [])
        self.turn_times: List[float] = [float(t) for t in times if isinstance(t, (int, float))] \
            if isinstance(times, list) else []
        self.turn: Optional[Dict[str, Any]] = None
        # Natural read-aloud voices made here (lib/table_tts.py); tests plug in a fake.
        self.tts_dir = self.dir / "tts"
        self.tts_engine = None
        self.tts_down_until = 0.0
        # The level each PC's sheet was last BUILT at (HP, abilities): a PC whose
        # level is higher (XP crossed a threshold, or a milestone) can level up
        # from their sheet. A PC first seen counts as built at their level.
        self.levels_path = self.dir / "levels.json"
        self.built_levels: Dict[str, int] = self._read_json(self.levels_path, {})
        # Portraits (see portrait_pass): who we've tried, when we first saw them.
        self.portrait_tried: Dict[str, float] = {}
        self.portrait_seen: Dict[str, float] = {}
        self.portrait_wake = threading.Event()
        self.portrait_maker = None            # tests plug in a fake: (name, campaign_dir) -> filename
        self.place_maker = None               # ditto, for places
        self.foe_maker = None                 # ditto: (name, campaign_dir, boss, look) -> filename
        self.item_maker = None                # ditto: (name, campaign_dir, look, owner) -> filename
        # Foes and treasures to show: queued by the GM's say, posted when painted.
        self.art_jobs: List[Dict[str, Any]] = []
        self.enemy_looks: Dict[str, str] = {}
        self.gallery_path = self.dir / "gallery.json"
        g = self._read_json(self.gallery_path, {})
        self.shown_foes: List[List[Any]] = [x for x in g.get("foes", []) if isinstance(x, list)]
        self.shown_treasures: List[str] = [x for x in g.get("treasures", []) if isinstance(x, str)]
        self.chat: List[Dict[str, Any]] = []           # players only; never written to disk
        # The Narrator (lib/narrator.py): each player's private questions and answers.
        self.narrator_log: Dict[str, List[Dict[str, Any]]] = {}
        self.narrator_busy: set = set()
        self.narrator_slots = threading.Semaphore(2)
        self.narrator_ask = None                        # tests plug in a fake model
        # Composed music: villains' and bosses' themes and the PCs' anthems are
        # composed in the background (lib/composer.py) when the composer is set up.
        self.music_jobs: List[Dict[str, Any]] = []
        self.music_maker = None              # tests: (kind, name, boss, look, sheet) -> file
        self.music_revert: Optional[Dict[str, Any]] = None   # a heroic anthem, then back
        # Places the party has been (only their pictures are shown: no spoilers).
        self.places_path = self.dir / "places.json"
        visited = self._read_json(self.places_path, {}).get("visited", [])
        self.visited: List[str] = [v for v in visited if isinstance(v, str)]
        # Characters rolled on the join screen, not created yet: roll id -> roll.
        self.pending_rolls: Dict[str, Dict[str, Any]] = {}
        # Actions corrected AFTER the GM read them: id -> the text the GM read.
        self.corrections: Dict[int, str] = {}
        try:
            self.gm_cursor = int(self.cursor_path.read_text().strip())
        except (OSError, ValueError):
            self.gm_cursor = self.messages[-1]["id"] if self.messages else 0

    @staticmethod
    def _read_json(path: Path, default):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return default

    def _write_seats(self) -> None:
        tmp = self.seats_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.seats, indent=2), encoding="utf-8")
        tmp.replace(self.seats_path)

    def set_lang(self, pc: str, lang: Optional[str]) -> None:
        if lang not in LANGS or not pc:
            return
        with self.lock:
            if self.langs.get(pc) == lang:
                return
            self.langs[pc] = lang
            tmp = self.langs_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.langs, indent=2), encoding="utf-8")
            tmp.replace(self.langs_path)

    def seated_langs(self) -> Dict[str, str]:
        """Language of every seated player (English when never stated)."""
        with self.lock:
            return {name: self.langs.get(name, "en")
                    for name in dict.fromkeys(self.seats.values())}

    # --- music ---
    def music_dirs(self) -> List[Path]:
        return [self.campaign_dir / "music", PROJECT_ROOT / "music"]

    def find_music(self, name: str) -> Optional[Path]:
        """A music file by (case-insensitive) file name or name without extension."""
        wanted = Path(str(name)).name.lower()
        for d in self.music_dirs() + [self.campaign_dir / "music" / "themes",
                                      self.campaign_dir / "music" / "anthems"]:
            if not d.is_dir():
                continue
            for f in sorted(d.iterdir()):
                if f.is_file() and f.suffix.lower() in AUDIO_TYPES and \
                        wanted in (f.name.lower(), f.stem.lower()):
                    return f
        return None

    def list_music(self) -> List[Dict[str, str]]:
        out, seen = [], set()
        for d in self.music_dirs():
            if not d.is_dir():
                continue
            for f in sorted(d.iterdir()):
                if f.is_file() and f.suffix.lower() in AUDIO_TYPES and f.name.lower() not in seen:
                    seen.add(f.name.lower())
                    out.append({"track": f.name, "where": str(d)})
        return out

    # --- automatic music by scene mood ---
    @property
    def auto_music(self) -> bool:
        return self.settings.get("auto_music", True) is not False

    # --- rounds ---
    @property
    def round_seconds(self) -> int:
        try:
            return max(0, int(self.settings.get("round_seconds", ROUND_SECONDS)))
        except (TypeError, ValueError):
            return ROUND_SECONDS

    def set_round_seconds(self, seconds: int) -> None:
        with self.lock:
            self.settings["round_seconds"] = max(0, int(seconds))
            tmp = self.settings_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.settings, indent=2), encoding="utf-8")
            tmp.replace(self.settings_path)

    @staticmethod
    def _sent_at(msg: Dict[str, Any]) -> float:
        if isinstance(msg.get("t"), (int, float)):
            return float(msg["t"])
        try:
            return time.mktime(time.strptime(msg.get("ts", ""), "%Y-%m-%dT%H:%M:%S"))
        except (TypeError, ValueError):
            return time.time()

    def round_state(self, now: Optional[float] = None) -> Dict[str, Any]:
        """The round the GM will answer next: the actions it hasn't read yet. It
        opens with the first of them (so nobody is timed while the table is on a
        break) and closes when every seated player has acted, or after
        round_seconds. While it's open the GM can't read the actions or narrate."""
        now = now or time.time()
        secs = self.round_seconds
        with self.lock:
            acts = [m for m in self.messages if m["id"] > self.gm_cursor and m["kind"] == "player"]
            seated = list(dict.fromkeys(self.seats.values()))
        if not acts:
            return {"open": False, "seconds": secs}
        acted = {party_roster.slugify(m.get("pc", "")) for m in acts}
        out = self.out_of_action()
        waiting = [n for n in seated if party_roster.slugify(n) not in acted and n not in out]
        started = self._sent_at(acts[0])
        deadline = started + secs
        return {"open": bool(secs and waiting and now < deadline), "seconds": secs,
                "out_of_action": {n: why for n, why in out.items() if n in seated},
                "started_at": started, "deadline": deadline, "waiting_on": waiting,
                "timed_out": bool(secs and waiting and now >= deadline)}

    def out_of_action(self) -> Dict[str, str]:
        """Seated PCs who can't act (dead, unconscious...): name -> why. Read from
        the live sheets, so a knock-out counts from the moment the GM records it."""
        out = {}
        for _, raw in party_roster.all_pcs(self.campaign_dir):
            sheet = to_flat(raw)
            why = cant_act(sheet)
            if why and sheet.get("name"):
                out[sheet["name"]] = why
        return out

    # --- the players' side chat (the GM is not privy to it) ---
    def chat_post(self, pc: str, text: str) -> Dict[str, Any]:
        with self.lock:
            msg = {"id": (self.chat[-1]["id"] + 1) if self.chat else 1,
                   "t": round(time.time(), 2), "pc": pc, "text": text}
            self.chat.append(msg)
            del self.chat[:-CHAT_KEEP]
            return dict(msg)

    def chat_since(self, after: int) -> List[Dict[str, Any]]:
        with self.lock:
            return [dict(m) for m in self.chat if m["id"] > after]

    # --- the Narrator: reminds a player of the story so far (private, read-only) ---
    def narrator_question(self, pc: str, question: str) -> Dict[str, Any]:
        import narrator
        with self.lock:
            if pc in self.narrator_busy:
                return {"ok": False, "error": "One question at a time."}
            self.narrator_busy.add(pc)
        try:
            lang = self.langs.get(pc, "en")
            lines = narrator.story_lines(self.since(0, pc), pc, lang)
            shown = self.sheet(pc, pc)
            history = [{"q": x["q"], "a": x["a"]} for x in self.narrator_log.get(pc, [])]
            prompt = narrator.build_prompt(lines, shown and shown["sheet"], self.party_for(pc),
                                           self.overview().get("location"), history, question, pc)
            with self.narrator_slots:
                got = narrator.answer(question, lines, prompt, lang, ask=self.narrator_ask)
            entry = {"id": len(self.narrator_log.get(pc, [])) + 1, "t": round(time.time(), 2),
                     "q": question, "a": got["answer"], "source": got["source"]}
            with self.lock:
                self.narrator_log.setdefault(pc, []).append(entry)
                del self.narrator_log[pc][:-50]
            return {"ok": True, "entry": entry}
        finally:
            with self.lock:
                self.narrator_busy.discard(pc)

    def gm_read_since_narration(self) -> bool:
        """Has the GM read players' actions since it last narrated to everyone?"""
        with self.lock:
            last = max((m["id"] for m in self.messages if m["kind"] == "gm" and not m.get("to")),
                       default=0)
            return self.gm_cursor > last

    def set_auto_music(self, on: bool) -> None:
        with self.lock:
            self.settings["auto_music"] = bool(on)
            tmp = self.settings_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.settings, indent=2), encoding="utf-8")
            tmp.replace(self.settings_path)

    @staticmethod
    def _tokens(name: str) -> set:
        word, out = [], set()
        for ch in Path(name).stem.lower() + " ":
            if ch.isalnum():
                word.append(ch)
            elif word:
                out.add("".join(word))
                word = []
        return out

    # --- enemy themes ---
    @property
    def themes_path(self) -> Path:
        return self.campaign_dir / "music-themes.json"

    def themes(self) -> Dict[str, str]:
        data = self._read_json(self.themes_path, {})
        return data if isinstance(data, dict) else {}

    def assign_theme(self, name: str, track: Optional[str]) -> None:
        themes = self.themes()
        key = next((k for k in themes if party_roster._same_name(k, name)), name)
        if track:
            themes[key] = track
        else:
            themes.pop(key, None)
        tmp = self.themes_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(themes, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.themes_path)

    def theme_track(self, name: str, boss: bool = False) -> str:
        """The track that is this enemy's theme: an assigned one, else a music
        file named after them (``<name>-boss.*`` preferred for a boss fight),
        else their generated leitmotif (theme:<name>)."""
        for key, track in self.themes().items():
            if party_roster._same_name(key, name):
                return track
        composed = composer.theme_file(self.campaign_dir, name, boss)
        if composed:
            return composed
        wanted = self._tokens(name + ".x") - NAME_STOPWORDS
        if wanted:
            named = [f["track"] for f in self.list_music() if wanted <= self._tokens(f["track"])]
            bossy = [f for f in named if self._tokens(f) & {"boss", "battle", "fight"}]
            calm = [f for f in named if f not in bossy]
            if named:
                return (bossy or calm)[0] if boss else (calm or bossy)[0]
        return "theme:" + name

    def apply_theme(self, name: str, boss: bool = False) -> Optional[Dict[str, Any]]:
        name = " ".join(str(name).split())
        if boss:
            self.queue_theme(name, True)   # a boss earns a composed battle theme
        same = party_roster._same_name(self.music.get("theme"), name) and self.music.get("track")
        if same and (bool(self.music.get("boss")) == boss or not boss):
            return None       # already playing (a plain re-mention never calms a boss down)
        track = self.theme_track(name, boss)
        if same and track == self.music.get("track") and not track.startswith("theme:"):
            # No separate boss version (yet: one may be being composed). It IS a boss
            # fight now, so a boss theme that lands takes over.
            if boss:
                with self.lock:
                    self.music["boss"] = True
                self.show_foe(name, True)  # the boss portrait still comes
            return None
        title = f"{name}'s theme"
        music = self.set_music(track, 0.7 if boss else 0.6, True, title,
                               mood="boss" if boss else "combat", theme=name, boss=boss)
        self.show_foe(name, boss)          # and their portrait (the boss one when it escalates)
        return music

    # --- composed music (lib/composer.py): villains, bosses, heroes ---
    def queue_theme(self, name: str, boss: bool, look: str = "") -> None:
        if self.music_maker is None and not composer.available():
            return
        name = " ".join(str(name).split())
        if composer.has_theme(self.campaign_dir, name, boss) or any(
                j["kind"] == "theme" and j["name"] == name and j["boss"] == boss for j in self.music_jobs):
            return
        self.music_jobs.append({"kind": "theme", "name": name, "boss": boss,
                                "look": look or self.enemy_looks.get(name, "")})
        self.portrait_wake.set()

    def music_pass(self) -> List[str]:
        """Compose what's queued (villain/boss themes), then one missing PC anthem.
        When a theme lands while its foe's music is playing, it takes over."""
        if self.music_maker is None and not composer.available():
            self.music_jobs.clear()
            return []
        done = []
        while self.music_jobs:
            job = self.music_jobs.pop(0)
            try:
                if self.music_maker is not None:
                    f = self.music_maker("theme", job["name"], job["boss"], job["look"], None)
                else:
                    f = composer.compose_theme(self.campaign_dir, job["name"], job["boss"], job["look"])
            except Exception as e:
                print(f"[compose] {job['name']}: {e}", flush=True)
                continue
            done.append(job["name"])
            playing = self.music
            if (party_roster._same_name(playing.get("theme"), job["name"])
                    and bool(playing.get("boss")) == job["boss"] and playing.get("track") != f):
                music = self.set_music(f, playing.get("volume", 0.6), True, playing.get("title"),
                                       mood=playing.get("mood"), theme=job["name"], boss=job["boss"])
                self.announce_music(music)
        for path, raw in party_roster.all_pcs(self.campaign_dir):
            sheet = to_flat(raw)
            name = sheet.get("name") or path.stem
            if composer.anthem(self.campaign_dir, name):
                continue
            if time.time() - self.portrait_tried.get("anthem:" + name, -PORTRAIT_RETRY) < PORTRAIT_RETRY:
                continue
            self.portrait_tried["anthem:" + name] = time.time()
            try:
                if self.music_maker is not None:
                    self.music_maker("anthem", name, False, "", sheet)
                else:
                    composer.compose_anthem(self.campaign_dir, sheet)
                done.append(name)
            except Exception as e:
                print(f"[compose] {name}'s anthem: {e}", flush=True)
            break                              # one anthem per pass: pictures get a turn
        return done

    def heroic_moment(self, pc: str) -> Optional[Dict[str, Any]]:
        """A PC does something heroic: their anthem plays (or, before it's composed,
        the victory music), then the scene's music comes back."""
        pc = " ".join(str(pc).split())
        before = (self.music_revert or {}).get("music") or dict(self.music)
        rec = composer.anthem(self.campaign_dir, pc)
        if rec:
            track, seconds, title, loop = rec["file"], float(rec.get("seconds") or 20), f"{pc}'s anthem", False
        else:
            files = [f for f in self.mood_files("victory") if f != before.get("src")] or self.mood_files("victory")
            track = secrets.choice(files) if files else "ambient:" + MOODS["victory"]["ambient"]
            seconds, title, loop = 30.0, None, True
        music = self.set_music(track, 0.75, loop, title, mood="victory", keep_revert=True)
        with self.lock:
            self.music_revert = {"at": time.time() + seconds + 0.5, "music": before}
        return music

    def music_tick(self) -> Optional[Dict[str, Any]]:
        """After a heroic anthem: the music it interrupted, quietly."""
        with self.lock:
            r = self.music_revert
            if not r or time.time() < r["at"]:
                return None
            self.music_revert = None
        prev = r["music"]
        if not prev.get("track"):
            return self.set_music(None, mood=prev.get("mood"))
        return self.set_music(prev["track"], prev.get("volume", 0.5), prev.get("loop", True),
                              prev.get("title"), mood=prev.get("mood"), theme=prev.get("theme"),
                              boss=bool(prev.get("boss")))

    def announce_music(self, music: Dict[str, Any]) -> None:
        if not music.get("track"):
            self.append("system", "🎵 The music fades away.", event={"type": "music_stop"})
            return
        event = {"type": "music", "kind": music["kind"], "src": music["src"],
                 "title": music["title"]}
        if music.get("theme"):
            event["theme"] = music["theme"]
        if music.get("boss"):
            event["boss"] = True
        self.append("system", f"🎵 {music['title']}", event=event)

    def mood_files(self, mood: str) -> List[str]:
        """Music files for a mood: those listed under it in any music/moods.json,
        otherwise every file whose name carries one of the mood's keywords."""
        listed = []
        for d in self.music_dirs():
            mapping = self._read_json(d / "moods.json", {})
            for name in (mapping.get(mood) or []) if isinstance(mapping, dict) else []:
                found = self.find_music(str(name))
                if found is not None and found.name not in listed:
                    listed.append(found.name)
        if listed:
            return listed
        keywords = set(MOODS.get(mood, {}).get("keywords", []))
        keywords |= {k + "s" for k in keywords}
        return [f["track"] for f in self.list_music() if self._tokens(f["track"]) & keywords]

    def apply_mood(self, mood: str, force: bool = False) -> Optional[Dict[str, Any]]:
        """Switch the table's music to fit a scene mood. Returns the new music
        state, or None when nothing changed (same mood, or auto music is off)."""
        if not force and not self.auto_music:
            return None
        current = self.music if self.music.get("track") or self.music.get("mood") else {}
        if current.get("theme") and current.get("track") and mood in THEME_HOLDS_THROUGH:
            if mood == "boss" and not current.get("boss"):
                # The fight escalates: same enemy, their theme's boss version.
                return self.apply_theme(current["theme"], boss=True)
            return None    # the enemy's theme carries the rest of the encounter
        if current.get("mood") == mood and not current.get("theme"):
            return None
        if mood == SILENCE:
            return self.set_music(None, mood=SILENCE)
        spec = MOODS[mood]
        files = self.mood_files(mood)
        if files:
            fresh = [f for f in files if f != current.get("src")] or files
            track = secrets.choice(fresh)
        else:
            track = "ambient:" + spec["ambient"]
        return self.set_music(track, spec["volume"], True, None, mood=mood)

    def set_music(self, track: Optional[str], volume: float = 0.5,
                  loop: bool = True, title: Optional[str] = None,
                  mood: Optional[str] = None, theme: Optional[str] = None,
                  boss: bool = False, keep_revert: bool = False) -> Dict[str, Any]:
        """Point every browser at one track (None = silence). Returns the state."""
        with self.lock:
            if not keep_revert:
                self.music_revert = None       # any other music change ends an anthem
            next_id = int(self.music.get("id", 0)) + 1
            if not track:
                self.music = {"id": next_id, "track": None, "mood": mood}
            else:
                if track.startswith("theme:"):
                    kind, src = "theme", track.split(":", 1)[1]
                    title = title or f"{src}'s theme"
                elif track.startswith("ambient:"):
                    kind, src = "ambient", track.split(":", 1)[1]
                    title = title or AMBIENT.get(src, src).split(" (")[0]
                elif track.startswith(("http://", "https://")):
                    kind, src = "url", track
                    title = title or Path(urlparse(track).path).stem or "Music"
                else:
                    kind, src = "file", Path(track).name
                    title = title or Path(src).stem.replace("-", " ").replace("_", " ")
                self.music = {"id": next_id, "track": track, "kind": kind, "src": src,
                              "title": title, "volume": max(0.0, min(1.0, float(volume))),
                              "loop": bool(loop), "started_at": time.time(), "mood": mood}
                if theme:
                    self.music["theme"] = theme
                if boss:
                    self.music["boss"] = True
                if kind == "file":
                    from music_library import credit_for
                    credit = credit_for(src, PROJECT_ROOT / "music" / "library.json")
                    if credit:
                        self.music["credit"] = credit   # shown on the page (CC BY needs it)
            tmp = self.music_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.music, indent=2), encoding="utf-8")
            tmp.replace(self.music_path)
            return dict(self.music)

    # --- messages ---
    def append(self, kind: str, text: str, pc: Optional[str] = None,
               to: Optional[str] = None, image: Optional[str] = None,
               lang: Optional[str] = None, voice: bool = False,
               event: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self.lock:
            msg = {"id": (self.messages[-1]["id"] + 1) if self.messages else 1,
                   "ts": _now(), "t": round(time.time(), 2), "kind": kind, "text": text}
            if pc:
                msg["pc"] = pc
            if to:
                msg["to"] = to
            if image:
                msg["image"] = image
            if lang in LANGS:
                msg["lang"] = lang
            if voice:
                msg["voice"] = True
            if event:
                msg["event"] = event   # lets each browser word the notice in its language
            self.rev += 1
            msg["rev"] = self.rev
            self.messages.append(msg)
            if kind == "gm" and not to:
                self._gm_spoke(lang if lang in LANGS else None)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({k: v for k, v in msg.items() if k != "rev"},
                                   ensure_ascii=False) + "\n")
            return msg

    def visible_to(self, msg: Dict[str, Any], pc: Optional[str]) -> bool:
        """Private messages (GM whispers, a player's aside to the GM) are seen
        only by the PC they concern."""
        to = msg.get("to")
        if not to:
            return True
        return pc is not None and party_roster._same_name(to, pc)

    def since(self, after: int, pc: Optional[str], rev: int = 0) -> List[Dict[str, Any]]:
        """New messages (id > after), plus older ones changed since revision
        ``rev`` (a translation arrived), so browsers can update them in place."""
        with self.lock:
            return [m for m in self.messages
                    if (m["id"] > after or (rev and m.get("rev", 0) > rev))
                    and self.visible_to(m, pc)]

    # --- natural read-aloud voices ---
    def tts_ready(self) -> bool:
        return ((self.tts_engine is not None or table_tts.installed())
                and time.time() >= self.tts_down_until)

    def speech(self, text: str, voice: str) -> Path:
        """The mp3 of one chunk of narration. When the voice service fails, pages
        fall back to their own voices and it isn't asked again for a minute
        (already-made audio is still served)."""
        engine = self.tts_engine
        if time.time() < self.tts_down_until:
            def engine(*_):
                raise table_tts.Unavailable("the online voice is unreachable; retrying shortly")
        try:
            return table_tts.synthesize(text, voice, self.tts_dir, engine)
        except table_tts.Unavailable:
            if time.time() >= self.tts_down_until:
                self.tts_down_until = time.time() + 60
            raise

    def answered(self, msg: Dict[str, Any]) -> bool:
        """Has the GM narrated since this action (publicly, or to its player)?
        (caller holds the lock)"""
        return any(m["id"] > msg["id"] and m["kind"] == "gm"
                   and (not m.get("to") or m.get("to") == msg.get("pc"))
                   for m in reversed(self.messages))

    def edit(self, pc: str, msg_id: Any, text: str) -> Dict[str, Any]:
        """A player fixes their own action (a typo, a misheard word) — allowed
        until the GM answers it. If the GM already read it, the next inbox shows
        the correction next to what the GM read."""
        try:
            msg_id = int(msg_id)
        except (TypeError, ValueError):
            return {"ok": False, "error": "No such message.", "reason": "missing"}
        with self.lock:
            msg = next((m for m in self.messages if m["id"] == msg_id), None)
            if msg is None or msg["kind"] != "player" or not party_roster._same_name(
                    msg.get("pc") or "", pc):
                return {"ok": False, "error": "You can only edit your own actions.",
                        "reason": "not-yours"}
            if self.answered(msg):
                return {"ok": False, "error": "The GM already answered that — write a new action.",
                        "reason": "answered"}
            if text == msg.get("text"):
                return {"ok": True, "message": dict(msg)}
            if msg_id <= self.gm_cursor:
                self.corrections.setdefault(msg_id, msg.get("text", ""))
            msg["text"] = text
            msg["edited"] = _now()
            msg.pop("tr", None)                 # re-translated from the new text
            self.rev += 1
            msg["rev"] = self.rev
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"patch": msg_id, "text": text, "edited": msg["edited"]},
                                   ensure_ascii=False) + "\n")
            return {"ok": True, "message": dict(msg)}

    # --- translation: every player reads one language ---
    @staticmethod
    def text_lang(text: str) -> str:
        """'he' or 'en', by which script most of the letters are in."""
        he = sum(1 for ch in text if "\u0590" <= ch <= "\u05ff")
        latin = sum(1 for ch in text if ch.isascii() and ch.isalpha())
        return "he" if he > latin else "en"

    # --- the public dice log: the table rolls, everyone sees ---
    def roll(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Roll for the GM and show it to every player at once — with its DC/AC,
        which is part of the same request, so it is fixed before the dice land.
        A secret roll is announced (players see that the GM rolled), and its
        result kept in table/secret-rolls.jsonl."""
        import dice
        notation = str(spec.get("notation", "")).strip()
        try:
            result = dice.DiceRoller().roll(notation)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        target = spec.get("target")
        try:
            target = int(target) if target is not None else None
        except (TypeError, ValueError):
            return {"ok": False, "error": "the DC/AC must be a number"}
        label = "AC" if spec.get("target_label") == "AC" else "DC"
        roll = {"notation": notation, "rolls": result.get("kept") or result.get("rolls") or [],
                "discarded": result.get("discarded") or [],
                "modifier": result.get("modifier", 0), "total": result["total"],
                "natural": dice.natural(result), "target": target, "target_label": label,
                "outcome": dice.judge(result, target)}
        why = " ".join(str(spec.get("why") or "").split())[:120] or None
        why_tr = {l: " ".join(str(t).split())[:120] for l, t in (spec.get("why_tr") or {}).items()
                  if l in LANGS and str(t).strip()}
        pc = " ".join(str(spec.get("pc") or "").split())[:60] or None
        secret = bool(spec.get("secret"))
        with self.lock:
            msg_id = (self.messages[-1]["id"] + 1) if self.messages else 1
        if secret:
            with open(self.dir / "secret-rolls.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": msg_id, "ts": _now(), "pc": pc, "why": why,
                                    "roll": roll}, ensure_ascii=False) + "\n")
            msg = self.append("roll", "", pc=pc, event={"secret": True})
        else:
            event = {"roll": roll, "why": why}
            if why_tr:
                event["why_tr"] = why_tr
            msg = self.append("roll", "", pc=pc, event=event)
        self.set_stage("dice")
        return {"ok": True, "result": result, "roll": roll, "message_id": msg["id"],
                "secret": secret}

    def needs_translation(self, ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """Public player actions that some seated player can't read yet:
        [{id, pc, from, to: [langs], text}] — at a mixed table, or when someone writes
        in a language the rest of the table doesn't read."""
        langs = set(self.seated_langs().values())
        if not langs:
            return []
        out = []
        with self.lock:
            pool = [m for m in self.messages if m["kind"] == "player" and not m.get("to")]
            if ids is not None:
                pool = [m for m in pool if m["id"] in ids]
            for m in pool[-20:]:
                src = m.get("lang") or self.text_lang(m.get("text", ""))
                missing = sorted(l for l in langs if l != src and l not in (m.get("tr") or {}))
                if missing:
                    out.append({"id": m["id"], "pc": m.get("pc"), "from": src,
                                "to": missing, "text": m.get("text", "")})
        return out

    def translate(self, translations: Dict[str, Dict[str, str]]) -> List[int]:
        """Store translations {message id: {lang: text}}; returns the ids updated."""
        done = []
        with self.lock:
            by_id = {m["id"]: m for m in self.messages}
            for raw_id, versions in (translations or {}).items():
                try:
                    msg = by_id.get(int(raw_id))
                except (TypeError, ValueError):
                    continue
                if msg is None or msg.get("to") or not isinstance(versions, dict):
                    continue
                clean = {l: str(t).strip()[:MAX_TEXT] for l, t in versions.items()
                         if l in LANGS and str(t).strip()}
                if not clean:
                    continue
                msg.setdefault("tr", {}).update(clean)
                self.rev += 1
                msg["rev"] = self.rev
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"patch": msg["id"], "tr": clean},
                                       ensure_ascii=False) + "\n")
                done.append(msg["id"])
        return done

    def gm_unread(self, mark: bool) -> List[Dict[str, Any]]:
        with self.lock:
            unread = [m for m in self.messages
                      if m["id"] > self.gm_cursor and m["kind"] in ("player", "system")]
            by_id = {m["id"]: m for m in self.messages}
            fixed = [dict(by_id[i], corrected_from=was)
                     for i, was in sorted(self.corrections.items()) if i in by_id]
            unread = fixed + unread
            if mark and self.messages:
                self.corrections.clear()
                self.gm_cursor = self.messages[-1]["id"]
                self.cursor_path.write_text(str(self.gm_cursor))
                if any(m["kind"] == "player" for m in unread):
                    self._start_turn()
            return unread

    # --- the GM's turn (what the players' progress bar shows) ---
    def turn_estimate(self) -> float:
        """Seconds the GM usually takes: the median of the last turns."""
        if not self.turn_times:
            return float(DEFAULT_TURN_SECONDS)
        times = sorted(self.turn_times[-TURN_HISTORY:])
        mid = len(times) // 2
        return times[mid] if len(times) % 2 else (times[mid - 1] + times[mid]) / 2

    def _start_turn(self) -> None:
        """The GM just read players' actions: a turn starts (caller holds the lock)."""
        now = time.time()
        if self.turn and now - self.turn["started_at"] < STALE_TURN_SECONDS:
            return            # still answering the earlier actions
        langs = {self.langs.get(n, "en") for n in self.seats.values()} or {"en"}
        self.turn = {"started_at": now, "start_id": self.messages[-1]["id"],
                     "estimate": round(self.turn_estimate(), 1),
                     "stage": "reading", "stage_at": now,
                     "langs_needed": sorted(langs), "langs_done": [],
                     # The sheets as the players last saw them. The GM records
                     # every change BEFORE narrating it, so without this the HP
                     # bars would give the outcome away before the story does.
                     "party": self.party(sheets=True)}

    def set_stage(self, stage: str) -> bool:
        with self.lock:
            if not self.turn or stage not in STAGES:
                return False
            self.turn["stage"], self.turn["stage_at"] = stage, time.time()
            return True

    def _gm_spoke(self, lang: Optional[str]) -> None:
        """Narration went out (caller holds the lock). The turn ends once every
        language at the table has its version of the beat."""
        if not self.turn:
            return
        done = set(self.turn["langs_done"])
        done |= {lang} if lang else set(self.turn["langs_needed"])
        self.turn["langs_done"] = sorted(done)
        if not set(self.turn["langs_needed"]) <= done:
            self.turn["stage"], self.turn["stage_at"] = "translating", time.time()
            return
        took = time.time() - self.turn["started_at"]
        self.turn = None
        if 1 <= took <= STALE_TURN_SECONDS:
            self.turn_times = (self.turn_times + [round(took, 1)])[-TURN_HISTORY:]
            tmp = self.turn_times_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.turn_times), encoding="utf-8")
            tmp.replace(self.turn_times_path)

    def progress(self) -> Dict[str, Any]:
        """What the players' progress bar needs: is the GM working, since when,
        how long it usually takes, what it's doing — or are actions queued."""
        with self.lock:
            if self.turn and time.time() - self.turn["started_at"] < STALE_TURN_SECONDS:
                t = self.turn
                return {"state": "working", "started_at": t["started_at"],
                        "start_id": t["start_id"], "estimate": t["estimate"],
                        "stage": t["stage"], "stage_at": t["stage_at"],
                        "langs_done": t["langs_done"]}
            queued = any(m["id"] > self.gm_cursor and m["kind"] == "player"
                         for m in self.messages)
            return {"state": "queued" if queued else "idle"}

    def waiting_on(self) -> List[str]:
        """Seated PCs who have not acted since the GM last spoke."""
        with self.lock:
            last_gm = max((m["id"] for m in self.messages if m["kind"] == "gm"), default=0)
            acted = {party_roster.slugify(m.get("pc", "")) for m in self.messages
                     if m["id"] > last_gm and m["kind"] == "player"}
            names = list(dict.fromkeys(self.seats.values()))
        out = self.out_of_action()
        return [n for n in names if party_roster.slugify(n) not in acted and n not in out]

    # --- seats ---
    def pc_for(self, token: Optional[str]) -> Optional[str]:
        if not token:
            return None
        with self.lock:
            name = self.seats.get(token)
        if name and party_roster.find_pc(self.campaign_dir, name) is None:
            return None  # the PC left the table (or died and was replaced)
        return name

    def claimed_by_anyone(self, name: str) -> bool:
        return any(party_roster._same_name(n, name) for n in self.seats.values())

    def claim(self, name: str) -> Dict[str, Any]:
        path = party_roster.find_pc(self.campaign_dir, name)
        if path is None:
            return {"ok": False, "error": f"No player character named {name}."}
        real = (party_roster._read(path) or {}).get("name", name)
        with self.lock:
            if self.claimed_by_anyone(real):
                return {"ok": False, "error": f"{real} is already being played. Ask the "
                                              f"host to free the seat if that was you."}
            token = secrets.token_urlsafe(18)
            self.seats[token] = real
            self._write_seats()
        return {"ok": True, "token": token, "pc": real}

    def release(self, token: str) -> Optional[str]:
        with self.lock:
            name = self.seats.pop(token, None)
            self._write_seats()
        return name

    def free(self, name: str) -> bool:
        with self.lock:
            tokens = [t for t, n in self.seats.items() if party_roster._same_name(n, name)]
            for t in tokens:
                del self.seats[t]
            self._write_seats()
        return bool(tokens)

    # --- party view ---
    def party_for(self, viewer: Optional[str]) -> List[Dict[str, Any]]:
        """The party as this viewer should see it right now: during the GM's turn,
        the sheets as they were when the turn began — until this viewer's own
        narration is out — so HP, conditions and deaths land with the story,
        not before it. Seats ('claimed') and newcomers are always live."""
        live = self.party()
        with self.lock:
            turn = self.turn
            if not turn or time.time() - turn["started_at"] >= STALE_TURN_SECONDS:
                return live
            lang = self.langs.get(viewer, "en") if viewer else None
            if lang is not None and lang in turn["langs_done"]:
                return live
            held = {p["name"]: p for p in turn.get("party") or []}
        out = []
        for pc in live:
            before = held.get(pc["name"])
            if before is None:
                out.append(pc)
            else:
                out.append({**{k: v for k, v in before.items() if k != "sheet"},
                            "claimed": pc["claimed"], "lead": pc["lead"]})
        return out

    def last_narration(self, viewer: Optional[str]) -> int:
        """Id of the newest GM message this viewer can see. The page holds sheet
        changes until it has that message, so HP never moves ahead of the story."""
        with self.lock:
            for m in reversed(self.messages):
                if m["kind"] == "gm" and self.visible_to(m, viewer):
                    return m["id"]
        return 0

    def sheet(self, viewer: Optional[str], name: str, rev: Optional[str] = None
              ) -> Optional[Dict[str, Any]]:
        """A PC's full character sheet: the version with revision ``rev`` (the
        page asks for the one its party panel is showing — during the GM's turn
        that can still be the sheet from before the turn), else the version this
        viewer's party panel would show now."""
        live = [p for p in self.party(sheets=True) if party_roster._same_name(p["name"], name)]
        with self.lock:
            held = [p for p in ((self.turn or {}).get("party") or [])
                    if party_roster._same_name(p["name"], name)]
        versions = live + held
        if not versions:
            return None
        shown = next((p for p in self.party_for(viewer)
                      if party_roster._same_name(p["name"], name)), None)
        for want in (rev, shown and shown.get("sheet_rev")):
            for v in versions:
                if want and v.get("sheet_rev") == want:
                    return {"name": v["name"], "rev": v["sheet_rev"], "sheet": v["sheet"]}
        v = live[0] if live else versions[0]
        return {"name": v["name"], "rev": v["sheet_rev"], "sheet": v["sheet"]}

    def sheet_for(self, viewer: Optional[str], name: str, rev: Optional[str] = None
                  ) -> Optional[Dict[str, Any]]:
        """sheet(), plus — on the viewer's OWN sheet — what levelling up offers."""
        found = self.sheet(viewer, name, rev)
        if found and viewer and party_roster._same_name(viewer, found["name"]):
            live = party_roster.find_pc(self.campaign_dir, found["name"])
            if live is not None:
                opts = self.level_up_options(
                    found["name"], to_flat(json.loads(live.read_text(encoding="utf-8"))))
                if opts:
                    found["level_up"] = opts
        return found

    def party(self, sheets: bool = False) -> List[Dict[str, Any]]:
        """The PCs, summarised for the party panel. Each carries ``sheet_rev``, a
        fingerprint of the whole sheet, so pages refetch a sheet only when it
        changed; ``sheets=True`` includes the sheets themselves."""
        out = []
        for path, raw in party_roster.all_pcs(self.campaign_dir):
            c = to_flat(raw)
            hp = c.get("hp") or {}
            sheet_json = json.dumps(c, sort_keys=True, ensure_ascii=False, default=str)
            out.append({
                "name": c.get("name", path.stem),
                "lead": path.name == party_roster.LEAD_FILE,
                "level": c.get("level", 1),
                "race": c.get("race", ""), "class": c.get("class", ""),
                "concept": c.get("concept", ""),
                "hp": hp.get("current", 0), "hp_max": hp.get("max", 0),
                "status": c.get("status", "alive"),
                "conditions": c.get("conditions", []),
                "claimed": self.claimed_by_anyone(c.get("name", "")),
                "sheet_rev": hashlib.sha1(sheet_json.encode("utf-8")).hexdigest()[:12],
                "portrait": c.get("portrait"),
                "level_up": max(0, self._level_of(c) - self._built(c.get("name", path.stem),
                                                                   self._level_of(c))),
            })
            if sheets:          # (a copy, in the sheet's own order: STR DEX CON...)
                out[-1]["sheet"] = json.loads(json.dumps(c, ensure_ascii=False, default=str))
        return out

    def overview(self) -> Dict[str, Any]:
        o = self._read_json(self.campaign_dir / "campaign-overview.json", {})
        return {"campaign": o.get("campaign_name") or self.campaign_dir.name,
                "location": (o.get("player_position") or {}).get("current_location"),
                "time": o.get("time_of_day")}

    def abilities(self) -> List[str]:
        """The abilities this campaign's characters have (the classic six by default)."""
        ruleset = self._read_json(self.campaign_dir / "ruleset.json", {})
        schema = ruleset.get("stat_schema") if isinstance(ruleset, dict) else None
        attrs = schema.get("attributes") if isinstance(schema, dict) else None
        names = [str(a) for a in attrs if str(a).strip()] if isinstance(attrs, list) else []
        return names[:12] or list(CLASSIC_SIX)

    def roll_character(self, lang: Optional[str] = None, previous: Optional[str] = None
                       ) -> Dict[str, Any]:
        """Roll a new character: the dice (fair: the OS random source), kept here
        so the scores can't be edited before they're used. ``previous`` (the
        roll it replaces) counts the tries, which the table is told."""
        import dice
        rng = dice._rng
        tries = 1
        with self.lock:
            if previous and previous in self.pending_rolls:
                tries = self.pending_rolls.pop(previous)["tries"] + 1
        abilities = self.abilities()
        rolls = {}
        for a in abilities:
            d = [rng.randint(1, 6) for _ in range(4)]
            low = d.index(min(d))
            rolls[a] = {"dice": d, "dropped": low, "score": sum(d) - d[low]}
        stats = {a: r["score"] for a, r in rolls.items()}
        he = lang == "he"
        name_en, name_he = rng.choice(NAMES)
        roll: Dict[str, Any] = {"stats": stats, "dice": rolls, "tries": tries,
                                "name": name_he if he else name_en}
        if [a.lower() for a in abilities] == CLASSIC_SIX:
            low = {a.lower(): v for a, v in stats.items()}
            best = max(low.values())
            fits = [c for c, (_, _, leans) in CLASSES.items() if any(low[x] == best for x in leans)]
            cls = rng.choice(fits or list(CLASSES))
            race = rng.choice(list(RACES))
            cls_he, hit_die, _ = CLASSES[cls]
            hp = max(1, hit_die + _mod(low["con"]))
            roll.update({"race": race, "class": cls, "hp": hp, "ac": 10 + _mod(low["dex"]),
                         "concept": f"{RACES[race]} {cls_he}" if he else f"a {race.lower()} {cls.lower()}"})
        roll_id = secrets.token_urlsafe(9)
        with self.lock:
            self.pending_rolls[roll_id] = roll
            while len(self.pending_rolls) > MAX_PENDING_ROLLS:
                self.pending_rolls.pop(next(iter(self.pending_rolls)))
        return {"ok": True, "roll_id": roll_id, **roll}

    def apply_roll(self, pc: str, roll_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Write a rolled character's numbers onto the PC just created."""
        with self.lock:
            roll = self.pending_rolls.pop(roll_id, None) if roll_id else None
        path = party_roster.find_pc(self.campaign_dir, pc) if roll else None
        if not roll or path is None:
            return None
        sheet = to_flat(json.loads(path.read_text(encoding="utf-8")))
        sheet["stats"] = dict(roll["stats"])
        for k in ("race", "class", "ac"):
            if k in roll:
                sheet[k] = roll[k]
        if "hp" in roll:
            sheet["hp"] = {"current": roll["hp"], "max": roll["hp"]}
        sheet.setdefault("level", 1)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(sheet, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
        return roll

    # --- levelling up from the sheet ---
    def _built(self, name: str, level: int) -> int:
        with self.lock:
            if name not in self.built_levels:
                self.built_levels[name] = level
                self._save_levels()
            return self.built_levels[name]

    def _save_levels(self) -> None:          # caller holds the lock
        tmp = self.levels_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.built_levels, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.levels_path)

    @staticmethod
    def _level_of(sheet: Dict[str, Any]) -> int:
        try:
            return max(1, int(sheet.get("level") or 1))
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _class_of(sheet: Dict[str, Any]) -> Optional[str]:
        text = str(sheet.get("class") or "").lower()
        return next((c for c in CLASSES if c.lower() in text), None)

    def level_up_options(self, name: str, sheet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """What levelling up offers this PC now, or None when there's nothing to do."""
        level = self._level_of(sheet)
        built = self._built(name, level)
        if built >= level:
            return None
        to = built + 1
        cls = self._class_of(sheet)
        hit_die = None
        raw = sheet.get("hit_die")
        import re
        found = re.search(r"(\d+)\s*$", str(raw or ""))    # 8, "d8", "1d8"
        hit_die = int(found.group(1)) if found and int(found.group(1)) in (4, 6, 8, 10, 12, 20) else None
        if hit_die is None and cls:
            hit_die = CLASSES[cls][1]
        stats = sheet.get("stats") if isinstance(sheet.get("stats"), dict) else {}
        low = {str(k).lower(): v for k, v in stats.items()}
        con = low.get("con", low.get("constitution"))
        classic = sorted(low) == sorted(CLASSIC_SIX) and all(isinstance(v, int) for v in low.values())
        asi = classic and (to in ASI_LEVELS or to in ASI_EXTRA.get(cls or "", set()))
        return {"to": to, "pending": level - built, "hit_die": hit_die,
                "con_mod": _mod(con) if isinstance(con, int) else 0,
                "asi": bool(asi), "abilities": list(stats) if asi else []}

    def level_up(self, pc: str, choice: Dict[str, Any]) -> Dict[str, Any]:
        """Build one level: HP (rolled at the table, or the average), an ability
        score increase where the class gets one, and the player's wishes for the
        GM (subclass, spells, a feat), who adds the class features."""
        path = party_roster.find_pc(self.campaign_dir, pc)
        if path is None:
            return {"ok": False, "error": "No such character."}
        sheet = to_flat(json.loads(path.read_text(encoding="utf-8")))
        name = sheet.get("name", pc)
        opts = self.level_up_options(name, sheet)
        if not opts:
            return {"ok": False, "error": "There's no new level to take yet.", "reason": "none"}
        to = opts["to"]
        asi = {}
        if opts["asi"] and choice.get("asi"):
            stats = sheet["stats"]
            try:
                asi = {k: int(v) for k, v in dict(choice["asi"]).items() if int(v)}
            except (TypeError, ValueError):
                return {"ok": False, "error": "Pick abilities to raise."}
            if (sum(asi.values()) != 2 or any(v not in (1, 2) for v in asi.values())
                    or any(k not in stats for k in asi)
                    or any(stats[k] + v > 20 for k, v in asi.items())):
                return {"ok": False, "error": "Raise one ability by 2, or two by 1 (20 at most)."}
        wish = " ".join(str(choice.get("wish") or "").split())[:400]

        gain, how = None, None
        if opts["hit_die"]:
            mod = opts["con_mod"]
            if choice.get("hp") == "roll":
                notation = f"1d{opts['hit_die']}" + (f"{mod:+d}" if mod else "")
                rolled = self.roll({"notation": notation, "pc": name, "why": f"HP for level {to}",
                                    "why_tr": {"he": f"נקודות חיים לדרגה {to}"}})
                gain, how = max(1, rolled["result"]["total"]), "rolled"
            else:
                gain, how = max(1, opts["hit_die"] // 2 + 1 + mod), "average"
            hp = sheet.get("hp") if isinstance(sheet.get("hp"), dict) else {}
            hp_max = int(hp.get("max") or 0) + gain
            sheet["hp"] = {**hp, "max": hp_max, "current": min(hp_max, int(hp.get("current") or 0) + gain)}
        for k, v in asi.items():
            sheet["stats"][k] += v
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(sheet, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
        with self.lock:
            self.built_levels[name] = to
            self._save_levels()

        parts = [f"{name} reaches level {to}"]
        if gain is not None:
            parts.append(f"HP +{gain} ({how})")
        if asi:
            parts.append(", ".join(f"{k.upper()} +{v}" for k, v in asi.items()))
        line = " · ".join(parts) + "." + (f' Asks: "{wish}"' if wish else "")
        self.append("system", line, pc=name,
                    event={"type": "levelup", "level": to, "hp_gain": gain, "hp_how": how,
                           "asi": asi, "wish": wish})
        return {"ok": True, "level": to, "hp_gain": gain, "asi": asi,
                "more": opts["pending"] - 1}

    # --- portraits and places ---
    def _art_on(self, fake) -> bool:
        if fake is not None:
            return True
        try:
            import image_gen
            return image_gen.images_status()[0]
        except Exception:
            return False

    def _note_visit(self) -> Optional[str]:
        """The party's current location, remembered as visited."""
        here = self.overview().get("location")
        if here and here not in self.visited:
            with self.lock:
                self.visited.append(here)
                tmp = self.places_path.with_suffix(".tmp")
                tmp.write_text(json.dumps({"visited": self.visited}, indent=2, ensure_ascii=False),
                               encoding="utf-8")
                tmp.replace(self.places_path)
        return here

    def place_pass(self, now: Optional[float] = None) -> Optional[str]:
        """Paint the party's current location if it's an important place (the GM
        has written about it) with no picture yet, and show it to the table."""
        import image_gen
        now = now or time.time()
        here = self._note_visit()
        if not here:
            return None
        try:
            found = image_gen.find_location(here, self.campaign_dir)
        except (OSError, ValueError):
            return None
        if not found:
            return None
        _, key, rec = found
        if rec.get("image") and (self.campaign_dir / "images" / str(rec["image"])).is_file():
            return None
        if not image_gen.location_is_important(rec) or not self._art_on(self.place_maker):
            return None
        if now - self.portrait_tried.get("place:" + key, -PORTRAIT_RETRY) < PORTRAIT_RETRY:
            return None
        self.portrait_tried["place:" + key] = now
        try:
            filename = (self.place_maker(key, self.campaign_dir) if self.place_maker is not None
                        else image_gen.generate_location_image(key, self.campaign_dir)["image"])
        except Exception as e:
            print(f"[place] {key}: {e}", flush=True)
            return None
        self.append("system", f"{key}.", image=filename, event={"type": "place", "location": key})
        return key

    # --- foes and treasures: painted once, shown when they appear ---
    def show_foe(self, name: str, boss: bool = False, look: str = "") -> None:
        name = " ".join(str(name).split())
        if look:
            self.enemy_looks[name] = look
        if [name, boss] in self.shown_foes or any(
                j["kind"] == "foe" and j["name"] == name and j["boss"] == boss for j in self.art_jobs):
            return
        self.art_jobs.append({"kind": "foe", "name": name, "boss": boss,
                              "look": look or self.enemy_looks.get(name, "")})
        self.portrait_wake.set()

    def show_loot(self, name: str, look: str = "", owner: str = "") -> None:
        name = " ".join(str(name).split())[:80]
        if name and name not in self.shown_treasures and not any(
                j["kind"] == "loot" and j["name"] == name for j in self.art_jobs):
            self.art_jobs.append({"kind": "loot", "name": name, "look": look, "owner": owner})
            self.portrait_wake.set()

    def _save_gallery(self) -> None:
        with self.lock:
            tmp = self.gallery_path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"foes": self.shown_foes, "treasures": self.shown_treasures},
                                      indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.gallery_path)

    def _post_art(self, job: Dict[str, Any], filename: str) -> None:
        if job["kind"] == "foe":
            self.shown_foes.append([job["name"], job["boss"]])
            self.append("system", f"{job['name']}.", image=filename,
                        event={"type": "foe", "name": job["name"], "boss": job["boss"]})
        else:
            self.shown_treasures.append(job["name"])
            event = {"type": "loot", "name": job["name"]}
            if job.get("owner"):
                event["owner"] = job["owner"]
            self.append("system", f"{job['name']}.", pc=job.get("owner") or None,
                        image=filename, event=event)
        self._save_gallery()

    def _take(self, job: Dict[str, Any]) -> bool:
        """Claim a job (the request thread and the art worker both run passes)."""
        with self.lock:
            if job.get("taken") or job not in self.art_jobs:
                return False
            job["taken"] = True
            return True

    def _finish(self, job: Dict[str, Any], filename: Optional[str]) -> None:
        with self.lock:
            if job in self.art_jobs:
                self.art_jobs.remove(job)
        if filename:
            self._post_art(job, filename)

    def art_pass(self, ready_only: bool = False) -> List[str]:
        """Show the queued foes and treasures: at once when already painted (a foe
        met before), else paint them first (not when ``ready_only``). With no image
        source the jobs are simply dropped: the game goes on in words."""
        import image_gen
        done = []
        for job in list(self.art_jobs):
            if not self._take(job):
                continue
            if job["kind"] == "foe":
                have = image_gen.enemy_art(job["name"], job["boss"], self.campaign_dir)
            else:
                have = image_gen.treasure_art(job["name"], self.campaign_dir)
            if not have:
                maker = self.foe_maker if job["kind"] == "foe" else self.item_maker
                if ready_only:
                    job["taken"] = False                # the worker paints it
                    continue
                if not self._art_on(maker):
                    self._finish(job, None)             # no pictures tonight
                    continue
                try:
                    if job["kind"] == "foe":
                        have = (maker(job["name"], self.campaign_dir, job["boss"], job["look"])
                                if maker else image_gen.generate_enemy_portrait(
                                    job["name"], self.campaign_dir, job["boss"], job["look"])["image"])
                    else:
                        have = (maker(job["name"], self.campaign_dir, job["look"], job["owner"])
                                if maker else image_gen.generate_item_image(
                                    job["name"], self.campaign_dir, job["look"], job["owner"])["image"])
                except Exception as e:
                    print(f"[art] {job['name']}: {e}", flush=True)
                    self._finish(job, None)
                    continue
            self._finish(job, have)
            done.append(job["name"])
        return done

    def gallery(self) -> Dict[str, List[Dict[str, Any]]]:
        """What the players have seen: foes met and treasures found (newest first)."""
        import image_gen
        foes, treasures = [], []
        for name, boss in reversed(self.shown_foes):
            f = image_gen.enemy_art(name, boss, self.campaign_dir)
            if f:
                foes.append({"name": name, "image": f, "boss": bool(boss)})
        table = image_gen._load(self.campaign_dir / "treasures.json")
        for name in reversed(self.shown_treasures):
            f = image_gen.treasure_art(name, self.campaign_dir)
            if f:
                rec = table.get(image_gen._entry(table, name)) or {}
                treasures.append({"name": name, "image": f, "owner": rec.get("owner") or ""})
        return {"foes": foes, "treasures": treasures}

    def places(self) -> List[Dict[str, str]]:
        """Pictures of the places the party has been, newest visit first."""
        try:
            import image_gen
            out = []
            for name in reversed(self.visited):
                found = image_gen.find_location(name, self.campaign_dir)
                img = found and found[2].get("image")
                if img and (self.campaign_dir / "images" / str(img)).is_file():
                    out.append({"name": found[1], "image": img})
            return out
        except (OSError, ValueError):
            return []

    def portrait_pass(self, now: Optional[float] = None) -> List[str]:
        """Draw the portrait of every PC who has none (one at a time; slow on a
        laptop GPU), and show it to the table. Returns the names drawn."""
        now = now or time.time()
        if not self._art_on(self.portrait_maker):
            return []
        drawn = []
        for path, raw in party_roster.all_pcs(self.campaign_dir):
            sheet = to_flat(raw)
            name = sheet.get("name") or path.stem
            if sheet.get("portrait") and (self.campaign_dir / "images" / sheet["portrait"]).is_file():
                continue
            first = self.portrait_seen.setdefault(name, now)
            if not sheet.get("visual_appearance") and now - first < PORTRAIT_GRACE:
                continue                    # give the GM a moment to write their look
            if now - self.portrait_tried.get(name, -PORTRAIT_RETRY) < PORTRAIT_RETRY:
                continue
            self.portrait_tried[name] = now
            try:
                if self.portrait_maker is not None:
                    filename = self.portrait_maker(name, self.campaign_dir)
                else:
                    import image_gen
                    filename = image_gen.generate_portrait(name, self.campaign_dir)["portrait"]
            except Exception as e:          # no GPU memory, service down...: try later
                print(f"[portrait] {name}: {e}", flush=True)
                continue
            self.append("system", f"{name}'s portrait.", pc=name, image=filename,
                        event={"type": "portrait"})
            drawn.append(name)
        return drawn

    def portrait_worker(self) -> None:
        while True:
            self.portrait_wake.wait(30)
            self.portrait_wake.clear()
            self.music_tick()
            # The scene first; composing (minutes each) last, so pictures don't wait on it.
            for job in (self.place_pass, self.art_pass, self.portrait_pass, self.music_pass):
                try:
                    job()
                except Exception as e:
                    print(f"[art] {e}", flush=True)

    def create_pc(self, mode: str, name: str, concept: str) -> Dict[str, Any]:
        from identity_onboarding import IdentityOnboarding
        # Always THIS table's campaign — never whichever campaign happens to be
        # active now (the host may have switched since the table opened).
        onboarding = IdentityOnboarding(self.base, campaign_dir=self.campaign_dir)
        if mode == "nameless":
            result = onboarding.join("nameless")
        else:
            result = onboarding.join("original", name=name, concept=concept)
        if not result.get("success"):
            return {"ok": False, "error": result.get("error", "could not create character")}
        return {"ok": True, "pc": result["character"].get("name", name)}


# ============================================================ HTTP layer =====

def make_handler(state: TableState, code: str, host_key: str):
    page = (Path(__file__).parent / "table_page.html").read_text(encoding="utf-8")

    class Handler(BaseHTTPRequestHandler):
        server_version = "GMTable/1.0"

        def log_message(self, fmt, *args):  # keep the host's terminal quiet
            pass

        # --- helpers ---
        def _send(self, status: int, body: bytes, ctype: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data: Any, status: int = 200) -> None:
            self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")

        def _err(self, msg: str, status: int = 400) -> None:
            self._json({"ok": False, "error": msg}, status)

        def _body(self) -> Dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise ValueError("request too large")
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(data, dict):
                raise ValueError("expected a JSON object")
            return data

        def _code_ok(self, supplied: Optional[str]) -> bool:
            return hmac.compare_digest(str(supplied or "").strip().lower(), code.lower())

        def _is_host(self) -> bool:
            return hmac.compare_digest(self.headers.get("X-Host-Key", ""), host_key)

        # --- routes ---
        def do_GET(self):
            url = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            if url.path in ("/", "/index.html"):
                return self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
            if url.path.startswith("/music/"):
                if not self._code_ok(q.get("code")):
                    return self._err("bad table code", 403)
                return self._audio(url.path[len("/music/"):])
            if url.path.startswith("/images/"):
                if not self._code_ok(q.get("code")):
                    return self._err("bad table code", 403)
                return self._image(url.path[len("/images/"):])
            if url.path.startswith("/api/gm/"):
                if not self._is_host():
                    return self._err("host only", 403)
                if url.path == "/api/gm/pending":
                    return self._json({"ok": True, "round": state.round_state(),
                                   "unread": len(state.gm_unread(mark=False)),
                                   "waiting_on": state.waiting_on(),
                                   "seated": sorted(set(state.seats.values())),
                                   "langs": state.seated_langs()})
                return self._err("not found", 404)
            if not self._code_ok(q.get("code")):
                return self._err("bad table code", 403)
            me = state.pc_for(q.get("token"))
            if url.path == "/api/info":
                state.music_tick()
                return self._json({"ok": True, "me": me, "party": state.party_for(me),
                                   "waiting_on": state.waiting_on(),
                                   "music": state.music, "server_now": time.time(),
                                   "progress": state.progress(), "tts": state.tts_ready(),
                                   "places": state.places(), **state.gallery(),
                                   "round": state.round_state(),
                                   "narration_id": state.last_narration(me),
                                   **state.overview()})
            if url.path == "/api/messages":
                try:
                    after = int(q.get("after", 0))
                    rev = int(q.get("rev", 0))
                except ValueError:
                    after, rev = 0, 0
                return self._json({"ok": True, "me": me, "rev": state.rev,
                                   "messages": state.since(after, me, rev)})
            if url.path == "/api/narrator":
                if not me:
                    return self._err("Take a seat first.", 403)
                return self._json({"ok": True, "entries": state.narrator_log.get(me, [])})
            if url.path == "/api/chat":
                if not me:                      # seated players only: never the host key
                    return self._err("Take a seat first.", 403)
                try:
                    after = int(q.get("after", 0))
                except ValueError:
                    after = 0
                return self._json({"ok": True, "messages": state.chat_since(after)})
            if url.path == "/api/sheet":
                if not me:
                    return self._err("Take a seat first.", 403)
                found = state.sheet_for(me, q.get("pc", ""), q.get("rev"))
                if found is None:
                    return self._err("No such character.", 404)
                return self._json({"ok": True, **found})
            if url.path == "/api/tts":
                if not me:
                    return self._err("Take a seat first.", 403)
                try:
                    path = state.speech(q.get("text", ""), q.get("voice", ""))
                except ValueError as e:
                    return self._err(str(e))
                except table_tts.Unavailable as e:
                    return self._err(str(e), 503)
                return self._serve_file(path, "audio/mpeg", cache=True)
            return self._err("not found", 404)

        def do_POST(self):
            url = urlparse(self.path)
            try:
                data = self._body()
            except (ValueError, UnicodeDecodeError) as e:
                return self._err(str(e))
            if url.path.startswith("/api/gm/"):
                if not self._is_host():
                    return self._err("host only", 403)
                return self._gm(url.path, data)
            if not self._code_ok(data.get("code")):
                return self._err("bad table code", 403)

            if url.path == "/api/claim":
                result = state.claim(str(data.get("pc", "")))
                if result["ok"]:
                    state.append("system", f"{result['pc']} takes their seat at the table.",
                                 pc=result["pc"], event={"type": "seat"})
                return self._json(result, 200 if result["ok"] else 409)

            if url.path == "/api/roll-character":
                lang = data.get("lang") if data.get("lang") in LANGS else None
                return self._json(state.roll_character(lang, data.get("previous")))

            if url.path == "/api/create":
                name = " ".join(str(data.get("name", "")).split())[:60]
                concept = " ".join(str(data.get("concept", "")).split())[:200]
                mode = "nameless" if data.get("mode") == "nameless" else "original"
                if mode == "original" and not name:
                    return self._err("Give your character a name.")
                created = state.create_pc(mode, name, concept)
                if not created["ok"]:
                    existing = party_roster.find_pc(state.campaign_dir, name) if name else None
                    if existing is not None and not state.claimed_by_anyone(name):
                        created["error"] = (f"{name} is already at the table with an empty seat — "
                                            f"pick them in the list above to play them.")
                        created["existing"] = name
                    return self._json(created, 409)
                rolled = state.apply_roll(created["pc"], data.get("roll_id"))
                result = state.claim(created["pc"])
                if result["ok"]:
                    line = f"A new player joins: {created['pc']}"
                    line += f" — {concept}." if concept else "."
                    event = {"type": "join", "concept": concept}
                    if rolled:
                        scores = ", ".join(f"{a.upper()} {v}" for a, v in rolled["stats"].items())
                        line += (f" Rolled: {scores}"
                                 + (f" ({rolled['race']} {rolled['class']}, HP {rolled['hp']}, "
                                    f"AC {rolled['ac']})" if "class" in rolled else "")
                                 + (f" — roll #{rolled['tries']}." if rolled["tries"] > 1 else "."))
                        event["rolled"] = {k: rolled[k] for k in
                                           ("stats", "dice", "tries", "race", "class", "hp", "ac")
                                           if k in rolled}
                    state.append("system", line, pc=created["pc"], event=event)
                    state.portrait_wake.set()        # start on their portrait
                return self._json(result, 200 if result["ok"] else 409)

            me = state.pc_for(data.get("token"))
            if url.path == "/api/say":
                if not me:
                    return self._err("Take a seat first.", 403)
                text = str(data.get("text", "")).strip()
                if not text:
                    return self._err("Say something.")
                if len(text) > MAX_PLAYER_TEXT:
                    return self._err(f"Keep it under {MAX_PLAYER_TEXT} characters.")
                private = bool(data.get("private"))
                lang = data.get("lang") if data.get("lang") in LANGS else None
                state.set_lang(me, lang)
                msg = state.append("player", text, pc=me, to=me if private else None,
                                   lang=lang, voice=bool(data.get("voice")))
                return self._json({"ok": True, "message": msg})

            if url.path == "/api/edit":
                if not me:
                    return self._err("Take a seat first.", 403)
                text = str(data.get("text", "")).strip()
                if not text:
                    return self._err("Say something.")
                if len(text) > MAX_PLAYER_TEXT:
                    return self._err(f"Keep it under {MAX_PLAYER_TEXT} characters.")
                result = state.edit(me, data.get("id"), text)
                return self._json(result, 200 if result["ok"] else 409)

            if url.path == "/api/chat":
                if not me:
                    return self._err("Take a seat first.", 403)
                text = " ".join(str(data.get("text", "")).split())
                if not text:
                    return self._err("Say something.")
                if len(text) > CHAT_TEXT:
                    return self._err(f"Keep it under {CHAT_TEXT} characters.")
                return self._json({"ok": True, "message": state.chat_post(me, text)})

            if url.path == "/api/narrator":
                if not me:
                    return self._err("Take a seat first.", 403)
                question = " ".join(str(data.get("question", "")).split())[:400]
                if not question:
                    return self._err("Ask something.")
                result = state.narrator_question(me, question)
                return self._json(result, 200 if result["ok"] else 429)

            if url.path == "/api/level-up":
                if not me:
                    return self._err("Take a seat first.", 403)
                result = state.level_up(me, data)
                return self._json(result, 200 if result["ok"] else 409)

            if url.path == "/api/lang":
                if not me:
                    return self._err("Take a seat first.", 403)
                state.set_lang(me, data.get("lang"))
                return self._json({"ok": True})

            if url.path == "/api/leave":
                name = state.release(str(data.get("token", "")))
                if name:
                    state.append("system", f"{name} steps away from the table.", pc=name,
                                 event={"type": "leave"})
                return self._json({"ok": True})
            return self._err("not found", 404)

        def _gm(self, path: str, data: Dict[str, Any]):
            if path == "/api/gm/inbox":
                rnd = state.round_state()
                if rnd["open"]:
                    # The players are still acting: their actions wait for the round.
                    return self._json({"ok": True, "messages": [], "held": True, "round": rnd,
                                       "waiting_on": rnd["waiting_on"], "langs": state.seated_langs(),
                                       "music": state.music, "auto_music": state.auto_music})
                unread = state.gm_unread(mark=True)
                return self._json({"ok": True, "messages": unread,
                                   "waiting_on": state.waiting_on(),
                                   "langs": state.seated_langs(),
                                   "translate": state.needs_translation(),
                                   "music": state.music, "auto_music": state.auto_music})
            if path == "/api/gm/say":
                text = str(data.get("text", "")).strip()
                image = data.get("image")
                if image:
                    image = Path(str(image)).name
                    if not (state.campaign_dir / "images" / image).is_file():
                        return self._err(f"no image named {image} in the campaign's images/")
                if not text and not image:
                    return self._err("nothing to say")
                rnd = state.round_state()
                if not data.get("to") and rnd["open"] and not state.gm_read_since_narration():
                    left = max(0, int(rnd["deadline"] - time.time()))
                    return self._json({"ok": False, "round": rnd, "error": (
                        f"The players are still acting — waiting for {', '.join(rnd['waiting_on'])} "
                        f"(the round closes in {left} s). Run: bash tools/gm-table.sh wait")}, 409)
                if len(text) > MAX_TEXT * 4:
                    return self._err("narration too long; split it into beats")
                to = data.get("to")
                if to:
                    path_ = party_roster.find_pc(state.campaign_dir, str(to))
                    if path_ is None:
                        return self._err(f"no player character named {to}")
                    to = (party_roster._read(path_) or {}).get("name", to)
                lang = data.get("lang")
                if lang and lang not in LANGS:
                    return self._err(f"unknown language {lang} (use: {', '.join(LANGS)})")
                mood = data.get("mood")
                if mood and mood not in MOODS and mood != SILENCE:
                    return self._err(f"unknown mood {mood} (use: {', '.join(list(MOODS) + [SILENCE])})")
                theme = " ".join(str(data.get("theme") or "").split())[:80]
                if theme and data.get("look"):
                    state.enemy_looks[theme] = " ".join(str(data["look"]).split())[:300]
                state.music_tick()
                # The music changes first, so it is already swelling as the beat is read.
                # An enemy's theme (an always-explicit choice) wins over the mood.
                music = None
                if not to and theme:
                    music = state.apply_theme(theme, boss=bool(data.get("boss")) or mood == "boss")
                elif not to and mood:
                    music = state.apply_mood(mood)
                if not to and theme and data.get("villain"):
                    state.queue_theme(theme, False)      # a main villain: compose their theme
                hero = " ".join(str(data.get("heroic") or "").split())[:60]
                if not to and hero:
                    music = state.heroic_moment(hero)    # their anthem, then back to the scene
                if music is not None:
                    self._announce_music(music)
                msg = state.append("gm", text, to=to or None, image=image, lang=lang)
                loot = " ".join(str(data.get("loot") or "").split())
                if loot and not to:
                    state.show_loot(loot, " ".join(str(data.get("loot_look") or "").split())[:300],
                                    " ".join(str(data.get("loot_for") or "").split())[:60])
                state.art_pass(ready_only=True)   # a foe met before shows up with the beat
                warning = None
                seated = state.seated_langs()
                table_langs = set(seated.values())
                if to:
                    want = seated.get(to) or next((l for n, l in seated.items()
                                                   if party_roster._same_name(n, to)), None)
                    if want and text and state.text_lang(text) != want:
                        warning = (f"{to} plays in {LANGS[want]} — whisper in {LANGS[want]}.")
                elif not lang and text and len(table_langs) > 1:
                    wrote = state.text_lang(text)
                    others = sorted(LANGS[l] for l in table_langs if l != wrote)
                    warning = (f"Mixed table: this beat has no --lang, so {', '.join(others)} "
                               f"players get it in {LANGS[wrote]}. Next time post one version "
                               f"per language with --lang.")
                return self._json({"ok": True, "message": msg, "music": music,
                                   "warning": warning})
            if path == "/api/gm/music":
                if "auto" in data:
                    state.set_auto_music(bool(data["auto"]))
                    return self._json({"ok": True, "auto": state.auto_music})
                if data.get("theme"):
                    name = " ".join(str(data["theme"]).split())[:80]
                    if "assign" in data:
                        track = data.get("assign")
                        if track and not str(track).startswith(("http://", "https://")):
                            found = state.find_music(str(track))
                            if found is None:
                                return self._err(f"no music file named {track} in music/")
                            track = found.name
                        state.assign_theme(name, track or None)
                        return self._json({"ok": True, "theme": name,
                                           "track": state.theme_track(name)})
                    music = state.apply_theme(name, boss=bool(data.get("boss")))
                    if music is not None:
                        self._announce_music(music)
                    return self._json({"ok": True, "music": music or state.music})
                if data.get("mood"):
                    mood = data["mood"]
                    if mood not in MOODS and mood != SILENCE:
                        return self._err(f"unknown mood {mood}")
                    music = state.apply_mood(mood, force=True)
                    if music is not None:
                        self._announce_music(music)
                    return self._json({"ok": True, "music": music or state.music})
                track = data.get("track")
                if track in (None, "", "stop", "off", "none"):
                    music = state.set_music(None)
                    state.append("system", "🎵 The music fades away.",
                                 event={"type": "music_stop"})
                    return self._json({"ok": True, "music": music})
                track = str(track).strip()
                if track.startswith("ambient:"):
                    if track.split(":", 1)[1] not in AMBIENT:
                        return self._err("unknown ambience; choose from: "
                                         + ", ".join("ambient:" + a for a in AMBIENT))
                elif track.startswith(("http://", "https://")):
                    pass
                else:
                    found = state.find_music(track)
                    if found is None:
                        return self._err(f"no music file named {track} in music/ "
                                         f"(gm-table.sh music list)")
                    track = found.name
                try:
                    volume = float(data.get("volume", 0.5))
                except (TypeError, ValueError):
                    return self._err("volume must be a number between 0 and 1")
                music = state.set_music(track, volume, data.get("loop", True) is not False,
                                        data.get("title"))
                self._announce_music(music)
                return self._json({"ok": True, "music": music})
            if path == "/api/gm/roll":
                result = state.roll(data)
                return self._json(result, 200 if result.get("ok") else 400)
            if path == "/api/gm/translate":
                updated = state.translate(data.get("translations") or {})
                return self._json({"ok": True, "updated": updated,
                                   "still_needed": state.needs_translation()})
            if path == "/api/gm/shutdown":
                # Graceful stop on every platform (no Unix signals needed).
                self._json({"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if path == "/api/gm/activity":
                return self._json({"ok": state.set_stage(str(data.get("stage", "")))})
            if path == "/api/gm/round":
                if "seconds" in data:
                    try:
                        state.set_round_seconds(int(data["seconds"]))
                    except (TypeError, ValueError):
                        return self._err("seconds must be a number (0 = off)")
                return self._json({"ok": True, "seconds": state.round_seconds,
                                   "round": state.round_state()})
            if path == "/api/gm/free":
                freed = state.free(str(data.get("pc", "")))
                return self._json({"ok": True, "freed": freed})
            return self._err("not found", 404)

        def _announce_music(self, music: Dict[str, Any]) -> None:
            state.announce_music(music)

        def _audio(self, name: str):
            from urllib.parse import unquote
            path = state.find_music(unquote(name))
            if path is None:
                return self._err("not found", 404)
            return self._serve_file(path, AUDIO_TYPES[path.suffix.lower()])

        def _serve_file(self, path: Path, ctype: str, cache: bool = False):
            """A file, with byte ranges (audio seeking; Safari insists on them)."""
            size = path.stat().st_size
            start, end = 0, size - 1
            rng = self.headers.get("Range", "")
            partial = rng.startswith("bytes=")
            if partial:
                try:
                    a, b = rng[6:].split(",")[0].split("-")
                    if a:
                        start = int(a)
                        end = int(b) if b else size - 1
                    else:                      # suffix range: the last N bytes
                        start = max(0, size - int(b))
                    end = min(end, size - 1)
                    if start > end:
                        raise ValueError
                except ValueError:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
            length = end - start + 1
            self.send_response(206 if partial else 200)
            self.send_header("Content-Type", ctype)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(length))
            if cache:                      # same text + voice = same audio
                self.send_header("Cache-Control", "private, max-age=86400")
            if partial:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            with open(path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(65536, remaining))
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError):
                        return
                    remaining -= len(chunk)

        def _image(self, name: str):
            name = Path(name).name
            path = state.campaign_dir / "images" / name
            ctype = IMAGE_TYPES.get(path.suffix.lower())
            if not ctype or not path.is_file():
                return self._err("not found", 404)
            return self._send(200, path.read_bytes(), ctype)

    return Handler


class _TableHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer without the reverse-DNS lookup in server_bind
    (socket.getfqdn), which can stall startup for many seconds on macOS. The
    name it looks up is never used."""
    daemon_threads = True

    def server_bind(self):
        import socketserver
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name, self.server_port = str(host), port


# ============================================================ host side ======

def _lan_ip() -> str:
    """Best guess at this machine's LAN address (no packet is sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def _active_campaign() -> tuple:
    mgr = CampaignManager()
    camp = mgr.get_active_campaign_dir()
    if camp is None:
        sys.exit("[ERROR] No active campaign. Pick one with gm-campaign.sh switch <name>.")
    return Path(camp).resolve(), str(mgr.world_state_dir)


def _server_info(campaign_dir: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads((table_dir(campaign_dir) / "server.json").read_text())
    except (OSError, ValueError):
        return None


def _alive(pid: Optional[int]) -> bool:
    """Is that process still running? (Never signals it: on Windows os.kill(pid, 0)
    would send it a Ctrl-C.)"""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(code))) \
                and code.value == 259                       # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True        # running, under another user
    except OSError:
        return False


def _open_tables(base: str) -> List[tuple]:
    """(campaign_dir, server info) for every table that is open right now, in any
    campaign — the host may have switched campaigns since one was opened."""
    out = []
    campaigns = Path(base) / "campaigns"
    if not campaigns.is_dir():
        return out
    for info_path in sorted(campaigns.glob("*/table/server.json")):
        camp = info_path.parent.parent.resolve()
        info = _server_info(camp)
        if info and _alive(info.get("pid")):
            out.append((camp, info))
    return out


def _stop_server(campaign_dir: Path, info: Dict[str, Any]) -> bool:
    """Close one table: ask it to shut down, else end the process."""
    pid = info.get("pid")
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{info['port']}/api/gm/shutdown", method="POST", data=b"{}",
            headers={"X-Host-Key": info.get("host_key", ""), "Content-Type": "application/json"})
        urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=5).read()
    except (OSError, ValueError, KeyError):
        pass
    for _ in range(50):
        if not _alive(pid):
            break
        time.sleep(0.1)
    if _alive(pid):
        try:
            os.kill(int(pid), signal.SIGTERM)   # on Windows this ends the process
        except (OSError, ValueError):
            pass
        for _ in range(30):
            if not _alive(pid):
                break
            time.sleep(0.1)
    (table_dir(campaign_dir) / "server.json").unlink(missing_ok=True)
    return not _alive(pid)


def _start_server(campaign_dir: Path, base: str, port: int, bind: str,
                  code: Optional[str]) -> None:
    """Open the table in the background (detached, so it outlives this command),
    on Windows, macOS and Linux alike."""
    import subprocess
    tdir = table_dir(campaign_dir)
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / "server.json").unlink(missing_ok=True)
    args = [sys.executable, str(Path(__file__).resolve()), "serve", "--port", str(port),
            "--bind", bind] + (["--code", code] if code else [])
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    kwargs: Dict[str, Any] = {"stdin": subprocess.DEVNULL, "env": env,
                              "cwd": str(Path.cwd())}
    if os.name == "nt":
        kwargs["creationflags"] = (subprocess.CREATE_NEW_PROCESS_GROUP
                                   | getattr(subprocess, "DETACHED_PROCESS", 0x8)
                                   | getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        kwargs["start_new_session"] = True
    with open(tdir / "server.log", "w", encoding="utf-8") as log:
        proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, **kwargs)
    started = time.time()
    while time.time() - started < 30:          # a slow first start is fine; a dead one isn't
        if (tdir / "server.json").exists() or proc.poll() is not None:
            break
        time.sleep(0.1)
    time.sleep(0.2)
    print((tdir / "server.log").read_text(encoding="utf-8", errors="replace").rstrip())
    if not (tdir / "server.json").exists():
        code_now = proc.poll()
        state = (f"it exited with code {code_now}" if code_now is not None
                 else f"it is still starting after {time.time() - started:.0f} s")
        sys.exit(f"[ERROR] The table server did not start: {state} (log above).")
    print("\nPlayers: open the link and enter the table code.")
    print("Friends elsewhere: run a tunnel (see: gm-table.sh help) and share its https link.")


def roll_at_table(spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Have the open table roll (lib/dice.py calls this). None when no table is
    open for the active campaign — then the caller rolls locally as before."""
    try:
        camp = CampaignManager().get_active_campaign_dir()
    except Exception:
        return None
    if camp is None:
        return None
    info = _server_info(Path(camp).resolve())
    if not info or not _alive(info.get("pid")):
        return None
    req = urllib.request.Request(
        f"http://127.0.0.1:{info['port']}/api/gm/roll", method="POST",
        data=json.dumps(spec).encode("utf-8"),
        headers={"X-Host-Key": info["host_key"], "Content-Type": "application/json"})
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except ValueError:
            return {"ok": False, "error": f"HTTP {e.code}"}
    except (urllib.error.URLError, OSError):
        return None          # table unreachable: roll locally rather than fail the game


def _wrong_campaign_hint(campaign_dir: Path, base: str) -> Optional[str]:
    others = [(c, i) for c, i in _open_tables(base) if c != campaign_dir]
    if not others:
        return None
    camp, _info = others[0]
    return (f"[ERROR] The table is open for campaign '{camp.name}', but the active campaign is "
            f"'{campaign_dir.name}' — players are seeing '{camp.name}'.\n"
            f"  Move the table to this campaign (same link and code): bash tools/gm-table.sh start\n"
            f"  Or switch back: bash tools/gm-campaign.sh switch {camp.name}")


def serve(port: int, bind: str, code: Optional[str]) -> None:
    campaign_dir, base = _active_campaign()
    info = _server_info(campaign_dir)
    if info and _alive(info.get("pid")) and info.get("pid") != os.getpid():
        sys.exit(f"[ERROR] The table is already open (pid {info['pid']}, port {info['port']}). "
                 f"Use gm-table.sh stop first.")
    code = (code or f"{secrets.choice(CODE_WORDS)}-{secrets.randbelow(900) + 100}").lower()
    host_key = secrets.token_urlsafe(24)
    state = TableState(campaign_dir, base)
    try:
        httpd = _TableHTTPServer((bind, port), make_handler(state, code, host_key))
    except OSError as e:
        sys.exit(f"[ERROR] Port {port} is not available ({e.strerror or e}). Another table or "
                 f"program is using it — try: bash tools/gm-table.sh start --port {port + 1}")
    httpd.daemon_threads = True
    threading.Thread(target=state.portrait_worker, daemon=True).start()
    lan = _lan_ip()
    record = {"campaign": campaign_dir.name, "port": port, "bind": bind, "code": code,
              "host_key": host_key,
              "pid": os.getpid(), "started": _now(),
              "local_url": f"http://localhost:{port}/",
              "lan_url": f"http://{lan}:{port}/"}
    info_path = table_dir(campaign_dir) / "server.json"
    info_path.write_text(json.dumps(record, indent=2))
    try:
        os.chmod(info_path, 0o600)
    except OSError:
        pass
    print(f"TABLE OPEN for campaign '{campaign_dir.name}'")
    print(f"  On this computer:   {record['local_url']}")
    print(f"  Same Wi-Fi/network: {record['lan_url']}")
    print(f"  Table code:         {code}")
    print("  Over the internet:  expose this port with a tunnel (see gm-table.sh help)")
    sys.stdout.flush()

    def _shutdown(*_):
        threading.Thread(target=httpd.shutdown, daemon=True).start()
    try:
        signal.signal(signal.SIGTERM, _shutdown)
    except (ValueError, OSError, AttributeError):
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        current = _server_info(campaign_dir)
        if current and current.get("pid") == os.getpid():
            info_path.unlink(missing_ok=True)


def _call(campaign_dir: Path, method: str, path: str, data: Optional[dict] = None) -> dict:
    info = _server_info(campaign_dir)
    if not info or not _alive(info.get("pid")):
        hint = _wrong_campaign_hint(campaign_dir, str(CampaignManager().world_state_dir))
        sys.exit(hint or "[ERROR] The table is not open. Start it with: bash tools/gm-table.sh start")
    req = urllib.request.Request(
        f"http://127.0.0.1:{info['port']}{path}", method=method,
        data=json.dumps(data).encode("utf-8") if data is not None else None,
        headers={"X-Host-Key": info["host_key"], "Content-Type": "application/json"})
    # The host talks to its own server directly, never through an HTTP proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except ValueError:
            return {"ok": False, "error": f"HTTP {e.code}"}
    except urllib.error.URLError as e:
        sys.exit(f"[ERROR] Could not reach the table server: {e.reason}")


def _print_translate_request(needed: List[dict]) -> None:
    """Tell the GM exactly what to translate, as a ready-to-fill command."""
    if not needed:
        return
    print("\nTRANSLATE for the table (players each read one language) — one call, before you narrate:")
    for item in needed:
        to = ", ".join(LANGS[l] for l in item["to"])
        print(f"  #{item['id']} {item.get('pc') or '?'} ({LANGS.get(item['from'], item['from'])} -> {to}): "
              f"{item['text']}")
    example = {str(item["id"]): {l: "..." for l in item["to"]} for item in needed}
    print("  bash tools/gm-table.sh translate --stdin <<'JSON'")
    print("  " + json.dumps(example, ensure_ascii=False))
    print("  JSON")


def _print_messages(messages: List[dict], waiting_on: List[str],
                    langs: Optional[Dict[str, str]] = None,
                    music: Optional[Dict[str, Any]] = None, auto_music: bool = True,
                    translate: Optional[List[dict]] = None) -> None:
    if not messages:
        print("(no new player messages)")
    for m in messages:
        if m["kind"] == "system":
            kind = str((m.get("event") or {}).get("type", ""))
            if kind == "levelup":
                print(f"[#{m['id']} LEVEL UP] {m['text']} -> HP and ability scores are done; add "
                      f"level {m['event'].get('level')}'s class features/spells to the sheet "
                      f"(gm-player.sh), honouring what they asked if the rules allow, and "
                      f"celebrate it in the story.")
                continue
            if kind in ("foe", "loot"):
                what = ("BOSS" if m["event"].get("boss") else "FOE") if kind == "foe" else "LOOT"
                print(f"[#{m['id']} {what} PICTURE] {m['event'].get('name')} — shown to the table "
                      f"({m.get('image')}).")
                continue
            if kind == "place":
                print(f"[#{m['id']} PLACE] The table painted {m['event'].get('location')} and "
                      f"showed everyone ({m.get('image')}) — no need to illustrate its "
                      f"establishing shot yourself.")
                continue
            if kind == "portrait":
                print(f"[#{m['id']} PORTRAIT] {m['text']} (shown to the table: {m.get('image')})")
                continue
            label = "MUSIC" if kind.startswith("music") else "JOIN/LEAVE"
            print(f"[#{m['id']} {label}] {m['text']}")
            if kind == "join":
                print(f"   -> welcome {m.get('pc')} in the fiction. If scene images are ENABLED, "
                      f"write their look now (bash tools/gm-player.sh set-appearance "
                      f"\"{m.get('pc')}\" --sex … --age … --race … --hair … --face … --eyes … "
                      f"--clothing … --gear … --demeanor … --size …): the table draws their "
                      f"portrait from it within a few minutes.")
        else:
            tags = [LANGS[m["lang"]]] if m.get("lang") in LANGS else []
            if m.get("voice"):
                tags.append("spoken")
            if m.get("to"):
                tags.append("private, to GM only")
            if m.get("corrected_from") is not None:
                tags.append("CORRECTED — use this version; you read: "
                            + json.dumps(m["corrected_from"], ensure_ascii=False))
            elif m.get("edited"):
                tags.append("edited")
            tag = f" ({', '.join(tags)})" if tags else ""
            print(f"[#{m['id']} {m.get('pc', '?')}{tag}] {m['text']}")
    if waiting_on:
        print(f"Still waiting on: {', '.join(waiting_on)}")
    if langs:
        used = sorted(set(langs.values()))
        if len(used) > 1:
            print("Table languages: " + ", ".join(f"{pc}={LANGS.get(l, l)}" for pc, l in langs.items())
                  + "  -> post each beat once per language: say --lang he / say --lang en")
        elif used and used[0] != "en":
            print(f"Table language: {LANGS.get(used[0], used[0])} -> narrate in it")
    _print_translate_request(translate or [])
    if auto_music and music is not None:
        mood = music.get("mood")
        playing = music.get("title") if music.get("track") else "silence"
        if music.get("theme") and music.get("track"):
            playing += (f" ({'BOSS ' if music.get('boss') else ''}enemy theme — holds through "
                        f"{'/'.join(sorted(THEME_HOLDS_THROUGH))}"
                        + ("" if music.get("boss") else "; --mood boss escalates it") + ")")
        print(f"Scene mood: {mood or '(not set)'} — playing: {playing}. Add --mood to your "
              f"next say when the scene's feel changes ({', '.join(MOODS)}, {SILENCE}); "
              f"--theme \"<name>\" when a special enemy enters.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Online table for remote players")
    sub = parser.add_subparsers(dest="action")

    st = sub.add_parser("start", help="Open the table in the background (moves an open table "
                                       "to the active campaign)")
    st.add_argument("--port", type=int, help=f"default {DEFAULT_PORT} (or the open table's)")
    st.add_argument("--bind", default="0.0.0.0")
    st.add_argument("--code", help="Table code (default: the open table's, else random)")

    p = sub.add_parser("serve", help="Run the table server in the foreground")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--bind", default="0.0.0.0", help="Address to listen on (default all)")
    p.add_argument("--code", help="Table code players must enter (default: random)")

    sub.add_parser("status", help="Is the table open? URLs, code, seats")
    sub.add_parser("inbox", help="Print unread player messages and mark them read")

    w = sub.add_parser("wait", help="Block until players act, then print their messages")
    w.add_argument("--timeout", type=int, default=540, help="Give up after N seconds")
    w.add_argument("--settle", type=float, default=4.0,
                   help="After the first message, wait this long for others to chime in")
    w.add_argument("--all", action="store_true",
                   help="Wait until EVERY seated player has acted (or timeout)")

    s = sub.add_parser("say", help="Post GM narration to every player's screen")
    s.add_argument("text", nargs="?", help="The narration (or use --stdin)")
    s.add_argument("--stdin", action="store_true", help="Read the narration from stdin")
    s.add_argument("--to", help="Whisper to one player character only")
    s.add_argument("--image", help="Attach an image from the campaign's images/ folder")
    s.add_argument("--lang", choices=sorted(LANGS),
                   help="This is the version of the beat for players in this language only")
    s.add_argument("--mood", choices=list(MOODS) + [SILENCE],
                   help="The scene's mood; the music follows it (no change if it's the same)")
    s.add_argument("--theme", metavar="ENEMY",
                   help="A special enemy enters: play their own theme music")
    tr = sub.add_parser("translate", help="Translate players' actions for the rest of the table")
    tr.add_argument("json", nargs="?", help='{"12": {"en": "..."}, "13": {"he": "..."}} (or --stdin)')
    tr.add_argument("--stdin", action="store_true", help="Read the JSON from stdin")

    s.add_argument("--boss", action="store_true",
                   help="With --theme: this is a boss — play the fast, thundering version")
    s.add_argument("--look", help="With --theme: what the foe looks like (for their portrait)")
    s.add_argument("--villain", action="store_true",
                   help="With --theme: a MAIN villain — compose them a theme (if the composer is set up)")
    s.add_argument("--heroic", metavar="PC",
                   help="This PC just did something heroic: their anthem plays, then the scene's music")
    s.add_argument("--loot", metavar="ITEM", help="Important loot is found: paint it for the table")
    s.add_argument("--loot-look", help="With --loot: what it looks like")
    s.add_argument("--loot-for", metavar="PC", help="With --loot: who takes it")

    mu = sub.add_parser("music", help="Set the shared background music for every player")
    mu.add_argument("track", nargs="?",
                    help="A file in music/, an https audio link, ambient:<name>, "
                         "'list' to see choices, 'stop', or 'auto on|off'")
    mu.add_argument("value", nargs="?", help="on/off after 'auto'; the enemy after 'theme'")
    mu.add_argument("extra", nargs="?",
                    help="After 'theme <enemy>': the file / https link to make their theme "
                         "('none' to go back to the generated one)")
    mu.add_argument("--mood", choices=list(MOODS) + [SILENCE],
                    help="Play whatever fits this mood (same choice as say --mood)")
    mu.add_argument("--boss", action="store_true", help="With 'theme <enemy>': the boss version")
    mu.add_argument("--volume", type=float, default=0.5, help="0.0 – 1.0 (default 0.5)")
    mu.add_argument("--no-loop", action="store_true", help="Play once instead of looping")
    mu.add_argument("--title", help="What players see (default: from the file name)")

    f = sub.add_parser("free", help="Free a player's seat so they can rejoin from another device")
    f.add_argument("pc")

    ro = sub.add_parser("round", help="How long the GM waits for everyone once the first player acts")
    ro.add_argument("value", nargs="?", help="Seconds (default 60), or 'off'. Omit to show it.")

    sub.add_parser("stop", help="Close the table")

    args = parser.parse_args()
    if args.action == "serve":
        return serve(args.port, args.bind, args.code)

    campaign_dir, base = _active_campaign()

    if args.action == "start":
        info = _server_info(campaign_dir)
        if info and _alive(info.get("pid")):
            args.action = "status"           # already open for this campaign
        else:
            port, code = args.port, args.code
            for other, other_info in _open_tables(base):
                # One table at a time: move it here, keeping its link and code.
                print(f"Moving the table from campaign '{other.name}' to '{campaign_dir.name}'...")
                _stop_server(other, other_info)
                port = port or other_info.get("port")
                code = code or other_info.get("code")
            return _start_server(campaign_dir, base, port or DEFAULT_PORT, args.bind, code)

    if args.action == "status":
        info = _server_info(campaign_dir)
        if not info or not _alive(info.get("pid")):
            print(_wrong_campaign_hint(campaign_dir, base)
                  or "The table is closed. Open it with: bash tools/gm-table.sh start")
            return
        pending = _call(campaign_dir, "GET", "/api/gm/pending")
        print(f"TABLE OPEN (pid {info['pid']}) for campaign '{campaign_dir.name}'")
        print(f"  On this computer:   {info['local_url']}")
        print(f"  Same Wi-Fi/network: {info['lan_url']}")
        print(f"  Table code:         {info['code']}")
        langs = pending.get("langs") or {}
        seated = [f"{pc} ({LANGS.get(langs.get(pc, 'en'), '?')})" for pc in pending.get("seated") or []]
        print(f"  Seated players:     {', '.join(seated) or '(nobody yet)'}")
        print(f"  Unread actions:     {pending.get('unread', 0)}")
        return

    if args.action == "round":
        body = {}
        if args.value:
            body["seconds"] = 0 if args.value.lower() in ("off", "0", "none") else int(args.value)
        r = _call(campaign_dir, "POST", "/api/gm/round", body)
        secs = r.get("seconds", 0)
        print(f"Round: {'off — the GM answers as soon as anyone acts' if not secs else f'the GM waits for every player, or {secs} s after the first one acts'}")
        return

    if args.action == "inbox":
        r = _call(campaign_dir, "POST", "/api/gm/inbox", {})
        if r.get("held"):
            rnd = r["round"]
            print(f"(the players are still acting: waiting for {', '.join(rnd['waiting_on'])}; "
                  f"the round closes in {max(0, int(rnd['deadline'] - time.time()))} s — run wait)")
            return
        return _print_messages(r.get("messages", []), r.get("waiting_on", []), r.get("langs"),
                               r.get("music"), r.get("auto_music", True),
                               r.get("translate"))

    if args.action == "wait":
        deadline = time.time() + args.timeout
        first_seen = None
        rnd = {}
        while time.time() < deadline:
            r = _call(campaign_dir, "GET", "/api/gm/pending")
            rnd = r.get("round") or {}
            if r.get("unread") and rnd.get("seconds"):
                # Rounds: every seated player has acted, or the round's time is up.
                if not rnd.get("open") and (not args.all or not r.get("waiting_on")):
                    break
            elif r.get("unread"):
                if args.all:
                    if not r.get("waiting_on"):
                        break
                else:
                    first_seen = first_seen or time.time()
                    if time.time() - first_seen >= args.settle or not r.get("waiting_on"):
                        break
            time.sleep(1.0)
        r = _call(campaign_dir, "POST", "/api/gm/inbox", {})
        if r.get("held"):
            print(f"(the players are still acting — run wait again)")
            return
        if not r.get("messages"):
            print(f"(no player messages after {args.timeout}s — run wait again)")
            return
        if rnd.get("timed_out"):
            print(f"ROUND CLOSED after {rnd['seconds']} s: {', '.join(rnd['waiting_on'])} didn't act "
                  f"— narrate for those who did; the others act in the next beat.")
        if rnd.get("out_of_action"):
            print("Not waited for (can't act): " + ", ".join(
                f"{n} ({why})" for n, why in rnd["out_of_action"].items()))
        return _print_messages(r["messages"], r.get("waiting_on", []), r.get("langs"),
                               r.get("music"), r.get("auto_music", True),
                               r.get("translate"))

    if args.action == "translate":
        raw = sys.stdin.read() if args.stdin else (args.json or "")
        try:
            translations = json.loads(raw)
            assert isinstance(translations, dict)
        except (ValueError, AssertionError):
            sys.exit('[ERROR] Give JSON like {"12": {"en": "I light a torch."}}')
        r = _call(campaign_dir, "POST", "/api/gm/translate", {"translations": translations})
        print(f"TRANSLATED {len(r.get('updated', []))} message(s): "
              + ", ".join(f"#{i}" for i in r.get("updated", [])))
        if r.get("still_needed"):
            _print_translate_request(r["still_needed"])
        return

    if args.action == "say":
        text = sys.stdin.read() if args.stdin else (args.text or "")
        r = _call(campaign_dir, "POST", "/api/gm/say",
                  {"text": text.strip(), "to": args.to, "image": args.image,
                   "lang": args.lang, "mood": args.mood, "theme": args.theme,
                   "boss": args.boss, "look": args.look, "loot": args.loot,
                   "villain": args.villain, "heroic": args.heroic,
                   "loot_look": args.loot_look, "loot_for": args.loot_for})
        if not r.get("ok"):
            sys.exit(f"[ERROR] {r.get('error')}")
        m = r["message"]
        who = f" (whisper to {m['to']})" if m.get("to") else " to the whole table"
        if m.get("lang"):
            who += f", {LANGS[m['lang']]} speakers only"
        print(f"POSTED #{m['id']}{who}")
        if r.get("warning"):
            print(f"[WARNING] {r['warning']}")
        if r.get("music"):
            mu_ = r["music"]
            print(f"MUSIC -> {mu_.get('title') if mu_.get('track') else 'silence'} "
                  f"(mood: {mu_.get('mood')})")
        return

    if args.action == "music":
        if args.mood:
            r = _call(campaign_dir, "POST", "/api/gm/music", {"mood": args.mood})
            if not r.get("ok"):
                sys.exit(f"[ERROR] {r.get('error')}")
            m = r["music"]
            print(f"MUSIC {m.get('title') if m.get('track') else 'stopped'} (mood: {m.get('mood')})")
            return
        if args.track == "themes":
            state = TableState(campaign_dir, str(CampaignManager().world_state_dir))
            themes = state.themes()
            print("Enemy themes (say --theme \"<name>\" plays one):")
            if not themes:
                print("  none assigned — every enemy gets a generated theme from their name,")
                print("  or a file in music/ named after them (grimaldi.mp3)")
            for name, track in themes.items():
                print(f"  {name:<24} {track}")
            return
        if args.track == "theme":
            if not args.value:
                sys.exit("Usage: gm-table.sh music theme \"<enemy>\" [file|https-link|none]")
            if args.extra:
                r = _call(campaign_dir, "POST", "/api/gm/music",
                          {"theme": args.value,
                           "assign": None if args.extra == "none" else args.extra})
                if not r.get("ok"):
                    sys.exit(f"[ERROR] {r.get('error')}")
                print(f"THEME {r['theme']} -> {r['track']}")
                return
            r = _call(campaign_dir, "POST", "/api/gm/music", {"theme": args.value, "boss": args.boss})
            m = r.get("music") or {}
            print(f"MUSIC {m.get('title')} [{m.get('track')}]")
            return
        if args.track == "auto":
            if args.value not in ("on", "off"):
                sys.exit("Usage: gm-table.sh music auto on|off")
            r = _call(campaign_dir, "POST", "/api/gm/music", {"auto": args.value == "on"})
            print("Automatic music is " + ("ON — say --mood picks the track."
                                           if r.get("auto") else "OFF — music only changes "
                                           "when you set it."))
            return
        if args.track in (None, "list"):
            state = TableState(campaign_dir, str(CampaignManager().world_state_dir))
            current = state.music
            print("Now playing: " + (f"{current.get('title')} [{current.get('track')}]"
                                     if current.get("track") else "(silence)")
                  + (f" — mood: {current['mood']}" if current.get("mood") else ""))
            print(f"Automatic music: {'ON' if state.auto_music else 'OFF'} "
                  f"(say --mood <mood> switches the track when the mood changes)")
            print("\nMoods (say --mood ...) and what each would play:")
            for name, spec in MOODS.items():
                files = state.mood_files(name)
                plays = ", ".join(files) if files else f"ambient:{spec['ambient']} (built-in)"
                print(f"  {name:<8} {spec['use']}\n           -> {plays}")
            print(f"  {SILENCE:<8} fade the music out")
            print("\nEnemy themes: say --theme \"<name>\" (see: music themes)")
            print("\nBuilt-in ambience (works with no files):")
            for name, desc in AMBIENT.items():
                print(f"  ambient:{name:<9} {desc}")
            files = state.list_music()
            print("\nMusic files:" if files else
                  "\nMusic files: none yet — run `bash tools/gm-music-library.sh fetch` for a "
                  "starter library, or drop .mp3/.ogg files into music/")
            for f in files:
                print(f"  {f['track']}")
            print("\nOr any direct https link to an audio file.")
            return
        track = None if args.track in ("stop", "off", "none") else args.track
        r = _call(campaign_dir, "POST", "/api/gm/music",
                  {"track": track, "volume": args.volume, "loop": not args.no_loop,
                   "title": args.title})
        if not r.get("ok"):
            sys.exit(f"[ERROR] {r.get('error')}")
        m = r["music"]
        print(f"MUSIC {m['title']} ({m['track']}, volume {m['volume']})" if m.get("track")
              else "MUSIC stopped")
        return

    if args.action == "free":
        r = _call(campaign_dir, "POST", "/api/gm/free", {"pc": args.pc})
        print(f"Freed {args.pc}'s seat." if r.get("freed") else f"{args.pc} had no seat.")
        return

    if args.action == "stop":
        tables = _open_tables(base)          # whichever campaign it was opened for
        (table_dir(campaign_dir) / "server.json").unlink(missing_ok=True)
        if not tables:
            print("The table is already closed.")
            return
        for camp, info in tables:
            ok = _stop_server(camp, info)
            print("The table is closed." if ok else
                  f"[WARNING] Could not stop the table server (pid {info.get('pid')}).")
        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
