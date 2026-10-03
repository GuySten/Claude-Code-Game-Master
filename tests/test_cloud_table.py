"""The online table hosted from a cloud session (lib/cloud_table.py): the players'
requests arrive as saved Artifact documents, are replayed into the real table
server, and what the players should see goes back as "gm" documents."""

import json
import re

import pytest

from lib import cloud_table
from tests.test_table_server import CODE, HOST_KEY, table  # noqa: F401  (the real server)


@pytest.fixture
def bridge(table, tmp_path):
    port = int(table["base"].rsplit(":", 1)[1])
    (table["camp"] / "table" / "server.json").write_text(json.dumps(
        {"port": port, "code": CODE, "host_key": HOST_KEY, "pid": 1}))
    inbox = tmp_path / "saved"
    sent = []

    def player(path, body=None, client="", t=None, viewer=""):
        """A page saving one request into the Artifact's "rq" collection."""
        rid = f"r{len(sent) + 1:03d}"
        doc = {"id": rid, "t": t if t is not None else 1_700_000_000_000 + len(sent),
               "path": path, "body": body or {}, "client": client, "viewer": viewer}
        (inbox / "rq").mkdir(parents=True, exist_ok=True)
        # As ArtifactData saves it: the document, sometimes wrapped with its metadata.
        wrapped = {"id": rid, "version": 1, "data": doc} if len(sent) % 2 else doc
        (inbox / "rq" / f"{rid}.json").write_text(json.dumps(wrapped))
        sent.append(rid)
        return rid

    b = cloud_table.Bridge(table["camp"])
    yield {"b": b, "player": player, "inbox": inbox, "out": tmp_path / "out", **table}


def docs(batches):
    return [json.loads(open(w["file_path"]).read()) for batch in batches for w in batch]


def test_a_player_joins_acts_and_sees_the_story(bridge):
    b, player = bridge["b"], bridge["player"]
    join = player("/api/create", {"name": "Bram", "concept": "a dwarf cleric", "code": "x"}, client="c_page1")
    lines = b.pull(bridge["inbox"])
    assert lines == ["[Bram] joins"]
    # The page gets its own token back, never the server's.
    resp = b.state["outbox"][join]
    assert resp["ok"] and resp["pc"] == "Bram" and resp["token"] == "c_page1"
    assert b.seated() == {"c_page1": "Bram"}

    act = player("/api/say", {"text": "I bless the party", "lang": "en"}, client="c_page1")
    assert b.pull(bridge["inbox"]) == ["[Bram] acts"]       # the join isn't replayed
    _, inbox = bridge["call"]("/api/gm/inbox", {}, host=True)
    assert any(m.get("pc") == "Bram" and m["text"] == "I bless the party" for m in inbox["messages"])
    bridge["call"]("/api/gm/say", {"text": "Light settles on **Bram**'s shield."}, host=True)

    got = docs(b.push(bridge["out"]))
    assert got[0]["full"] and got[0]["seq"] == 1 and got[0]["base"] == 1
    merged = {}
    for d in got:
        for k, v in d.items():
            merged.setdefault(k, v if not isinstance(v, (dict, list)) else type(v)())
            if isinstance(v, dict):
                merged[k].update(v)
            elif isinstance(v, list):
                merged[k] += v
    assert merged["seats"] == {"c_page1": "Bram"}
    assert {join, act} <= set(merged["responses"])
    texts = [m["text"] for m in merged["msgs"]]
    assert "I bless the party" in texts and "Light settles on **Bram**'s shield." in texts
    info = merged["views"]["Bram"]["info"]
    assert info["me"] == "Bram" and {p["name"] for p in info["party"]} == {"Pip", "Bram"}
    assert "bram|bram" in merged["sheets"] and "bram|pip" in merged["sheets"]
    assert merged["sheets"]["bram|pip"].get("public")          # others' sheets: the public part
    assert merged["pub"]["party"] and "me" not in merged["pub"]

    # Next turn: only what changed goes out.
    bridge["call"]("/api/gm/say", {"text": "The door creaks."}, host=True)
    later = docs(b.push(bridge["out"]))
    assert len(later) == 1 and not later[0]["full"] and later[0]["base"] == 1
    assert [m["text"] for m in later[0]["msgs"]] == ["The door creaks."]
    assert "responses" not in later[0] and "seats" not in later[0]


