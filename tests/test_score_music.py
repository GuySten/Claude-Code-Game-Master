"""Written music at the table (lib/score_music.py): scores the GM wrote are rendered by
the orchestra and played where they belong; PCs' anthems follow their story; places
earn their own music."""

import json
import time
from pathlib import Path

import pytest

from lib import score_music, composer
from tests.test_table_server import table, CODE  # noqa: F401  (the fixture)

TUNE = {"seed": "Pip", "meter": "4/4", "mode": "dorian", "kind": "test", "hook": 3, "pickup": [],
        "motif": [[0, 1], [2, 1], [4, 2]], "again": [[4, 1], [2, 1], [1, 2]],
        "climb": [[2, 1], [4, 1], [6, 2]], "home": [[4, 1], [1, 1], [0, 2]]}


def _score(camp, name, use, tune=None, **extra):
    folder = Path(camp) / "music" / "arrangements"
    folder.mkdir(parents=True, exist_ok=True)
    spec = {"title": name, "use": use, "tune": tune or {"seed": use.get("who", "x"), "mode": "minor"},
            "tempo": 80, **extra}
    (folder / f"{name}.json").write_text(json.dumps(spec, ensure_ascii=False))
    return spec


def test_scores_say_what_they_are_for_and_a_score_on_another_tune_is_set_aside(tmp_path):
    camp = tmp_path
    (camp / "music" / "tunes").mkdir(parents=True)
    (camp / "music" / "tunes" / "pip.json").write_text(json.dumps(TUNE))
    _score(camp, "pip-old", {"as": "anthem", "who": "Pip", "stage": 1}, {"seed": "Pip", "stage": 1})
    _score(camp, "pip-theme", {"as": "anthem", "who": "Pip"}, {"seed": "Pip", "stage": 2, "written": TUNE})
    _score(camp, "grim", {"as": "boss", "who": "Grimaldi"})
    _score(camp, "notes-only", {"as": "nonsense"})
    got = {it["file"].name: it for it in score_music.index(camp)}
    assert set(got) == {"pip-old.json", "pip-theme.json", "grim.json"}
    assert got["pip-old.json"]["problem"] == "tune"               # (not Pip's tune any more)
    assert got["pip-theme.json"]["use"]["version"] == "s2-d0-w0-b0"  # (the stage from its tune)
    assert got["grim.json"]["problem"] is None
    assert score_music.has_score(camp, "boss", "grimaldi")
    assert not score_music.has_score(camp, "theme", "Grimaldi")
    # A title or a note changes nothing to render; a note of the music does.
    spec = json.loads((camp / "music/arrangements/grim.json").read_text())
    assert score_music.fingerprint({**spec, "title": "new"}) == score_music.fingerprint(spec)
    assert score_music.fingerprint({**spec, "tempo": 81}) != score_music.fingerprint(spec)


def test_the_newest_of_two_scores_for_one_use_wins(tmp_path):
    _score(tmp_path, "grim-v1", {"as": "theme", "who": "Grimaldi"})
    time.sleep(0.02)
    _score(tmp_path, "grim-v2", {"as": "theme", "who": "Grimaldi"}, tempo=90)
    got = {it["file"].name: it["problem"] for it in score_music.index(tmp_path)}
    assert got == {"grim-v2.json": None, "grim-v1.json": "superseded"}


def test_rendered_pieces_are_registered_where_the_table_looks(tmp_path):
    camp = tmp_path
    for use, sub in (({"as": "anthem", "who": "Pip", "stage": 1, "dark": 0, "wound": False, "warm": False,
                       "version": "s1-d0-w0-b0"}, "anthems"),
                     ({"as": "boss", "who": "Grimaldi"}, "themes"),
                     ({"as": "place", "place": "The Hip"}, "places")):
        out = score_music.target(camp, use)
        assert out.parent.name == sub
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"OggS")
        score_music.register(camp, use, out, 40.0, "score", "abc")
        assert score_music.registered(camp, use)["hash"] == "abc"
    assert composer.theme_file(camp, "Grimaldi", True) == "grimaldi-boss-score.ogg"
    assert composer.anthem(camp, "Pip")["file"] == "anthem-pip-s1-d0-w0-b0-score.ogg"
    assert score_music.place_file(camp, "the hip") == "place-the-hip.ogg"


