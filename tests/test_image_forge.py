"""Local images: a Stable Diffusion WebUI Forge (or AUTOMATIC1111) as the image source."""

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from lib import image_gen

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
            if self.path != "/sdapi/v1/txt2img":
                return self.send_error(404)
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
    assert "Character portrait of Pip, Halfling Rogue" in sent["prompt"]
    assert "red curls" in sent["prompt"] and "ink and watercolor" in sent["prompt"]
    assert json.loads((camp / "character.json").read_text())["portrait"] == out["portrait"]
    assert (camp / "images" / out["portrait"]).read_bytes() == PNG

    npc = image_gen.generate_portrait("Grimnar", camp)
    assert "dwarf blacksmith" in forge["seen"]["requests"][-1]["prompt"]
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
    assert "Establishing view of The Crooked Lantern" in sent["prompt"] and "green lantern" in sent["prompt"]
    saved = json.loads((camp / "locations.json").read_text())
    assert saved["The Crooked Lantern"]["image"] == out["image"]
    with pytest.raises(image_gen.ImageGenError, match="No location"):
        image_gen.generate_location_image("Atlantis", camp)
