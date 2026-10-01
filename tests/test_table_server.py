"""The online table: remote players join from their own browser.

Runs the real HTTP handler in-process on an ephemeral port and drives it the
way a browser (players) and gm-table.sh (the host) do.
"""

import json
import threading
import urllib.error
import urllib.request
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
