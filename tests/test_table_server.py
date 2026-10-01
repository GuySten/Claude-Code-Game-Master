"""The online table: remote players join from their own browser.

Runs the real HTTP handler in-process on an ephemeral port and drives it the
way a browser (players) and gm-table.sh (the host) do.
"""

import json
import threading
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
def table(tmp_path):
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


def test_players_can_fix_their_action_until_the_gm_answers(table):
    call, state = table["call"], table["state"]
    pip = call("/api/claim", {"code": CODE, "pc": "Pip"})[1]["token"]
    bram = call("/api/create", {"code": CODE, "name": "Bram", "concept": "a dwarf"})[1]["token"]
    _, said = call("/api/say", {"code": CODE, "token": pip, "text": "I pick the lcok."})
    mid = said["message"]["id"]

    # Before the GM reads it: the GM simply gets the fixed text.
    status, body = call("/api/edit", {"code": CODE, "token": pip, "id": mid, "text": "I pick the lock."})
    assert status == 200 and body["message"]["text"] == "I pick the lock." and body["message"]["edited"]
    inbox = call("/api/gm/inbox", {}, host=True)[1]["messages"]
    assert [m["text"] for m in inbox if m["kind"] == "player"] == ["I pick the lock."]
    assert not any("corrected_from" in m for m in inbox)

    # Only your own actions.
    assert call("/api/edit", {"code": CODE, "token": bram, "id": mid, "text": "Mine now."})[0] == 409

    # After the GM read it: the next inbox flags the correction with what the GM read.
    state.translate({str(mid): {"he": "אני פורץ את המנעול."}})
    call("/api/edit", {"code": CODE, "token": pip, "id": mid, "text": "I pick the lock quietly."})
    assert call("/api/gm/pending", host=True)[1]["unread"] == 1
    inbox = call("/api/gm/inbox", {}, host=True)[1]["messages"]
    assert inbox[0]["text"] == "I pick the lock quietly."
    assert inbox[0]["corrected_from"] == "I pick the lock."
    assert "tr" not in inbox[0]                       # the old translation is dropped
    assert call("/api/gm/inbox", {}, host=True)[1]["messages"] == []

    # Other players see it change in place (new rev).
    _, seen = call(f"/api/messages?code={CODE}&token={bram}&after={mid}&rev=1")
    assert any(m["id"] == mid and m["text"] == "I pick the lock quietly." for m in seen["messages"])

    # The edit survives a restart.
    reloaded = TableState(table["camp"], str(table["world"]))
    again = next(m for m in reloaded.messages if m["id"] == mid)
    assert again["text"] == "I pick the lock quietly." and again.get("edited") and "tr" not in again

    # Once the GM has answered, it's history.
    call("/api/gm/say", {"text": "The lock clicks open."}, host=True)
    status, body = call("/api/edit", {"code": CODE, "token": pip, "id": mid, "text": "Never mind."})
    assert status == 409 and body["reason"] == "answered"


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
