#!/usr/bin/env python3
"""The host laptop's graphics card, offered to a game running elsewhere.

When the game runs on a computer without a graphics card (GAME-NIGHT.md), another
machine's can do the work. This small server runs on the host's computer next to its picture
program (Forge, or ComfyUI with IMAGE_BACKEND=comfyui in this machine's .env) and
the music composer, and does their work for it (lib/gpu_remote.py is the other
end). The picture settings (FORGE_* / COMFY_*) are this machine's too: it owns
the models.

    bash tools/gm-gpu-server.sh                       # port 7861, prints its password
    cloudflared tunnel --url http://localhost:7861    # the https link to give the GM

Jobs are queued and run one at a time (one model on the card at a time, as at
home; lib/gpu_turn.py still applies). A job is submitted with ``POST /jobs`` and
fetched with ``GET /jobs/<id>`` when done, so no single request outlives a
tunnel's ~100 s limit.

  image          {prompt, quality, size, avoid} -> {image: png base64, model, size},
                 painted by this machine's Forge or ComfyUI with its own settings
  txt2img        Forge's own txt2img payload -> {"images": [png base64]} (older games)
  warmup         read the picture model into RAM now
  compose        {prompt, seconds, loop, ext} -> {audio: base64, ext, seconds, device}
  compose-start  read the music model into RAM now

Every request needs ``Authorization: Bearer <password>``.
"""

import argparse
import base64
import hmac
import json
import os
import queue
import secrets
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent))

import comfy  # noqa: E402
import composer  # noqa: E402
import image_gen  # noqa: E402
from gpu_turn import gpu_turn  # noqa: E402

KEEP_SECONDS = 1800          # a finished job's result waits this long to be fetched
MAX_BODY = 1_000_000


class Jobs:
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.todo: "queue.Queue[str]" = queue.Queue()
        threading.Thread(target=self._worker, daemon=True).start()

    def submit(self, kind: str, payload: Dict[str, Any]) -> str:
        job_id = secrets.token_urlsafe(9)
        with self.lock:
            self._prune()
            self.jobs[job_id] = {"kind": kind, "payload": payload, "status": "queued",
                                 "at": time.time()}
        self.todo.put(job_id)
        return job_id

    def get(self, job_id: str):
        with self.lock:
            job = self.jobs.get(job_id)
            return None if job is None else {k: v for k, v in job.items() if k != "payload"}

    def _prune(self) -> None:
        old = [k for k, j in self.jobs.items()
               if j["status"] in ("done", "failed") and time.time() - j["at"] > KEEP_SECONDS]
        for k in old:
            del self.jobs[k]

    def _worker(self) -> None:
        while True:
            job_id = self.todo.get()
            with self.lock:
                job = self.jobs[job_id]
                job["status"] = "running"
            try:
                result = run_job(job["kind"], job["payload"])
                update = {"status": "done", "result": result}
            except Exception as e:                       # one bad job doesn't stop the server
                update = {"status": "failed", "error": f"{type(e).__name__}: {e}"}
            with self.lock:
                job.update(update, at=time.time())
                job.pop("payload", None)


