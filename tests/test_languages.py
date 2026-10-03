"""The adventure's languages (lib/languages.py, ``gm-table.sh languages``): English
alone by default, or any number of them, chosen when the adventure starts. Every
beat, action, character sheet, hover card and the page's own words exist in each,
so a player can switch language at any moment and find it all there."""

import json

import pytest

from lib import cloud_table, languages
from tests.test_cloud_table import bridge, docs  # noqa: F401  (the cloud bridge)
from tests.test_table_server import CODE, set_languages, table, wait_for  # noqa: F401


def test_codes_names_and_writing_systems():
    assert languages.parse(["en", "he,FR", "pt-br"]) == ["en", "he", "fr", "pt-BR"]
    with pytest.raises(ValueError):
        languages.parse(["english!"])
    assert languages.name("he") == "Hebrew" and languages.native("fr") == "Français"
    assert languages.rtl("ar") and not languages.rtl("fr") and languages.name("xx") == "xx"
    assert languages.guess("אני מדליק לפיד", ["en", "he"]) == "he"
    assert languages.guess("Открываю дверь", ["en", "ru"]) == "ru"
    assert languages.guess("J'ouvre la porte", ["en", "fr"]) == "en"    # one alphabet: English wins
    assert languages.guess("J'ouvre la porte", ["fr", "he"]) == "fr"
    # What a reader would need translated on a sheet.
    assert languages.foreign_to("Stealth", "he") and not languages.foreign_to("התגנבות", "he")
    assert languages.foreign_to("Stealth", "fr") and not languages.foreign_to("Stealth", "en")
    assert languages.foreign_to("התגנבות", "en") and not languages.foreign_to("1d8+2", "fr")


