"""Local images: a Stable Diffusion WebUI Forge (or AUTOMATIC1111) as the image source."""

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from lib import image_gen


def gpu_turn_is_free():
    import gpu_turn
    with gpu_turn.gpu_turn("probe", wait=0) as t:
        return t.held

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")


@pytest.fixture
def forge(monkeypatch, tmp_path):
    seen = {"requests": [], "models": [{"title": "dreamshaperXL_lightning"}]}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, data):
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/sdapi/v1/sd-models":
                return self._json(seen["models"])
            self.send_error(404)

        def do_POST(self):
            if self.path == "/sdapi/v1/unload-checkpoint":
                seen["unloads"] = seen.get("unloads", 0) + 1
                return self._json({})
            if self.path != "/sdapi/v1/txt2img":
                return self.send_error(404)
            seen["card_free"] = gpu_turn_is_free()
            seen["requests"].append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self._json({"images": [base64.b64encode(PNG).decode()], "info": "{}"})

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    camp = tmp_path / "camp"
    camp.mkdir()
    (camp / "chronicler.json").write_text(json.dumps({"name": "Astreus", "style": "ink and watercolor"}))
    monkeypatch.setattr(image_gen, "resolve_campaign_dir", lambda *a, **k: camp)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    for k in ("FORGE_STEPS", "FORGE_LANDSCAPE", "FORGE_MODEL", "FORGE_CFG"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("IMAGE_BACKEND", "forge")
    monkeypatch.setenv("FORGE_URL", f"http://127.0.0.1:{httpd.server_address[1]}")
    yield {"seen": seen, "camp": camp}
    httpd.shutdown()
    httpd.server_close()


def test_forge_makes_the_picture_locally_for_free(forge):
    assert image_gen.images_status() == (True, "forge", f"local Forge at {image_gen.forge_url()}")
    out = image_gen.generate_image("A cozy tavern at night", title="The Crooked Lantern")
    sent = forge["seen"]["requests"][0]
    # Tuned for an SDXL Lightning model: a landscape it's good at, few steps, low CFG.
    assert (sent["width"], sent["height"], sent["steps"], sent["cfg_scale"]) == (1216, 832, 6, 2.0)
    assert sent["sampler_name"] == "DPM++ SDE" and sent["scheduler"] == "Karras"
    assert "ink and watercolor" in sent["prompt"]          # the campaign's locked style
    assert "watermark" in sent["negative_prompt"]
    assert open(out["path"], "rb").read() == PNG and out["cost"] == 0.0
    log = (forge["camp"] / "images" / "_gen-log.jsonl").read_text().splitlines()
    assert json.loads(log[-1])["model"] == "forge:current model"


def test_forge_settings_and_portraits(forge, monkeypatch):
    monkeypatch.setenv("FORGE_PORTRAIT", "512x768")
    monkeypatch.setenv("FORGE_STEPS", "25")
    monkeypatch.setenv("FORGE_MODEL", "dreamshaper_8")
    image_gen.generate_image("A portrait of Pip", title="Pip", size="1024x1536", quality="low")
    sent = forge["seen"]["requests"][0]
    assert (sent["width"], sent["height"], sent["steps"]) == (512, 768, 23)
    assert sent["override_settings"] == {"sd_model_checkpoint": "dreamshaper_8"}


def test_images_are_off_when_forge_is_down_or_empty(forge, monkeypatch):
    forge["seen"]["models"] = []
    assert image_gen.images_status()[0] is False
    monkeypatch.setenv("FORGE_URL", "http://127.0.0.1:9")          # nothing listening
    on, source, why = image_gen.images_status()
    assert not on and source == "forge" and "start it" in why
    with pytest.raises(image_gen.ImageGenError, match="Can't reach Forge"):
        image_gen.generate_image("A tavern", title="x")


def test_no_source_at_all(monkeypatch):
    monkeypatch.delenv("IMAGE_BACKEND", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert image_gen.backend() == "off" and image_gen.images_status()[0] is False
    with pytest.raises(image_gen.ImageGenError, match="IMAGE_BACKEND=forge"):
        image_gen.generate_image("A tavern")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert image_gen.backend() == "openai"


def test_the_session_brief_names_the_image_source(forge, dcc_world):
    from lib.session_manager import SessionManager
    ctx = SessionManager(dcc_world).get_full_context()
    assert "Scene images: ENABLED (local Forge at" in ctx and "free here" in ctx
    forge["seen"]["models"] = []
    ctx = SessionManager(dcc_world).get_full_context()
    assert "Scene images: DISABLED (Forge is running but has no model" in ctx


def subject(prompt: str) -> str:
    """A Forge prompt after the campaign style's headline, which leads it."""
    return prompt.split("\n\n", 1)[1] if "\n\n" in prompt else prompt


def test_portraits_are_drawn_and_kept_on_the_record(forge):
    camp = forge["camp"]
    (camp / "character.json").write_text(json.dumps({
        "name": "Pip", "race": "Halfling", "class": "Rogue", "concept": "a nervous lockpick",
        "hp": {"current": 9, "max": 9},
        "visual_appearance": {"sex": "female", "hair": "red curls", "gear": "lockpicks"}}))
    (camp / "npcs.json").write_text(json.dumps({"Grimnar": {"description": "dwarf blacksmith"}}))

    out = image_gen.generate_portrait("pip", camp)
    sent = forge["seen"]["requests"][-1]
    assert (sent["width"], sent["height"]) == (832, 1216)                 # a portrait shape
    # On Forge the style's headline comes first, then the subject, sex first
    # (the model weighs the start most), and Forge is told what NOT to draw.
    assert subject(sent["prompt"]).startswith("Close-up portrait of a woman, Halfling Rogue, red curls")
    assert "Pip" not in sent["prompt"]                                   # looks, never names
    assert sent["negative_prompt"].startswith("man, male, masculine face, beard")
    assert "red curls" in sent["prompt"] and "ink and watercolor" in sent["prompt"]
    assert json.loads((camp / "character.json").read_text())["portrait"] == out["portrait"]
    assert (camp / "images" / out["portrait"]).read_bytes() == PNG

    npc = image_gen.generate_portrait("Grimnar", camp)
    sent = forge["seen"]["requests"][-1]
    assert "dwarf blacksmith" in sent["prompt"]
    assert subject(sent["prompt"]).startswith("Close-up portrait of a person")      # sex unknown: no guess
    assert not sent["negative_prompt"].startswith(("man,", "woman,"))
    assert json.loads((camp / "npcs.json").read_text())["Grimnar"]["portrait"] == npc["portrait"]
    with pytest.raises(image_gen.ImageGenError, match="No character"):
        image_gen.generate_portrait("Nobody", camp)


def test_places_are_painted_and_kept_on_the_location(forge):
    camp = forge["camp"]
    (camp / "locations.json").write_text(json.dumps({
        "The Crooked Lantern": {"position": "on the river road",
                                "description": "a leaning tavern with a green lantern", "connections": []},
        "Back Alley": {"position": "unknown", "description": "", "connections": []}}))
    assert image_gen.location_is_important(image_gen.find_location("the crooked lantern", camp)[2])
    assert not image_gen.location_is_important(image_gen.find_location("Back Alley", camp)[2])
    out = image_gen.generate_location_image("the crooked lantern", camp)
    sent = forge["seen"]["requests"][-1]
    assert (sent["width"], sent["height"]) == (1216, 832)
    assert subject(sent["prompt"]).startswith("Wide view: a leaning tavern") and "green lantern" in sent["prompt"]
    assert "Crooked Lantern" not in sent["prompt"]
    saved = json.loads((camp / "locations.json").read_text())
    assert saved["The Crooked Lantern"]["image"] == out["image"]
    with pytest.raises(image_gen.ImageGenError, match="No location"):
        image_gen.generate_location_image("Atlantis", camp)


def test_foes_bosses_and_treasures_are_painted_and_kept(forge):
    camp = forge["camp"]
    (camp / "npcs.json").write_text(json.dumps({"Grimaldi": {"description": "a rotting circus ringmaster"}}))
    foe = image_gen.generate_enemy_portrait("grimaldi", camp)
    sent = forge["seen"]["requests"][-1]
    assert "Menacing portrait of a rotting circus ringmaster" in sent["prompt"] and "Grimaldi" not in sent["prompt"]
    assert (sent["width"], sent["height"], sent["steps"]) == (832, 1216, 6)
    boss = image_gen.generate_enemy_portrait("Grimaldi", camp, boss=True)
    sent = forge["seen"]["requests"][-1]
    assert "Epic boss portrait" in sent["prompt"] and sent["steps"] == 8      # bosses: high quality
    assert image_gen.enemy_art("GRIMALDI", False, camp) == foe["image"]
    assert image_gen.enemy_art("grimaldi", True, camp) == boss["image"]
    assert image_gen.enemy_art("Goblin", False, camp) == ""

    image_gen.generate_enemy_portrait("Cave Troll", camp, look="moss-covered, one tusk")
    assert "Cave Troll, moss-covered, one tusk" in forge["seen"]["requests"][-1]["prompt"]

    item = image_gen.generate_item_image("Sword of Dawn", camp, look="a sunsteel blade", owner="Pip")
    sent = forge["seen"]["requests"][-1]
    assert "Treasure art of a sunsteel blade" in sent["prompt"] and "Dawn" not in sent["prompt"]
    assert (sent["width"], sent["height"]) == (1024, 1024)
    assert json.loads((camp / "treasures.json").read_text())["Sword of Dawn"] == {
        "image": item["image"], "look": "a sunsteel blade", "owner": "Pip"}
    assert image_gen.treasure_art("sword of dawn", camp) == item["image"]


def test_forge_without_its_api_is_named_as_such(monkeypatch):
    """A running Forge started without --api answers 404 for /sdapi/...: say so."""
    class NoApi(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            self.send_error(404)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), NoApi)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setenv("IMAGE_BACKEND", "forge")
    monkeypatch.setenv("FORGE_URL", f"http://127.0.0.1:{httpd.server_address[1]}")
    try:
        on, _, why = image_gen.images_status()
        assert not on and "API is off" in why and "--api" in why
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_pictures_take_their_turn_on_the_graphics_card(forge, monkeypatch, tmp_path):
    import gpu_turn
    monkeypatch.setattr(gpu_turn, "LOCK_PATH", tmp_path / "gpu.lock")
    image_gen.generate_image("a tavern", title="Tavern")
    assert forge["seen"]["card_free"] is False           # held while Forge painted
    assert gpu_turn_is_free()                             # and given back
    # Before music, Forge is asked to move its model off the card (into RAM).
    assert image_gen.forge_release_gpu() is True and forge["seen"]["unloads"] == 1
    monkeypatch.setenv("IMAGE_BACKEND", "off")
    assert image_gen.forge_release_gpu() is False and forge["seen"]["unloads"] == 1


def test_forge_is_warmed_up_at_the_start_of_the_game(forge, monkeypatch, tmp_path):
    import gpu_turn
    monkeypatch.setattr(gpu_turn, "LOCK_PATH", tmp_path / "gpu.lock")
    monkeypatch.setenv("FORGE_MODEL", "dreamshaper_8")
    assert image_gen.forge_warm_up() is True
    warm = forge["seen"]["requests"][-1]
    assert warm["steps"] == 1 and (warm["width"], warm["height"]) == (64, 64)        # a few seconds
    assert warm["override_settings"] == {"sd_model_checkpoint": "dreamshaper_8"}      # the right model
    assert forge["seen"]["unloads"] == 1               # then off the card, waiting in RAM
    monkeypatch.setenv("IMAGE_BACKEND", "off")
    assert image_gen.forge_warm_up() is False and len(forge["seen"]["requests"]) == 1


def test_the_table_loads_the_picture_model_then_the_music_model(monkeypatch):
    import composer
    import image_gen as ig                             # the module the table imports
    import table_server
    order = []
    monkeypatch.setattr(ig, "forge_warm_up", lambda: order.append("pictures") or True)
    monkeypatch.setattr(composer, "available", lambda: True)
    monkeypatch.setattr(composer, "start_server", lambda: order.append("music") or True)
    table_server.warm_up()
    assert order == ["pictures", "music"]              # one after the other, not both at once


def test_a_creature_is_painted_as_a_creature_whatever_its_name(forge):
    camp = forge["camp"]
    (camp / "npcs.json").write_text(json.dumps({
        "Old Mother Coil": {"description": "a giant ancient snake summoned by Noa"},
        "Ember": {"description": "Noa's familiar", "visual_appearance": {"species": "owl"}},
        "Marta": {"description": "a woman who keeps a pet snake"}}))
    image_gen.generate_portrait("Old Mother Coil", camp)
    sent = forge["seen"]["requests"][-1]
    assert subject(sent["prompt"]).startswith("Portrait of a snake, an animal, not a person")   # not a woman
    assert sent["negative_prompt"].startswith("human, person, woman, man")
    image_gen.generate_portrait("Ember", camp)
    assert subject(forge["seen"]["requests"][-1]["prompt"]).startswith("Portrait of an owl")
    image_gen.generate_portrait("Marta", camp)                       # a person with a pet snake
    assert subject(forge["seen"]["requests"][-1]["prompt"]).startswith("Close-up portrait of a person")
    assert image_gen.creature_of({"description": "נחשה ענקית"}) == "snake"


def test_a_place_inside_is_painted_from_inside(forge):
    # "Establishing view ... landscape" first made a cavern inside a castle into the
    # castle seen from outside under a blue sky.
    camp = forge["camp"]
    (camp / "locations.json").write_text(json.dumps({
        "The Hip": {"description": "A cavern of iron chain-galleries inside the Keep.",
                    "position": "opening stage"},
        "The Moor": {"description": "Burnt hills under a low sky."},
        "The Locker": {"position": "A cramped iron cage beside the shaft."}}))
    image_gen.generate_location_image("The Hip", camp)
    sent = forge["seen"]["requests"][-1]
    assert subject(sent["prompt"]).startswith("Interior view, inside: A cavern of iron chain-galleries")
    assert "opening stage" not in sent["prompt"]
    assert "sky" in sent["negative_prompt"] and "people" in sent["negative_prompt"]
    image_gen.generate_location_image("The Moor", camp)
    sent = forge["seen"]["requests"][-1]
    assert subject(sent["prompt"]).startswith("Wide view: Burnt hills") and "sky" not in sent["negative_prompt"]
    image_gen.generate_location_image("The Locker", camp)            # described only in position
    assert "cramped iron cage" in forge["seen"]["requests"][-1]["prompt"]