def test_stale_scores_are_the_new_and_the_changed(tmp_path):
    camp = tmp_path
    spec = _score(camp, "grim", {"as": "theme", "who": "Grimaldi"})
    assert [it["file"].name for it in score_music.stale(camp)] == ["grim.json"]
    use = score_music.use_of(spec)
    out = score_music.target(camp, use)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"OggS")
    score_music.register(camp, use, out, 30.0, "score", score_music.fingerprint(spec))
    assert score_music.stale(camp) == []
    _score(camp, "grim", {"as": "theme", "who": "Grimaldi"}, tempo=70)       # the GM revised it
    assert [it["file"].name for it in score_music.stale(camp)] == ["grim.json"]


def test_what_the_gm_still_has_to_write(tmp_path):
    camp = tmp_path
    score_music.request(camp, "boss", "Grimaldi")
    score_music.request(camp, "boss", "grimaldi")                          # (once)
    _score(camp, "pip-1", {"as": "anthem", "who": "Pip", "stage": 0}, {"seed": "Pip", "stage": 0})
    got = score_music.wanted(camp, pcs=["Pip"], places=["The Hip"])
    what = [(w["what"], w.get("who") or w.get("place"), w.get("version")) for w in got]
    assert what[0] == ("boss", "Grimaldi", None)                           # the most pressing first
    assert ("tune", "Pip", None) in what
    assert ("anthem", "Pip", "s1-d0-w0-b0") in what                       # (their next growth)
    assert ("anthem", "Pip", "s0-d0-w0-b0") not in what                   # (written)
    assert ("place", "The Hip", None) in what and ("dark", "Pip", None) in what


@pytest.mark.parametrize("name,rec,seconds,visits,opening,story,why", [
    ("The Hip", {}, 11 * 60, 1, False, False, "minutes"),
    ("The Hip", {}, 60, 1, True, False, "opens"),
    ("The Hip", {}, 60, 2, False, False, "came back"),
    ("The Stair of Tallies", {}, 60, 3, False, False, None),        # (passed through, again and again)
    ("The Stair of Tallies", {}, 60, 1, False, True, None),
    ("The Stair of Tallies", {"music": True}, 0, 1, False, False, "marked"),
    ("The Hip", {"music": False}, 3600, 9, True, True, None),     # (the GM said no)
    ("The Vault", {}, 60, 1, False, True, "quest"),
    ("The Vault", {}, 60, 1, False, False, None),
])
def test_which_places_earn_music(name, rec, seconds, visits, opening, story, why):
    got = score_music.earns_music(name, rec, seconds, visits, opening, story)
    assert (got is None) if why is None else (why in got)


def test_a_place_sketch_is_a_quiet_loop_with_the_adventures_motif(tmp_path):
    rec = {"description": "A cavern of black iron chain-galleries, grease pits, blue lamps."}
    a = score_music.place_sketch(tmp_path, "The Hip", rec, adventure="The Striding Keep")
    b = score_music.place_sketch(tmp_path, "The High Towers", {"description": "wind over the battlements"})
    assert a["loop"] and a["role"] == "place" and a["sketch"] and a["use"] == {"as": "place", "place": "The Hip"}
    assert a["colour"] == "deep" and b["colour"] == "high"
    assert a["tune"]["written"]["motif"] == b["tune"]["written"]["motif"]    # the adventure's signature
    assert a["tune"]["written"]["again"] != b["tune"]["written"]["again"]    # each place's own answer
    assert max(v for _, v in a["dynamics"]) <= 70                            # under the voices
    assert json.loads((tmp_path / "music/tunes/signature.json").read_text())["seed"] == "The Striding Keep"
    assert score_music.ensure_sketch(tmp_path, "The Hip", rec) is not None
    assert score_music.ensure_sketch(tmp_path, "The Hip", rec) is None       # (once; the GM's replaces it)


def test_a_place_sketch_passes_the_critic(tmp_path):
    pytest.importorskip("numpy")
    from lib import arrangement
    for name, rec in (("The Hip", {"description": "iron chain-galleries, a cavern"}),
                      ("Saint Orla's Chapel", {"description": "a ruined shrine"}),
                      ("The Market Square", {"description": "a crowded town square"})):
        spec = score_music.place_sketch(tmp_path, name, rec, adventure="Test")
        errors = [m for level, m in arrangement.check(spec, listen=False) if level == "error"]
        assert errors == [], (name, errors)


