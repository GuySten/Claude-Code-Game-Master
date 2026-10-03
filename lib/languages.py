#!/usr/bin/env python3
"""The languages an adventure is played in.

Chosen when the adventure starts (``gm-table.sh languages en he``) and kept with
the campaign (``<campaign>/table/languages.json``). English alone is the
default. With more than one, the table is multilingual: every player reads
every beat, action, sheet and hover card in their own language, and switches
language at any moment without waiting for the GM.

Languages are ISO 639-1 codes ("en", "he", "fr", "pt-BR" ...). Any code works;
the ones below also have a name, their own name, and a writing direction.
"""

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

DEFAULT = ["en"]

# code -> (English name, the language's own name)
KNOWN: Dict[str, tuple] = {
    "en": ("English", "English"), "he": ("Hebrew", "עברית"), "ar": ("Arabic", "العربية"),
    "fa": ("Persian", "فارسی"), "ur": ("Urdu", "اردو"), "yi": ("Yiddish", "ייִדיש"),
    "fr": ("French", "Français"), "es": ("Spanish", "Español"), "de": ("German", "Deutsch"),
    "it": ("Italian", "Italiano"), "pt": ("Portuguese", "Português"),
    "pt-BR": ("Brazilian Portuguese", "Português (Brasil)"), "nl": ("Dutch", "Nederlands"),
    "sv": ("Swedish", "Svenska"), "no": ("Norwegian", "Norsk"), "da": ("Danish", "Dansk"),
    "fi": ("Finnish", "Suomi"), "pl": ("Polish", "Polski"), "cs": ("Czech", "Čeština"),
    "ro": ("Romanian", "Română"), "hu": ("Hungarian", "Magyar"), "tr": ("Turkish", "Türkçe"),
    "ru": ("Russian", "Русский"), "uk": ("Ukrainian", "Українська"), "bg": ("Bulgarian", "Български"),
    "el": ("Greek", "Ελληνικά"), "hi": ("Hindi", "हिन्दी"), "ja": ("Japanese", "日本語"),
    "zh": ("Chinese", "中文"), "ko": ("Korean", "한국어"), "th": ("Thai", "ไทย"),
    "vi": ("Vietnamese", "Tiếng Việt"), "id": ("Indonesian", "Bahasa Indonesia"),
    "ca": ("Catalan", "Català"), "eo": ("Esperanto", "Esperanto"),
}
RTL = {"he", "yi", "ar", "fa", "ur"}

# Writing systems, to tell which language a text is in when it doesn't say.
SCRIPTS = {
    "hebrew": ("֐", "׿"), "arabic": ("؀", "ۿ"), "cyrillic": ("Ѐ", "ӿ"),
    "greek": ("Ͱ", "Ͽ"), "devanagari": ("ऀ", "ॿ"), "thai": ("฀", "๿"),
    "hangul": ("가", "힯"), "kana": ("぀", "ヿ"), "han": ("一", "鿿"),
}
LANG_SCRIPT = {"he": "hebrew", "yi": "hebrew", "ar": "arabic", "fa": "arabic", "ur": "arabic",
               "ru": "cyrillic", "uk": "cyrillic", "bg": "cyrillic", "el": "greek",
               "hi": "devanagari", "th": "thai", "ko": "hangul", "ja": "kana", "zh": "han"}

_CODE = re.compile(r"^[a-z]{2,3}(-[A-Za-z]{2,4})?$")


def base(code: str) -> str:
    return str(code).split("-")[0].lower()


def valid(code: str) -> bool:
    return bool(_CODE.match(str(code or "")))


def name(code: str) -> str:
    """The language's English name ("Hebrew"), or the code itself."""
    return (KNOWN.get(code) or KNOWN.get(base(code)) or (code,))[0]


def native(code: str) -> str:
    """The language's own name ("עברית"), for the language picker."""
    entry = KNOWN.get(code) or KNOWN.get(base(code))
    return entry[1] if entry else code


