"""The online table: remote players join from their own browser.

Runs the real HTTP handler in-process on an ephemeral port and drives it the
way a browser (players) and gm-table.sh (the host) do.
"""

import json
import sys
import threading
import time
from pathlib import Path
import urllib.error
import urllib.request
import urllib.parse
from http.server import ThreadingHTTPServer

import pytest

from lib.identity_onboarding import IdentityOnboarding
from lib.player_manager import PlayerManager
from lib.table_server import TableState, make_handler

CODE = "ember-123"
HOST_KEY = "host-secret"


@pytest.fixture
def table(tmp_path, monkeypatch):
    monkeypatch.setenv("NARRATOR_BACKEND", "off")      # never the host's real model in tests
    import lib.table_server
    monkeypatch.setattr(lib.table_server, "EDIT_GRACE", 0)   # (the typo window: its own test)
    world = tmp_path / "world-state"
    camp = world / "campaigns" / "camp"
    camp.mkdir(parents=True)
    (world / "active-campaign.txt").write_text("camp")
    (camp / "campaign-overview.json").write_text(json.dumps({
        "campaign_name": "Camp", "opening_matched_to_pc": True,
        "player_position": {"current_location": "The Rusty Tankard"}}))
    IdentityOnboarding(str(world)).onboard("original", name="Pip", concept="a halfling rogue")

    state = TableState(camp, str(world))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state, CODE, HOST_KEY))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    def call(path, body=None, host=False):
        headers = {"Content-Type": "application/json"}
        if host:
            headers["X-Host-Key"] = HOST_KEY
        req = urllib.request.Request(
            base + path, data=json.dumps(body).encode() if body is not None else None,
            headers=headers, method="POST" if body is not None else "GET")
        try:
            with opener.open(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    yield {"call": call, "world": world, "camp": camp, "state": state,
           "base": base, "opener": opener}
    httpd.shutdown()
    httpd.server_close()


def test_a_wrong_code_is_turned_away(table):
    status, body = table["call"]("/api/info?code=nope")
    assert status == 403 and not body["ok"]
    status, _ = table["call"]("/api/claim", {"code": "nope", "pc": "Pip"})
    assert status == 403


def test_claim_is_one_browser_per_character(table):
    call = table["call"]
    status, first = call("/api/claim", {"code": "EMBER-123", "pc": "pip"})
    assert status == 200 and first["pc"] == "Pip"
    status, second = call("/api/claim", {"code": CODE, "pc": "Pip"})
    assert status == 409 and "already being played" in second["error"]
    _, info = call(f"/api/info?code={CODE}&token={first['token']}")
    assert info["me"] == "Pip"
    assert info["party"][0]["claimed"] is True


def test_a_remote_player_can_create_their_own_character(table):
    status, body = table["call"]("/api/create", {
        "code": CODE, "name": "Bram", "concept": "a dwarf cleric"})
    assert status == 200 and body["pc"] == "Bram"
    sheet = json.loads((table["camp"] / "players" / "bram.json").read_text())
    assert sheet["name"] == "Bram"
    status, dup = table["call"]("/api/create", {"code": CODE, "name": "pip"})
    assert status == 409


def test_actions_reach_the_gm_and_narration_reaches_everyone(table):
    call = table["call"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    bram = call("/api/create", {"code": CODE, "name": "Bram"})[1]["token"]
    assert call("/api/say", {"code": CODE, "token": pip, "text": "I check for traps."})[0] == 200
    assert call("/api/say", {"code": CODE, "token": bram, "text": "I pocket the coin.",
                             "private": True})[0] == 200

    _, pending = call("/api/gm/pending", host=True)
    assert pending["unread"] == 4  # two joins + two actions
    _, inbox = call("/api/gm/inbox", {}, host=True)
    actions = [(m.get("pc"), m["text"], m.get("to")) for m in inbox["messages"] if m["kind"] == "player"]
    assert actions == [("Pip", "I check for traps.", None), ("Bram", "I pocket the coin.", "Bram")]
    assert call("/api/gm/pending", host=True)[1]["unread"] == 0

    call("/api/gm/say", {"text": "You spot a tripwire."}, host=True)
    call("/api/gm/say", {"text": "The coin is warm.", "to": "bram"}, host=True)
    pip_view = [m["text"] for m in call(f"/api/messages?code={CODE}&token={pip}")[1]["messages"]]
    bram_view = [m["text"] for m in call(f"/api/messages?code={CODE}&token={bram}")[1]["messages"]]
    assert "You spot a tripwire." in pip_view and "You spot a tripwire." in bram_view
    assert "The coin is warm." not in pip_view and "I pocket the coin." not in pip_view
    assert "The coin is warm." in bram_view and "I pocket the coin." in bram_view


def test_players_cannot_use_host_endpoints_or_act_unseated(table):
    call = table["call"]
    assert call("/api/gm/pending")[0] == 403
    assert call("/api/gm/say", {"text": "I am the GM now"})[0] == 403
    assert call("/api/say", {"code": CODE, "text": "hello"})[0] == 403
    assert call(f"/images/..%2Fcharacter.json?code={CODE}")[0] == 404


def test_party_view_tracks_live_sheets_and_departures(table):
    call = table["call"]
    bram = call("/api/create", {"code": CODE, "name": "Bram"})[1]["token"]
    PlayerManager(str(table["world"])).modify_hp("Bram", -3)
    _, info = call(f"/api/info?code={CODE}&token={bram}")
    assert {p["name"]: p["hp"] for p in info["party"]} == {"Pip": 10, "Bram": 7}
    PlayerManager(str(table["world"])).remove_player("Bram")
    _, info = call(f"/api/info?code={CODE}&token={bram}")
    assert info["me"] is None  # the browser is sent back to pick a seat


def test_the_log_survives_a_server_restart(table):
    call = table["call"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    call("/api/say", {"code": CODE, "token": pip, "text": "Onward."})
    reloaded = TableState(table["camp"], str(table["world"]))
    assert [m["text"] for m in reloaded.messages][-1] == "Onward."
    assert reloaded.pc_for(pip) == "Pip"


def test_each_player_language_reaches_the_gm_and_lang_beats_are_tagged(table):
    call = table["call"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    bram = call("/api/create", {"code": CODE, "name": "Bram"})[1]["token"]
    call("/api/say", {"code": CODE, "token": pip, "text": "I open the door.", "lang": "en"})
    call("/api/say", {"code": CODE, "token": bram, "text": "אני מדליק לפיד", "lang": "he",
                      "voice": True})
    _, inbox = call("/api/gm/inbox", {}, host=True)
    spoken = [m for m in inbox["messages"] if m["kind"] == "player"]
    assert [(m["pc"], m.get("lang"), m.get("voice", False)) for m in spoken] == [
        ("Pip", "en", False), ("Bram", "he", True)]
    assert inbox["langs"] == {"Pip": "en", "Bram": "he"}

    status, body = call("/api/gm/say", {"text": "הלפיד מאיר את המסדרון.", "lang": "he"}, host=True)
    assert status == 200 and body["message"]["lang"] == "he"
    assert call("/api/gm/say", {"text": "x", "lang": "fr"}, host=True)[0] == 400

    call("/api/lang", {"code": CODE, "token": pip, "lang": "he"})
    assert table["state"].seated_langs()["Pip"] == "he"


def test_music_is_shared_by_every_player(table):
    call = table["call"]
    _, info = call(f"/api/info?code={CODE}")
    assert not info["music"].get("track")

    status, body = call("/api/gm/music", {"track": "ambient:storm", "volume": 0.4}, host=True)
    assert status == 200 and body["music"]["kind"] == "ambient"
    _, info = call(f"/api/info?code={CODE}")
    assert info["music"]["src"] == "storm" and info["music"]["volume"] == 0.4
    assert info["server_now"] >= info["music"]["started_at"]

    assert call("/api/gm/music", {"track": "ambient:polka"}, host=True)[0] == 400
    assert call("/api/gm/music", {"track": "missing.mp3"}, host=True)[0] == 400
    assert call("/api/gm/music", {"track": "https://example.com/a.ogg"}, host=True)[0] == 200
    assert call("/api/gm/music", {"track": "stop"}, host=True)[1]["music"]["track"] is None
    assert call("/api/gm/music", {"track": "ambient:wind"})[0] == 403  # players can't


def test_music_files_are_served_with_seeking(table):
    music = table["camp"] / "music"
    music.mkdir()
    (music / "Tavern Night.ogg").write_bytes(bytes(range(256)) * 4)
    call = table["call"]
    status, body = call("/api/gm/music", {"track": "tavern night"}, host=True)
    assert status == 200 and body["music"]["src"] == "Tavern Night.ogg"
    assert body["music"]["title"] == "Tavern Night"

    opener, url = table["opener"], table["base"]
    req = urllib.request.Request(f"{url}/music/Tavern%20Night.ogg?code={CODE}",
                                 headers={"Range": "bytes=256-511"})
    with opener.open(req, timeout=5) as resp:
        assert resp.status == 206
        assert resp.headers["Content-Range"] == "bytes 256-511/1024"
        assert resp.read() == bytes(range(256))
    with pytest.raises(urllib.error.HTTPError) as denied:
        opener.open(f"{url}/music/Tavern%20Night.ogg?code=nope", timeout=5)
    assert denied.value.code == 403


def _touch_music(camp, *names):
    music = camp / "music"
    music.mkdir(exist_ok=True)
    for name in names:
        (music / name).write_bytes(b"\0" * 2048)


def test_say_mood_picks_matching_music_and_only_switches_on_change(table):
    call, state = table["call"], table["state"]
    _touch_music(table["camp"], "tavern-pippin.mp3", "battle-drums.ogg")
    _, body = call("/api/gm/say", {"text": "The inn is warm.", "mood": "tavern"}, host=True)
    assert body["music"]["src"] == "tavern-pippin.mp3" and body["music"]["mood"] == "tavern"
    first_id = state.music["id"]
    _, body = call("/api/gm/say", {"text": "Someone laughs.", "mood": "tavern"}, host=True)
    assert body["music"] is None and state.music["id"] == first_id   # same mood: no restart
    _, body = call("/api/gm/say", {"text": "Steel is drawn!", "mood": "combat"}, host=True)
    assert body["music"]["src"] == "battle-drums.ogg"
    _, body = call("/api/gm/say", {"text": "Into the crypt.", "mood": "dungeon"}, host=True)
    assert body["music"]["track"] == "ambient:cave"                  # no file: built-in sound
    _, body = call("/api/gm/say", {"text": "Hush.", "mood": "silence"}, host=True)
    assert body["music"]["track"] is None
    assert call("/api/gm/say", {"text": "x", "mood": "polka"}, host=True)[0] == 400


def test_moods_json_overrides_keywords_and_auto_can_be_turned_off(table):
    call, state = table["call"], table["state"]
    _touch_music(table["camp"], "track01.mp3")
    (table["camp"] / "music" / "moods.json").write_text(json.dumps({"calm": ["track01.mp3"]}))
    assert state.mood_files("calm") == ["track01.mp3"]
    call("/api/gm/music", {"auto": False}, host=True)
    _, body = call("/api/gm/say", {"text": "Rest.", "mood": "calm"}, host=True)
    assert body["music"] is None
    call("/api/gm/music", {"auto": True}, host=True)
    _, body = call("/api/gm/say", {"text": "Rest.", "mood": "calm"}, host=True)
    assert body["music"]["src"] == "track01.mp3"


def test_each_enemy_gets_their_own_theme_that_holds_through_the_fight(table):
    call, state = table["call"], table["state"]
    _, body = call("/api/gm/say", {"text": "A clown grins.", "theme": "Grimaldi"}, host=True)
    assert body["music"]["track"] == "theme:Grimaldi" and body["music"]["theme"] == "Grimaldi"
    assert call("/api/gm/say", {"text": "It attacks!", "mood": "combat"}, host=True)[1]["music"] is None
    _, body = call("/api/gm/say", {"text": "Another foe.", "theme": "The Hollow King"}, host=True)
    assert body["music"]["track"] == "theme:The Hollow King"
    _, body = call("/api/gm/say", {"text": "You won.", "mood": "victory"}, host=True)
    assert body["music"]["mood"] == "victory" and not body["music"].get("theme")


def test_boss_themes_are_the_exciting_version_and_a_fight_can_escalate(table):
    call = table["call"]
    _, body = call("/api/gm/say", {"text": "The Lich rises.", "theme": "Lich", "boss": True}, host=True)
    assert body["music"]["boss"] is True and body["music"]["mood"] == "boss"
    # Re-mentioning the boss without --boss never calms the music down.
    assert call("/api/gm/say", {"text": "x", "theme": "Lich"}, host=True)[1]["music"] is None

    _, body = call("/api/gm/say", {"text": "A knight blocks the way.", "theme": "Black Knight"}, host=True)
    assert not body["music"].get("boss")
    _, body = call("/api/gm/say", {"text": "He reveals his true form!", "mood": "boss"}, host=True)
    assert body["music"]["theme"] == "Black Knight" and body["music"]["boss"] is True

    _, body = call("/api/gm/say", {"text": "Thunder.", "mood": "boss"}, host=True)
    assert body["music"] is None        # still the Black Knight's boss theme
    call("/api/gm/say", {"text": "Calm.", "mood": "calm"}, host=True)
    _, body = call("/api/gm/say", {"text": "A nameless horror!", "mood": "boss"}, host=True)
    assert body["music"]["track"] == "ambient:epic"


def test_theme_files_assigned_or_named_after_the_enemy(table):
    call, state = table["call"], table["state"]
    _touch_music(table["camp"], "grimaldi.mp3", "grimaldi-boss.mp3", "clown-waltz.ogg")
    assert state.theme_track("Grimaldi") == "grimaldi.mp3"
    assert state.theme_track("Grimaldi", boss=True) == "grimaldi-boss.mp3"
    status, body = call("/api/gm/music", {"theme": "Mordecai", "assign": "clown-waltz"}, host=True)
    assert status == 200 and body["track"] == "clown-waltz.ogg"
    assert json.loads((table["camp"] / "music-themes.json").read_text()) == {"Mordecai": "clown-waltz.ogg"}
    _, body = call("/api/gm/say", {"text": "Mordecai!", "theme": "mordecai"}, host=True)
    assert body["music"]["src"] == "clown-waltz.ogg"
    assert call("/api/gm/music", {"theme": "X", "assign": "nope.mp3"}, host=True)[0] == 400


def test_starter_library_files_land_in_their_moods(tmp_path):
    from lib import music_library
    tracks = music_library.load_library()
    assert len(tracks) >= 20
    assert all(t["file"].startswith(t["mood"] + "-") and t["license"] for t in tracks)
    for t in tracks:
        mood = t["mood"]
        other = {m for m in ("calm", "tavern", "travel", "mystery", "dread", "dungeon", "combat",
                             "boss", "sad", "storm", "victory") if m != mood}
        tokens = TableState._tokens(t["file"])
        from lib.table_server import MOODS
        clash = [m for m in other if tokens & (set(MOODS[m]["keywords"])
                                               | {k + "s" for k in MOODS[m]["keywords"]})]
        assert not clash, f"{t['file']} would also play for {clash}"
    credit = music_library.credit_for(tracks[0]["file"])
    assert "Kevin MacLeod" in credit and "CC BY 4.0" in credit


def test_progress_follows_the_gms_turn_and_learns_how_long_it_takes(table):
    call, state = table["call"], table["state"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    assert call(f"/api/info?code={CODE}")[1]["progress"] == {"state": "idle"}
    call("/api/say", {"code": CODE, "token": pip, "text": "I open the door."})
    assert call(f"/api/info?code={CODE}")[1]["progress"] == {"state": "queued"}

    call("/api/gm/inbox", {}, host=True)                       # the GM reads: turn starts
    prog = call(f"/api/info?code={CODE}")[1]["progress"]
    assert prog["state"] == "working" and prog["stage"] == "reading"
    assert prog["estimate"] == 45                               # no history yet
    assert call("/api/gm/activity", {"stage": "dice"}, host=True)[1]["ok"]
    assert call(f"/api/info?code={CODE}")[1]["progress"]["stage"] == "dice"
    assert not call("/api/gm/activity", {"stage": "hacking"}, host=True)[1]["ok"]
    assert call("/api/gm/activity", {"stage": "dice"})[0] == 403  # players can't

    state.turn["started_at"] -= 30                              # pretend it took 30 s
    call("/api/gm/say", {"text": "Whisper.", "to": "Pip"}, host=True)
    assert call(f"/api/info?code={CODE}")[1]["progress"]["state"] == "working"  # not the beat
    call("/api/gm/say", {"text": "The door creaks open."}, host=True)
    assert call(f"/api/info?code={CODE}")[1]["progress"] == {"state": "idle"}
    assert state.turn_times and 29 <= state.turn_times[-1] <= 32
    assert json.loads((table["camp"] / "table" / "turn-times.json").read_text()) == state.turn_times

    # The next turn's estimate comes from that history.
    call("/api/say", {"code": CODE, "token": pip, "text": "I step in."})
    call("/api/gm/inbox", {}, host=True)
    assert 29 <= call(f"/api/info?code={CODE}")[1]["progress"]["estimate"] <= 32


def test_a_mixed_language_turn_ends_when_every_language_has_its_version(table):
    table["state"].set_round_seconds(0)        # (rounds: tested on their own)
    call = table["call"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    noa = call("/api/create", {"code": CODE, "name": "Noa"})[1]["token"]
    call("/api/lang", {"code": CODE, "token": noa, "lang": "he"})
    call("/api/say", {"code": CODE, "token": pip, "text": "Go.", "lang": "en"})
    call("/api/gm/inbox", {}, host=True)
    call("/api/gm/say", {"text": "English beat.", "lang": "en"}, host=True)
    prog = call(f"/api/info?code={CODE}")[1]["progress"]
    assert prog["state"] == "working" and prog["stage"] == "translating"
    assert prog["langs_done"] == ["en"]
    call("/api/gm/say", {"text": "קטע בעברית.", "lang": "he"}, host=True)
    assert call(f"/api/info?code={CODE}")[1]["progress"] == {"state": "idle"}


def test_turn_estimate_is_the_median_of_recent_turns(table):
    state = table["state"]
    state.turn_times = [10, 200, 30, 40, 20]
    assert state.turn_estimate() == 30
    state.turn_times = [10, 20, 30, 40]
    assert state.turn_estimate() == 25


def test_the_claude_code_hook_reports_the_gms_stage(table, monkeypatch):
    import subprocess
    import time as _time
    from pathlib import Path
    hook = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "table-progress.sh"
    port = int(table["base"].rsplit(":", 1)[1])
    (table["camp"] / "table" / "server.json").write_text(
        json.dumps({"port": port, "host_key": HOST_KEY}))
    call = table["call"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    call("/api/say", {"code": CODE, "token": pip, "text": "Attack!"})
    call("/api/gm/inbox", {}, host=True)

    import os
    import shutil
    bash = shutil.which("bash") or "bash"      # Git Bash on Windows, as Claude Code uses

    def run(command, expect):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
        done = subprocess.run([bash, str(hook)], input=payload, text=True, capture_output=True,
                              env={**os.environ, "GM_WORLD_STATE_BASE": str(table["world"])},
                              timeout=20)
        assert done.returncode == 0 and done.stdout == ""     # never blocks the tool
        for _ in range(40):                                     # the report is sent async
            if table["state"].turn["stage"] == expect:
                break
            _time.sleep(0.05)
        _time.sleep(0.3)                                        # and nothing else follows
        return table["state"].turn["stage"]

    assert run("uv run python lib/dice.py 1d20+5", "dice") == "dice"
    assert run("bash tools/gm-player.sh hp Pip -3", "sheets") == "sheets"
    assert run("bash tools/gm-table.sh say 'x'", "sheets") == "sheets"   # say/wait don't count
    assert run("ls -la", "sheets") == "sheets"                  # unrelated commands: nothing


def test_new_characters_join_the_tables_campaign_even_after_a_campaign_switch(table):
    world = table["world"]
    other = world / "campaigns" / "other"
    other.mkdir()
    (other / "campaign-overview.json").write_text(json.dumps({"campaign_name": "Other"}))
    (world / "active-campaign.txt").write_text("other")       # the host switched campaigns
    status, body = table["call"]("/api/create", {"code": CODE, "name": "Asterisk",
                                                  "concept": "A tough barbarian"})
    assert status == 200 and body["pc"] == "Asterisk"
    assert (table["camp"] / "players" / "asterisk.json").exists()
    assert not (other / "character.json").exists()


def test_creating_an_unclaimed_existing_name_points_at_the_list(table):
    call = table["call"]
    call("/api/create", {"code": CODE, "name": "Bram"})
    call("/api/leave", {"code": CODE, "token": table["state"].claim("Pip")["token"]})
    table["state"].free("Bram")
    status, body = call("/api/create", {"code": CODE, "name": "bram"})
    assert status == 409 and body["existing"] == "bram" and "pick them in the list" in body["error"]


def test_actions_are_translated_for_players_of_the_other_language(table):
    call, state = table["call"], table["state"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    noa = call("/api/create", {"code": CODE, "name": "Noa"})[1]["token"]
    call("/api/lang", {"code": CODE, "token": noa, "lang": "he"})
    call("/api/say", {"code": CODE, "token": pip, "text": "I light a torch.", "lang": "en"})
    msg_id = call("/api/say", {"code": CODE, "token": noa, "text": "אני פותחת את הדלת",
                               "lang": "he"})[1]["message"]["id"]

    _, inbox = call("/api/gm/inbox", {}, host=True)
    needed = {n["id"]: (n["from"], n["to"]) for n in inbox["translate"]}
    assert needed[msg_id] == ("he", ["en"]) and len(needed) == 2

    _, seen = call(f"/api/messages?code={CODE}&token={pip}&after=0")
    rev = seen["rev"]
    status, body = call("/api/gm/translate", {"translations": {
        str(msg_id): {"en": "I open the door."},
        str(msg_id - 1): {"he": "אני מדליק לפיד."}}}, host=True)
    assert status == 200 and sorted(body["updated"]) == [msg_id - 1, msg_id]
    assert body["still_needed"] == []

    # Browsers that already saw the messages get the updated ones (by revision).
    _, update = call(f"/api/messages?code={CODE}&token={pip}&after={msg_id}&rev={rev}")
    tr = {m["id"]: m.get("tr") for m in update["messages"]}
    assert tr[msg_id] == {"en": "I open the door."}

    # Translations survive a restart of the table server.
    reloaded = TableState(table["camp"], str(table["world"]))
    by_id = {m["id"]: m for m in reloaded.messages}
    assert by_id[msg_id]["tr"] == {"en": "I open the door."}
    assert by_id[msg_id - 1]["tr"] == {"he": "אני מדליק לפיד."}
    assert reloaded.rev >= state.rev


def test_untagged_narration_at_a_mixed_table_warns_the_gm(table):
    call = table["call"]
    call("/api/claim", {"code": CODE, "pc": "Pip"})
    noa = call("/api/create", {"code": CODE, "name": "Noa"})[1]["token"]
    call("/api/lang", {"code": CODE, "token": noa, "lang": "he"})
    _, body = call("/api/gm/say", {"text": "The door creaks open."}, host=True)
    assert "Hebrew players get it in English" in body["warning"]
    _, body = call("/api/gm/say", {"text": "The door creaks open.", "lang": "en"}, host=True)
    assert body["warning"] is None
    _, body = call("/api/gm/say", {"text": "Psst.", "to": "Noa"}, host=True)
    assert "whisper in Hebrew" in body["warning"]


def test_hp_changes_wait_for_the_narration_that_explains_them(table):
    table["state"].set_round_seconds(0)        # (rounds: tested on their own)
    call, world = table["call"], table["world"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    noa = call("/api/create", {"code": CODE, "name": "Noa"})[1]["token"]
    call("/api/lang", {"code": CODE, "token": noa, "lang": "he"})
    hp = lambda token: {p["name"]: p["hp"] for p in
                        call(f"/api/info?code={CODE}&token={token}")[1]["party"]}

    call("/api/say", {"code": CODE, "token": pip, "text": "I attack the troll!", "lang": "en"})
    call("/api/gm/inbox", {}, host=True)                    # the GM starts its turn...
    PlayerManager(str(world)).modify_hp("Pip", -6)          # ...and records the damage first
    assert hp(pip)["Pip"] == 10 and hp(noa)["Pip"] == 10    # nobody sees it before the story

    call("/api/create", {"code": CODE, "name": "Wren"})     # a newcomer still appears at once
    assert "Wren" in hp(pip)

    call("/api/gm/say", {"text": "The troll's club catches you: 6 damage.", "lang": "en"}, host=True)
    assert hp(pip)["Pip"] == 4                              # English story out: English sees it
    assert hp(noa)["Pip"] == 10                             # Hebrew version not out yet
    call("/api/gm/say", {"text": "האלה של הטרול פוגעת בך: 6 נזק.", "lang": "he"}, host=True)
    assert hp(noa)["Pip"] == 4

    PlayerManager(str(world)).modify_hp("Pip", +2)          # outside a turn: live, as before
    assert hp(pip)["Pip"] == 6


def test_the_table_rolls_in_public_with_the_dc_fixed_first(table):
    call, state = table["call"], table["state"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    status, body = call("/api/gm/roll", {"notation": "1d20+5", "target": 15, "target_label": "DC",
                                         "pc": "Pip", "why": "Stealth",
                                         "why_tr": {"he": "התגנבות"}}, host=True)
    assert status == 200 and body["ok"]
    roll = body["roll"]
    assert roll["total"] == roll["rolls"][0] + 5 and roll["target"] == 15
    assert roll["outcome"] == ("success" if roll["rolls"][0] == 20 or
                               (roll["rolls"][0] != 1 and roll["total"] >= 15) else "failure")

    # Every player sees it, DC and all, as it happens.
    _, seen = call(f"/api/messages?code={CODE}&token={pip}&after=0")
    shown = [m for m in seen["messages"] if m["kind"] == "roll"][-1]
    assert shown["event"]["roll"] == roll and shown["event"]["why_tr"] == {"he": "התגנבות"}

    # A secret roll is announced, but its result never reaches the players.
    _, body = call("/api/gm/roll", {"notation": "1d20+7", "why": "the assassin's Stealth",
                                    "secret": True}, host=True)
    assert body["ok"] and body["secret"]
    _, seen = call(f"/api/messages?code={CODE}&token={pip}&after=0")
    secret = [m for m in seen["messages"] if m["kind"] == "roll"][-1]
    assert secret["event"] == {"secret": True} and "assassin" not in json.dumps(secret)
    kept = (table["camp"] / "table" / "secret-rolls.jsonl").read_text(encoding="utf-8")
    assert "assassin" in kept and str(body["roll"]["total"]) in kept

    assert call("/api/gm/roll", {"notation": "banana"}, host=True)[0] == 400
    assert call("/api/gm/roll", {"notation": "1d20"})[0] == 403      # players can't roll as the GM


def test_dice_natural_and_judge():
    from lib import dice
    assert dice.natural({"notation": "1d20+5", "type": "standard", "rolls": [20]}) == 20
    assert dice.natural({"notation": "2d20kh1+3", "type": "advantage", "kept": [1],
                         "rolls": [1, 1]}) == 1
    assert dice.natural({"notation": "2d6", "type": "standard", "rolls": [1, 1]}) is None
    assert dice.natural({"notation": "1d200", "type": "standard", "rolls": [20]}) is None
    assert dice.judge({"notation": "1d20+9", "type": "standard", "rolls": [1], "total": 10}, 5) == "failure"
    assert dice.judge({"notation": "1d20", "type": "standard", "rolls": [20], "total": 20}, 30) == "success"
    assert dice.judge({"notation": "1d20+2", "type": "standard", "rolls": [13], "total": 15}, 15) == "success"
    assert dice.judge({"notation": "2d6", "type": "standard", "rolls": [3, 4], "total": 7}, None) is None


def test_players_can_fix_their_action_until_the_gm_reads_it(table):
    table["state"].set_round_seconds(0)        # (rounds: tested on their own)
    call, state = table["call"], table["state"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    bram = call("/api/create", {"code": CODE, "name": "Bram", "concept": "a dwarf"})[1]["token"]
    call("/api/gm/inbox", {}, host=True)                          # (the join notices)
    _, said = call("/api/say", {"code": CODE, "token": pip, "text": "I pick the lcok."})
    mid = said["message"]["id"]

    # Before the GM reads it: the GM simply gets the fixed text.
    status, body = call("/api/edit", {"code": CODE, "token": pip, "id": mid, "text": "I pick the lock."})
    assert status == 200 and body["message"]["text"] == "I pick the lock." and body["message"]["edited"]
    assert not body["message"].get("read")
    # Only your own actions.
    assert call("/api/edit", {"code": CODE, "token": bram, "id": mid, "text": "Mine now."})[0] == 409
    # Other players see it change in place (new rev).
    _, seen = call(f"/api/messages?code={CODE}&token={bram}&after={mid - 1}&rev=1")
    assert any(m["id"] == mid and m["text"] == "I pick the lock." for m in seen["messages"])

    # The GM reads it: from now on the GM plays it out (rolls for it), so it's final,
    # and the players' pages learn that (the message comes again, marked read).
    rev = state.rev
    inbox = call("/api/gm/inbox", {}, host=True)[1]["messages"]
    assert [m["text"] for m in inbox if m["kind"] == "player"] == ["I pick the lock."]
    status, body = call("/api/edit", {"code": CODE, "token": pip, "id": mid, "text": "I kick the door."})
    assert status == 409 and body["reason"] == "read"
    _, seen = call(f"/api/messages?code={CODE}&token={pip}&after=0&rev={rev}")
    assert any(m["id"] == mid and m.get("read") for m in seen["messages"])

    # Dice rolled after an action lock it too, read or not.
    _, said = call("/api/say", {"code": CODE, "token": bram, "text": "I swing my axe."})
    call("/api/gm/roll", {"notation": "1d20+3", "pc": "Bram", "why": "attack"}, host=True)
    status, body = call("/api/edit", {"code": CODE, "token": bram, "id": said["message"]["id"],
                                      "text": "I run away."})
    assert status == 409 and body["reason"] == "rolled"

    # It all survives a restart: the edit, and that the GM read it.
    reloaded = TableState(table["camp"], str(table["world"]))
    again = next(m for m in reloaded.messages if m["id"] == mid)
    assert again["text"] == "I pick the lock." and again.get("edited") and again.get("read")

    # Once the GM has answered, it's history.
    call("/api/gm/say", {"text": "The lock clicks open."}, host=True)
    status, body = call("/api/edit", {"code": CODE, "token": pip, "id": mid, "text": "Never mind."})
    assert status == 409 and body["reason"] == "answered"


def test_every_action_can_be_fixed_for_its_first_seconds(table, monkeypatch):
    import lib.table_server
    monkeypatch.setattr(lib.table_server, "EDIT_GRACE", 1.5)
    call, state = table["call"], table["state"]
    state.set_round_seconds(0)                                    # even with rounds off
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    call("/api/gm/inbox", {}, host=True)
    mid = call("/api/say", {"code": CODE, "token": pip, "text": "I pick the lcok."})[1]["message"]["id"]
    # The GM can't read it yet...
    held = call("/api/gm/inbox", {}, host=True)[1]
    assert held["held"] and held["messages"] == [] and held["round"]["settling"]
    # ...and even a roll in those seconds doesn't take the edit away.
    call("/api/gm/roll", {"notation": "1d20"}, host=True)
    assert call("/api/edit", {"code": CODE, "token": pip, "id": mid, "text": "I pick the lock."})[0] == 200
    # Then the GM reads the fixed action.
    time.sleep(1.6)
    got = call("/api/gm/inbox", {}, host=True)[1]["messages"]
    assert [m["text"] for m in got if m["kind"] == "player"] == ["I pick the lock."]


def test_players_say_how_their_portrait_looks_when_they_join(table):
    call, state, camp = table["call"], table["state"], table["camp"]
    (camp / "images").mkdir(exist_ok=True)
    painted = []

    def maker(name, campaign_dir):
        import party_roster
        path = party_roster.find_pc(campaign_dir, name)
        sheet = json.loads(path.read_text())
        painted.append((name, (sheet.get("visual_appearance") or {}).get("sex")))
        f = f"portrait-{name.lower()}.png"
        (campaign_dir / "images" / f).write_bytes(b"\x89PNG")
        sheet["portrait"] = f
        path.write_text(json.dumps(sheet))
        return f

    state.portrait_maker = maker
    noa = call("/api/create", {"code": CODE, "name": "Noa", "concept": "an elf ranger", "sex": "female"})[1]["token"]
    import party_roster
    sheet = json.loads(party_roster.find_pc(camp, "Noa").read_text())
    assert sheet["visual_appearance"]["sex"] == "female"            # chosen on the join page
    state.portrait_pass()                                            # she has a look: painted at once
    assert ("Noa", "female") in painted
    state.portrait_pass()
    assert len([p for p in painted if p[0] == "Noa"]) == 1           # once: players can't redo it
    assert call("/api/portrait", {"code": CODE, "token": noa, "sex": "male"})[0] == 404


def test_recurring_npcs_get_portraits_by_themselves(table):
    call, state, camp = table["call"], table["state"], table["camp"]
    state.set_round_seconds(0)
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    (camp / "images").mkdir(exist_ok=True)
    (camp / "npcs.json").write_text(json.dumps({"npcs": {
        "Marta": {"description": "the innkeeper"}, "Old Tom": {"description": "a fisherman"}}}))
    painted = []

    def maker(name, campaign_dir):
        painted.append(name)
        f = f"portrait-{name.lower().replace(' ', '-')}.png"
        (campaign_dir / "images" / f).write_bytes(b"\x89PNG")
        data = json.loads((campaign_dir / "npcs.json").read_text())
        data["npcs"][name]["portrait"] = f
        (campaign_dir / "npcs.json").write_text(json.dumps(data))
        return f

    state.portrait_maker = maker
    state.portrait_tried["Pip"] = time.time()                 # (Pip's own portrait: not this test)
    call("/api/gm/alias", {"name": "Marta", "alias": "מרתה"}, host=True)
    for text in ("Marta pours ale.", "Old Tom waves.", "מרתה מחייכת."):
        call("/api/gm/say", {"text": text}, host=True)
    call("/api/gm/say", {"text": "Marta, privately: the cellar.", "to": "Pip"}, host=True)
    assert state.npc_pass() == []                            # twice in public: not yet recurring
    assert state.npc_mentions() == {"Marta": 2, "Old Tom": 1}
    call("/api/gm/say", {"text": "Marta winks at Old Tom."}, host=True)
    assert state.npc_pass() == ["Marta"] and painted == ["Marta"]
    shown = [m for m in state.messages if (m.get("event") or {}).get("type") == "npc"]
    assert shown[-1]["image"] == "portrait-marta.png"          # shown to the table
    assert state.npc_pass() == []                              # once
    _, info = call(f"/api/info?code={CODE}&token={pip}")
    assert info["people"] == [{"name": "Marta", "image": "portrait-marta.png"}]
    state.narrator_ask = lambda system, prompt: "The innkeeper."
    assert call(f"/api/lore?code={CODE}&token={pip}&term=Marta")[1]["image"] == "portrait-marta.png"
    # One the GM painted already is shown the same way, without painting again.
    (camp / "images" / "tom.png").write_bytes(b"\x89PNG")
    data = json.loads((camp / "npcs.json").read_text())
    data["npcs"]["Old Tom"]["portrait"] = "tom.png"
    (camp / "npcs.json").write_text(json.dumps(data))
    for _ in range(2):
        call("/api/gm/say", {"text": "Old Tom mends a net."}, host=True)
    assert state.npc_pass() == ["Old Tom"] and painted == ["Marta"]
    assert [p["name"] for p in call(f"/api/info?code={CODE}&token={pip}")[1]["people"]] == ["Old Tom", "Marta"]


def test_the_host_makes_natural_voices_for_seated_players(table):
    import table_tts
    call, state = table["call"], table["state"]
    made = []

    def engine(text, voice, dest):
        made.append((text, voice))
        dest.write_bytes(b"ID3fake-mp3:" + text.encode("utf-8"))

    state.tts_engine = engine
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    assert call(f"/api/info?code={CODE}&token={pip}")[1]["tts"] is True
    q = urllib.parse.urlencode({"code": CODE, "token": pip, "voice": "he-IL-HilaNeural",
                                "text": "סוף ההרפתקה. תודה ששיחקתם!"})
    opener = table["opener"]
    with opener.open(f"{table['base']}/api/tts?{q}", timeout=5) as r:
        assert r.headers["Content-Type"] == "audio/mpeg"
        assert r.read() == "ID3fake-mp3:סוף ההרפתקה. תודה ששיחקתם!".encode("utf-8")
    with opener.open(f"{table['base']}/api/tts?{q}", timeout=5) as r:
        r.read()
    assert made == [("סוף ההרפתקה. תודה ששיחקתם!", "he-IL-HilaNeural")]   # made once, cached

    # Seated players only, known voices only.
    assert call("/api/tts?" + q.replace(f"token={pip}", "token=nope"))[0] == 403
    assert call("/api/tts?" + q.replace("he-IL-HilaNeural", "evil"))[0] == 400

    # The service is down: 503 (pages use their own voice), cached audio still plays.
    def broken(text, voice, dest):
        raise OSError("no internet")

    state.tts_engine = broken
    other = urllib.parse.urlencode({"code": CODE, "token": pip, "voice": "he-IL-AvriNeural",
                                    "text": "שלום"})
    status, body = call("/api/tts?" + other)
    assert status == 503 and "didn't answer" in body["error"]
    assert call(f"/api/info?code={CODE}&token={pip}")[1]["tts"] is False
    with opener.open(f"{table['base']}/api/tts?{q}", timeout=5) as r:
        assert r.status == 200
    assert not list((table["camp"] / "table" / "tts").glob("*.part"))
    assert table_tts.VOICES["he-IL-HilaNeural"][0] == "he"


def test_sheets_follow_the_story_like_the_party_panel(table):
    call, camp = table["call"], table["camp"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    sheet_path = camp / "character.json"
    sheet = json.loads(sheet_path.read_text())
    sheet.update({"stats": {"str": 8, "dex": 17}, "skills": {"stealth": 5}, "hp": {"current": 10, "max": 10}})
    sheet_path.write_text(json.dumps(sheet))

    _, info = call(f"/api/info?code={CODE}&token={pip}")
    rev = info["party"][0]["sheet_rev"]
    assert "sheet" not in info["party"][0]                 # summaries only in the polled info
    _, got = call(f"/api/sheet?code={CODE}&token={pip}&pc=Pip")
    assert got["rev"] == rev and list(got["sheet"]["stats"]) == ["str", "dex"]   # sheet's own order

    # The GM's turn: the hit is recorded before it's narrated -> still the old sheet.
    call("/api/say", {"code": CODE, "token": pip, "text": "I sneak past."})
    call("/api/gm/inbox", {}, host=True)
    sheet["hp"]["current"] = 4
    sheet_path.write_text(json.dumps(sheet))
    _, got = call(f"/api/sheet?code={CODE}&token={pip}&pc=Pip")
    assert got["rev"] == rev and got["sheet"]["hp"]["current"] == 10

    # Narrated: the new sheet, and the page can still fetch the one it's showing.
    _, said = call("/api/gm/say", {"text": "The guard spots Pip."}, host=True)
    _, info = call(f"/api/info?code={CODE}&token={pip}")
    new_rev = info["party"][0]["sheet_rev"]
    assert new_rev != rev and info["narration_id"] == said["message"]["id"]
    assert call(f"/api/sheet?code={CODE}&token={pip}&pc=Pip")[1]["sheet"]["hp"]["current"] == 4
    assert call(f"/api/sheet?code={CODE}&token={pip}&pc=Pip&rev={new_rev}")[1]["rev"] == new_rev

    assert call(f"/api/sheet?code={CODE}&token=nope&pc=Pip")[0] == 403
    assert call(f"/api/sheet?code={CODE}&token={pip}&pc=Nobody")[0] == 404


def test_a_joining_player_can_roll_a_character(table):
    call, state = table["call"], table["state"]
    _, r1 = call("/api/roll-character", {"code": CODE, "lang": "en"})
    assert r1["ok"] and list(r1["stats"]) == ["str", "dex", "con", "int", "wis", "cha"]
    for a, d in r1["dice"].items():
        assert len(d["dice"]) == 4 and all(1 <= x <= 6 for x in d["dice"])
        assert d["score"] == sum(d["dice"]) - d["dice"][d["dropped"]] == r1["stats"][a]
        assert d["dice"][d["dropped"]] == min(d["dice"])
    assert r1["class"] and r1["race"] and r1["hp"] >= 1 and r1["tries"] == 1

    _, r2 = call("/api/roll-character", {"code": CODE, "lang": "he", "previous": r1["roll_id"]})
    assert r2["tries"] == 2 and r1["roll_id"] not in state.pending_rolls
    assert any("֐" <= ch <= "׿" for ch in r2["name"] + r2["concept"])   # Hebrew suggestions

    # Created with the roll: the sheet gets exactly the server's numbers, whatever the page sends.
    status, seat = call("/api/create", {"code": CODE, "name": "Bram", "concept": "a dwarf",
                                        "roll_id": r2["roll_id"], "stats": {"str": 18}})
    assert status == 200
    _, sheet = call(f"/api/sheet?code={CODE}&token={seat['token']}&pc=Bram")
    assert sheet["sheet"]["stats"] == r2["stats"] and sheet["sheet"]["class"] == r2["class"]
    assert sheet["sheet"]["hp"] == {"current": r2["hp"], "max": r2["hp"]}
    join = [m for m in state.messages if (m.get("event") or {}).get("type") == "join"][-1]
    assert join["event"]["rolled"]["tries"] == 2 and "Rolled: STR" in join["text"]
    assert not state.pending_rolls                       # a roll is used once

    # A campaign with its own abilities rolls those.
    (table["camp"] / "ruleset.json").write_text(json.dumps(
        {"stat_schema": {"attributes": ["might", "guile", "grit"]}}))
    _, r3 = call("/api/roll-character", {"code": CODE})
    assert list(r3["stats"]) == ["might", "guile", "grit"] and "class" not in r3
    assert call("/api/roll-character", {"code": "wrong"})[0] == 403


def test_a_ready_level_up_is_announced_once(table):
    call, state, camp = table["call"], table["state"], table["camp"]
    state.set_round_seconds(0)
    path = camp / "character.json"
    sheet = json.loads(path.read_text())
    sheet.update({"class": "Rogue", "level": 1})
    path.write_text(json.dumps(sheet))
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    call(f"/api/info?code={CODE}&token={pip}")                    # first seen at level 1
    notices = lambda: [m for m in state.messages if (m.get("event") or {}).get("type") == "levelready"]
    assert state.announce_level_ups() == [] and notices() == []
    # The GM awards XP (the award raises the level), then narrates: the player is told.
    sheet["level"], sheet["xp"] = 2, {"current": 300, "next_level": 900}
    path.write_text(json.dumps(sheet))
    call("/api/gm/say", {"text": "The goblins flee. You gain 300 XP."}, host=True)
    assert wait_for(lambda: len(notices()) == 1)
    assert notices()[0]["pc"] == "Pip" and notices()[0]["event"]["level"] == 2
    call("/api/gm/say", {"text": "Night falls."}, host=True)      # once per level
    time.sleep(0.3)
    assert len(notices()) == 1 and state.announce_level_ups() == []
    again = TableState(camp, str(table["world"]))                 # (kept across a restart)
    assert again.announce_level_ups() == []


def test_players_level_up_from_their_sheet(table):
    call, state, camp = table["call"], table["state"], table["camp"]
    path = camp / "character.json"
    sheet = json.loads(path.read_text())
    sheet.update({"class": "Rogue", "level": 3, "hp": {"current": 20, "max": 24},
                  "stats": {"str": 8, "dex": 17, "con": 14, "int": 12, "wis": 10, "cha": 13}})
    path.write_text(json.dumps(sheet))
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    _, info = call(f"/api/info?code={CODE}&token={pip}")
    assert info["party"][0]["level_up"] == 0          # first seen at 3: built at 3
    assert "level_up" not in call(f"/api/sheet?code={CODE}&token={pip}&pc=Pip")[1]
    assert call("/api/level-up", {"code": CODE, "token": pip})[0] == 409

    # XP takes Pip to level 4 (the GM's award bumps the level, nothing else).
    sheet["level"] = 4
    path.write_text(json.dumps(sheet))
    _, info = call(f"/api/info?code={CODE}&token={pip}")
    assert info["party"][0]["level_up"] == 1
    offer = call(f"/api/sheet?code={CODE}&token={pip}&pc=Pip")[1]["level_up"]
    assert offer == {"to": 4, "pending": 1, "hit_die": 8, "con_mod": 2, "asi": True,
                     "abilities": ["str", "dex", "con", "int", "wis", "cha"]}

    assert call("/api/level-up", {"code": CODE, "token": pip, "asi": {"dex": 3}})[0] == 409
    assert call("/api/level-up", {"code": CODE, "token": pip, "asi": {"dex": 1}})[0] == 409
    status, done = call("/api/level-up", {"code": CODE, "token": pip, "hp": "average",
                                          "asi": {"dex": 1, "con": 1}, "wish": "Arcane Trickster"})
    assert status == 200 and done["hp_gain"] == 8 // 2 + 1 + 2 and done["level"] == 4
    after = json.loads(path.read_text())
    assert after["hp"] == {"current": 27, "max": 31} and after["stats"]["dex"] == 18
    assert after["stats"]["con"] == 15
    note = [m for m in state.messages if (m.get("event") or {}).get("type") == "levelup"][-1]
    assert note["event"]["wish"] == "Arcane Trickster" and "reaches level 4" in note["text"]
    assert call("/api/level-up", {"code": CODE, "token": pip})[0] == 409      # built now

    # Rolling HP happens at the table, in the public dice log.
    sheet = json.loads(path.read_text()); sheet["level"] = 5
    path.write_text(json.dumps(sheet))
    status, done = call("/api/level-up", {"code": CODE, "token": pip, "hp": "roll"})
    roll = [m for m in state.messages if m["kind"] == "roll"][-1]
    assert status == 200 and roll["event"]["roll"]["notation"] == "1d8+2"
    assert done["hp_gain"] == max(1, roll["event"]["roll"]["total"])
    reloaded = TableState(camp, str(table["world"]))
    assert reloaded.built_levels["Pip"] == 5


def test_every_pc_gets_a_portrait_shown_to_the_table(table):
    import table_server
    call, state, camp = table["call"], table["state"], table["camp"]
    drawn, fail = [], {"on": False}

    def maker(name, campaign_dir):
        if fail["on"]:
            raise RuntimeError("out of GPU memory")
        drawn.append(name)
        (campaign_dir / "images").mkdir(exist_ok=True)
        fname = f"000{len(drawn)}-portrait-{name.lower()}.png"
        (campaign_dir / "images" / fname).write_bytes(b"png")
        path = camp / "character.json" if name == "Pip" else next((camp / "players").glob("*.json"))
        data = json.loads(path.read_text()); data["portrait"] = fname; path.write_text(json.dumps(data))
        return fname

    state.portrait_maker = maker
    t0 = 1000.0
    assert state.portrait_pass(now=t0) == []                  # no look written yet: wait a bit
    assert state.portrait_pass(now=t0 + table_server.PORTRAIT_GRACE) == ["Pip"]
    msg = state.messages[-1]
    assert msg["event"] == {"type": "portrait"} and msg["image"] == "0001-portrait-pip.png"
    assert state.portrait_pass(now=t0 + 9999) == []           # has one now

    # A new player with a written look is drawn at once; a failure is retried later.
    tok = call("/api/create", {"code": CODE, "name": "Bram", "concept": "a dwarf"})[1]["token"]
    assert state.portrait_wake.is_set()
    bram = next((camp / "players").glob("*.json"))
    data = json.loads(bram.read_text()); data["visual_appearance"] = {"sex": "male"}
    bram.write_text(json.dumps(data))
    fail["on"] = True
    assert state.portrait_pass(now=t0 + 10000) == []
    fail["on"] = False
    assert state.portrait_pass(now=t0 + 10001) == []          # not hammering a broken GPU
    assert state.portrait_pass(now=t0 + 10000 + table_server.PORTRAIT_RETRY) == ["Bram"]
    _, info = call(f"/api/info?code={CODE}&token={tok}")
    assert {p["name"]: p["portrait"] for p in info["party"]} == {
        "Pip": "0001-portrait-pip.png", "Bram": "0002-portrait-bram.png"}


def test_important_places_are_painted_when_the_party_arrives(table):
    import table_server
    call, state, camp = table["call"], table["state"], table["camp"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    painted = []

    def maker(name, campaign_dir):
        painted.append(name)
        (campaign_dir / "images").mkdir(exist_ok=True)
        fname = f"place-{len(painted)}.png"
        (campaign_dir / "images" / fname).write_bytes(b"png")
        locs = json.loads((campaign_dir / "locations.json").read_text())
        locs[name]["image"] = fname
        (campaign_dir / "locations.json").write_text(json.dumps(locs))
        return fname

    state.place_maker = maker
    overview = json.loads((camp / "campaign-overview.json").read_text())
    locs = {"The Rusty Tankard": {"position": "unknown", "description": ""},
            "The Sunken Crypt": {"position": "under the old chapel", "description": "flooded, green torchlight"}}
    (camp / "locations.json").write_text(json.dumps(locs))

    # A bare stop (nothing written about it) isn't painted.
    overview["player_position"]["current_location"] = "The Rusty Tankard"
    (camp / "campaign-overview.json").write_text(json.dumps(overview))
    assert state.place_pass(now=1000) is None and painted == []

    # An important place is, once, and the table sees it.
    overview["player_position"]["current_location"] = "The Sunken Crypt"
    (camp / "campaign-overview.json").write_text(json.dumps(overview))
    assert state.place_pass(now=1001) == "The Sunken Crypt"
    assert state.messages[-1]["event"] == {"type": "place", "location": "The Sunken Crypt"}
    assert state.place_pass(now=1002 + table_server.PORTRAIT_RETRY) is None

    # Only places the party has BEEN are listed (a painted-ahead place stays secret).
    locs = json.loads((camp / "locations.json").read_text())
    locs["Dragon's Lair"] = {"position": "the mountain", "image": "place-1.png"}
    (camp / "locations.json").write_text(json.dumps(locs))
    _, info = call(f"/api/info?code={CODE}&token={pip}")
    assert info["places"] == [{"name": "The Sunken Crypt", "image": "place-1.png"}]
    assert TableState(camp, str(table["world"])).visited == ["The Rusty Tankard", "The Sunken Crypt"]


def _fake_painters(state, camp):
    painted = []

    def paint(kind, name, boss=False):
        painted.append((kind, name, boss))
        (camp / "images").mkdir(exist_ok=True)
        fname = f"{kind}-{len(painted)}.png"
        (camp / "images" / fname).write_bytes(b"png")
        return fname

    def foe(name, campaign_dir, boss, look):
        f = paint("foe", name, boss)
        path = campaign_dir / "bestiary.json"
        data = json.loads(path.read_text()) if path.exists() else {}
        data.setdefault(name, {})["boss_portrait" if boss else "portrait"] = f
        path.write_text(json.dumps(data))
        return f

    def item(name, campaign_dir, look, owner):
        f = paint("loot", name)
        path = campaign_dir / "treasures.json"
        data = json.loads(path.read_text()) if path.exists() else {}
        data[name] = {"image": f, "owner": owner}
        path.write_text(json.dumps(data))
        return f

    state.foe_maker, state.item_maker = foe, item
    return painted


def test_foes_bosses_and_loot_are_shown_to_the_table(table):
    call, state, camp = table["call"], table["state"], table["camp"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    painted = _fake_painters(state, camp)

    call("/api/gm/say", {"text": "A clown steps out.", "theme": "Grimaldi", "look": "rotting ringmaster"},
         host=True)
    assert state.art_jobs and state.art_jobs[0]["look"] == "rotting ringmaster"
    assert state.art_pass() == ["Grimaldi"]
    assert state.messages[-1]["event"] == {"type": "foe", "name": "Grimaldi", "boss": False}
    call("/api/gm/say", {"text": "He laughs again.", "theme": "Grimaldi"}, host=True)
    assert state.art_pass() == []                          # same foe: not shown twice

    # The fight escalates: the boss portrait.
    call("/api/gm/say", {"text": "He grows to fill the tent!", "mood": "boss"}, host=True)
    assert state.art_pass() == ["Grimaldi"] and painted[-1] == ("foe", "Grimaldi", True)
    assert state.messages[-1]["event"]["boss"] is True

    # Loot, for Pip.
    call("/api/gm/say", {"text": "In the chest: a blade of dawn.", "loot": "Sword of Dawn",
                         "loot_look": "sunsteel", "loot_for": "Pip"}, host=True)
    assert state.art_pass() == ["Sword of Dawn"]
    assert state.messages[-1]["event"] == {"type": "loot", "name": "Sword of Dawn", "owner": "Pip"}
    _, info = call(f"/api/info?code={CODE}&token={pip}")
    assert [f["boss"] for f in info["foes"]] == [True, False]
    assert info["treasures"] == [{"name": "Sword of Dawn", "image": "loot-3.png", "owner": "Pip"}]

    # A new table later: a foe met before is shown with the beat itself, no repaint.
    fresh = TableState(camp, str(table["world"]))
    fresh.shown_foes = []
    fresh.show_foe("Grimaldi", True)
    assert fresh.art_pass(ready_only=True) == ["Grimaldi"] and len(painted) == 3


def test_the_game_plays_in_words_without_any_image_source(table, monkeypatch):
    """No OpenAI key, no Forge: every picture feature stands down quietly."""
    import image_gen
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("IMAGE_BACKEND", raising=False)
    assert image_gen.images_status()[0] is False
    call, state, camp = table["call"], table["state"], table["camp"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    (camp / "locations.json").write_text(json.dumps({"The Crypt": {"position": "under the chapel"}}))
    overview = json.loads((camp / "campaign-overview.json").read_text())
    overview["player_position"]["current_location"] = "The Crypt"
    (camp / "campaign-overview.json").write_text(json.dumps(overview))
    tok = call("/api/create", {"code": CODE, "name": "Bram", "concept": "a dwarf"})[1]["token"]

    status, _ = call("/api/gm/say", {"text": "The boss rises!", "theme": "Lich", "boss": True,
                                     "loot": "Crown of Bone", "loot_for": "Bram"}, host=True)
    assert status == 200
    assert state.place_pass(now=10**9) is None
    assert state.portrait_pass(now=10**9) == []
    assert state.art_pass() == [] and state.art_jobs == []          # dropped, not stuck
    assert not any(m.get("image") for m in state.messages)
    _, info = call(f"/api/info?code={CODE}&token={tok}")
    assert info["places"] == [] and info["foes"] == [] and info["treasures"] == []
    assert all(p["portrait"] is None for p in info["party"])
    _, sheet = call(f"/api/sheet?code={CODE}&token={pip}&pc=Pip")
    assert sheet["ok"] and "portrait" not in sheet["sheet"]
    assert state.music.get("theme") == "Lich"                       # the music still works


def test_villains_bosses_and_heroes_get_composed_music(table):
    call, state, camp = table["call"], table["state"], table["camp"]
    call("/api/claim", {"code": CODE, "pc": "Pip"})
    made = []

    def maker(kind, name, boss, look, sheet):
        import composer
        made.append((kind, name, boss))
        sub = "themes" if kind == "theme" else "anthems"
        (camp / "music" / sub).mkdir(parents=True, exist_ok=True)
        f = f"{composer.slug(name)}-{'boss' if boss else 'theme'}.ogg" if kind == "theme" else "anthem-pip.ogg"
        (camp / "music" / sub / f).write_bytes(b"OggS")
        reg = composer.load_registry(camp)
        if kind == "theme":
            reg["themes"].setdefault(name, {})["boss" if boss else "normal"] = f
        else:
            reg["anthems"][name] = {"file": f, "seconds": 20}
        composer.save_registry(camp, reg)
        return f

    state.music_maker = maker
    # A main villain: their theme is composed and takes over while they're on stage.
    call("/api/gm/say", {"text": "Grimaldi bows.", "theme": "Grimaldi", "villain": True}, host=True)
    assert state.music["track"] == "theme:Grimaldi"                    # the generated one, meanwhile
    assert state.music_pass() == ["Grimaldi", "Pip"]                   # + Pip's anthem
    assert state.music["track"] == "grimaldi-theme.ogg" and state.music["theme"] == "Grimaldi"
    assert state.find_music("grimaldi-theme.ogg") is not None          # served to the players

    # The fight turns into a boss fight: a boss theme, without asking.
    call("/api/gm/say", {"text": "He grows!", "mood": "boss"}, host=True)
    assert state.music_pass() == ["Grimaldi"] and made[-1] == ("theme", "Grimaldi", True)
    assert state.music["track"] == "grimaldi-boss.ogg" and state.music["boss"] is True
    assert state.mood_files("boss") == []           # never picked for some other fight

    # Pip does something heroic: the anthem, then back to the boss theme.
    call("/api/gm/say", {"text": "Pip leaps onto the beast!", "heroic": "Pip"}, host=True)
    assert state.music["track"] == "anthem-pip.ogg" and state.music["loop"] is False
    state.music_revert["at"] = 0
    call(f"/api/info?code={CODE}")
    assert state.music["track"] == "grimaldi-boss.ogg"


def test_the_table_composes_with_the_model_kept_in_ram(table, monkeypatch, tmp_path):
    import composer
    from tests.test_composer import fake_composer
    call, state, camp = table["call"], table["state"], table["camp"]
    log, released = fake_composer(tmp_path, monkeypatch, composer)
    call("/api/claim", {"code": CODE, "pc": "Pip"})
    call("/api/create", {"code": CODE, "name": "Bram", "concept": "a dwarf"})
    try:
        assert composer.start_server()                     # at table start: model into RAM
        call("/api/gm/say", {"text": "Grimaldi bows.", "theme": "Grimaldi", "villain": True}, host=True)
        assert sorted(state.music_pass()) == ["Bram", "Grimaldi", "Pip"]
        assert state.music["track"] == "grimaldi-theme.ogg"    # took over
        assert composer.anthem(camp, "Bram") and composer.anthem(camp, "Pip")
        assert state.music_pass() == []                        # nothing left
        call("/api/gm/say", {"text": "He grows!", "mood": "boss"}, host=True)
        assert state.music_pass() == ["Grimaldi"] and state.music["track"] == "grimaldi-boss.ogg"
        assert log.read_text() == "load\n"                    # read from disk once, all evening
        assert len(released) == 4                              # Forge stepped off the card each time
    finally:
        composer.stop_server()


def test_heroic_moments_and_bosses_without_a_composer(table, monkeypatch):
    monkeypatch.setenv("MUSIC_COMPOSE", "off")
    call, state = table["call"], table["state"]
    call("/api/gm/say", {"text": "The lich!", "theme": "Lich", "boss": True, "villain": True}, host=True)
    assert state.music_jobs == [] and state.music["track"] == "theme:Lich"
    assert state.music_pass() == []
    call("/api/gm/say", {"text": "Pip strikes true!", "heroic": "Pip"}, host=True)
    assert state.music["mood"] == "victory"                     # the victory music instead
    state.music_revert["at"] = 0
    state.music_tick()
    assert state.music["track"] == "theme:Lich" and state.music["boss"] is True


def test_the_gm_waits_for_everyone_or_a_minute_after_the_first_action(table):
    import table_server
    call, state = table["call"], table["state"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    bram = call("/api/create", {"code": CODE, "name": "Bram", "concept": "a dwarf"})[1]["token"]
    call("/api/gm/inbox", {}, host=True)                         # (the join notices)

    # On a break: nobody has acted, nothing is ticking.
    assert state.round_state()["open"] is False
    assert call("/api/gm/say", {"text": "The fire crackles."}, host=True)[0] == 200

    # Pip acts: the round opens, the minute starts.
    call("/api/say", {"code": CODE, "token": pip, "text": "I check the door."})
    rnd = call(f"/api/info?code={CODE}&token={bram}")[1]["round"]
    assert rnd["open"] and rnd["waiting_on"] == ["Bram"] and rnd["seconds"] == 60
    assert 59 <= rnd["deadline"] - time.time() <= 60
    # ...and the GM can neither read it nor answer yet.
    held = call("/api/gm/inbox", {}, host=True)[1]
    assert held["held"] and held["messages"] == []
    status, body = call("/api/gm/say", {"text": "The door creaks open."}, host=True)
    assert status == 409 and "Bram" in body["error"]
    assert call("/api/gm/say", {"text": "Psst.", "to": "Pip"}, host=True)[0] == 200   # whispers are fine
    assert call("/api/gm/roll", {"notation": "1d20"}, host=True)[0] == 200            # so are rolls

    # Bram acts: everyone has, the round closes at once.
    call("/api/say", {"code": CODE, "token": bram, "text": "I guard the rear."})
    assert state.round_state()["open"] is False
    got = call("/api/gm/inbox", {}, host=True)[1]["messages"]
    assert [m["text"] for m in got if m["kind"] == "player"] == ["I check the door.", "I guard the rear."]
    # A player acting while the GM writes doesn't block the answer to the round it read.
    call("/api/say", {"code": CODE, "token": pip, "text": "I wait."})
    assert state.round_state()["open"] and call("/api/gm/say", {"text": "The hall is dark."},
                                                host=True)[0] == 200

    # Bram is away: the round closes a minute after Pip's action anyway.
    rnd = state.round_state(now=time.time() + table_server.ROUND_SECONDS + 1)
    assert rnd["open"] is False and rnd["timed_out"] and rnd["waiting_on"] == ["Bram"]

    # The host can change it, or turn it off.
    assert call("/api/gm/round", {"seconds": 90}, host=True)[1]["seconds"] == 90
    assert state.round_state()["seconds"] == 90 and state.round_state()["open"]
    call("/api/gm/round", {"seconds": 0}, host=True)
    assert state.round_state()["open"] is False
    assert TableState(table["camp"], str(table["world"])).round_seconds == 0


def test_the_round_never_waits_for_a_pc_who_cannot_act(table):
    import table_server
    call, state, camp = table["call"], table["state"], table["camp"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    bram_tok = call("/api/create", {"code": CODE, "name": "Bram", "concept": "a dwarf"})[1]["token"]
    call("/api/gm/inbox", {}, host=True)
    bram = next((camp / "players").glob("*.json"))

    for knocked_out in ({"conditions": ["unconscious"]}, {"conditions": [{"name": "Stunned"}]},
                        {"status": "dead"}, {"hp": {"current": 0, "max": 12}}):
        sheet = {**json.loads(bram.read_text()), "conditions": [], "status": "alive",
                 "hp": {"current": 12, "max": 12}, **knocked_out}
        bram.write_text(json.dumps(sheet))
        assert table_server.cant_act(sheet)
        call("/api/say", {"code": CODE, "token": pip, "text": "I drag Bram to safety."})
        rnd = state.round_state()
        assert rnd["open"] is False and "Bram" in rnd["out_of_action"]     # no need to wait
        assert "Bram" not in state.waiting_on()
        assert call("/api/gm/inbox", {}, host=True)[1]["messages"]
        call("/api/gm/say", {"text": "You pull him behind a pillar."}, host=True)

    # Back on his feet: waited for again.
    bram.write_text(json.dumps({**json.loads(bram.read_text()), "hp": {"current": 3, "max": 12}}))
    assert table_server.cant_act(json.loads(bram.read_text())) is None
    call("/api/say", {"code": CODE, "token": pip, "text": "Get up!"})
    assert state.round_state()["waiting_on"] == ["Bram"] and state.round_state()["open"]
    assert table_server.cant_act({"conditions": ["poisoned", "prone"]}) is None


def test_table_talk_is_for_the_players_only(table):
    call, state, camp = table["call"], table["state"], table["camp"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    bram = call("/api/create", {"code": CODE, "name": "Bram", "concept": "a dwarf"})[1]["token"]
    status, sent = call("/api/chat", {"code": CODE, "token": pip, "text": "psst, let's rob the GM's favourite NPC"})
    assert status == 200 and sent["message"]["pc"] == "Pip"
    _, seen = call(f"/api/chat?code={CODE}&token={bram}&after=0")
    assert [m["text"] for m in seen["messages"]] == ["psst, let's rob the GM's favourite NPC"]
    assert call(f"/api/chat?code={CODE}&token={bram}&after=1")[1]["messages"] == []

    # Never the GM's: not in its inbox, its log, any file, or with the host key.
    inbox = json.dumps(call("/api/gm/inbox", {}, host=True)[1])
    assert "favourite" not in inbox and state.round_state()["open"] is False   # chat isn't an action
    assert call(f"/api/chat?code={CODE}&after=0", host=True)[0] == 403
    assert call(f"/api/chat?code={CODE}&token=nope&after=0")[0] == 403
    for f in camp.rglob("*"):
        if f.is_file():
            assert b"favourite" not in f.read_bytes(), f
    assert call("/api/chat", {"code": CODE, "token": pip, "text": "  "})[0] == 400
    assert call("/api/chat", {"code": CODE, "token": pip, "text": "x" * 501})[0] == 400


def test_the_narrator_remembers_only_what_this_player_saw(table):
    import narrator
    call, state = table["call"], table["state"]
    state.set_round_seconds(0)
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    bram = call("/api/create", {"code": CODE, "name": "Bram", "concept": "a dwarf"})[1]["token"]
    call("/api/lang", {"code": CODE, "token": pip, "lang": "en"})
    call("/api/gm/say", {"text": "Old Marta hands you a brass key.", "lang": "en"}, host=True)
    call("/api/gm/say", {"text": "מרתה הזקנה נותנת לכם מפתח.", "lang": "he"}, host=True)
    call("/api/gm/say", {"text": "Bram, you notice Marta is lying.", "to": "Bram"}, host=True)
    call("/api/gm/roll", {"notation": "1d20", "why": "assassin", "secret": True}, host=True)
    call("/api/say", {"code": CODE, "token": pip, "text": "I pocket the key."})
    seen = {}

    def ask(system, prompt):
        seen["system"], seen["prompt"] = system, prompt
        return "Old Marta gave it to you."

    state.narrator_ask = ask
    log_before = (table["camp"] / "table" / "log.jsonl").read_text(encoding="utf-8")
    status, body = call("/api/narrator", {"code": CODE, "token": pip, "question": "Who gave us the key?"})
    assert status == 200 and body["entry"]["a"] == "Old Marta gave it to you."
    p = seen["prompt"]
    assert "Old Marta hands you a brass key." in p and "I pocket the key." in p
    assert "מרתה" not in p                       # the other language's version
    assert "lying" not in p                      # someone else's whisper
    assert "assassin" not in p                   # a secret roll
    assert "Who gave us the key?" in p and "never" in seen["system"].lower()
    assert "Answer in English" in seen["system"]

    # Private, and it changes nothing.
    assert (table["camp"] / "table" / "log.jsonl").read_text(encoding="utf-8") == log_before
    assert call(f"/api/narrator?code={CODE}&token={pip}")[1]["entries"][0]["q"] == "Who gave us the key?"
    assert call(f"/api/narrator?code={CODE}&token={bram}")[1]["entries"] == []
    assert call(f"/api/narrator?code={CODE}", host=True)[0] == 403
    assert "Marta gave" not in json.dumps(call("/api/gm/inbox", {}, host=True)[1])

    # Follow-ups carry the conversation; with no model, the story's own lines.
    call("/api/narrator", {"code": CODE, "token": pip, "question": "And what did I do with it?"})
    assert "Earlier, Pip asked: Who gave us the key?" in seen["prompt"]

    def broken(system, prompt):
        raise RuntimeError("offline")

    state.narrator_ask = broken
    got = call("/api/narrator", {"code": CODE, "token": pip, "question": "brass key"})[1]["entry"]
    assert got["source"] == "recall" and "Old Marta hands you a brass key." in got["a"]
    lines = narrator.story_lines(state.since(0, "Pip"), "Pip", "en")
    assert narrator.recall(lines, "zeppelin?", "en").startswith("I couldn't find")


def test_hover_cards_show_what_the_player_knows_and_nothing_more(table):
    call, state, camp = table["call"], table["state"], table["camp"]
    state.cards_warmed.add("Pip")                  # (sitting-down warm-up: its own test)
    state.set_round_seconds(0)
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    (camp / "npcs.json").write_text(json.dumps({
        "Marta": {"description": "innkeeper; SECRETLY the cult leader"},
        "Vex": {"description": "the hidden villain"}}))
    (camp / "locations.json").write_text(json.dumps({"The Crooked Lantern": {"position": "river road"}}))
    (camp / "world-bible.json").write_text(json.dumps({"factions": {"nodes": [{"name": "The Ashen Hand"}]}}))
    call("/api/gm/say", {"text": "At the Crooked Lantern, Marta hands Pip a key. "
                                 "The Ashen Hand's sigil is carved on the bar."}, host=True)
    call("/api/gm/alias", {"name": "Marta", "alias": "מרתה"}, host=True)
    call("/api/gm/say", {"text": "מרתה מחייכת.", "lang": "he"}, host=True)
    assert wait_for(lambda: state.after_busy == 0)  # (the follow-ups ran without a model)
    asked = []

    def ask(system, prompt):
        asked.append(prompt)
        return "Marta is the innkeeper who gave you a key."

    state.narrator_ask = ask
    _, info = call(f"/api/info?code={CODE}&token={pip}")
    terms = {t["term"]: t["kind"] for t in info["lore_terms"]}
    assert terms["Marta"] == "npc" and terms["The Crooked Lantern"] == "place"
    assert terms["The Ashen Hand"] == "faction" and terms["Pip"] == "pc"
    assert "Vex" not in terms                       # never mentioned to them: not even the name
    assert "מרתה" not in terms                      # Pip reads English: not in their story

    status, card = call(f"/api/lore?code={CODE}&token={pip}&term=marta")
    assert status == 200 and card["name"] == "Marta" and card["kind"] == "npc"
    assert card["text"] == "Marta is the innkeeper who gave you a key."
    assert "SECRETLY" not in asked[-1] and "Marta hands Pip a key" in asked[-1]
    call(f"/api/lore?code={CODE}&token={pip}&term=Marta")
    assert len(asked) == 1                          # cached until the story says more
    assert call(f"/api/lore?code={CODE}&token={pip}&term=Vex")[0] == 404
    assert call(f"/api/lore?code={CODE}&term=Marta", host=True)[0] == 403

    # A Hebrew reader: the alias is hoverable and means Marta.
    call("/api/lang", {"code": CODE, "token": pip, "lang": "he"})
    terms = {t["term"]: t for t in state.lore_terms("Pip")}
    assert terms["מרתה"]["of"] == "Marta" and terms["מרתה"]["kind"] == "npc"


def wait_for(cond, limit=5.0):
    end = time.time() + limit
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.05)
    return cond()


def test_hebrew_narration_spellings_of_known_names_are_learned(table):
    call, state, camp = table["call"], table["state"], table["camp"]
    state.set_round_seconds(0)
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    call("/api/create", {"code": CODE, "name": "Bram", "concept": "a dwarf"})
    (camp / "npcs.json").write_text(json.dumps({"Marta": {"description": "innkeeper"}, "Vex": {}}))
    asked = []

    def ask(system, prompt):
        if "passage" not in system:
            return "A card."                                     # (hover cards being prepared)
        asked.append(json.loads(prompt))
        return '{"Marta": "מרתה", "Bram": "בראם", "Vex": "וקס"}'   # Vex isn't in the passage

    state.narrator_ask = ask
    call("/api/lang", {"code": CODE, "token": pip, "lang": "he"})
    call("/api/gm/say", {"text": "למרתה יש מפתח. בראם מהנהן.", "lang": "he"}, host=True)
    assert wait_for(lambda: "Bram" in state.aliases().values())
    assert state.aliases() == {"מרתה": "Marta", "בראם": "Bram"}       # only spellings really there
    assert "Pip" in asked[0]["names"] and "Marta" in asked[0]["names"]
    terms = {t["term"]: t for t in call(f"/api/info?code={CODE}&token={pip}")[1]["lore_terms"]}
    assert terms["מרתה"]["of"] == "Marta" and terms["בראם"]["kind"] == "pc"   # hoverable at once
    # English narration needs nothing learned; known spellings aren't asked again.
    call("/api/gm/say", {"text": "Marta smiles."}, host=True)
    call("/api/gm/say", {"text": "מרתה מחייכת.", "lang": "he"}, host=True)
    time.sleep(0.3)
    assert len(asked) == 2 and "Marta" not in asked[1]["names"]


def test_every_player_character_has_a_card_and_the_sheet_speaks_the_players_language(table):
    call, state, camp = table["call"], table["state"], table["camp"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    call("/api/create", {"code": CODE, "name": "Bram", "concept": "a dwarf"})
    calls = []

    def ask(system, prompt):
        calls.append(system)
        if "character sheet" in system:
            return json.dumps({k: "ע:" + v for k, v in json.loads(prompt).items()})
        return "Bram, a dwarf."

    state.narrator_ask = ask
    # Bram hasn't been in the story yet: still, everyone at the table knows who he is.
    status, card = call(f"/api/lore?code={CODE}&token={pip}&term=Bram")
    assert status == 200 and card["kind"] == "pc" and card["name"] == "Bram"

    # An English reader: the sheet as written, nothing to translate.
    assert call(f"/api/sheet-tr?code={CODE}&token={pip}&pc=Pip")[1] == {"ok": True, "tr": {}, "pending": False}
    # A Hebrew reader: what's written on the sheet is translated, once, in the background.
    call("/api/lang", {"code": CODE, "token": pip, "lang": "he"})
    first = call(f"/api/sheet-tr?code={CODE}&token={pip}&pc=Pip")[1]
    assert first["pending"] is True
    assert wait_for(lambda: not call(f"/api/sheet-tr?code={CODE}&token={pip}&pc=Pip")[1]["pending"])
    got = call(f"/api/sheet-tr?code={CODE}&token={pip}&pc=Pip")[1]["tr"]
    assert got["a halfling rogue"] == "ע:a halfling rogue"
    assert "Pip" not in got                                      # the name stays the name
    n = len(calls)
    call(f"/api/sheet-tr?code={CODE}&token={pip}&pc=Pip")
    assert len(calls) == n                                       # kept: never asked twice
    assert json.loads((state.dir / "sheet-tr-he.json").read_text(encoding="utf-8"))["a halfling rogue"]


def test_hover_cards_are_ready_before_the_hover_and_kept(table):
    call, state, camp, world = table["call"], table["state"], table["camp"], table["world"]
    state.cards_warmed.add("Pip")                  # (sitting-down warm-up: its own test)
    state.set_round_seconds(0)
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    (camp / "npcs.json").write_text(json.dumps({"Marta": {"description": "innkeeper"}}))
    asked, gate = [], threading.Event()
    gate.set()

    def ask(system, prompt):
        gate.wait(10)
        asked.append(prompt)
        return f"Card #{len(asked)}"

    state.narrator_ask = ask
    # The narration mentions Marta: her card is made in the background, before any hover.
    call("/api/gm/say", {"text": "Marta waves from the bar."}, host=True)
    assert wait_for(lambda: len(asked) == 1)
    status, card = call(f"/api/lore?code={CODE}&token={pip}&term=Marta")
    assert status == 200 and card["text"] == "Card #1" and card["stale"] is False and len(asked) == 1
    n1 = card["n"]
    terms = {t["term"]: t for t in call(f"/api/info?code={CODE}&token={pip}")[1]["lore_terms"]}
    assert terms["Marta"]["n"] == n1                     # the page knows its card is current

    # The story moves on while the model is slow: the last card comes at once,
    # marked stale, and the fresh one replaces it when it's written.
    gate.clear()
    call("/api/gm/say", {"text": "Marta slips a note under the door."}, host=True)
    started = time.time()
    status, card = call(f"/api/lore?code={CODE}&token={pip}&term=Marta")
    assert time.time() - started < 2 and card["text"] == "Card #1" and card["stale"] is True
    gate.set()
    assert wait_for(lambda: not call(f"/api/lore?code={CODE}&token={pip}&term=Marta")[1]["stale"])
    card = call(f"/api/lore?code={CODE}&token={pip}&term=Marta")[1]
    assert card["text"] == "Card #2" and card["n"] > n1 and len(asked) == 2

    # Kept on disk: a restarted table still has it, with no new model call.
    again = TableState(camp, str(world))
    again.narrator_ask = ask
    again.langs = dict(state.langs)
    again.messages = list(state.messages)
    assert again.lore_card("Pip", "Marta")["text"] == "Card #2" and len(asked) == 2


def test_a_player_sitting_down_finds_their_recent_cards_ready(table):
    import lib.table_server as ts
    call, state, camp = table["call"], table["state"], table["camp"]
    state.set_round_seconds(0)
    names = {f"Npc{i}": {} for i in range(15)}
    (camp / "npcs.json").write_text(json.dumps(names))
    for i in range(15):                                     # (told before this table run)
        state.append("gm", f"Npc{i} nods.")
    assert wait_for(lambda: state.after_busy == 0)
    asked = []
    state.narrator_ask = lambda system, prompt: asked.append(prompt) or "A card."
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    call(f"/api/info?code={CODE}&token={pip}")              # sits down
    assert wait_for(lambda: len(state.lore_store) >= ts.WARM_CARDS and not state.card_jobs)
    ready = {k.split("|")[1] for k in state.lore_store}
    assert "npc14" in ready and "npc0" not in ready         # the most recent names, not all
    n = len(asked)
    started = time.time()
    card = call(f"/api/lore?code={CODE}&token={pip}&term=Npc14")[1]
    assert card["text"] == "A card." and len(asked) == n and time.time() - started < 1


def test_pictures_are_kept_by_browsers_and_come_small_where_shown_small(table):
    Image = pytest.importorskip("PIL.Image")
    import io
    camp, base, opener = table["camp"], table["base"], table["opener"]
    (camp / "images").mkdir(exist_ok=True)
    Image.effect_noise((1216, 832), 60).convert("RGB").save(camp / "images" / "crypt.png")
    big = (camp / "images" / "crypt.png").stat().st_size

    with opener.open(f"{base}/images/crypt.png?code={CODE}") as r:
        assert r.headers["Content-Type"] == "image/png" and len(r.read()) == big
        assert "max-age" in r.headers["Cache-Control"]          # kept: not fetched on every hover
    with opener.open(f"{base}/images/crypt.png?code={CODE}&w=390") as r:
        body = r.read()
        assert r.headers["Content-Type"] == "image/jpeg" and len(body) < big / 4
        assert Image.open(io.BytesIO(body)).size == (400, 274)   # the nearest size, same shape
    assert (table["state"].dir / "thumbs" / "crypt-400.jpg").is_file()   # made once
    with opener.open(f"{base}/images/crypt.png?code={CODE}&w=nonsense") as r:
        assert r.headers["Content-Type"] == "image/png" and len(r.read()) == big   # the original


def test_sheet_translations_come_back_by_number():
    import narrator
    seen = []

    def ask(system, prompt):
        seen.append(json.loads(prompt))
        # the model retypes one phrase differently, and answers out of order
        return 'Here: {"2": "שכנוע", "1": "ידע קסום", "3": "  "}'

    got = narrator.translate(["Arcana", "Persuasion", "Fire Bolt (1d10)"], "he", ask=ask)
    assert seen[0] == {"1": "Arcana", "2": "Persuasion", "3": "Fire Bolt (1d10)"}
    assert got == {"Arcana": "ידע קסום", "Persuasion": "שכנוע"}      # the blank one is left out


def test_sheet_strings_are_the_words_a_player_reads():
    import table_server
    got = table_server.sheet_strings({
        "name": "Pip", "portrait": "p.png", "race": "Halfling", "hp": {"current": 7, "max": 9},
        "stats": {"str": 8}, "spell_slots": {"1": 2}, "skills": {"stealth": 5},
        "equipment": [{"name": "Shortsword", "damage": "1d6+2"}, "Thieves' tools", "קרן"]})
    assert "Pip" not in got and "p.png" not in got and "1d6+2" not in got and "קרן" not in got
    for s in ("Halfling", "Race", "Spell slots", "Stealth", "Shortsword", "Damage", "Thieves' tools", "Str"):
        assert s in got, s


def test_the_host_wrapper_knows_every_table_command():
    """gm-table.sh passes only the actions it lists; a new table_server command must be added."""
    import re
    root = Path(__file__).resolve().parent.parent
    commands = set(re.findall(r'sub\.add_parser\("([a-z-]+)"', (root / "lib" / "table_server.py").read_text(encoding="utf-8")))
    case = re.search(r'^\s*("serve"[^)]*)\)', (root / "tools" / "gm-table.sh").read_text(encoding="utf-8"), re.M).group(1)
    allowed = set(re.findall(r'"([a-z-]+)"', case))
    assert commands <= allowed, commands - allowed
