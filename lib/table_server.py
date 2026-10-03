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
import re
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
import languages
import party_roster
import table_tts
from campaign_manager import CampaignManager
from character_schema import to_flat


def fold_name(s: str) -> str:
    """A name as compared: lower case, without niqqud, so קֶסְטְרֶל is קסטרל."""
    return languages.NIQQUD.sub("", str(s)).lower()


MAX_TEXT = 4000            # longest single message (GM narration can be long)
MAX_PLAYER_TEXT = 1200     # longest player action
MAX_BODY = 16 * 1024
DEFAULT_PORT = 8765
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".webp": "image/webp", ".gif": "image/gif"}
lang_name = languages.name          # "he" -> "Hebrew" (the adventure's languages: lib/languages.py)
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


def _stamp() -> float:
    """Now, to the hundredth of a second, rounded DOWN (never in the future: the
    round's deadline is counted from it)."""
    return int(time.time() * 100) / 100


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
# Every action can be fixed for at least this long: the GM can't read it sooner.
EDIT_GRACE = 5.0
# The players' side chat: kept in memory only, never on disk and never in any
# GM endpoint, so the GM (and Claude, who can read the campaign's files) can't
# see it. It clears when the table restarts.
CHAT_KEEP = 500
CHAT_WAIT_MAX = 25.0     # longest a page's chat request is held open (long polling)
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
# A recorded NPC the narration has named this many times gets a portrait by itself.
NPC_PORTRAIT_MENTIONS = 3
CARD_WORKERS = 2           # hover cards prepared at the same time
WARM_CARDS = 12            # a player's most recently mentioned names kept ready
THUMB_WIDTHS = (96, 200, 400, 800)   # the small versions of pictures pages ask for
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
        self.chat_changed = threading.Condition(self.lock)   # wakes pages waiting on the chat
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
                        if entry.get("read"):  # the GM read it: no more editing
                            target["read"] = True
                        target["rev"] = self.rev
                    continue
                entry["rev"] = self.rev
                self.messages.append(entry)
                by_id[entry.get("id")] = entry
        self.seats: Dict[str, str] = self._read_json(self.seats_path, {})
        self.langs_path = self.dir / "langs.json"
        self.langs: Dict[str, str] = self._read_json(self.langs_path, {})
        self._languages: List[str] = []
        self._languages_at: Optional[float] = None
        # The page's own words in the adventure's other languages (translated once,
        # by the Narrator's small model; table/ui-<lang>.json).
        self.ui_busy: set = set()
        self.ui_failed: Dict[str, float] = {}
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
        self.shown_people: List[str] = [x for x in g.get("people", []) if isinstance(x, str)]
        self.chat: List[Dict[str, Any]] = []           # players only; never written to disk
        # The Narrator (lib/narrator.py): each player's private questions and answers.
        self.narrator_log: Dict[str, List[Dict[str, Any]]] = {}
        self.narrator_busy: set = set()
        self.narrator_slots = threading.Semaphore(2)
        self.narrator_ask = None                        # tests plug in a fake model
        self.lore_cache: Dict[tuple, Dict[str, Any]] = {}
        # Hover cards, kept per player and language across restarts:
        # "viewer|name|lang" -> {n (story lines mentioning it then), text, source}.
        self.lore_store_path = self.dir / "lore-cards.json"
        store = self._read_json(self.lore_store_path, {})
        self.lore_store: Dict[str, Dict[str, Any]] = store if isinstance(store, dict) else {}
        self.card_jobs: List[tuple] = []
        self.card_workers = 0
        self.card_running: set = set()
        self.cards_warmed: set = set()
        self.after_busy = 0
        self.thumb_lock = threading.Lock()                            # narrations still being followed up
        self.level_notices_path = self.dir / "level-notices.json"
        notices = self._read_json(self.level_notices_path, {})
        self.level_notices: Dict[str, int] = notices if isinstance(notices, dict) else {}
        self.aliases_path = self.dir / "aliases.json"
        self.spelling_lock = threading.Lock()
        # Character sheets in the player's language: each phrase translated once by
        # the Narrator's small model, in the background, and kept (table/sheet-tr-<lang>.json).
        self.sheet_tr: Dict[str, Dict[str, str]] = {}
        self.sheet_tr_busy: set = set()
        self.sheet_tr_failed: Dict[str, float] = {}
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
        try:
            self.gm_cursor = int(self.cursor_path.read_text().strip())
        except (OSError, ValueError):
            self.gm_cursor = self.messages[-1]["id"] if self.messages else 0
        for m in self.messages:                 # what the GM has read can't be edited
            if m["kind"] == "player" and m["id"] <= self.gm_cursor:
                m["read"] = True

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

    # --- the adventure's languages ---
    @property
    def languages(self) -> List[str]:
        """The languages this adventure is played in (``gm-table.sh languages``),
        the first being the one it is mainly told in. English alone by default."""
        p = languages.path(self.campaign_dir)
        try:
            mtime = p.stat().st_mtime
        except OSError:
            return languages.load(self.campaign_dir)   # never chosen: follows the players
        if mtime != self._languages_at:
            self._languages_at, self._languages = mtime, languages.load(self.campaign_dir)
        return self._languages

    def multilingual(self) -> bool:
        return len(self.languages) > 1

    def lang_for(self, viewer: Optional[str], lang: Optional[str] = None) -> str:
        """``lang`` if the table plays in it, else the viewer's own, else the main one."""
        langs = self.languages
        if lang in langs:
            return lang
        mine = self.langs.get(viewer) if viewer else None
        return mine if mine in langs else langs[0]

    def table_langs(self) -> List[str]:
        """Every language the table's text must exist in: all the adventure's
        languages, and any a seated player reads."""
        return list(dict.fromkeys(self.languages + list(self.seated_langs().values())))

    def set_lang(self, pc: str, lang: Optional[str]) -> None:
        if not pc or lang not in self.languages:
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
            return {"open": False, "seconds": secs, "settling": False}
        acted = {party_roster.slugify(m.get("pc", "")) for m in acts}
        out = self.out_of_action()
        waiting = [n for n in seated if party_roster.slugify(n) not in acted and n not in out]
        started = self._sent_at(acts[0])
        deadline = started + secs
        # The newest action is a few seconds old at most: its player may still be
        # fixing a typo. The GM waits that out too (rounds on or off).
        ready_at = max(self._sent_at(m) for m in acts) + EDIT_GRACE
        return {"open": bool(secs and waiting and now < deadline), "seconds": secs,
                "settling": now < ready_at, "ready_at": ready_at,
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
                   "t": _stamp(), "pc": pc, "text": text}
            self.chat.append(msg)
            del self.chat[:-CHAT_KEEP]
            self.chat_changed.notify_all()
            return dict(msg)

    def chat_since(self, after: int, wait: float = 0) -> List[Dict[str, Any]]:
        """Messages after ``after``. With ``wait``, hold the request open (long
        polling) until one arrives or ``wait`` seconds pass, so a line reaches the
        other players at once instead of on their next poll."""
        deadline = time.time() + max(0.0, min(wait, CHAT_WAIT_MAX))
        with self.lock:
            while True:
                new = [dict(m) for m in self.chat if m["id"] > after]
                left = deadline - time.time()
                if new or left <= 0:
                    return new
                self.chat_changed.wait(left)

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
            entry = {"id": len(self.narrator_log.get(pc, [])) + 1, "t": _stamp(),
                     "q": question, "a": got["answer"], "source": got["source"]}
            with self.lock:
                self.narrator_log.setdefault(pc, []).append(entry)
                del self.narrator_log[pc][:-50]
            return {"ok": True, "entry": entry}
        finally:
            with self.lock:
                self.narrator_busy.discard(pc)

    # --- hover cards: what a player knows about a name in the story ---
    def aliases(self) -> Dict[str, str]:
        """Other names for the same thing (a Hebrew spelling): alias -> name."""
        data = self._read_json(self.aliases_path, {})
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}

    def set_alias(self, name: str, alias: str) -> None:
        with self.lock:
            data = self.aliases()
            data[" ".join(languages.NIQQUD.sub("", alias).split())] = " ".join(name.split())
            tmp = self.aliases_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.aliases_path)
            # Pages pick the new spelling up on their next refresh (not only after
            # the next message).
            self.lore_cache = {k: v for k, v in self.lore_cache.items() if k[0] != "terms"}

    def should_learn_spellings(self, text: str, lang: Optional[str] = None) -> bool:
        """Narration not in English may spell the campaign's names its own way."""
        import narrator
        lang = lang or self.text_lang(text or "")
        return bool(text) and languages.base(lang) != "en" and (
            self.narrator_ask is not None or narrator.backend() != "off")

    def _learn_spellings(self, text: str, lang: str) -> None:
        """Narration in another language spells the campaign's names its own way
        (מרתה for Marta): find which known names it mentions and remember those
        spellings, so they get hover cards too (a small model)."""
        import narrator
        with self.spelling_lock:                 # one at a time
            low = fold_name(text)
            aliases = self.aliases()
            spelled = {n.lower() for a, n in aliases.items() if fold_name(a) in low}
            names = [n for n in self._named_things()
                     if fold_name(n) not in low and n.lower() not in spelled][:200]
            try:
                found = narrator.find_names(text, names, lang, ask=self.narrator_ask)
            except Exception as e:               # offline...: names just aren't hoverable
                print(f"[lore] finding names: {e}", flush=True)
                return
            # A small model can slide a spelling onto the wrong name (קסטרל, a PC's own
            # name, came back as "Ma Grisk"). Never take a spelling that already is
            # another name or another name's alias, nor one given for two names.
            taken = {fold_name(n): n for n in self._named_things()}
            taken.update({fold_name(a): n for a, n in aliases.items()})
            counts: Dict[str, int] = {}
            for spelling in found.values():
                counts[fold_name(spelling)] = counts.get(fold_name(spelling), 0) + 1
            for name, spelling in found.items():
                key = fold_name(spelling)
                owner = taken.get(key)
                if key == fold_name(name) or counts[key] > 1 or (owner and owner.lower() != name.lower()):
                    continue
                if languages.NIQQUD.sub("", spelling) not in aliases:
                    self.set_alias(name, spelling)

    def _named_things(self) -> Dict[str, str]:
        """Every name the campaign knows -> its kind (only names; never what the
        GM's files say about them)."""
        names: Dict[str, str] = {}

        def table(fn: str, key: str = "") -> Dict[str, Any]:
            data = self._read_json(self.campaign_dir / fn, {})
            if key and isinstance(data, dict) and isinstance(data.get(key), dict):
                data = data[key]
            return data if isinstance(data, dict) else {}

        for n in table("npcs.json", "npcs"):
            names[n] = "npc"
        for n in table("locations.json", "locations"):
            names[n] = "place"
        factions = table("world-bible.json").get("factions")
        nodes = factions.get("nodes") if isinstance(factions, dict) else factions
        for f in nodes if isinstance(nodes, list) else []:
            if isinstance(f, dict) and f.get("name"):
                names[str(f["name"])] = "faction"
        for name, _boss in self.shown_foes:
            names.setdefault(name, "foe")
        for name in self.shown_treasures:
            names.setdefault(name, "treasure")
        for pc in self.party():
            names[pc["name"]] = "pc"
        return {n: k for n, k in names.items() if len(n.strip()) >= 3}

    def _spellings(self) -> Dict[str, set]:
        """name (lower case) -> every spelling of it the story may use."""
        out: Dict[str, set] = {}
        for alias, name in self.aliases().items():
            out.setdefault(name.lower(), {fold_name(name)}).add(fold_name(alias))
        return out

    def lore_terms(self, viewer: Optional[str], lang: Optional[str] = None) -> List[Dict[str, Any]]:
        """The names this player has met in the story (so they can be hovered).
        A name only appears once the narration they saw has used it: no spoilers.
        Each carries ``n``, how many story lines mention it: a card made at the
        same ``n`` is still current."""
        import narrator
        lang = self.lang_for(viewer, lang)
        key = ("terms", viewer, self.rev, lang)
        if key in self.lore_cache:
            return self.lore_cache[key]["terms"]
        # Compared without niqqud: narration may point a name (קֶסְטְרֶל) or not.
        lines = [fold_name(l) for l in narrator.story_lines(self.since(0, viewer), viewer or "", lang)]
        seen = "\n".join(lines)
        things = self._named_things()
        spellings = self._spellings()

        def mentions(name: str) -> Dict[str, int]:
            """How many story lines mention it, and the latest one that does."""
            forms = spellings.get(name.lower(), {fold_name(name)})
            hits = [i for i, l in enumerate(lines) if any(f in l for f in forms)]
            return {"n": len(hits), "last": hits[-1] if hits else -1}

        out = [{"term": n, "kind": k, **mentions(n)} for n, k in things.items() if fold_name(n) in seen]
        for alias, name in self.aliases().items():
            kind = things.get(name) or next((k for n, k in things.items() if n.lower() == name.lower()), None)
            if kind and fold_name(alias) in seen:
                out.append({"term": alias, "kind": kind, "of": name, **mentions(name)})
        out.sort(key=lambda t: -len(t["term"]))
        self.lore_cache = {k: v for k, v in self.lore_cache.items()
                           if k[0] != "terms" or k[1] != viewer or k[3] != lang}
        self.lore_cache[key] = {"terms": out}
        return out

    def lore_card(self, viewer: str, term: str, refresh: bool = False,
                  lang: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """What ``viewer`` knows about ``term``. A card is kept per player and
        language (on disk too) and is current while no new story line mentions the
        name. When the story has moved on, the last card is returned at once
        (``stale``) and a fresh one is made in the background. ``refresh`` (the
        background worker): make the card now if it's missing or out of date."""
        import image_gen
        import narrator
        lang = self.lang_for(viewer, lang)
        known = {fold_name(t["term"]): t for t in self.lore_terms(viewer, lang)}
        hit = known.get(fold_name(" ".join(str(term).split())))
        party = self.party()
        if not hit:                             # everyone at the table knows who's at the table
            pc = next((p["name"] for p in party if party_roster._same_name(p["name"], term)), None)
            hit = {"term": pc, "kind": "pc"} if pc else None
        if not hit:
            return None                         # not met in the story: nothing to say
        name, kind = hit.get("of") or hit["term"], hit["kind"]
        forms = self._spellings().get(name.lower(), {fold_name(name)})
        lines = [l for l in narrator.story_lines(self.since(0, viewer), viewer, lang)
                 if any(f in fold_name(l) for f in forms)]
        key = f"{viewer}|{name.lower()}|{lang}"
        for _ in range(150):                    # no card yet, but one is being made: wait for it
            with self.lock:
                have = self.lore_store.get(key)
                if refresh or have or key not in self.card_running:
                    break
            time.sleep(0.2)
        stale = bool(have) and have["n"] != len(lines)
        if refresh and have and not stale:
            return None                         # current already
        if refresh or not have:
            if refresh:
                with self.lock:
                    if key in self.card_running:
                        return None             # the other worker has it
                    self.card_running.add(key)
            try:
                spelled = [a for a, n in self.aliases().items() if n.lower() == name.lower()]
                got = narrator.answer(f"{name}?", lines[-30:],
                                      narrator.lore_prompt(name, kind, lines[-30:], viewer, spelled),
                                      lang, ask=self.narrator_ask)
            finally:
                if refresh:
                    with self.lock:
                        self.card_running.discard(key)
            have = {"n": len(lines), "text": got["answer"], "source": got["source"]}
            with self.lock:
                self.lore_store[key] = have
                tmp = self.lore_store_path.with_suffix(".tmp")
                tmp.write_text(json.dumps(self.lore_store, ensure_ascii=False), encoding="utf-8")
                tmp.replace(self.lore_store_path)
            stale = False
        elif stale:
            self.queue_card(viewer, term, lang=lang)    # the last one now, a fresh one shortly
        image, sub = None, ""
        if kind == "place":
            image = next((p["image"] for p in self.places() if p["name"].lower() == name.lower()), None)
        elif kind == "foe":
            image = next((f["image"] for f in self.gallery()["foes"] if f["name"].lower() == name.lower()), None)
        elif kind == "treasure":
            image = image_gen.treasure_art(name, self.campaign_dir) or None
        elif kind == "npc" and name in self.shown_people:
            image = self._npcs().get(name, {}).get("portrait")
        elif kind == "pc":
            pc = next((p for p in party if p["name"] == name), {})
            image = pc.get("portrait")
            sub = " ".join(str(x) for x in (pc.get("race"), pc.get("class")) if x)
            if pc.get("level") is not None:
                sub = (sub + " · " if sub else "") + f"level {pc['level']}"
        return {"term": hit["term"], "name": name, "kind": kind, "sub": sub, "image": image,
                "text": have["text"], "source": have["source"], "n": have["n"], "stale": stale}

    def _after_narration(self, msg: Dict[str, Any]) -> None:
        """In the background, after the GM speaks: learn the spellings it used,
        then get the hover cards of what it mentioned ready."""
        try:
            self.announce_level_ups()
            text = msg.get("text") or ""
            lang = msg.get("lang") or self.text_lang(text)
            if self.should_learn_spellings(text, lang):
                self._learn_spellings(text, lang)
            self.prepare_cards(msg)
        except Exception as e:
            print(f"[lore] after narration: {e}", flush=True)
        finally:
            with self.lock:
                self.after_busy -= 1

    def announce_level_ups(self) -> List[str]:
        """A PC whose level rose (the GM awarded XP, or a milestone) is told so in
        the story, once per level: open your sheet and level up there."""
        told = []
        for pc in self.party():
            if not pc.get("level_up"):
                continue
            with self.lock:
                if self.level_notices.get(pc["name"], 0) >= pc["level"]:
                    continue
                self.level_notices[pc["name"]] = pc["level"]
                tmp = self.level_notices_path.with_suffix(".tmp")
                tmp.write_text(json.dumps(self.level_notices, ensure_ascii=False), encoding="utf-8")
                tmp.replace(self.level_notices_path)
            self.append("system", f"{pc['name']} can level up.", pc=pc["name"],
                        event={"type": "levelready", "level": pc["level"]})
            told.append(pc["name"])
        return told

    def queue_card(self, viewer: str, term: str, soon: bool = True, lang: Optional[str] = None) -> None:
        """Make (or bring up to date) a hover card in the background: ``soon`` ones
        (just mentioned) before the rest."""
        with self.lock:
            job = (viewer, term, self.lang_for(viewer, lang))
            if job in self.card_jobs:
                if not soon:
                    return
                self.card_jobs.remove(job)
            if soon:
                self.card_jobs.insert(0, job)
            else:
                self.card_jobs.append(job)
            if self.card_workers < CARD_WORKERS:
                self.card_workers += 1
                threading.Thread(target=self._card_worker, daemon=True).start()

    def warm_cards(self, viewer: str) -> None:
        """Get ready the cards a player is likely to hover: the names their story
        mentioned most recently that have no card yet (not every name: each card
        is a model call)."""
        import narrator
        if self.narrator_ask is None and narrator.backend() == "off":
            return
        # Every language the table plays in, the player's own first: switching
        # language shows the cards and sheets at once.
        mine = self.lang_for(viewer)
        for lang in [mine] + [l for l in self.table_langs() if l != mine]:
            for pc in self.party():                 # and every sheet, in that language
                self.sheet_translation(viewer, pc["name"], lang)
            with self.lock:
                have = set(self.lore_store)
            terms = sorted(self.lore_terms(viewer, lang), key=lambda t: -t.get("last", -1))
            for t in terms[:WARM_CARDS]:
                if f"{viewer}|{(t.get('of') or t['term']).lower()}|{lang}" not in have:
                    self.queue_card(viewer, t["term"], soon=False, lang=lang)

    def _card_worker(self) -> None:
        while True:
            with self.lock:
                if not self.card_jobs:
                    self.card_workers -= 1
                    return
                viewer, term, lang = self.card_jobs.pop(0)
            try:
                self.lore_card(viewer, term, refresh=True, lang=lang)
            except Exception as e:              # offline...: the old card stays
                print(f"[lore] {term}: {e}", flush=True)

    def prepare_cards(self, msg: Dict[str, Any]) -> None:
        """After a narration: get the cards of the names it mentions ready for every
        seated player who saw it, before anyone hovers them."""
        import narrator
        if self.narrator_ask is None and narrator.backend() == "off":
            return                              # without a model, cards are instant anyway
        low = (msg.get("text") or "").lower()
        for pc in [p["name"] for p in self.party() if p.get("claimed")]:
            if not self.visible_to(msg, pc):
                continue
            # (a beat told in one language: that language's cards)
            for lang in [msg["lang"]] if msg.get("lang") else self.table_langs():
                mentioned = [t["term"] for t in self.lore_terms(pc, lang) if t["term"].lower() in low]
                for term in mentioned[:8]:
                    self.queue_card(pc, term, lang=lang)
            self.warm_cards(pc)

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
        """Compose what's queued (villain/boss themes) and the missing PC anthems, all
        in one go: the model loads once per batch, not once per piece (it's the slow,
        memory-hungry part). When a theme lands while its foe's music is playing, it
        takes over at once, while the rest are still being composed."""
        if self.music_maker is None and not composer.available():
            self.music_jobs.clear()
            return []
        pieces = []
        while self.music_jobs:
            pieces.append(self.music_jobs.pop(0))
        for path, raw in party_roster.all_pcs(self.campaign_dir):
            sheet = to_flat(raw)
            name = sheet.get("name") or path.stem
            if composer.anthem(self.campaign_dir, name):
                continue
            if time.time() - self.portrait_tried.get("anthem:" + name, -PORTRAIT_RETRY) < PORTRAIT_RETRY:
                continue
            self.portrait_tried["anthem:" + name] = time.time()
            pieces.append({"kind": "anthem", "name": name, "boss": False, "look": "", "sheet": sheet})
        if not pieces:
            return []
        done: List[str] = []

        def landed(job: Dict[str, Any], f: str) -> None:
            done.append(job["name"])
            playing = self.music
            if (job["kind"] == "theme" and party_roster._same_name(playing.get("theme"), job["name"])
                    and bool(playing.get("boss")) == job["boss"] and playing.get("track") != f):
                music = self.set_music(f, playing.get("volume", 0.6), True, playing.get("title"),
                                       mood=playing.get("mood"), theme=job["name"], boss=job["boss"])
                self.announce_music(music)

        if self.music_maker is not None:
            for job in pieces:
                try:
                    landed(job, self.music_maker(job["kind"], job["name"], job["boss"], job["look"],
                                                 job.get("sheet")))
                except Exception as e:
                    print(f"[compose] {job['name']}: {e}", flush=True)
            return done
        try:
            files = composer.compose_pieces(self.campaign_dir, pieces, landed)
            for job, f in zip(pieces, files):
                if not f:
                    print(f"[compose] {job['name']}: that piece failed", flush=True)
        except Exception as e:
            print(f"[compose] {', '.join(j['name'] for j in pieces)}: {e}", flush=True)
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
                   "ts": _now(), "t": _stamp(), "kind": kind, "text": text}
            if pc:
                msg["pc"] = pc
            if to:
                msg["to"] = to
            if image:
                msg["image"] = image
            if lang and languages.valid(lang):
                msg["lang"] = lang
            if voice:
                msg["voice"] = True
            if event:
                msg["event"] = event   # lets each browser word the notice in its language
            self.rev += 1
            msg["rev"] = self.rev
            self.messages.append(msg)
            if kind == "gm" and not to:
                self._gm_spoke(lang if lang and languages.valid(lang) else None)
            if kind == "gm":
                self.after_busy += 1            # (tests wait for this to reach 0)
                threading.Thread(target=self._after_narration, args=(dict(msg),), daemon=True).start()
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

    def locked(self, msg: Dict[str, Any]) -> Optional[str]:
        """Why this action can no longer be edited, or None: the GM has read it
        (and may already be rolling for it), dice were rolled after it, or the
        GM answered. (caller holds the lock)"""
        if self.answered(msg):
            return "answered"
        if msg.get("read") or msg["id"] <= self.gm_cursor:
            return "read"
        if time.time() - self._sent_at(msg) < EDIT_GRACE:
            return None                         # its first seconds: always fixable
        if any(m["id"] > msg["id"] and m["kind"] == "roll" for m in self.messages):
            return "rolled"
        return None

    def edit(self, pc: str, msg_id: Any, text: str) -> Dict[str, Any]:
        """A player fixes their own action (a typo, a misheard word) — allowed
        until the GM reads it: after that the GM acts on what it read (rolls the
        dice for it), so a change would be ignored."""
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
            why = self.locked(msg)
            if why:
                return {"ok": False, "reason": why,
                        "error": "The GM is already playing that out — write a new action."}
            if text == msg.get("text"):
                return {"ok": True, "message": dict(msg)}
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
    def text_lang(self, text: str) -> str:
        """Which of the table's languages ``text`` is in, by its writing system."""
        return languages.guess(text, self.table_langs())

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
                  if languages.valid(l) and str(t).strip()}
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
        """What some language at the table can't read yet: [{id, pc, kind, from, to:
        [langs], text}]. Players' public actions, and GM narration posted without
        --lang (or whispered), each into every language the adventure is played in
        (and any a seated player reads), so a player who switches language finds
        it all there."""
        langs = set(self.table_langs())
        out = []
        with self.lock:
            pool = [m for m in self.messages if (m["kind"] == "player" and not m.get("to"))
                    or (m["kind"] == "gm" and not m.get("lang") and (m.get("text") or "").strip())]
            if ids is not None:
                pool = [m for m in pool if m["id"] in ids]
            for m in pool[-20:]:
                src = m.get("lang") or self.text_lang(m.get("text", ""))
                missing = sorted(l for l in langs if l != src and l not in (m.get("tr") or {}))
                if missing:
                    out.append({"id": m["id"], "pc": m.get("pc") or ("GM" if m["kind"] == "gm" else None),
                                "kind": m["kind"], "from": src, "to": missing,
                                "text": m.get("text", "")})
        return out

    def missing_versions(self) -> Dict[str, int]:
        """At a multilingual table: how many of the GM's latest beats (since the
        players last acted) each language is still missing, e.g. {"he": 1}: the
        English version is up, the Hebrew one isn't yet."""
        langs = self.languages
        if len(langs) < 2:
            return {}
        told: List[str] = []
        with self.lock:
            for m in reversed(self.messages):
                if m["kind"] == "player" and not m.get("to"):
                    break
                if m["kind"] == "gm" and not m.get("to") and m.get("lang"):
                    told.append(m["lang"])
        if not told:
            return {}
        counts = {l: told.count(l) for l in langs}
        top = max(counts.values())
        return {l: top - n for l, n in counts.items() if n < top}

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
                if msg is None or not isinstance(versions, dict) or (
                        msg.get("to") and msg["kind"] != "gm"):     # (a GM whisper: yes)
                    continue
                clean = {l: str(t).strip()[:MAX_TEXT] for l, t in versions.items()
                         if languages.valid(l) and str(t).strip()}
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
            if mark and self.messages:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    for m in unread:            # read: no more editing (pages see it)
                        if m["kind"] == "player" and not m.get("read"):
                            m["read"] = True
                            self.rev += 1
                            m["rev"] = self.rev
                            f.write(json.dumps({"patch": m["id"], "read": True}) + "\n")
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
        # Every language the adventure is played in has its version of the beat.
        langs = set(self.table_langs()) if self.multilingual() else (
            {self.langs.get(n, self.languages[0]) for n in self.seats.values()} or {self.languages[0]})
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
        """sheet(), plus — on the viewer's OWN sheet — what levelling up offers.
        Someone else's character shows only what the party can see of them."""
        found = self.sheet(viewer, name, rev)
        if found and not (viewer and party_roster._same_name(viewer, found["name"])):
            found = {**found, "sheet": public_sheet(found["sheet"]), "public": True}
        if found and viewer and party_roster._same_name(viewer, found["name"]):
            live = party_roster.find_pc(self.campaign_dir, found["name"])
            if live is not None:
                opts = self.level_up_options(
                    found["name"], to_flat(json.loads(live.read_text(encoding="utf-8"))))
                if opts:
                    found["level_up"] = opts
        return found

    # --- character sheets in the player's language ---
    def _sheet_tr(self, lang: str) -> Dict[str, str]:
        if lang not in self.sheet_tr:
            data = self._read_json(self.dir / f"sheet-tr-{lang}.json", {})
            self.sheet_tr[lang] = {k: v for k, v in data.items() if isinstance(v, str)} \
                if isinstance(data, dict) else {}
        return self.sheet_tr[lang]

    def sheet_translation(self, viewer: Optional[str], name: str,
                          lang: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """{tr: {english: translation}, pending}: the viewer's language for what's
        written on ``name``'s sheet. Missing phrases are translated in the background
        (``pending`` until they land); without a model the sheet stays as written."""
        import narrator
        lang = self.lang_for(viewer, lang)
        found = self.sheet_for(viewer, name)          # (another's: only what's public)
        if found is None:
            return None
        strings = sheet_strings(found["sheet"], lang)
        with self.lock:
            known = self._sheet_tr(lang)
            tr = {s: known[s] for s in strings if s in known}
            missing = [s for s in strings if s not in known]
            can = self.narrator_ask is not None or narrator.backend() != "off"
            pending = bool(missing) and can and time.time() - self.sheet_tr_failed.get(lang, 0) > 600
            if pending and lang not in self.sheet_tr_busy:
                self.sheet_tr_busy.add(lang)
                threading.Thread(target=self._translate_sheet, args=(lang, missing), daemon=True).start()
        return {"tr": tr, "pending": pending}

    # --- the page's own words, in the adventure's languages ---
    def ui_strings(self, lang: str) -> Optional[Dict[str, Any]]:
        """{strings, pending} for the page in ``lang`` (one of the adventure's
        languages). English and Hebrew come with the page; any other is translated
        once by the Narrator's small model (in the background) and kept in
        table/ui-<lang>.json. None: the table isn't played in ``lang``."""
        import narrator
        if lang not in self.languages:
            return None
        builtin = page_strings()
        if lang in builtin:
            return {"strings": builtin[lang], "pending": False}
        path = self.dir / f"ui-{lang}.json"
        have = self._read_json(path, {})
        have = {k: v for k, v in have.items() if isinstance(v, str)} if isinstance(have, dict) else {}
        missing = [k for k in builtin["en"] if k not in have]
        can = self.narrator_ask is not None or narrator.backend() != "off"
        with self.lock:
            pending = bool(missing) and can and time.time() - self.ui_failed.get(lang, 0) > 600
            if pending and lang not in self.ui_busy:
                self.ui_busy.add(lang)
                threading.Thread(target=self._translate_ui, args=(lang, missing, path),
                                 daemon=True).start()
        return {"strings": have, "pending": pending}

    def ui_status(self, lang: str) -> str:
        if lang in page_strings():
            return "built in"
        if lang in self.ui_busy:
            return "translating"
        got = self.ui_strings(lang) or {}
        if not got.get("pending") and len(got.get("strings") or {}) >= len(page_strings()["en"]):
            return "ready"
        return "translating" if got.get("pending") else "no model to translate it (the page shows English)"

    def _translate_ui(self, lang: str, keys: List[str], path: Path) -> None:
        import narrator
        en = page_strings()["en"]
        try:
            todo = [k for k in keys if re.search(r"[^\W\d_]", en[k])]
            got: Dict[str, str] = {k: en[k] for k in keys if k not in todo}   # (just ⬆, emoji...)
            for i in range(0, len(todo), 60):
                part = todo[i:i + 60]
                tr = narrator.translate([en[k] for k in part], lang, ask=self.narrator_ask, kind="ui")
                if not tr:
                    raise RuntimeError("no translation came back")
                got.update({k: tr[en[k]] for k in part if en[k] in tr})
            with self.lock:
                have = self._read_json(path, {})
                have = have if isinstance(have, dict) else {}
                have.update(got)
                tmp = path.with_suffix(".tmp")
                tmp.write_text(json.dumps(have, ensure_ascii=False, indent=1), encoding="utf-8")
                tmp.replace(path)
        except Exception as e:                   # offline...: the page shows English meanwhile
            print(f"[ui] translating the page to {lang}: {e}", flush=True)
            with self.lock:
                self.ui_failed[lang] = time.time()
        finally:
            with self.lock:
                self.ui_busy.discard(lang)

    def _translate_sheet(self, lang: str, missing: List[str]) -> None:
        import narrator
        try:
            for i in range(0, len(missing), 60):
                got = narrator.translate(missing[i:i + 60], lang, ask=self.narrator_ask)
                if not got:
                    raise RuntimeError("no translation came back")
                with self.lock:
                    known = self._sheet_tr(lang)
                    known.update(got)
                    path = self.dir / f"sheet-tr-{lang}.json"
                    tmp = path.with_suffix(".tmp")
                    tmp.write_text(json.dumps(known, ensure_ascii=False, indent=1), encoding="utf-8")
                    tmp.replace(path)
        except Exception as e:                   # offline, not logged in...: the sheet stays as written
            print(f"[sheet] translating to {lang}: {e}", flush=True)
            with self.lock:
                self.sheet_tr_failed[lang] = time.time()
        finally:
            with self.lock:
                self.sheet_tr_busy.discard(lang)

    def party(self, sheets: bool = False) -> List[Dict[str, Any]]:
        """The PCs, summarised for the party panel. Each carries ``sheet_rev``, a
        fingerprint of the whole sheet, so pages refetch a sheet only when it
        changed; ``sheets=True`` includes the sheets themselves."""
        out = []
        companions: Dict[str, List[Dict[str, Any]]] = {}
        for n, r in self._npcs().items():
            if r.get("companion_of"):
                companions.setdefault(str(r["companion_of"]).lower(), []).append(
                    {"name": n, "description": r.get("description", ""),
                     "portrait": r.get("portrait") if n in self.shown_people else None})
        for path, raw in party_roster.all_pcs(self.campaign_dir):
            c = to_flat(raw)
            mine = companions.get(str(c.get("name", path.stem)).lower())
            if mine:
                c = {**c, "companions": mine}
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
            tmp.write_text(json.dumps({"foes": self.shown_foes, "treasures": self.shown_treasures,
                                       "people": self.shown_people},
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
        npcs = self._npcs()
        people = [{"name": n, "image": npcs[n]["portrait"]} for n in reversed(self.shown_people)
                  if n in npcs and self._has_image(npcs[n].get("portrait"))]
        return {"foes": foes, "treasures": treasures, "people": people}

    def _has_image(self, filename: Any) -> bool:
        return bool(filename) and (self.campaign_dir / "images" / str(filename)).is_file()

    def _npcs(self) -> Dict[str, Dict[str, Any]]:
        """The campaign's recorded NPCs: name -> record."""
        data = self._read_json(self.campaign_dir / "npcs.json", {})
        if isinstance(data, dict) and isinstance(data.get("npcs"), dict):
            data = data["npcs"]
        return {k: v for k, v in data.items() if isinstance(v, dict)} if isinstance(data, dict) else {}

    def npc_mentions(self) -> Dict[str, int]:
        """How many of the GM's public narrations name each recorded NPC (in any
        spelling): the recurring ones are the ones worth a portrait."""
        spellings = self._spellings()
        with self.lock:
            told = [m["text"].lower() for m in self.messages
                    if m["kind"] == "gm" and not m.get("to") and m.get("text")]
        out = {}
        for name in self._npcs():
            forms = spellings.get(name.lower(), {name.lower()})
            out[name] = sum(1 for t in told if any(f in t for f in forms))
        return out

    def npc_pass(self, now: Optional[float] = None) -> List[str]:
        """Recurring NPCs (named in NPC_PORTRAIT_MENTIONS narrations or more) get a
        portrait, one per pass, shown to the table and kept in the gallery's People.
        One the GM already painted is shown the same way."""
        now = now or time.time()
        if not self._art_on(self.portrait_maker):
            return []
        npcs = self._npcs()
        # A PC's companion (familiar, pet, mount) or a party member: at once. Others
        # once the story keeps naming them.
        close = [(n, 10 ** 6) for n, r in npcs.items()
                 if (r.get("companion_of") or r.get("is_party_member")) and n not in self.shown_people]
        recurring = close + sorted(((n, c) for n, c in self.npc_mentions().items()
                                    if c >= NPC_PORTRAIT_MENTIONS and n not in self.shown_people
                                    and (n, 10 ** 6) not in close), key=lambda x: -x[1])
        for name, _ in recurring:
            filename = npcs[name].get("portrait")
            if not self._has_image(filename):
                key = "npc:" + name
                if now - self.portrait_tried.get(key, -PORTRAIT_RETRY) < PORTRAIT_RETRY:
                    continue
                self.portrait_tried[key] = now
                try:
                    if self.portrait_maker is not None:
                        filename = self.portrait_maker(name, self.campaign_dir)
                    else:
                        import image_gen
                        filename = image_gen.generate_portrait(name, self.campaign_dir)["portrait"]
                except Exception as e:          # no GPU memory, service down...: try later
                    print(f"[portrait] {name}: {e}", flush=True)
                    continue
            self.shown_people.append(name)
            self._save_gallery()
            event = {"type": "npc", "name": name}
            if npcs[name].get("companion_of"):
                event["of"] = npcs[name]["companion_of"]
            self.append("system", f"{name}.", image=filename, event=event)
            return [name]                       # one per pass: the scene's pictures get a turn
        return []

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

    def thumbnail(self, path: Path, width: Any) -> Optional[Path]:
        """A small JPEG of a picture (for hover cards, avatars, the gallery's list),
        made once and kept in the table folder: a fraction of the original's size,
        which matters over the tunnel. None (send the original) when it can't be made."""
        try:
            w = min(THUMB_WIDTHS, key=lambda x: abs(x - int(width)))
        except (TypeError, ValueError):
            return None
        out = self.dir / "thumbs" / f"{path.stem}-{w}.jpg"
        try:
            if out.is_file() and out.stat().st_mtime >= path.stat().st_mtime:
                return out
            from PIL import Image
            with self.thumb_lock:
                out.parent.mkdir(exist_ok=True)
                with Image.open(path) as im:
                    if im.width <= w:
                        return None                 # small already
                    im = im.convert("RGB")
                    im.thumbnail((w, w * 4))
                    tmp = out.with_suffix(".tmp")
                    im.save(tmp, "JPEG", quality=82, optimize=True)
                    tmp.replace(out)
            return out
        except Exception:                           # no Pillow, an odd file...: the original
            return None

    def set_sex(self, pc: str, sex: str) -> bool:
        """Record a PC's sex in their appearance (what their portrait shows)."""
        sex = {"male": "male", "female": "female"}.get(str(sex).strip().lower(), "")
        path = party_roster.find_pc(self.campaign_dir, pc)
        if not sex or path is None:
            return False
        with self.lock:
            data = json.loads(path.read_text(encoding="utf-8"))
            va = data.get("visual_appearance") if isinstance(data.get("visual_appearance"), dict) else {}
            data["visual_appearance"] = {**va, "sex": sex}
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
        return True

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
            for job in (self.place_pass, self.art_pass, self.portrait_pass, self.npc_pass, self.music_pass):
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


SHEET_TR_SKIP = {"name", "id", "origin", "voice", "portrait", "image", "current_location"}
# What a player sees of ANOTHER player's character: what the table sees anyway.
PUBLIC_SHEET_KEYS = ("name", "race", "class", "level", "concept", "pronouns", "portrait",
                     "hp", "status", "conditions", "companions")


def public_sheet(sheet: Dict[str, Any]) -> Dict[str, Any]:
    """Another player's character: no abilities, skills, spells, gear or notes."""
    return {k: sheet[k] for k in PUBLIC_SHEET_KEYS if k in sheet}


def _pretty_key(k: Any) -> str:
    """A sheet key as the page labels it (``spell_slots`` -> ``Spell slots``)."""
    s = str(k).replace("_", " ")
    return s[:1].upper() + s[1:]


_PAGE_STRINGS: Dict[str, Dict[str, str]] = {}


def page_strings() -> Dict[str, Dict[str, str]]:
    """The page's words in the languages it ships with (lib/table_strings.json)."""
    if not _PAGE_STRINGS:
        _PAGE_STRINGS.update(json.loads((Path(__file__).parent / "table_strings.json")
                                        .read_text(encoding="utf-8")))
    return _PAGE_STRINGS


def page_html() -> str:
    """table_page.html with its words put in (they live in table_strings.json)."""
    page = (Path(__file__).parent / "table_page.html").read_text(encoding="utf-8")
    return page.replace("/*TABLE_STRINGS*/", json.dumps(page_strings(), ensure_ascii=False) + " || ", 1)


def sheet_strings(sheet: Dict[str, Any], lang: str = "he") -> List[str]:
    """What a ``lang`` reader would find in another language on a sheet: its values
    and the labels of its keys (numbers and dice left out) — words in another
    writing system, or, for a language written like English, any words. A phrase
    that mixes two ("Fire Bolt (קרן אש, 1d10)") is in either way: it comes back
    all in ``lang``."""
    out: List[str] = []

    def add(s: Any) -> None:
        s = str(s).strip()
        if s and len(s) <= 800 and languages.foreign_to(s, lang):
            out.append(s)

    def walk(v: Any) -> None:
        if isinstance(v, str):
            add(v)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            for k, x in v.items():
                if k in ("portrait", "image"):
                    continue
                if k not in ("name", "title", "item"):
                    add(_pretty_key(k))
                walk(x)

    for k, v in (sheet or {}).items():
        if k in SHEET_TR_SKIP:
            continue
        add(_pretty_key(k))
        walk(v)
    return list(dict.fromkeys(out))


def _held_note(rnd: Dict[str, Any]) -> str:
    """Why the GM can't read or narrate yet, for the GM."""
    if rnd.get("open"):
        left = max(0, int(rnd["deadline"] - time.time()))
        return (f"The players are still acting — waiting for {', '.join(rnd['waiting_on'])} "
                f"(the round closes in {left} s)")
    left = max(1, int(rnd.get("ready_at", time.time()) - time.time() + 0.99))
    return f"A player just acted and may still fix a typo — readable in {left} s"


def warm_up() -> None:
    """At the start of the game, read the AI models into RAM, one after the other
    (not both at once from the disk): the picture model, then the music model.
    They wait there all evening, each on the graphics card only while it works;
    the music model is released when the table stops, Forge's when Forge is closed."""
    try:
        import image_gen
        if image_gen.warm_up():
            print("[art] the picture model is loaded (in RAM)", flush=True)
    except Exception as e:
        print(f"[art] picture warm-up: {e}", flush=True)
    if composer.available() and composer.start_server():
        print("[compose] the music model is loaded (in RAM)", flush=True)


# ============================================================ HTTP layer =====

def make_handler(state: TableState, code: str, host_key: str):
    page = page_html()

    class Handler(BaseHTTPRequestHandler):
        server_version = "GMTable/1.0"

        def log_message(self, fmt, *args):  # keep the host's terminal quiet
            pass

        # --- helpers ---
        def _send(self, status: int, body: bytes, ctype: str, cache: str = "no-store") -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (ConnectionResetError, BrokenPipeError):
                pass                            # the page went away mid-download

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
                return self._image(url.path[len("/images/"):], q.get("w"))
            if url.path.startswith("/api/gm/"):
                if not self._is_host():
                    return self._err("host only", 403)
                if url.path == "/api/gm/pending":
                    return self._json({"ok": True, "round": state.round_state(),
                                   "unread": len(state.gm_unread(mark=False)),
                                   "waiting_on": state.waiting_on(),
                                   "seated": sorted(set(state.seats.values())),
                                   "langs": state.seated_langs(),
                                   "languages": state.languages})
                return self._err("not found", 404)
            if not self._code_ok(q.get("code")):
                return self._err("bad table code", 403)
            me = state.pc_for(q.get("token"))
            if url.path == "/api/info":
                state.music_tick()
                if me and me not in state.cards_warmed:     # a player sits down: their cards
                    state.cards_warmed.add(me)
                    threading.Thread(target=state.warm_cards, args=(me,), daemon=True).start()
                return self._json({"ok": True, "me": me, "party": state.party_for(me),
                                   "waiting_on": state.waiting_on(),
                                   "music": state.music, "server_now": time.time(),
                                   "progress": state.progress(), "tts": state.tts_ready(),
                                   "places": state.places(), **state.gallery(),
                                   "round": state.round_state(),
                                   "lore_terms": state.lore_terms(me, q.get("lang")),
                                   "languages": languages.describe(state.languages),
                                   "lang": state.lang_for(me),
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
            if url.path == "/api/lore":
                if not me:
                    return self._err("Take a seat first.", 403)
                card = state.lore_card(me, q.get("term", ""), lang=q.get("lang"))
                if card is None:
                    return self._err("Nothing known about that yet.", 404)
                return self._json({"ok": True, **card})
            if url.path == "/api/chat":
                if not me:                      # seated players only: never the host key
                    return self._err("Take a seat first.", 403)
                try:
                    after = int(q.get("after", 0))
                    wait = float(q.get("wait", 0))
                except ValueError:
                    after, wait = 0, 0.0
                return self._json({"ok": True, "messages": state.chat_since(after, wait)})
            if url.path == "/api/sheet-tr":
                if not me:
                    return self._err("Take a seat first.", 403)
                got = state.sheet_translation(me, q.get("pc", ""), q.get("lang"))
                if got is None:
                    return self._err("No such character.", 404)
                return self._json({"ok": True, **got})
            if url.path == "/api/ui":
                # The page's own words in one of the adventure's languages.
                got = state.ui_strings(q.get("lang", ""))
                if got is None:
                    return self._err("This table isn't played in that language.", 404)
                return self._json({"ok": True, **got})
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
                lang = data.get("lang") if data.get("lang") in state.languages else None
                return self._json(state.roll_character(lang, data.get("previous")))

            if url.path == "/api/create":
                name = " ".join(str(data.get("name", "")).split())[:60]
                concept = " ".join(str(data.get("concept", "")).split())[:200]
                mode = "nameless" if data.get("mode") == "nameless" else "original"
                if mode == "original" and not name:
                    return self._err("Give your character a name.")
                created = state.create_pc(mode, name, concept)
                if created["ok"] and data.get("sex"):
                    state.set_sex(created["pc"], str(data["sex"]))
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
                lang = data.get("lang") if data.get("lang") in state.languages else None
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
                if rnd["open"] or rnd.get("settling"):
                    # The players are still acting (or just did, and may fix a typo):
                    # their actions wait.
                    return self._json({"ok": True, "messages": [], "held": True, "round": rnd,
                                       "waiting_on": rnd["waiting_on"], "langs": state.seated_langs(),
                                       "languages": state.languages,
                                       "music": state.music, "auto_music": state.auto_music})
                unread = state.gm_unread(mark=True)
                return self._json({"ok": True, "messages": unread,
                                   "waiting_on": state.waiting_on(),
                                   "langs": state.seated_langs(),
                                   "languages": state.languages,
                                   "missing": state.missing_versions(),
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
                if (not data.get("to") and (rnd["open"] or rnd.get("settling"))
                        and not state.gm_read_since_narration()):
                    return self._json({"ok": False, "round": rnd, "error": (
                        _held_note(rnd) + " Run: bash tools/gm-table.sh wait")}, 409)
                if len(text) > MAX_TEXT * 4:
                    return self._err("narration too long; split it into beats")
                to = data.get("to")
                if to:
                    path_ = party_roster.find_pc(state.campaign_dir, str(to))
                    if path_ is None:
                        return self._err(f"no player character named {to}")
                    to = (party_roster._read(path_) or {}).get("name", to)
                lang = data.get("lang")
                if lang and lang not in state.table_langs():
                    return self._err(f"this adventure isn't played in {lang} (its languages: "
                                     f"{', '.join(state.languages)}; change them with "
                                     f"gm-table.sh languages)")
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
                        warning = (f"{to} plays in {lang_name(want)} — whisper in {lang_name(want)} "
                                   f"(then translate it for the table's other languages).")
                elif not lang and text and len(set(state.table_langs())) > 1:
                    wrote = state.text_lang(text)
                    others = sorted(lang_name(l) for l in state.table_langs() if l != wrote)
                    warning = (f"This beat has no --lang: until you translate it (see wait), "
                               f"{', '.join(others)} readers get it in {lang_name(wrote)}. Post one "
                               f"version per language: say --lang " + " / say --lang ".join(state.languages))
                missing = state.missing_versions() if lang and not to else {}
                reminder = ("Now the same beat in " + ", ".join(
                    f"{lang_name(l)} (say --lang {l})" for l in missing) + ".") if missing else None
                return self._json({"ok": True, "message": msg, "music": music,
                                   "warning": warning, "reminder": reminder})
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
            if path == "/api/gm/languages":
                if data.get("languages"):
                    try:
                        languages.save(state.campaign_dir, data["languages"])
                    except ValueError as e:
                        return self._err(str(e))
                    for l in state.languages:           # the page's words, ready
                        state.ui_strings(l)
                return self._json({"ok": True, "languages": languages.describe(state.languages),
                                   "ui": {l: state.ui_status(l) for l in state.languages}})
            if path == "/api/gm/alias":
                name, alias = str(data.get("name", "")).strip(), str(data.get("alias", "")).strip()
                if not name or not alias:
                    return self._err("give a name and its other spelling")
                state.set_alias(name, alias)
                return self._json({"ok": True, "aliases": state.aliases()})
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

        def _image(self, name: str, width: Optional[str] = None):
            name = Path(name).name
            path = state.campaign_dir / "images" / name
            ctype = IMAGE_TYPES.get(path.suffix.lower())
            if not ctype or not path.is_file():
                return self._err("not found", 404)
            small = state.thumbnail(path, width) if width else None
            if small is not None:
                path, ctype = small, "image/jpeg"
            # Every picture gets a new file name, so the browser may keep it: a
            # hover card or gallery opened again doesn't fetch it again.
            return self._send(200, path.read_bytes(), ctype, cache="private, max-age=604800")

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
    threading.Thread(target=warm_up, daemon=True).start()
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
        composer.stop_server()
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
        to = ", ".join(lang_name(l) for l in item["to"])
        print(f"  #{item['id']} {item.get('pc') or '?'} ({lang_name(item['from'])} -> {to}): "
              f"{item['text']}")
    example = {str(item["id"]): {l: "..." for l in item["to"]} for item in needed}
    print("  bash tools/gm-table.sh translate --stdin <<'JSON'")
    print("  " + json.dumps(example, ensure_ascii=False))
    print("  JSON")


def _print_messages(messages: List[dict], waiting_on: List[str],
                    langs: Optional[Dict[str, str]] = None,
                    music: Optional[Dict[str, Any]] = None, auto_music: bool = True,
                    translate: Optional[List[dict]] = None,
                    table_languages: Optional[List[str]] = None,
                    missing: Optional[Dict[str, int]] = None) -> None:
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
            tags = [lang_name(m["lang"])] if m.get("lang") else []
            if m.get("voice"):
                tags.append("spoken")
            if m.get("to"):
                tags.append("private, to GM only")
            if m.get("edited"):
                tags.append("edited")
            tag = f" ({', '.join(tags)})" if tags else ""
            print(f"[#{m['id']} {m.get('pc', '?')}{tag}] {m['text']}")
    if waiting_on:
        print(f"Still waiting on: {', '.join(waiting_on)}")
    table = list(dict.fromkeys(list(table_languages or []) + sorted(set((langs or {}).values()))))
    if len(table) > 1:
        print("Languages: " + ", ".join(lang_name(l) for l in table)
              + (" (players: " + ", ".join(f"{pc}={lang_name(l)}" for pc, l in langs.items()) + ")"
                 if langs else "")
              + "\n  -> tell EVERY beat once per language, the same story in each: "
              + " then ".join(f"say --lang {l}" for l in table))
    elif table and table[0] != "en":
        print(f"Language: {lang_name(table[0])} -> narrate in it")
    if missing:
        print("[MISSING] Your last beat isn't told yet in: "
              + ", ".join(f"{lang_name(l)} (say --lang {l})" for l in missing))
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
    s.add_argument("--lang", metavar="CODE",
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

    al = sub.add_parser("alias", help="Another spelling of a name (e.g. its Hebrew form), for hover cards")
    al.add_argument("name", help="The name as the campaign knows it (NPC, place, faction)")
    al.add_argument("alias", help="The other spelling, as it appears in the narration")

    lg = sub.add_parser("languages", help="The languages this adventure is played in "
                                          "(choose them when it starts; default: English only)")
    lg.add_argument("codes", nargs="*", help="ISO codes, the main one first: en he fr ... "
                                             "(omit to show the current ones)")

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
        seated = [f"{pc} ({lang_name(langs.get(pc, 'en'))})" for pc in pending.get("seated") or []]
        print(f"  Seated players:     {', '.join(seated) or '(nobody yet)'}")
        print(f"  Unread actions:     {pending.get('unread', 0)}")
        return

    if args.action == "alias":
        r = _call(campaign_dir, "POST", "/api/gm/alias", {"name": args.name, "alias": args.alias})
        if not r.get("ok"):
            sys.exit(f"[ERROR] {r.get('error')}")
        print(f"ALIAS {args.alias} -> {args.name}")
        return

    if args.action == "languages":
        info = _server_info(campaign_dir)
        if info and _alive(info.get("pid")):
            r = _call(campaign_dir, "POST", "/api/gm/languages",
                      {"languages": args.codes} if args.codes else {})
            if not r.get("ok"):
                sys.exit(f"[ERROR] {r.get('error')}")
            codes, ui = [x["code"] for x in r["languages"]], r.get("ui") or {}
        else:
            try:
                codes = languages.save(campaign_dir, args.codes) if args.codes else languages.load(campaign_dir)
            except ValueError as e:
                sys.exit(f"[ERROR] {e}")
            ui = {}
        print("LANGUAGES: " + ", ".join(f"{lang_name(c)} ({c})" for c in codes)
              + ("  — the main one is " + lang_name(codes[0]) if len(codes) > 1 else ""))
        for c, how in ui.items():
            if how not in ("built in", "ready"):
                print(f"  the page in {lang_name(c)}: {how}")
        if len(codes) > 1:
            print("Tell every beat once per language, the same story in each: "
                  + " then ".join(f"say --lang {c}" for c in codes)
                  + ". wait lists the players' actions to translate.")
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
            print(f"({_held_note(r['round'])} — run wait)")
            return
        return _print_messages(r.get("messages", []), r.get("waiting_on", []), r.get("langs"),
                               r.get("music"), r.get("auto_music", True),
                               r.get("translate"), r.get("languages"), r.get("missing"))

    if args.action == "wait":
        deadline = time.time() + args.timeout
        first_seen = None
        rnd = {}
        while time.time() < deadline:
            r = _call(campaign_dir, "GET", "/api/gm/pending")
            rnd = r.get("round") or {}
            if rnd.get("settling"):                 # a player may still be fixing a typo
                time.sleep(max(0.2, min(1.0, rnd["ready_at"] - time.time() + 0.05)))
                continue
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
                               r.get("translate"), r.get("languages"), r.get("missing"))

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
            who += f", {lang_name(m['lang'])} readers only"
        print(f"POSTED #{m['id']}{who}")
        if r.get("warning"):
            print(f"[WARNING] {r['warning']}")
        if r.get("reminder"):
            print(f"[NEXT] {r['reminder']}")
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