def rtl(code: str) -> bool:
    return base(code) in RTL


def script(code: str) -> str:
    return LANG_SCRIPT.get(base(code), "latin")


def describe(codes: Iterable[str]) -> List[Dict[str, object]]:
    """What a page needs to offer the languages: [{code, name, native, rtl}]."""
    return [{"code": c, "name": name(c), "native": native(c), "rtl": rtl(c)} for c in codes]


def text_script(text: str) -> Optional[str]:
    """The writing system most of ``text``'s letters are in (None: no letters)."""
    counts: Dict[str, int] = {}
    for ch in text or "":
        if not ch.isalpha():
            continue
        found = "latin"
        for sc, (lo, hi) in SCRIPTS.items():
            if lo <= ch <= hi:
                found = sc
                break
        else:
            if not (ch.isascii() or "À" <= ch <= "ɏ" or "Ḁ" <= ch <= "ỿ"):
                found = "other"
        if found == "han":
            found = "kana" if any("぀" <= c <= "ヿ" for c in text) else "han"
        counts[found] = counts.get(found, 0) + 1
    return max(counts, key=counts.get) if counts else None


def guess(text: str, candidates: Iterable[str]) -> str:
    """Which of ``candidates`` (the table's languages) ``text`` is written in, by
    its writing system. Languages sharing one (English and French) can't be told
    apart this way: English wins, else the first of them."""
    cands = list(candidates) or DEFAULT
    sc = text_script(text)
    same = [c for c in cands if script(c) == sc]
    if not same:
        return "en" if sc == "latin" else cands[0]
    return "en" if "en" in same else same[0]


def foreign_to(text: str, lang: str) -> bool:
    """Would a ``lang`` reader need ``text`` translated? Anything with words in
    another writing system; for a language that shares English's alphabet, any
    words at all (they can't be told apart, and a translation of a phrase already
    in ``lang`` just comes back the same)."""
    words = re.findall(r"[^\W\d_]{2,}", text or "")
    if not words:
        return False
    mine = script(lang)
    for w in words:
        sc = text_script(w)
        if sc != mine:
            return True
        if mine == "latin" and base(lang) != "en":
            return True
    return False


# ------------------------------------------------- the campaign's setting ----
def path(campaign_dir: Path) -> Path:
    return Path(campaign_dir) / "table" / "languages.json"


def load(campaign_dir: Path) -> List[str]:
    """The adventure's languages, first = the one it is mainly told in. A campaign
    that never chose keeps English, plus whatever its players already read in."""
    try:
        data = json.loads(path(campaign_dir).read_text(encoding="utf-8"))
        chosen = [c for c in data.get("languages", []) if valid(c)]
        if chosen:
            return list(dict.fromkeys(chosen))
    except (OSError, ValueError, AttributeError):
        pass
    out = list(DEFAULT)
    try:
        seated = json.loads((Path(campaign_dir) / "table" / "langs.json").read_text(encoding="utf-8"))
        out += [c for c in seated.values() if valid(c)]
    except (OSError, ValueError, AttributeError):
        pass
    return list(dict.fromkeys(out))


def parse(codes: Iterable[str]) -> List[str]:
    """``["en", "he,fr"]`` -> ``["en", "he", "fr"]``; raises ValueError on a bad code."""
    out: List[str] = []
    for item in codes:
        for c in re.split(r"[,\s]+", str(item).strip()):
            if not c:
                continue
            c = c if "-" not in c else base(c) + "-" + c.split("-", 1)[1].upper()
            c = c if "-" in c else c.lower()
            if not valid(c):
                raise ValueError(f"not a language code: {c} (use ISO codes like en, he, fr, es)")
            out.append(c)
    return list(dict.fromkeys(out)) or list(DEFAULT)


def save(campaign_dir: Path, codes: List[str]) -> List[str]:
    codes = parse(codes)
    p = path(campaign_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps({"languages": codes}, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
    return codes
