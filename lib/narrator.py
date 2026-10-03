#!/usr/bin/env python3
"""The Narrator: players ask it about the story so far ("who gave us the key?",
"what did the oracle say?"), and it reminds them, from what THEY have already
seen and heard at the table.

It can't affect the game. It reads nothing but that player's own view of the
table log, their character sheet as shown to them, and the party list. It has
no tools and writes nothing. Its answers go only to the player who asked, never
into the table log or to the GM.

The answers come from a small, quick model (Haiku):
  - by default through the host's own Claude Code (`claude -p`, no tools, no
    project files: it runs in an empty folder), so no API key is needed;
  - or the Anthropic API when ANTHROPIC_API_KEY is set (NARRATOR_BACKEND=api);
  - with neither (or NARRATOR_BACKEND=off) it quotes the story's own lines that
    match the question, which needs no model at all.
"""

import difflib
import json
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any, Callable, Dict, List, Optional

NARRATOR_MODEL = os.environ.get("NARRATOR_MODEL", "haiku")
API_MODEL = os.environ.get("NARRATOR_API_MODEL", "claude-haiku-4-5")
LOG_CHARS = 40000          # the newest part of the story the narrator reads
TIMEOUT = 90

RULES = """You are the Narrator's memory at a tabletop role-playing game. A player asks you about \
the story so far, because they forgot something. You answer ONLY from the story log you are \
given: what this player has seen and heard at the table.

Rules:
- Remind, don't invent. If the log doesn't say it, say you don't know, and that the Game \
Master may tell them in play. Never guess, never fill gaps, never make up names or facts.
- Never reveal or speculate about secrets, plans, enemies' intentions, what lies ahead, or \
anything the log doesn't show this player. Never give advice on what to do next, and never \
rule on game mechanics. You are not the Game Master and you can't change the game.
- Quote or closely paraphrase the log. Mention who said it or when, if that helps.
- Answer in {lang}, in 1-4 short sentences. Plain text, no markdown headings."""

try:
    import languages as _languages
except ImportError:                         # (imported as lib.narrator)
    from lib import languages as _languages


class _Names(dict):
    def get(self, code, default=None):
        return _languages.name(code) if code else default


LANG_NAMES = _Names()         # "he" -> "Hebrew", for any language code


def backend() -> str:
    """'claude' (the host's Claude Code), 'api' (ANTHROPIC_API_KEY) or 'off'."""
    chosen = os.environ.get("NARRATOR_BACKEND", "").strip().lower()
    has_cli, has_key = bool(shutil.which("claude")), bool(os.environ.get("ANTHROPIC_API_KEY"))
    if chosen in ("off", "none", "no"):
        return "off"
    if chosen == "api":
        return "api" if has_key else "off"
    if chosen == "claude":
        return "claude" if has_cli else "off"
    return "claude" if has_cli else "api" if has_key else "off"


# --------------------------------------------------------------- context ----
def story_lines(messages: List[Dict[str, Any]], viewer: str, lang: str) -> List[str]:
    """The table log as this player saw it, one line per entry."""
    out = []
    for m in messages:
        kind, text = m.get("kind"), (m.get("text") or "").strip()
        if kind == "gm":
            if m.get("lang") and m.get("lang") != lang:
                continue                         # the other language's version
            text = ((m.get("tr") or {}).get(lang) or text).strip()   # (a translated beat)
            who = "GM, privately to you" if m.get("to") else "GM"
            if text:
                out.append(f"[{who}] {text}")
        elif kind == "player":
            shown = (m.get("tr") or {}).get(lang) or text
            note = " (privately to the GM)" if m.get("to") else ""
            out.append(f"[{m.get('pc', '?')}{note}] {shown}")
        elif kind == "roll":
            ev = m.get("event") or {}
            r = ev.get("roll")
            if ev.get("secret") or not r:
                continue
            goal = f" vs {r.get('target_label', 'DC')} {r['target']}" if r.get("target") is not None else ""
            outcome = f", {r['outcome']}" if r.get("outcome") else ""
            why = (ev.get("why_tr") or {}).get(lang) or ev.get("why") or ""
            out.append(f"[dice] {m.get('pc') or 'GM'} rolled {r.get('notation')}"
                       f"{' for ' + why if why else ''}: {r.get('total')}{goal}{outcome}")
        elif kind == "system":
            ev = m.get("event") or {}
            if ev.get("type") in ("join", "levelup", "loot", "foe", "place"):
                out.append(f"[event] {text}")
    return out


