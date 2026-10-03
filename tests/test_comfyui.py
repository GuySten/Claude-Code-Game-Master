"""Pictures from ComfyUI (lib/comfy.py): locally with IMAGE_BACKEND=comfyui, and on
the host's GPU machine behind gm-gpu-server.sh."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from lib import image_gen  # noqa: F401  (puts lib/ on the path, as the game does)
from tests.test_image_forge import PNG

import comfy
import gpu_remote
import gpu_server


@pytest.fixture
def comfyui(monkeypatch, tmp_path):
    seen = {"graphs": [], "frees": 0, "checkpoints": ["dreamshaperXL_lightningDPMSDE.safetensors"],
            "fail": None}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, data, status=200):
            body = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/object_info/CheckpointLoaderSimple":
                return self._json({"CheckpointLoaderSimple": {"input": {"required": {
                    "ckpt_name": [seen["checkpoints"], {}]}}}})
            if url.path == "/system_stats":
                return self._json({"system": {}})
            if url.path.startswith("/history/"):
                pid = url.path.rsplit("/", 1)[1]
                if seen["fail"]:
                    return self._json({pid: {"outputs": {}, "status": {"status_str": "error", "messages": [
                        ["execution_error", {"exception_message": seen["fail"]}]]}}})
                return self._json({pid: {"outputs": {"7": {"images": [
                    {"filename": "gm_0001.png", "subfolder": "", "type": "temp"}]}},
                    "status": {"status_str": "success", "completed": True}}})
            if url.path == "/view":
                seen["view"] = parse_qs(url.query)
                self.send_response(200)
                self.send_header("Content-Length", str(len(PNG)))
                self.end_headers()
                self.wfile.write(PNG)
                return
            self.send_error(404)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path == "/free":
                seen["frees"] += 1
                return self._json({})
            if self.path == "/prompt":
                graph = body["prompt"]
                if any(n.get("class_type") == "Broken" for n in graph.values()):
                    return self._json({"error": {"message": "Prompt outputs failed validation"},
                                       "node_errors": {"9": {"class_type": "Broken", "errors": [
                                           {"message": "Value not in list", "details": "ckpt_name"}]}}}, 400)
                seen["graphs"].append(graph)
                return self._json({"prompt_id": f"p{len(seen['graphs'])}", "number": 1})
            self.send_error(404)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    camp = tmp_path / "camp"
    camp.mkdir()
    (camp / "chronicler.json").write_text(json.dumps({"name": "Astreus", "style": "ink and watercolor"}))
    monkeypatch.setattr(image_gen, "resolve_campaign_dir", lambda *a, **k: camp)
    monkeypatch.setattr(comfy, "POLL_SECONDS", 0.01)
    for k in ("OPENAI_API_KEY", "GPU_SERVER_URL", "COMFY_MODEL", "COMFY_STEPS", "COMFY_CFG",
              "COMFY_GUIDANCE", "COMFY_WORKFLOW", "COMFY_SAMPLER", "COMFY_SCHEDULER"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("IMAGE_BACKEND", "comfyui")
    monkeypatch.setenv("COMFY_URL", f"http://127.0.0.1:{httpd.server_address[1]}")
    yield {"seen": seen, "camp": camp}
    httpd.shutdown()
    httpd.server_close()


def nodes(graph, kind):
    return [n["inputs"] for n in graph.values() if n["class_type"] == kind]


def test_comfyui_paints_with_the_games_settings(comfyui):
    ok, source, why = image_gen.images_status()
    assert (ok, source) == (True, "comfyui") and "dreamshaperXL" in why
    out = image_gen.generate_image("A cozy tavern at night", title="The Crooked Lantern")
    graph = comfyui["seen"]["graphs"][0]
    sampler = nodes(graph, "KSampler")[0]
    # Tuned for an SDXL Lightning model, like the Forge defaults.
    assert (sampler["steps"], sampler["cfg"], sampler["sampler_name"], sampler["scheduler"]) == \
        (6, 2.0, "dpmpp_sde", "karras")
    assert nodes(graph, "EmptyLatentImage")[0]["width"] == 1216
    assert nodes(graph, "CheckpointLoaderSimple")[0]["ckpt_name"] == "dreamshaperXL_lightningDPMSDE.safetensors"
    texts = [n["text"] for n in nodes(graph, "CLIPTextEncode")]
    assert "ink and watercolor" in texts[0] and "watermark" in texts[1]
    assert not nodes(graph, "SaveImage")                 # nothing left in ComfyUI's output folder
    assert open(out["path"], "rb").read() == PNG and out["cost"] == 0.0
    assert comfyui["seen"]["view"]["type"] == ["temp"]


def test_flux_gets_its_guidance_node(comfyui, monkeypatch):
    monkeypatch.setenv("COMFY_GUIDANCE", "3.5")
    monkeypatch.setenv("COMFY_CFG", "1")
    monkeypatch.setenv("COMFY_SAMPLER", "euler")
    monkeypatch.setenv("COMFY_SCHEDULER", "simple")
    image_gen.generate_image("A dwarf cleric whispers to a halfling rogue")
    graph = comfyui["seen"]["graphs"][0]
    guide = [k for k, n in graph.items() if n["class_type"] == "FluxGuidance"]
    assert guide and graph[guide[0]]["inputs"]["guidance"] == 3.5
    assert nodes(graph, "KSampler")[0]["positive"] == [guide[0], 0]


def test_your_own_workflow_gets_the_games_values(comfyui, monkeypatch, tmp_path):
    flow = {"10": {"class_type": "MyFluxLoader", "inputs": {"unet_name": "flux-dev-Q8.gguf"}},
            "11": {"class_type": "CLIPTextEncodeFlux", "inputs": {"t5xxl": "{{prompt}}", "guidance": "{{guidance}}"}},
            "12": {"class_type": "EmptySD3LatentImage", "inputs": {"width": "{{width}}", "height": "{{height}}"}},
            "13": {"class_type": "KSampler", "inputs": {"seed": "{{seed}}", "steps": 20}},
            "14": {"class_type": "SaveImage", "inputs": {"filename_prefix": "table {{width}}"}}}
    path = tmp_path / "flux-api.json"
    path.write_text(json.dumps(flow))
    monkeypatch.setenv("COMFY_WORKFLOW", str(path))
    assert image_gen.images_status()[0] is True
    image_gen.generate_image("A storm over the drowned bell tower", size="1536x1024")
    sent = comfyui["seen"]["graphs"][0]
    assert "drowned bell tower" in sent["11"]["inputs"]["t5xxl"]
    assert sent["12"]["inputs"]["width"] == 1216 and isinstance(sent["13"]["inputs"]["seed"], int)
    assert sent["11"]["inputs"]["guidance"] == 3.5
    assert sent["14"]["inputs"]["filename_prefix"] == "table 1216"     # inside a longer string


def test_comfyui_errors_say_what_went_wrong(comfyui, monkeypatch):
    monkeypatch.setenv("COMFY_MODEL", "missing.safetensors")
    ok, _, why = image_gen.images_status()
    assert not ok and "missing.safetensors" in why
    monkeypatch.delenv("COMFY_MODEL")
    comfyui["seen"]["fail"] = "CUDA out of memory"
    with pytest.raises(image_gen.ImageGenError, match="out of memory"):
        image_gen.generate_image("A tavern")


def test_music_first_frees_comfyuis_card(comfyui):
    assert image_gen.release_gpu() is True and comfyui["seen"]["frees"] == 1


def test_the_host_machine_paints_with_its_own_comfyui(comfyui, monkeypatch):
    """The GPU machine runs ComfyUI; the game elsewhere just asks for a picture."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), gpu_server.make_handler(gpu_server.Jobs(), "pw"))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        monkeypatch.setattr(gpu_server, "pictures_backend", lambda: "comfyui")
        monkeypatch.delenv("IMAGE_BACKEND")                      # this side: remote
        monkeypatch.setenv("GPU_SERVER_URL", f"http://127.0.0.1:{httpd.server_address[1]}")
        monkeypatch.setenv("GPU_SERVER_PASSWORD", "pw")
        monkeypatch.setattr(gpu_remote, "POLL_SECONDS", 0.02)
        gpu_remote._health.update(at=0.0, value=None)
        ok, source, _ = image_gen.images_status()
        assert (ok, source) == (True, "remote")
        out = image_gen.generate_image("A cozy tavern at night")
        assert open(out["path"], "rb").read() == PNG
        assert out["model"].startswith("comfyui:") and len(comfyui["seen"]["graphs"]) == 1
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_an_older_gpu_server_still_gets_forges_request(monkeypatch, tmp_path):
    """A GPU server from before "image" jobs: the game sends Forge's own request."""
    from tests.test_image_forge import PNG as png
    calls = []

    def fake_run(kind, payload=None, timeout=1800):
        calls.append(kind)
        if kind == "image":
            raise gpu_remote.GpuRemoteError("the GPU server answered 500: unknown job kind 'image'")
        import base64
        return {"images": [base64.b64encode(png).decode()]}

    monkeypatch.setattr(gpu_remote, "run", fake_run)
    data, model, size = image_gen._remote_generate("A tavern", "medium", "1536x1024")
    assert calls == ["image", "txt2img"] and data == png and size == "1216x832"