def test_english_alone_unless_the_adventure_chose(table):
    call, camp, state = table["call"], table["camp"], table["state"]
    (camp / "table" / "languages.json").unlink()
    assert state.languages == ["en"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    info = call(f"/api/info?code={CODE}&token={pip}")[1]
    assert [x["code"] for x in info["languages"]] == ["en"] and info["lang"] == "en"
    call("/api/say", {"code": CODE, "token": pip, "text": "I open the door.", "lang": "fr"})
    _, inbox = call("/api/gm/inbox", {}, host=True)
    assert [m.get("lang") for m in inbox["messages"] if m["kind"] == "player"] == [None]
    assert not inbox["translate"] and inbox["languages"] == ["en"]
    assert call(f"/api/ui?code={CODE}&lang=fr")[0] == 404
    status, body = call("/api/gm/say", {"text": "La porte grince.", "lang": "fr"}, host=True)
    assert status == 400 and "gm-table.sh languages" in body["error"]


def test_three_languages_every_beat_and_action_in_each(table):
    call, camp, state = table["call"], table["camp"], table["state"]
    set_languages(camp, ["en", "he", "fr"])
    state.set_round_seconds(0)
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    noa = call("/api/create", {"code": CODE, "name": "Noa"})[1]["token"]
    call("/api/lang", {"code": CODE, "token": noa, "lang": "he"})
    info = call(f"/api/info?code={CODE}&token={noa}")[1]
    assert [x["code"] for x in info["languages"]] == ["en", "he", "fr"] and info["lang"] == "he"
    assert next(x for x in info["languages"] if x["code"] == "he")["rtl"] is True

    # An action is translated into every other language, even ones nobody reads yet.
    call("/api/say", {"code": CODE, "token": pip, "text": "I open the door.", "lang": "en"})
    _, inbox = call("/api/gm/inbox", {}, host=True)
    assert inbox["languages"] == ["en", "he", "fr"]
    assert [x["to"] for x in inbox["translate"] if x["kind"] == "player"] == [["fr", "he"]]

    # Each beat is told once per language; until it is, the GM is reminded.
    _, body = call("/api/gm/say", {"text": "The door creaks.", "lang": "en"}, host=True)
    assert "Hebrew (say --lang he)" in body["reminder"] and "French (say --lang fr)" in body["reminder"]
    assert state.missing_versions() == {"he": 1, "fr": 1}
    call("/api/gm/say", {"text": "הדלת חורקת.", "lang": "he"}, host=True)
    _, body = call("/api/gm/say", {"text": "La porte grince.", "lang": "fr"}, host=True)
    assert body["reminder"] is None and state.missing_versions() == {}

    # A beat posted without --lang is listed for translation into the others.
    _, body = call("/api/gm/say", {"text": "Thunder rolls."}, host=True)
    assert "--lang" in body["warning"]
    gm = [x for x in state.needs_translation() if x["kind"] == "gm"]
    assert gm and gm[0]["text"] == "Thunder rolls." and gm[0]["to"] == ["fr", "he"]
    call("/api/gm/translate", {"translations": {str(gm[0]["id"]): {"he": "רעם מתגלגל.",
                                                                   "fr": "Le tonnerre gronde."}}},
         host=True)
    assert not [x for x in state.needs_translation() if x["kind"] == "gm"]


def test_cards_and_sheets_are_ready_in_every_language(table):
    call, camp, state = table["call"], table["camp"], table["state"]
    state.cards_warmed.add("Pip")
    state.set_round_seconds(0)
    (camp / "npcs.json").write_text(json.dumps({"Marta": {"description": "innkeeper"}}))
    state.narrator_ask = lambda system, prompt: "כרטיס" if "in Hebrew" in system else "A card."
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    call("/api/gm/say", {"text": "Marta waves from the bar."}, host=True)
    # Made before anyone switches: both languages' cards.
    assert wait_for(lambda: {"Pip|marta|en", "Pip|marta|he"} <= set(state.lore_store))
    en = call(f"/api/lore?code={CODE}&token={pip}&term=Marta&lang=en")[1]
    he = call(f"/api/lore?code={CODE}&token={pip}&term=Marta&lang=he")[1]
    assert en["text"] == "A card." and he["text"] == "כרטיס"
    # The sheet, asked for in a language: translated into that one.
    asked = []
    state.sheet_tr_failed.clear()          # (the card model above can't translate: retry now)
    state.narrator_ask = lambda system, prompt: (asked.append(system) or
                                                 json.dumps({k: "[he] " + v for k, v in json.loads(prompt).items()}))
    got = call(f"/api/sheet-tr?code={CODE}&token={pip}&pc=Pip&lang=he")[1]
    assert got["ok"] and (got["pending"] or got["tr"])
    assert wait_for(lambda: call(f"/api/sheet-tr?code={CODE}&token={pip}&pc=Pip&lang=he")[1]["tr"])
    assert any("into Hebrew" in s for s in asked)


def test_the_page_speaks_a_language_it_does_not_ship_with(table):
    call, camp, state = table["call"], table["camp"], table["state"]
    set_languages(camp, ["en", "fr"])
    asked = []

    def ask(system, prompt):
        asked.append(system)
        return json.dumps({k: "FR " + v for k, v in json.loads(prompt).items()})

    state.narrator_ask = ask
    status, ui = call(f"/api/ui?code={CODE}&lang=fr")
    assert status == 200 and ui["pending"]
    assert wait_for(lambda: not call(f"/api/ui?code={CODE}&lang=fr")[1]["pending"])
    words = call(f"/api/ui?code={CODE}&lang=fr")[1]["strings"]
    assert words["send"] == "FR Send" and words["ev_join"].endswith("{pc}")
    assert words["lvlBadge"] == "⬆"                               # (no words: kept as is)
    assert "placeholder" in asked[0] and (camp / "table" / "ui-fr.json").exists()
    # English (and Hebrew) come with the page; a language the table doesn't play: none.
    assert call(f"/api/ui?code={CODE}&lang=en")[1]["strings"]["send"] == "Send"
    assert call(f"/api/ui?code={CODE}&lang=he")[0] == 404


def test_the_languages_command_sets_them_for_the_adventure(table):
    call, camp, state = table["call"], table["camp"], table["state"]
    status, body = call("/api/gm/languages", {"languages": ["he", "en", "es"]}, host=True)
    assert status == 200 and [x["code"] for x in body["languages"]] == ["he", "en", "es"]
    assert state.languages == ["he", "en", "es"] and body["ui"]["en"] == "built in"
    assert json.loads((camp / "table" / "languages.json").read_text())["languages"] == ["he", "en", "es"]
    assert call("/api/gm/languages", {"languages": ["not a code"]}, host=True)[0] == 400


def test_the_cloud_table_carries_every_language(bridge):
    b, player = bridge["b"], bridge["player"]
    camp, state = bridge["camp"], bridge["state"]
    set_languages(camp, ["en", "he", "fr"])
    (camp / "table" / "ui-fr.json").write_text(json.dumps({"send": "Envoyer"}))
    (camp / "npcs.json").write_text(json.dumps({"Marta": {"description": "innkeeper"}}))
    state.narrator_ask = lambda system, prompt: "כרטיס" if "in Hebrew" in system else "A card."
    player("/api/claim", {"pc": "Pip"}, client="c_page1")
    b.pull(bridge["inbox"])
    bridge["call"]("/api/gm/say", {"text": "Marta waves from the bar."}, host=True)
    assert wait_for(lambda: {"Pip|marta|en", "Pip|marta|he"} <= set(state.lore_store))
    got = docs(b.push(bridge["out"]))
    merged = {}
    for d in got:
        for k in ("lore", "ui", "views"):
            merged.setdefault(k, {}).update(d.get(k) or {})
    assert merged["lore"]["Pip|he"]["marta"]["text"] == "כרטיס"
    assert merged["lore"]["Pip|en"]["marta"]["text"] == "A card."
    assert set(merged["views"]["Pip"]["terms"]) == {"en", "he", "fr"}
    assert merged["ui"]["fr"]["send"] == "Envoyer" and "en" not in merged["ui"]
    # The page itself carries English and Hebrew words, the table's languages arrive with it.
    page = cloud_table.build_page()
    assert '"Send"' in page and "/*TABLE_STRINGS*/" not in page


def test_a_translated_beat_is_part_of_each_readers_story():
    """A beat told in one language and translated afterwards: the hover cards and
    the Narrator of a reader in the other language go by the translation."""
    import narrator
    beat = {"kind": "gm", "text": "מרתה מנגבת ספל.", "tr": {"en": "Marta wipes a mug."}}
    assert narrator.story_lines([beat], "Pip", "en") == ["[GM] Marta wipes a mug."]
    assert narrator.story_lines([beat], "Pip", "he") == ["[GM] מרתה מנגבת ספל."]