def build_prompt(lines: List[str], sheet: Optional[Dict[str, Any]], party: List[Dict[str, Any]],
                 location: Optional[str], history: List[Dict[str, str]], question: str,
                 viewer: str) -> str:
    log = "\n".join(lines)
    if len(log) > LOG_CHARS:
        log = "…" + log[-LOG_CHARS:]
    parts = [f"The player asking is {viewer}."]
    if location:
        parts.append(f"The party is now at: {location}.")
    if party:
        parts.append("The party: " + "; ".join(
            f"{p['name']} ({' '.join(x for x in (p.get('race'), p.get('class')) if x) or 'adventurer'}, "
            f"HP {p.get('hp')}/{p.get('hp_max')})" for p in party))
    if sheet:
        keep = {k: sheet[k] for k in ("name", "race", "class", "level", "hp", "conditions",
                                      "equipment", "features", "gold", "xp") if k in sheet}
        parts.append(f"{viewer}'s character sheet: {json.dumps(keep, ensure_ascii=False)}")
    parts.append("STORY LOG (oldest first):\n" + (log or "(nothing has happened yet)"))
    for qa in history[-6:]:
        parts.append(f"Earlier, {viewer} asked: {qa['q']}\nYou answered: {qa['a']}")
    parts.append(f"{viewer} asks: {question}")
    return "\n\n".join(parts)