def test_requests_are_relayed_once_even_from_a_slow_clock(bridge):
    b, player = bridge["b"], bridge["player"]
    player("/api/claim", {"pc": "Pip"}, client="c_a", t=2_000_000_000_000)
    assert b.pull(bridge["inbox"]) == ["[Pip] takes a seat"]
    # A second player whose clock runs behind: still fetched by the next query...
    player("/api/say", {"text": "hello"}, client="c_a", t=2_000_000_000_000 - 60_000)
    assert b.next_query()["where"][0][2] <= 2_000_000_000_000 - 60_000
    # ...and nothing is ever replayed twice.
    assert b.pull(bridge["inbox"]) == ["[Pip] acts"]
    assert b.pull(bridge["inbox"]) == []


def test_a_taken_seat_is_refused_back_to_the_page(bridge):
    b, player = bridge["b"], bridge["player"]
    player("/api/claim", {"pc": "Pip"}, client="c_a")
    second = player("/api/claim", {"pc": "Pip"}, client="c_b")
    assert b.pull(bridge["inbox"]) == ["[Pip] takes a seat",
                                       "[someone] takes a seat — refused: Pip is already being played. "
                                       "Ask the host to free the seat if that was you."]
    assert b.state["outbox"][second]["ok"] is False and "c_b" not in b.state["tokens"]


def test_pictures_must_be_uploaded_before_the_story_shows_them(bridge):
    b, player = bridge["b"], bridge["player"]
    player("/api/claim", {"pc": "Pip"}, client="c_a")
    b.pull(bridge["inbox"])
    images = bridge["camp"] / "images"
    images.mkdir()
    (images / "tavern.png").write_bytes(b"\x89PNG fake")
    bridge["call"]("/api/gm/say", {"text": "The tavern.", "image": "tavern.png"}, host=True)
    with pytest.raises(cloud_table.MediaMissing) as e:
        b.push(bridge["out"])
    assert list(e.value.missing) == ["images/tavern.png"]
    assert b.record_uploads([f"{images / 'tavern.png'}=https://claude.ai/_blob/abc"]) == ["images/tavern.png"]
    got = docs(b.push(bridge["out"]))
    assert got[0]["media"] == {"images/tavern.png": "https://claude.ai/_blob/abc"}
    # A changed picture under the same name has to go up again.
    (images / "tavern.png").write_bytes(b"\x89PNG repainted")
    assert list(b.missing_media()) == ["images/tavern.png"]


def test_big_snapshots_are_split_into_documents(bridge, monkeypatch):
    monkeypatch.setattr(cloud_table, "DOC_BYTES", 2_000)
    for i in range(30):
        bridge["call"]("/api/gm/say", {"text": f"Beat {i}: " + "words " * 40}, host=True)
    got = docs(bridge["b"].push(bridge["out"]))
    assert len(got) > 5 and [d["seq"] for d in got] == list(range(1, len(got) + 1))
    assert all(d["base"] == 1 for d in got)
    assert sum(len(d.get("msgs", [])) for d in got) == 30


def test_the_page_runs_the_cloud_transport_first():
    page = cloud_table.build_page()
    assert not page.lstrip().lower().startswith("<!doctype")      # the Artifact adds the skeleton
    assert page.startswith("<title>")
    first_script = page.index("<script>")
    assert "window.tableTransport" in page[first_script:page.index("</script>", first_script)]
    assert len(re.findall(r"<style>", page)) >= 1


def test_a_player_takes_their_own_character_back_from_a_new_tab(bridge):
    """A reload (or another device) while the seat is held by the old tab: the same
    person gets their character back; anyone else is still refused."""
    b, player = bridge["b"], bridge["player"]
    player("/api/create", {"name": "Bram"}, client="c_tab1", viewer="u_noa")
    b.pull(bridge["inbox"])
    assert b.seated() == {"c_tab1": "Bram"}
    other = player("/api/claim", {"pc": "Bram"}, client="c_tab9", viewer="u_someone")
    again = player("/api/create", {"name": "Bram"}, client="c_tab2", viewer="u_noa")
    lines = b.pull(bridge["inbox"])
    assert "refused" in lines[0] and "refused" not in lines[1]
    assert not b.state["outbox"][other]["ok"] and b.state["outbox"][again]["token"] == "c_tab2"
    assert b.seated() == {"c_tab2": "Bram"}