# --- at the table ---
def _orchestra(camp, made):
    def maker(job):
        out = Path(job["out"]) if "out" in job else score_music.target(camp, job["use"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"OggS")
        made.append(job.get("kind") or job["use"]["as"])
        return out
    return maker


def test_a_written_villain_theme_plays_instead_of_the_ai(table):  # noqa: F811
    call, state, camp = table["call"], table["state"], table["camp"]
    made, composed = [], []
    state.orchestra_maker = _orchestra(camp, made)
    state.music_maker = lambda *a: composed.append(a) or "x.ogg"
    _score(camp, "grimaldi-theme", {"as": "theme", "who": "Grimaldi"})
    call("/api/gm/say", {"text": "Grimaldi bows.", "theme": "Grimaldi", "villain": True}, host=True)
    state.music_pass()
    assert state.music["track"] == "grimaldi-theme-score.ogg" and state.music["theme"] == "Grimaldi"
    assert not [c for c in composed if c[0] == "theme"]              # (no AI theme for a written one)
    # A boss nobody has written yet: the GM is asked for it.
    call("/api/gm/say", {"text": "Dobbin roars.", "theme": "Dobbin", "boss": True}, host=True)
    assert ("boss", "Dobbin") in [(w["what"], w.get("who")) for w in score_music.wanted(camp)]


def test_pc_anthems_follow_their_story_on_the_orchestra(table):  # noqa: F811
    call, state, camp = table["call"], table["state"], table["camp"]
    call("/api/claim", {"code": CODE, "pc": "Pip"})
    made, composed = [], []
    state.orchestra_maker = _orchestra(camp, made)
    state.music_maker = lambda *a: composed.append(a) or "x.ogg"
    state.music_pass()
    assert made == ["theme", "theme"]                 # now (s0) and the next growth (s1), by rule
    assert composer.anthem(camp, "Pip")["file"].startswith("anthem-pip-s0-d0-w0-b0")
    assert not [c for c in composed if c[0] in ("anthem", "anthem_version")]
    # The GM writes Pip's theme as their story reached it: it replaces the rule's.
    (camp / "music" / "tunes").mkdir(parents=True, exist_ok=True)
    _score(camp, "pip-seed", {"as": "anthem", "who": "Pip", "stage": 0}, {"seed": "Pip", "stage": 0})
    state.music_pass()
    assert composer.anthem(camp, "Pip")["file"] == "anthem-pip-s0-d0-w0-b0-score.ogg"
    call("/api/gm/say", {"text": "Pip leaps!", "heroic": "Pip"}, host=True)
    assert state.music["track"] == "anthem-pip-s0-d0-w0-b0-score.ogg"


def test_iconic_places_play_their_own_music(table):  # noqa: F811
    call, state, camp = table["call"], table["state"], table["camp"]
    made = []
    state.orchestra_maker = _orchestra(camp, made)
    (camp / "locations.json").write_text(json.dumps({
        "The Rusty Tankard": {"position": "the village square", "description": "a warm, crowded inn"},
        "The Road North": {"position": "out of the village", "description": "a muddy road"}}))
    state.messages.append({"id": 999, "ts": "", "t": time.time(), "kind": "gm", "text": "."})
    call("/api/gm/say", {"text": "The inn is warm.", "mood": "tavern"}, host=True)
    state.place_pass()                                # the opening place: it earns its music
    assert "The Rusty Tankard" in state.place_music
    assert (camp / "music/arrangements/place-the-rusty-tankard.json").is_file()
    state.music_pass()                                # its sketch, rendered: it plays now
    assert state.music["track"] == "place-the-rusty-tankard.ogg" and state.music["place"] == "The Rusty Tankard"
    assert json.loads((camp / "table/places.json").read_text())["music"]["The Rusty Tankard"]
    # A fight breaks out: the fight's music, not the place's.
    call("/api/gm/say", {"text": "Knives!", "mood": "combat"}, host=True)
    assert state.music.get("place") is None and state.music["mood"] == "combat"
    call("/api/gm/say", {"text": "Quiet again.", "mood": "calm"}, host=True)
    assert state.music["track"] == "place-the-rusty-tankard.ogg"
    # They take the road: the scene's own music again.
    ov = json.loads((camp / "campaign-overview.json").read_text())
    ov["player_position"]["current_location"] = "The Road North"
    (camp / "campaign-overview.json").write_text(json.dumps(ov))
    state.place_pass()
    assert state.music.get("place") is None and state.music["mood"] == "calm"
    # Ten minutes of play there and the road would earn music - but it's passed through... unless
    # the GM marks it.
    assert "The Road North" not in state.place_music