def lore_prompt(name: str, kind: str, lines: List[str], viewer: str) -> str:
    """A hover card: what this player knows about one name, from the story only."""
    what = {"npc": "this person", "place": "this place", "faction": "this group",
            "pc": "this player character", "foe": "this foe", "treasure": "this item"}.get(kind, "this")
    log = "\n".join(lines)
    if len(log) > LOG_CHARS // 2:
        log = "…" + log[-(LOG_CHARS // 2):]
    # The lines are whole story beats, so they're full of other people: keep the
    # card on its subject, and about the subject rather than about the reader.
    return (f"STORY LOG lines that mention {name} (oldest first):\n{log}\n\n"
            f"In one or two short sentences, sum up what {viewer} knows about {what}, {name}, "
            f"from these lines only. Write about {name} alone: who or what they are, and what "
            f"they did or what was done to them. Leave out other people and events that don't "
            f"involve {name}. Don't write about {viewer} or what {viewer} saw. "
            f"No preamble; start with the facts.")


# --------------------------------------------------------------- answers ----
def _claude(system: str, prompt: str) -> str:
    exe = shutil.which("claude")
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    # No extended thinking: these are short lookups and translations, and `claude -p`
    # thinks by default — ~10k hidden tokens a sheet, 90 s+ instead of ~5 s.
    env["MAX_THINKING_TOKENS"] = "0"
    with tempfile.TemporaryDirectory() as empty:     # no project files, settings or hooks
        done = subprocess.run(  # (no console window on Windows)
            [exe, "-p", "--model", NARRATOR_MODEL, "--tools", "", "--no-session-persistence",
             "--strict-mcp-config", "--system-prompt", system],
            input=prompt, capture_output=True, text=True, timeout=TIMEOUT, cwd=empty, env=env,
            encoding="utf-8",
            **({"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if os.name == "nt" else {}))
    if done.returncode != 0 or not done.stdout.strip():
        raise RuntimeError((done.stderr or done.stdout or "no answer").strip()[-300:])
    return done.stdout.strip()


def _api(system: str, prompt: str, max_tokens: int = 400) -> str:
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(model=API_MODEL, max_tokens=max_tokens, system=system,
                                 messages=[{"role": "user", "content": prompt}])
    return "".join(getattr(b, "text", "") for b in msg.content).strip()


STOP = set("""the a an and or of to in on at for with what who whom whose which where when why how
did does do was were is are be been we you i our us me my it its that this there their they
again remember about tell said say name called mean happened happen""".split())


TRANSLATE_RULES = """You translate the text of a tabletop role-playing game's character sheet \
into {lang} (from whatever language each is in). Some strings mix two languages: give those \
entirely in {lang}, without repeating anything. A string already in {lang} comes back as it is. You get a JSON object of numbered strings, like {{"1": "Stealth", \
"2": "Fire Bolt (1d10)"}}. Reply with ONLY a JSON object with the same numbers, each mapped to \
a pair: the original string copied exactly, then its translation, like \
{{"1": ["Stealth", "..."], "2": ["Fire Bolt (1d10)", "..."]}}. Translate every one. Use the usual {lang} terms \
of role-playing games (Dungeons & Dragons) where they exist. Keep numbers, dice (1d8+2) and \
modifiers (+3) as they are. Write personal and place names in {lang} letters. No notes, no \
markdown."""


UI_RULES = """You translate the words of a web page where friends play a tabletop \
role-playing game together online, with an AI Game Master, into {lang}. You get a JSON object \
of numbered strings: buttons, labels, notices. Reply with ONLY a JSON object with the same \
numbers, each mapped to a pair: the original string copied exactly, then its translation, like \
{{"1": ["Send", "..."]}}. Keep every {{placeholder}} in curly braces exactly as \
it is (they are filled in later: {{pc}} is a character's name, {{n}} a number, {{t}} a time), \
keep emoji and symbols, and keep it short: they are buttons and labels. Use the usual {lang} \
terms of role-playing games (Dungeons & Dragons). No notes, no markdown."""


def translate(strings: List[str], lang: str,
              ask: Optional[Callable[[str, str], str]] = None, kind: str = "sheet") -> Dict[str, str]:
    """{original: translation} for ``strings`` (character-sheet text, or the
    page's own words with ``kind="ui"``) — what the model answered; {} with no
    model, or on an unreadable answer."""
    source = "test" if ask else backend()
    if not strings or source == "off":
        return {}
    system = (UI_RULES if kind == "ui" else TRANSLATE_RULES).format(lang=LANG_NAMES.get(lang, lang))
    if _languages.base(lang) == "he" and kind != "ui":
        # A name from another language is hard to read in Hebrew letters alone.
        system += " Write every personal and place name with full niqqud (vowel points)."
    # Numbered: the answer comes back by number, so a phrase the model retypes a
    # little differently (or translates) can't lose its translation.
    numbered = {str(i + 1): s for i, s in enumerate(strings)}
    prompt = json.dumps(numbered, ensure_ascii=False)
    if ask:
        text = ask(system, prompt)
    elif source == "claude":
        text = _claude(system, prompt)
    else:
        text = _api(system, prompt, max_tokens=8000)
    start, end = text.find("{"), text.rfind("}")
    try:
        got = json.loads(text[start:end + 1]) if start >= 0 else {}
    except ValueError:
        return {}
    if not isinstance(got, dict):
        return {}
    # A model that drops or merges one entry shifts every later number onto the
    # wrong phrase ("Skills" -> "Athletics"). So each answer carries the original
    # back, and an entry is kept only if that copy is the phrase we sent under
    # its number. A bare translation (no copy) is trusted only when the answer
    # has exactly our numbers, nothing missing or extra.
    exact_numbers = set(map(str, got)) == set(numbered)
    out = {}
    for k, v in got.items():
        src = numbered.get(str(k).strip()) or (k if k in strings else None)
        if not src:
            continue
        if isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(x, str) for x in v):
            echo, tr = v
            if not _same_phrase(echo, src):
                continue
        elif isinstance(v, str) and exact_numbers:
            tr = v
        else:
            continue
        if tr.strip():
            out[src] = tr.strip()
    return out


def _same_phrase(echo: str, src: str) -> bool:
    """The model's copy of a phrase is that phrase (allowing a retyped quote or space)."""
    norm = lambda s: " ".join(s.casefold().replace("’", "'").split())
    a, b = norm(echo), norm(src)
    return a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.9


FIND_NAMES_RULES = """You match names in a {lang} passage from a role-playing game to the game's \
own list of names (written in English). You get JSON: {{"names": [...], "passage": "..."}}. Reply \
with ONLY a JSON object mapping each listed name that the passage mentions to the exact spelling \
the passage uses for it: copy the letters exactly as they appear in the passage, without a \
one-letter prefix attached in front (ו ה ב ל מ ש כ). Leave out names the passage doesn't mention. \
No notes, no markdown."""


def find_names(passage: str, names: List[str], lang: str,
               ask: Optional[Callable[[str, str], str]] = None) -> Dict[str, str]:
    """{name: its spelling in ``passage``} for the listed names a non-English
    passage mentions (only spellings that really occur in it)."""
    source = "test" if ask else backend()
    if lang == "en" or not names or not passage.strip() or source == "off":
        return {}
    system = FIND_NAMES_RULES.format(lang=LANG_NAMES.get(lang, lang))
    prompt = json.dumps({"names": names, "passage": passage}, ensure_ascii=False)
    text = ask(system, prompt) if ask else (_claude if source == "claude" else _api)(system, prompt)
    start, end = text.find("{"), text.rfind("}")
    try:
        got = json.loads(text[start:end + 1]) if start >= 0 else {}
    except ValueError:
        return {}
    listed = {n.lower(): n for n in names}
    out = {}
    # Compared without niqqud: the passage may point a name the model copies bare.
    plain = lambda s: _languages.NIQQUD.sub("", s)
    for name, spelling in (got.items() if isinstance(got, dict) else []):
        spelling = plain(" ".join(str(spelling).split()))
        if str(name).lower() in listed and len(spelling) >= 2 and spelling in plain(passage):
            out[listed[str(name).lower()]] = spelling
    return out


def recall(lines: List[str], question: str, lang: str) -> str:
    """No model: quote the story lines that share words with the question."""
    words = {w for w in re.findall(r"\w+", question.lower()) if len(w) > 2 and w not in STOP}
    scored = []
    for i, line in enumerate(lines):
        text = line.lower()
        score = sum(1 for w in words if w in text)
        if score:
            scored.append((score, i, line))
    best = sorted(sorted(scored, reverse=True)[:3], key=lambda x: x[1])
    if not best:
        return ("לא מצאתי את זה בסיפור עד עכשיו." if lang == "he"
                else "I couldn't find that in the story so far.")
    head = "מה שהסיפור אמר:" if lang == "he" else "What the story said:"
    return head + "\n" + "\n".join("• " + (l if len(l) < 400 else l[:400] + "…") for _, _, l in best)


def answer(question: str, lines: List[str], prompt: str, lang: str,
           ask: Optional[Callable[[str, str], str]] = None) -> Dict[str, Any]:
    """{answer, source}: from the model, else the story's own matching lines."""
    system = RULES.format(lang=LANG_NAMES.get(lang, "English"))
    source = "test" if ask else backend()
    if source != "off":
        try:
            fn = ask or (_claude if source == "claude" else _api)
            text = fn(system, prompt)
            if text:
                return {"answer": text[:2000], "source": source}
        except Exception as e:                   # offline, not logged in, timed out...
            print(f"[narrator] {source}: {e}", flush=True)
    return {"answer": recall(lines, question, lang), "source": "recall"}
