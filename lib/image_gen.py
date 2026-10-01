"""image_gen.py — GM scene illustration via OpenAI gpt-image-2, or a local model.

Image sources (``IMAGE_BACKEND`` in .env):
  openai — OpenAI gpt-image-2 (needs OPENAI_API_KEY; the default when a key is set)
  forge  — a local Stable Diffusion WebUI Forge (or AUTOMATIC1111) started with
           --api: free, private, runs on the host's own GPU. FORGE_* settings tune
           it (defaults suit an SDXL "Lightning" model such as DreamShaper XL
           Lightning on a 6 GB laptop GPU; see GAME-NIGHT.md → Pictures).
  off    — no images (the default with no key).

The GM calls this at high-impact beats (new location, boss reveal, big loot) to
show the player a real image. The image is saved into the active campaign's
``images/`` folder and the path is handed back so the caller can show the player
a clickable link. Every generation is logged with an estimated cost so spend is
auditable.

Display path: we DON'T try to render pixels in the terminal. We save a PNG and
return its path; the VS Code terminal linkifies the path so the player clicks to
open it.

No third-party SDK — the request is a single JSON POST, done with stdlib urllib
so the project gains no new dependency.
"""

from __future__ import annotations

import json
import tempfile
import os
import re
import sys
import time
import base64
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from campaign_manager import CampaignManager
import visual_appearance as va_mod
from gpu_turn import gpu_turn


def resolve_campaign_dir(world_state_dir: str = "world-state"):
    """Return the active campaign dir as a Path, or None if none is active."""
    return CampaignManager(world_state_dir).get_active_campaign_dir()


def appearance_line(name: str, campaign_dir=None) -> str:
    """Return the 'character bible' line for a character by name.

    Looks up the player characters (character.json, then players/*.json)
    first, then NPCs (npcs.json), and
    renders the canonical visual_appearance block as one prompt-ready line.
    Returns "" if the name is unknown or has no appearance authored yet.
    """
    campaign_dir = campaign_dir or resolve_campaign_dir()
    if campaign_dir is None or not name:
        return ""
    campaign_dir = Path(campaign_dir)

    # PCs first (the lead, then any other players' characters).
    import party_roster
    for _path, char in party_roster.all_pcs(campaign_dir):
        if str(char.get("name", "")).strip().lower() == name.strip().lower():
            return va_mod.format_line(char.get("name", name),
                                      char.get("visual_appearance"))

    # Then NPCs (case-insensitive key match).
    npcs_path = campaign_dir / "npcs.json"
    if npcs_path.exists():
        try:
            npcs = json.loads(npcs_path.read_text(encoding="utf-8"))
            if isinstance(npcs.get("npcs"), dict):
                npcs = npcs["npcs"]
            for key, data in npcs.items():
                if key.strip().lower() == name.strip().lower() and isinstance(data, dict):
                    return va_mod.format_line(key, data.get("visual_appearance"))
        except (OSError, ValueError):
            pass

    return ""


CHRONICLER_FILE = "chronicler.json"


def _chronicler_path(campaign_dir) -> Path:
    return Path(campaign_dir) / CHRONICLER_FILE


def load_chronicler(campaign_dir=None):
    """Return this campaign's chronicler dict {name, style, persona}, or None."""
    campaign_dir = campaign_dir or resolve_campaign_dir()
    if campaign_dir is None:
        return None
    p = _chronicler_path(campaign_dir)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save_chronicler(*, name=None, style=None, persona=None, campaign_dir=None) -> dict:
    """Merge-update the campaign's chronicler. Only provided fields change."""
    campaign_dir = campaign_dir or resolve_campaign_dir()
    if campaign_dir is None:
        raise ImageGenError("No active campaign. Run /new-game or /import first.")
    data = load_chronicler(campaign_dir) or {}
    if name is not None:
        data["name"] = name
    if style is not None:
        data["style"] = style
    if persona is not None:
        data["persona"] = persona
    _chronicler_path(campaign_dir).write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


API_URL = "https://api.openai.com/v1/images/generations"
DEFAULT_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2")
DEFAULT_QUALITY = os.environ.get("OPENAI_IMAGE_QUALITY", "medium")
DEFAULT_SIZE = os.environ.get("OPENAI_IMAGE_SIZE", "1536x1024")  # cinematic landscape
REQUEST_TIMEOUT = 180  # gpt-image-2 can take up to ~2 min on complex prompts

# Published gpt-image-2 per-image USD pricing (docs). Used only to LOG estimated
# spend — not billed here. Unknown size/quality combos report None (logged as ?).
_COST = {
    "low":    {"1024x1024": 0.006, "1536x1024": 0.005, "1024x1536": 0.005},
    "medium": {"1024x1024": 0.053, "1536x1024": 0.041, "1024x1536": 0.041},
    "high":   {"1024x1024": 0.211, "1536x1024": 0.165, "1024x1536": 0.165},
}