def _forge(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    req = urllib.request.Request(image_gen.forge_url() + path, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with image_gen._forge_open(req, int(os.environ.get("FORGE_TIMEOUT", "600"))) as r:
        return json.loads(r.read().decode("utf-8"))


def pictures_backend() -> str:
    """How this machine paints: 'comfyui' (IMAGE_BACKEND=comfyui) or 'forge'."""
    chosen = os.environ.get("IMAGE_BACKEND", "").strip().lower()
    return "comfyui" if chosen in ("comfyui", "comfy") else "forge"


def run_job(kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if kind == "image":
        args = (str(payload.get("prompt", "")), str(payload.get("quality") or image_gen.DEFAULT_QUALITY),
                str(payload.get("size") or image_gen.DEFAULT_SIZE), str(payload.get("avoid") or ""))
        if pictures_backend() == "comfyui":
            data, model, size = image_gen._comfy_generate(*args)
        else:
            data, model, size = image_gen._forge_generate(*args)
        return {"image": base64.b64encode(data).decode("ascii"), "model": model, "size": size}
    if kind == "txt2img":
        try:
            with gpu_turn("pictures"):
                body = _forge("/sdapi/v1/txt2img", payload)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Forge error {e.code} (out of GPU memory?)") from e
        except (urllib.error.URLError, OSError) as e:
            raise RuntimeError(f"Forge isn't answering at {image_gen.forge_url()} — start it "
                               f"(run.bat) with --api") from e
        return {"images": (body.get("images") or [])[:1]}
    if kind == "warmup":
        if pictures_backend() == "comfyui":
            return {"ok": comfy.warm_up()}
        return {"ok": image_gen.forge_warm_up(local=True)}
    if kind == "compose-start":
        return {"ok": composer_ready() and composer.start_server(local=True)}
    if kind == "compose":
        ext = payload.get("ext") if payload.get("ext") in (".ogg", ".wav", ".mp3") else ".ogg"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / ("piece" + ext)
            twin = ({"prompt": str(payload["twin_prompt"]), "loop": True, "out": str(Path(tmp) / ("twin" + ext)),
                     **({"leitmotif": payload["twin_leitmotif"]} if isinstance(payload.get("twin_leitmotif"), dict) else {})}
                    if payload.get("twin_prompt") else None)
            melody_from = None
            if payload.get("melody_audio"):
                melody_from = Path(tmp) / ("melody" + (payload.get("melody_ext") if payload.get("melody_ext")
                                                       in (".ogg", ".wav", ".mp3") else ".ogg"))
                melody_from.write_bytes(base64.b64decode(payload["melody_audio"]))
            more = {**({"twin": twin} if twin else {}),
                    **({"melody_from": str(melody_from)} if melody_from else {}),
                    **({"leitmotif": payload["leitmotif"]} if isinstance(payload.get("leitmotif"), dict) else {}),
                    **({"heavy": True} if payload.get("heavy") else {})}
            r = composer.compose(str(payload.get("prompt", "")), float(payload.get("seconds", 30)),
                                 out, loop=bool(payload.get("loop")), local=True, **more)
            path = Path(r["path"])
            answer = {"audio": base64.b64encode(path.read_bytes()).decode("ascii"), "ext": path.suffix,
                      "seconds": r.get("seconds"), "device": r.get("device"), "elapsed": r.get("elapsed"),
                      "how": r.get("how")}
            if r.get("twin"):
                t = Path(r["twin"]["path"])
                answer.update(twin_audio=base64.b64encode(t.read_bytes()).decode("ascii"), twin_ext=t.suffix,
                              twin_seconds=r["twin"].get("seconds"), twin_how=r["twin"].get("how"))
            return answer
    raise ValueError(f"unknown job kind {kind!r}")


def composer_ready() -> bool:
    return not composer._turned_off() and composer._local_python() is not None


def health() -> Dict[str, Any]:
    backend = pictures_backend()
    ok, why = comfy.status() if backend == "comfyui" else image_gen.forge_status()
    # ("forge"/"forge_why": what games from before ComfyUI support read)
    return {"ok": True, "pictures": ok, "pictures_why": why, "pictures_backend": backend,
            "forge": ok, "forge_why": why, "composer": composer_ready()}


def make_handler(jobs: Jobs, password: str):
    class Handler(BaseHTTPRequestHandler):
        server_version = "GMGpu/1.0"

        def log_message(self, fmt, *args):
            pass

        def _json(self, data: Any, status: int = 200) -> None:
            body = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            given = self.headers.get("Authorization", "")
            if hmac.compare_digest(given, "Bearer " + password):
                return True
            self._json({"ok": False, "error": "wrong password"}, 401)
            return False

        def do_GET(self):
            if not self._authorized():
                return
            if self.path == "/health":
                return self._json(health())
            if self.path.startswith("/jobs/"):
                job = jobs.get(self.path[len("/jobs/"):])
                return self._json(job) if job else self._json({"ok": False, "error": "no such job"}, 404)
            self._json({"ok": False, "error": "not found"}, 404)

        def do_POST(self):
            if not self._authorized():
                return
            if self.path != "/jobs":
                return self._json({"ok": False, "error": "not found"}, 404)
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._json({"ok": False, "error": "request too large"}, 413)
            try:
                data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                kind, payload = str(data["kind"]), data.get("payload") or {}
                if not isinstance(payload, dict):
                    raise ValueError
            except (ValueError, KeyError, UnicodeDecodeError):
                return self._json({"ok": False, "error": "expected {kind, payload}"}, 400)
            self._json({"ok": True, "id": jobs.submit(kind, payload)})

    return Handler


def main() -> None:
    ap = argparse.ArgumentParser(description="Lend this computer's GPU to a game hosted elsewhere")
    ap.add_argument("--port", type=int, default=int(os.environ.get("GPU_SERVER_PORT", "7861")))
    ap.add_argument("--password", default=os.environ.get("GPU_SERVER_PASSWORD", ""))
    args = ap.parse_args()
    password = args.password or secrets.token_urlsafe(18)
    # This machine paints and composes itself: never forward to another GPU server,
    # and free its own picture model's card before composing.
    os.environ.pop("GPU_SERVER_URL", None)
    os.environ["IMAGE_BACKEND"] = pictures_backend()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(Jobs(), password))
    h = health()
    print(f"GPU server listening on http://localhost:{args.port}")
    name = "ComfyUI" if h["pictures_backend"] == "comfyui" else "Forge"
    print(f"  Pictures: {name + ' is ready' if h['pictures'] else h['pictures_why']}")
    print(f"  Music:    {'the composer is set up' if h['composer'] else 'not set up (bash tools/gm-music-compose.sh setup)'}")
    print()
    print("Give the GM these two lines (the link comes from the tunnel):")
    print("  GPU_SERVER_URL=<the https link cloudflared prints>")
    print(f"  GPU_SERVER_PASSWORD={password}")
    print()
    print(f"Tunnel, in another window:  cloudflared tunnel --url http://localhost:{args.port}")
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