def estimate_cost(quality: str, size: str):
    """Return the published per-image USD cost, or None if not in the table."""
    return _COST.get(quality, {}).get(size)


SLUG_MAX = 32  # keep filenames (and the file:// link) short enough not to line-wrap


def _slug(title: str) -> str:
    """A filesystem-safe, short slug from a scene title.

    Capped at SLUG_MAX chars, trimmed on a word boundary so names never cut
    mid-word (e.g. '...reads-the-dead-i'). Long titles keep their leading words.
    """
    s = re.sub(r"[^a-z0-9]+", "-", (title or "scene").lower()).strip("-")
    if len(s) > SLUG_MAX:
        s = s[:SLUG_MAX].rsplit("-", 1)[0]  # drop the partial trailing word
    return s.strip("-") or "scene"


def _next_path(images_dir: Path, title: str) -> Path:
    """Sequenced filename: NNNN-slug.png, continuing the highest existing index."""
    images_dir.mkdir(parents=True, exist_ok=True)
    highest = 0
    for p in images_dir.glob("[0-9][0-9][0-9][0-9]-*.png"):
        try:
            highest = max(highest, int(p.name[:4]))
        except ValueError:
            continue
    return images_dir / f"{highest + 1:04d}-{_slug(title)}.png"


# Short, shallow symlink dir so the clickable file:// link never line-wraps.
# The deep campaign path (~110 chars) wraps in the terminal and the wrap kills
# the click target; a symlink at <temp>/gm-img/<tag>-NNNN.png resolves to the real
# PNG when clicked while staying short on one line. (Where symlinks aren't allowed,
# e.g. Windows without Developer Mode, the real path is used instead.)
SHORTLINK_DIR = Path(tempfile.gettempdir()) / "gm-img"


def _short_link(out_path: Path, campaign_dir: str) -> Path | None:
    """Create a short symlink to ``out_path`` and return it (None on failure).

    Name: <campaign-initials>-<NNNN>.png — the descriptive slug stays in the real
    filename for browsing; the symlink is purely the clickable handle.
    """
    try:
        tag = "".join(w[:1] for w in Path(campaign_dir).name.split("-"))[:6] or "gm"
        seq = out_path.name[:4]
        SHORTLINK_DIR.mkdir(parents=True, exist_ok=True)
        link = SHORTLINK_DIR / f"{tag}-{seq}.png"
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(out_path.resolve())
        return link
    except OSError:
        return None  # fall back to the absolute path


def _log_generation(images_dir: Path, record: dict) -> None:
    """Append one JSON line to the per-campaign generation/spend log."""
    try:
        with (images_dir / "_gen-log.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass  # logging must never break a successful generation


class ImageGenError(Exception):
    """Raised for user-correctable failures (missing key, moderation, bad request)."""


# --------------------------------------------------------------- sources ----
def backend() -> str:
    """'openai', 'forge' or 'off' — from IMAGE_BACKEND, else whether a key is set."""
    chosen = os.environ.get("IMAGE_BACKEND", "").strip().lower()
    if chosen in ("forge", "a1111", "automatic1111", "sdwebui", "local"):
        return "forge"
    if chosen in ("off", "none", "no"):
        return "off"
    if chosen == "openai":
        return "openai"
    return "openai" if os.environ.get("OPENAI_API_KEY") else "off"


def forge_url() -> str:
    return os.environ.get("FORGE_URL", "http://127.0.0.1:7860").rstrip("/")


def _forge_open(req, timeout):
    # A local server: never route it through a proxy configured for the internet.
    return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout)


def forge_release_gpu() -> bool:
    """Ask Forge to move its model off the graphics card, into RAM (it stays loaded
    there; the next picture moves it back by itself). Done before music is composed
    so only one model is on the card. False if Forge isn't in use or didn't answer."""
    if backend() != "forge":
        return False
    req = urllib.request.Request(forge_url() + "/sdapi/v1/unload-checkpoint", data=b"{}",
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with _forge_open(req, 60) as r:
            r.read()
        return True
    except (urllib.error.URLError, OSError, ValueError):
        return False


def forge_warm_up() -> bool:
    """At the start of a game: have Forge read its picture model into RAM now (one
    tiny throwaway picture), then move it off the graphics card. The first real
    picture then doesn't wait on the disk. False if Forge isn't in use or isn't up."""
    if backend() != "forge" or not images_status()[0]:
        return False
    payload = {"prompt": "warm-up", "steps": 1, "width": 64, "height": 64, "seed": 1,
               "batch_size": 1, "n_iter": 1, "send_images": False, "save_images": False}
    model = os.environ.get("FORGE_MODEL", "").strip()
    if model:                                   # the model the game will use
        payload["override_settings"] = {"sd_model_checkpoint": model}
        payload["override_settings_restore_afterwards"] = False
    req = urllib.request.Request(forge_url() + "/sdapi/v1/txt2img", data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with gpu_turn("pictures"):
            with _forge_open(req, int(os.environ.get("FORGE_TIMEOUT", "600"))) as r:
                r.read()
            forge_release_gpu()
        return True
    except (urllib.error.URLError, OSError, ValueError):
        return False


def images_status(probe: bool = True):
    """(enabled, backend, why) — what the session brief tells the GM."""
    b = backend()
    if b == "off":
        return False, b, ("no image source: add OPENAI_API_KEY, or run a local Forge "
                          "and set IMAGE_BACKEND=forge in .env")
    if b == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            return False, b, "IMAGE_BACKEND=openai but OPENAI_API_KEY is not set"
        return True, b, "OpenAI gpt-image-2"
    if not probe:
        return True, b, f"local Forge at {forge_url()}"
    try:
        with _forge_open(urllib.request.Request(forge_url() + "/sdapi/v1/sd-models"), 3) as r:
            models = json.loads(r.read().decode("utf-8")) or []
    except urllib.error.HTTPError as e:
        if e.code == 404:                       # the web UI answers, its API doesn't
            return False, b, ("Forge is running but its API is off — add --api to "
                              "COMMANDLINE_ARGS in webui\\webui-user.bat and restart it")
        return False, b, f"Forge answered with an error ({e.code})"
    except (urllib.error.URLError, OSError, ValueError):
        return False, b, (f"Forge isn't answering at {forge_url()} — start it (run.bat) "
                          f"with --api, then images turn on")
    if not models:
        return False, b, "Forge is running but has no model — put one in models/Stable-diffusion"
    return True, b, f"local Forge at {forge_url()}"


# Requested size (OpenAI terms) -> the size the local model is good at.
def _forge_dims(size: str):
    try:
        w, h = (int(x) for x in str(size).lower().split("x"))
    except ValueError:
        w, h = 1536, 1024
    key, default = (("FORGE_LANDSCAPE", "1216x832") if w > h else
                    ("FORGE_PORTRAIT", "832x1216") if h > w else ("FORGE_SQUARE", "1024x1024"))
    try:
        fw, fh = (int(x) for x in os.environ.get(key, default).lower().split("x"))
    except ValueError:
        fw, fh = (int(x) for x in default.split("x"))
    return fw, fh


FORGE_NEGATIVE = ("text, words, letters, watermark, signature, logo, frame, border, lowres, "
                  "blurry, jpeg artifacts, deformed, disfigured, extra fingers, extra limbs, "
                  "bad hands, bad anatomy")


def _forge_generate(prompt: str, quality: str, size: str, avoid: str = ""):
    """One image from the local Forge/AUTOMATIC1111 API -> (png bytes, model, WxH).
    ``avoid``: more for the negative prompt (a man's portrait avoids "woman")."""
    w, h = _forge_dims(size)
    steps = int(os.environ.get("FORGE_STEPS", "6"))
    if quality == "low":
        steps = max(3, steps - 2)
    elif quality == "high":
        steps += 2
    payload = {
        "prompt": prompt,
        "negative_prompt": ", ".join(x for x in (avoid, os.environ.get("FORGE_NEGATIVE", FORGE_NEGATIVE)) if x),
        "steps": steps,
        "cfg_scale": float(os.environ.get("FORGE_CFG", "2")),
        "sampler_name": os.environ.get("FORGE_SAMPLER", "DPM++ SDE"),
        "scheduler": os.environ.get("FORGE_SCHEDULER", "Karras"),
        "width": w, "height": h, "seed": -1, "batch_size": 1, "n_iter": 1,
        "send_images": True, "save_images": False,
    }
    model = os.environ.get("FORGE_MODEL", "").strip()
    if model:
        payload["override_settings"] = {"sd_model_checkpoint": model}
        payload["override_settings_restore_afterwards"] = False
    req = urllib.request.Request(forge_url() + "/sdapi/v1/txt2img",
                                 data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        # The first image also loads the model: slow on a laptop GPU. The card is
        # shared with the music composer: wait for our turn on it.
        with gpu_turn("pictures"), _forge_open(req, int(os.environ.get("FORGE_TIMEOUT", "600"))) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode("utf-8")).get("detail") or ""
        except Exception:
            pass
        if e.code == 404:
            raise ImageGenError("Forge has no API at " + forge_url() + " — add --api to "
                                "COMMANDLINE_ARGS in webui-user.bat and restart it.") from e
        raise ImageGenError(f"Forge error {e.code}: {detail or 'request failed'} "
                            "(out of GPU memory? see GAME-NIGHT.md → Pictures)") from e
    except (urllib.error.URLError, OSError) as e:
        raise ImageGenError(f"Can't reach Forge at {forge_url()} — is it running (with --api)? "
                            f"({getattr(e, 'reason', e)})") from e
    try:
        b64 = body["images"][0]
        if "," in b64[:64]:
            b64 = b64.split(",", 1)[1]          # a data: URI
        return base64.b64decode(b64), "forge:" + (model or "current model"), f"{w}x{h}"
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise ImageGenError("Forge answered without an image.") from e


def inject_appearances(prompt: str, characters, campaign_dir=None) -> str:
    """Append each named character's canonical look to the prompt. Idempotent.

    Always injects when a stored appearance exists — a beat prompt naturally
    names its characters ("Carl swings the club..."), and until 2026-08-13 that
    name-mention suppressed the injection, letting recurring characters drift
    off-model. Only an appearance line already present verbatim is skipped.
    """
    out = prompt
    for cname in (characters or []):
        line = appearance_line(cname, campaign_dir)
        if line and line not in out:
            out = f"{out.rstrip()}\n\nCharacter (render exactly): {line}"
    return out


def build_prompt(prompt: str, characters=None, campaign_dir=None, *,
                 style_lock: bool = True, appearance_lock: bool = True,
                 chronicler=None) -> str:
    """The prompt actually sent to the model: the caller's text plus the two locks.

    Both locks default ON and stay belt-and-braces — they fire even on a direct
    fallback call where the caller forgot. Turning one off is a story call, not a
    tidiness one: a dream sequence or flashback rendered in another register
    (``style_lock=False``), or a transformation, disguise, or vision where the
    stored look is deliberately wrong (``appearance_lock=False``).
    """
    final = inject_appearances(prompt, characters, campaign_dir) if appearance_lock else prompt

    # Lock the campaign's art-style signature into every prompt so the gallery
    # reads like one artbook even if the caller forgets to restate the style.
    if style_lock:
        if chronicler is None:
            chronicler = load_chronicler(campaign_dir)
        style = (chronicler or {}).get("style", "").strip()
        if style and style.lower() not in final.lower():
            final = f"{final.rstrip()}\n\nConsistent art style (campaign signature): {style}."

    return final


def generate_image(prompt: str, *, title: str = "", quality: str = DEFAULT_QUALITY,
                   size: str = DEFAULT_SIZE, model: str = DEFAULT_MODEL,
                   characters=None, style_lock: bool = True,
                   appearance_lock: bool = True, campaign_dir=None, avoid: str = "") -> dict:
    """Generate one image and save it under the active campaign's images/ dir.

    ``characters`` is an optional list of character names in frame; each one's
    canonical visual_appearance block is auto-injected into the prompt so the PC
    and NPCs render CONSISTENTLY image-to-image, even on direct/fallback calls.
    ``style_lock`` / ``appearance_lock`` opt a single beat out of those
    injections (see ``build_prompt``).

    Returns {path, rel_path, cost, model, quality, size, title}. Raises
    ImageGenError for actionable problems (no campaign, no key, moderation).
    """
    source = backend()
    api_key = os.environ.get("OPENAI_API_KEY")
    if source == "off" or (source == "openai" and not api_key):
        raise ImageGenError(
            "No image source. Add OPENAI_API_KEY=sk-... to .env, or run a local Stable "
            "Diffusion WebUI Forge with --api and set IMAGE_BACKEND=forge in .env "
            "(GAME-NIGHT.md → Pictures)."
        )

    campaign_dir = campaign_dir or resolve_campaign_dir()
    if campaign_dir is None:
        raise ImageGenError("No active campaign. Run /new-game or /import first.")

    if not prompt or not prompt.strip():
        raise ImageGenError("Empty prompt — describe the scene to illustrate.")

    chronicler = load_chronicler(campaign_dir)
    final_prompt = build_prompt(prompt, characters, campaign_dir,
                                style_lock=style_lock, appearance_lock=appearance_lock,
                                chronicler=chronicler)

    if source == "forge":
        image_bytes, model, size = _forge_generate(final_prompt, quality, size, avoid)
        cost = 0.0
    else:
        image_bytes = _openai_generate(final_prompt, api_key, model, quality, size)
        cost = estimate_cost(quality, size)

    images_dir = Path(campaign_dir) / "images"
    out_path = _next_path(images_dir, title)
    out_path.write_bytes(image_bytes)

    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "file": out_path.name,
        "title": title,
        "model": model,
        "quality": quality,
        "size": size,
        "est_cost_usd": cost,
        "chronicler": (chronicler or {}).get("name"),
        "prompt": final_prompt[:500],
    }
    _log_generation(images_dir, record)

    short = _short_link(out_path, campaign_dir)
    return {
        "path": str(out_path),
        "rel_path": os.path.relpath(out_path, Path.cwd()),
        "short_path": str(short) if short else str(out_path),
        "cost": cost,
        "model": model,
        "quality": quality,
        "size": size,
        "title": title,
    }


# ------------------------------------------------------------ portraits ----
def _find_character(name: str, campaign_dir: Path):
    """('pc', path, sheet) or ('npc', path, record) for ``name``, else None."""
    import party_roster
    from character_schema import to_flat
    path = party_roster.find_pc(campaign_dir, name)
    if path is not None:
        return "pc", path, to_flat(json.loads(path.read_text(encoding="utf-8")))
    npcs_path = Path(campaign_dir) / "npcs.json"
    if npcs_path.exists():
        npcs = json.loads(npcs_path.read_text(encoding="utf-8"))
        table = npcs["npcs"] if isinstance(npcs.get("npcs"), dict) else npcs
        for key, data in table.items():
            if key.strip().lower() == name.strip().lower() and isinstance(data, dict):
                return "npc", npcs_path, dict(data, name=key)
    return None


SEXES = {"male": ("male", "man", "woman, female, feminine face, girl, breasts"),
         "female": ("female", "woman", "man, male, masculine face, beard, boy")}


def sex_of(record: dict) -> str:
    """'male', 'female' or '' from the record's stored appearance."""
    va = record.get("visual_appearance") if isinstance(record.get("visual_appearance"), dict) else {}
    s = str(va.get("sex") or record.get("sex") or "").strip().lower()
    if s in ("male", "man", "m", "boy", "masculine", "he", "זכר", "גבר"):
        return "male"
    if s in ("female", "woman", "f", "girl", "feminine", "she", "נקבה", "אישה"):
        return "female"
    return ""


# Words that mark a portrait's subject as a creature, not a person: a familiar, a
# pet, a summoned beast. Its name ("Old Mother Coil") mustn't make it a person.
CREATURES = re.compile(
    r"\b(snakes?|serpents?|vipers?|adders?|cobras?|pythons?|owls?|ravens?|crows?|hawks?|falcons?|"
    r"eagles?|parrots?|bats?|rats?|mice|mouse|cats?|kittens?|dogs?|hounds?|wolf|wolves|fox|foxes|"
    r"bears?|horses?|ponies|pony|mules?|donkeys?|boars?|goats?|stags?|deer|elk|oxen|ox|lions?|"
    r"tigers?|panthers?|leopards?|spiders?|scorpions?|beetles?|frogs?|toads?|lizards?|newts?|"
    r"salamanders?|octopus|crabs?|fish|eels?|sharks?|weasels?|ferrets?|badgers?|otters?|"
    r"monkeys?|apes?|drakes?|wyrms?|wyverns?|dragons?|griffons?|griffins?|beasts?|creatures?|"
    r"animals?|familiars?|imps?|pseudodragons?|sprites?|slimes?|oozes?|golems?|constructs?|"
    r"נחש|נחשה|ינשוף|עורב|חתול|חתולה|כלב|זאב|שועל|דוב|סוס|עכביש|עטלף|עכברוש|צפרדע|לטאה|דרקון|יצור|חיה)\b",
    re.IGNORECASE)
HE_CREATURES = {"נחש": "snake", "נחשה": "snake", "ינשוף": "owl", "עורב": "raven", "חתול": "cat",
                "חתולה": "cat", "כלב": "dog", "זאב": "wolf", "שועל": "fox", "דוב": "bear", "סוס": "horse",
                "עכביש": "spider", "עטלף": "bat", "עכברוש": "rat", "צפרדע": "frog", "לטאה": "lizard",
                "דרקון": "dragon", "יצור": "creature", "חיה": "animal"}
HUMANOID = re.compile(r"\b(human|man|woman|elf|elven|dwarf|halfling|gnome|orc|half-orc|half-elf|"
                      r"tiefling|goliath|aasimar|person|girl|boy|lady|lord|king|queen)\b", re.IGNORECASE)


def creature_of(record: dict) -> str:
    """'snake', 'owl'... when the record shows a creature rather than a person
    (its appearance's species/race first, then its description), else ''."""
    va = record.get("visual_appearance") if isinstance(record.get("visual_appearance"), dict) else {}
    kind = " ".join(str(va.get(k) or "") for k in ("species", "race")).strip()
    for text in (kind, str(record.get("race") or ""),
                 str(record.get("description") or record.get("concept") or "")):
        found = CREATURES.search(text)
        if found and not (text is not kind and HUMANOID.search(text[:found.start()])):
            word = found.group(0).lower()
            return HE_CREATURES.get(word, word)        # (the picture model reads English)
    return ""


def portrait_avoid(record: dict) -> str:
    """What a portrait must not show, for the negative prompt: a person, for a
    creature; the other sex, for a person."""
    if creature_of(record):
        return "human, person, woman, man, girl, boy, humanoid, human face, human skin"
    sex = sex_of(record)
    return SEXES[sex][2] if sex else ""


def portrait_prompt(record: dict) -> str:
    """A head-and-shoulders portrait brief from whatever the record says about them.
    Their sex comes FIRST: picture models weigh the start of a prompt most."""
    name = record.get("name", "")
    who = " ".join(str(record.get(k) or "").strip() for k in ("race", "class")).strip()
    about = record.get("concept") or record.get("description") or ""
    creature = creature_of(record)
    if creature:
        # What it IS comes first; the name comes last (a name like "Old Mother
        # Coil" would otherwise make it a woman).
        a = "an" if creature[0] in "aeiou" else "a"
        lines = [f"Portrait of {a} {creature}, an animal, not a person" + (f": {about}" if about else "") + "."]
        lines.append("Close-up of the creature, its head and body, simple softly lit background, no "
                     f"text. (It is called {name}.)")
        return " ".join(lines)
    sex = sex_of(record)
    if sex:
        adj, noun, _ = SEXES[sex]
        lines = [f"Character portrait of a {noun}: {name}, a {adj} {who or noun}."]
    else:
        lines = [f"Character portrait of {name}" + (f", {who}" if who else "") + "."]
    if about:
        lines.append(f"Who they are: {about}.")
    lines.append("Head-and-shoulders portrait facing the viewer, expressive detailed face, "
                 "simple softly lit background, no text.")
    return " ".join(lines)


def _record_portrait(kind: str, path: Path, name: str, filename: str) -> None:
    """Write ``portrait`` onto the PC sheet / NPC entry (re-read just before writing)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if kind == "pc":
        data["portrait"] = filename
    else:
        table = data["npcs"] if isinstance(data.get("npcs"), dict) else data
        key = next(k for k in table if k.strip().lower() == name.strip().lower())
        table[key]["portrait"] = filename
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def generate_portrait(name: str, campaign_dir=None, quality: str = DEFAULT_QUALITY) -> dict:
    """Draw ``name``'s portrait (PC or NPC) in the campaign's style, from their stored
    appearance, and record it on their sheet / NPC entry as ``portrait``."""
    campaign_dir = Path(campaign_dir or resolve_campaign_dir() or "")
    found = _find_character(name, campaign_dir) if str(campaign_dir) else None
    if not found:
        raise ImageGenError(f"No character named '{name}' in this campaign.")
    kind, path, record = found
    out = generate_image(portrait_prompt(record), title=f"portrait {record['name']}",
                         quality=quality, size="1024x1536", characters=[record["name"]],
                         campaign_dir=campaign_dir, avoid=portrait_avoid(record))
    filename = Path(out["path"]).name
    _record_portrait(kind, path, record["name"], filename)
    return {**out, "portrait": filename, "kind": kind, "name": record["name"]}


# --------------------------------------------------------------- places ----
def find_location(name: str, campaign_dir):
    """(locations.json path, key, record) for ``name`` (case-insensitive), else None."""
    path = Path(campaign_dir) / "locations.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    table = data["locations"] if isinstance(data.get("locations"), dict) else data
    for key, rec in table.items():
        if key.strip().lower() == str(name).strip().lower() and isinstance(rec, dict):
            return path, key, rec
    return None


def location_is_important(rec: dict) -> bool:
    """A place the GM has actually written about (a move alone creates a bare
    record: position "unknown", no description) or flagged ``important``."""
    position = str(rec.get("position") or "").strip().lower()
    return bool(rec.get("important") or str(rec.get("description") or "").strip()
                or position not in ("", "unknown"))


def location_prompt(name: str, rec: dict) -> str:
    bits = [f"Establishing view of {name}."]
    for k in ("description", "position"):
        v = str(rec.get(k) or "").strip()
        if v and v.lower() != "unknown":
            bits.append(v.rstrip(".") + ".")
    bits.append("Wide cinematic environment art with the place itself as the subject: "
                "architecture, landscape, light and atmosphere; no close-up figures, no text.")
    return " ".join(bits)


def generate_location_image(name: str, campaign_dir=None, quality: str = DEFAULT_QUALITY) -> dict:
    """Paint a place in the campaign's style and record it on the location as ``image``."""
    campaign_dir = Path(campaign_dir or resolve_campaign_dir() or "")
    found = find_location(name, campaign_dir) if str(campaign_dir) else None
    if not found:
        raise ImageGenError(f"No location named '{name}' (add it: gm-location.sh add).")
    path, key, rec = found
    out = generate_image(location_prompt(key, rec), title=f"place {key}", quality=quality,
                         size="1536x1024", campaign_dir=campaign_dir)
    filename = Path(out["path"]).name
    data = json.loads(path.read_text(encoding="utf-8"))          # re-read just before writing
    table = data["locations"] if isinstance(data.get("locations"), dict) else data
    table[key]["image"] = filename
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    return {**out, "image": filename, "name": key}


# --------------------------------------------------- foes and treasures ----
# Kept per campaign, so a foe or treasure is painted once and reused:
#   bestiary.json  {name: {"portrait": file, "boss_portrait": file, "look": text}}
#   treasures.json {name: {"image": file, "look": text, "owner": pc}}
def _load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _entry(table: dict, name: str):
    """The key in ``table`` matching ``name`` case-insensitively, else None."""
    return next((k for k in table if k.strip().lower() == str(name).strip().lower()), None)


def enemy_art(name: str, boss: bool, campaign_dir) -> str:
    """The stored portrait of this foe (the boss one for a boss), or ""."""
    table = _load(Path(campaign_dir) / "bestiary.json")
    key = _entry(table, name)
    rec = table.get(key) or {}
    f = rec.get("boss_portrait" if boss else "portrait") or ""
    return f if f and (Path(campaign_dir) / "images" / f).is_file() else ""


def treasure_art(name: str, campaign_dir) -> str:
    table = _load(Path(campaign_dir) / "treasures.json")
    rec = table.get(_entry(table, name)) or {}
    f = rec.get("image") or ""
    return f if f and (Path(campaign_dir) / "images" / f).is_file() else ""


def enemy_prompt(name: str, about: str, boss: bool) -> str:
    who = f"{name}" + (f", {about.rstrip('.')}" if about else "")
    if boss:
        return (f"Epic boss portrait of {who}. The climactic villain of the story: towering, "
                "terrifying and magnificent, seen from a low heroic angle, dramatic backlight and "
                "blazing rim light, swirling ominous energy, cinematic composition, intricate "
                "detail, no text.")
    return (f"Menacing portrait of {who}. A dangerous foe seen up close and ready to strike: "
            "low angle, harsh rim lighting, intimidating expression, rich detail, no text.")


def generate_enemy_portrait(name: str, campaign_dir=None, boss: bool = False, look: str = "",
                            quality: Optional[str] = None) -> dict:
    """Paint a foe — an epic version for a boss — in the campaign's style. Uses the
    NPC's record (description, stored appearance) when the foe is a known NPC."""
    campaign_dir = Path(campaign_dir or resolve_campaign_dir() or ".")
    found = _find_character(name, campaign_dir)
    rec = found[2] if found else {}
    about = look or rec.get("description") or rec.get("concept") or ""
    out = generate_image(enemy_prompt(rec.get("name", name), about, boss),
                         title=f"{'boss' if boss else 'foe'} {name}",
                         quality=quality or ("high" if boss else DEFAULT_QUALITY), size="1024x1536",
                         characters=[rec["name"]] if found else None, campaign_dir=campaign_dir)
    filename = Path(out["path"]).name
    path = campaign_dir / "bestiary.json"
    table = _load(path)
    key = _entry(table, name) or " ".join(str(name).split())
    table.setdefault(key, {})["boss_portrait" if boss else "portrait"] = filename
    if look:
        table[key]["look"] = look
    _save(path, table)
    return {**out, "image": filename, "name": key, "boss": boss}


def item_prompt(name: str, look: str) -> str:
    return (f"Treasure art of {name}" + (f": {look.rstrip('.')}" if look else "") + ". The object "
            "alone as the hero of the picture, on a dark backdrop with dramatic light, fine "
            "craftsmanship, glowing with magic if it is magical, rich detail, no text.")


def generate_item_image(name: str, campaign_dir=None, look: str = "", owner: str = "",
                        quality: str = DEFAULT_QUALITY) -> dict:
    """Paint an important piece of loot and keep it in treasures.json."""
    campaign_dir = Path(campaign_dir or resolve_campaign_dir() or ".")
    out = generate_image(item_prompt(name, look), title=f"treasure {name}", quality=quality,
                         size="1024x1024", campaign_dir=campaign_dir)
    filename = Path(out["path"]).name
    path = campaign_dir / "treasures.json"
    table = _load(path)
    key = _entry(table, name) or " ".join(str(name).split())
    table.setdefault(key, {})["image"] = filename
    if look:
        table[key]["look"] = look
    if owner:
        table[key]["owner"] = owner
    _save(path, table)
    return {**out, "image": filename, "name": key}


def _openai_generate(final_prompt: str, api_key: str, model: str, quality: str, size: str) -> bytes:
    payload = json.dumps({
        "model": model,
        "prompt": final_prompt,
        "size": size,
        "quality": quality,
        "n": 1,
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise ImageGenError(_format_http_error(e)) from e
    except urllib.error.URLError as e:
        raise ImageGenError(f"Network error reaching OpenAI: {e.reason}") from e

    try:
        b64 = body["data"][0]["b64_json"]
        return base64.b64decode(b64)
    except (KeyError, IndexError, ValueError) as e:
        raise ImageGenError("Unexpected response from image API (no image data).") from e


def _format_http_error(e: "urllib.error.HTTPError") -> str:
    """Turn an OpenAI HTTP error into an actionable one-line message."""
    try:
        err = json.loads(e.read().decode("utf-8")).get("error", {})
    except Exception:
        err = {}
    code = err.get("code")
    msg = err.get("message", "")
    if code == "moderation_blocked":
        stage = (err.get("moderation_details") or {}).get("moderation_stage", "input")
        return f"Image blocked by content moderation ({stage}). Revise the prompt and retry."
    if e.code == 401:
        return "OpenAI rejected the API key (401). Check OPENAI_API_KEY in .env."
    if e.code == 429:
        return "OpenAI rate limit / quota hit (429). Wait and retry, or check billing."
    return f"OpenAI error {e.code}: {msg or 'request failed'}"


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate a scene image with gpt-image-2")
    parser.add_argument("--prompt", help="Scene description (or read from stdin if omitted)")
    parser.add_argument("--title", default="", help="Scene title (used in filename + canvas)")
    parser.add_argument("--character", action="append", default=[], metavar="NAME",
                        help="Character in frame; auto-injects their visual_appearance. Repeatable.")
    parser.add_argument("--no-style-lock", dest="style_lock", action="store_false",
                        help="Skip the campaign art-style injection (dream sequence, flashback)")
    parser.add_argument("--no-appearance-lock", dest="appearance_lock", action="store_false",
                        help="Skip the visual_appearance injection (transformation, disguise, vision)")
    parser.add_argument("--portrait", metavar="NAME",
                        help="Draw this PC's or NPC's portrait and save it on their record")
    parser.add_argument("--location", metavar="NAME",
                        help="Paint this location and save the picture on its record")
    parser.add_argument("--enemy", metavar="NAME", help="Paint a foe's portrait (--boss: epic)")
    parser.add_argument("--item", metavar="NAME", help="Paint an important piece of loot")
    parser.add_argument("--boss", action="store_true", help="With --enemy: the boss portrait")
    parser.add_argument("--look", default="", help="With --enemy/--item: what it looks like")
    parser.add_argument("--owner", default="", help="With --item: who has it")
    parser.add_argument("--appearance", metavar="NAME",
                        help="Print one character's visual_appearance bible line and exit")
    parser.add_argument("--quality", default=DEFAULT_QUALITY, choices=["low", "medium", "high", "auto"])
    parser.add_argument("--size", default=DEFAULT_SIZE, help="e.g. 1536x1024, 1024x1024, auto")
    parser.add_argument("--json", action="store_true", help="Emit the result as JSON")
    parser.add_argument("--show-chronicler", action="store_true",
                        help="Print the campaign's chronicler (name/style/persona) and exit")
    parser.add_argument("--set-chronicler", action="store_true",
                        help="Save/merge the campaign's chronicler from the fields below, then exit")
    parser.add_argument("--name", help="Chronicler name (with --set-chronicler)")
    parser.add_argument("--style", help="Locked art-style signature (with --set-chronicler)")
    parser.add_argument("--persona", help="Chronicler persona/voice (with --set-chronicler)")
    args = parser.parse_args()

    if args.portrait is not None:
        try:
            out = generate_portrait(args.portrait, quality=args.quality)
        except ImageGenError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(out) if args.json else f"Portrait of {out['name']}: {out['path']}")
        return

    if args.location is not None:
        try:
            out = generate_location_image(args.location, quality=args.quality)
        except ImageGenError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(out) if args.json else f"Picture of {out['name']}: {out['path']}")
        return

    if args.enemy is not None or args.item is not None:
        try:
            if args.enemy is not None:
                out = generate_enemy_portrait(args.enemy, boss=args.boss, look=args.look,
                                              quality=None if args.quality == DEFAULT_QUALITY else args.quality)
            else:
                out = generate_item_image(args.item, look=args.look, owner=args.owner,
                                          quality=args.quality)
        except ImageGenError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(out) if args.json else f"{out['name']}: {out['path']}")
        return

    if args.appearance is not None:
        line = appearance_line(args.appearance)
        if args.json:
            print(json.dumps({"name": args.appearance, "appearance": line}))
        elif line:
            print(line)
        else:
            print(f"No visual_appearance set for '{args.appearance}' "
                  "(set it via gm-npc.sh set-appearance / gm-player.sh set-appearance).")
        return

    if args.show_chronicler:
        chronicler = load_chronicler()
        if args.json:
            print(json.dumps(chronicler or {}))
        elif not chronicler:
            print("No chronicler set for this campaign yet.")
        else:
            print(f"Chronicler: {chronicler.get('name', '(unnamed)')}")
            if chronicler.get("persona"):
                print(f"  persona: {chronicler['persona']}")
            if chronicler.get("style"):
                print(f"  style:   {chronicler['style']}")
        return

    if args.set_chronicler:
        if args.name is None and args.style is None and args.persona is None:
            print("[ERROR] --set-chronicler needs at least one of --name/--style/--persona",
                  file=sys.stderr)
            sys.exit(1)
        try:
            data = save_chronicler(name=args.name, style=args.style, persona=args.persona)
        except ImageGenError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(data) if args.json else f"Chronicler saved: {data.get('name', '(unnamed)')}")
        return

    prompt = args.prompt if args.prompt is not None else sys.stdin.read()

    try:
        result = generate_image(prompt, title=args.title, quality=args.quality,
                                size=args.size, characters=args.character,
                                style_lock=args.style_lock,
                                appearance_lock=args.appearance_lock)
    except ImageGenError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result))
    else:
        print(result["path"])


if __name__ == "__main__":
    main()
