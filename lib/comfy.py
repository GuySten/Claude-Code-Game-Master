#!/usr/bin/env python3
"""Pictures from a local ComfyUI (IMAGE_BACKEND=comfyui).

ComfyUI runs models as a graph of nodes. The game sends it one of two graphs:

- the built-in text-to-image graph: checkpoint -> prompt and negative prompt ->
  sampler -> decode. COMFY_* settings tune it (defaults suit an SDXL "Lightning"
  model, like the Forge defaults); COMFY_GUIDANCE adds Flux's guidance node.
- your own workflow (COMFY_WORKFLOW): in ComfyUI, "Export (API)" saves it as
  JSON. Write {{prompt}}, {{negative}}, {{seed}}, {{width}}, {{height}},
  {{steps}}, {{cfg}}, {{sampler}}, {{scheduler}}, {{model}} or {{guidance}}
  where the game's values go. A value that is exactly a placeholder gets the
  right type (a number for {{seed}}).

The picture comes back through ComfyUI's history and /view; nothing is saved in
ComfyUI's output folder (the graph ends in a preview node).
"""

import json
import os
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple

POLL_SECONDS = 0.5


class ComfyError(Exception):
    pass


def url() -> str:
    return os.environ.get("COMFY_URL", "http://127.0.0.1:8188").rstrip("/")


def _open(req, timeout: float):
    # A local server: never through a proxy configured for the internet.
    return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout)


def _call(path: str, data: Any = None, timeout: float = 30) -> Any:
    req = urllib.request.Request(url() + path, method="POST" if data is not None else "GET",
                                 data=json.dumps(data).encode("utf-8") if data is not None else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with _open(req, timeout) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        raise ComfyError(_error_text(e)) from e
    except (urllib.error.URLError, OSError) as e:
        raise ComfyError(f"ComfyUI isn't answering at {url()} — is it running? "
                         f"({getattr(e, 'reason', e)})") from e
    return json.loads(body.decode("utf-8")) if body.strip() else {}


def _error_text(e: urllib.error.HTTPError) -> str:
    try:
        body = json.loads(e.read().decode("utf-8"))
    except Exception:
        return f"ComfyUI error {e.code}"
    err = body.get("error") or {}
    bits = [err.get("message") or "", err.get("details") or ""]
    for node in (body.get("node_errors") or {}).values():
        for ne in node.get("errors") or []:
            bits.append(f"{node.get('class_type', 'node')}: {ne.get('message')} {ne.get('details') or ''}".strip())
    return "ComfyUI refused the picture: " + "; ".join(b for b in bits if b)


def checkpoints() -> List[str]:
    info = _call("/object_info/CheckpointLoaderSimple", timeout=5)
    try:
        return list(info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0])
    except (KeyError, IndexError, TypeError):
        return []


def model() -> str:
    """The checkpoint to use: COMFY_MODEL, else the first ComfyUI lists."""
    chosen = os.environ.get("COMFY_MODEL", "").strip()
    if chosen:
        return chosen
    found = checkpoints()
    if not found:
        raise ComfyError("ComfyUI has no checkpoint — put one in ComfyUI/models/checkpoints")
    return found[0]


def status() -> Tuple[bool, str]:
    """(ready, why) for the ComfyUI at COMFY_URL."""
    try:
        if os.environ.get("COMFY_WORKFLOW"):
            _call("/system_stats", timeout=5)
            return True, f"ComfyUI at {url()} (workflow {Path(os.environ['COMFY_WORKFLOW']).name})"
        found = checkpoints()
    except ComfyError as e:
        return False, str(e)
    chosen = os.environ.get("COMFY_MODEL", "").strip()
    if not found:
        return False, "ComfyUI is running but has no checkpoint — put one in ComfyUI/models/checkpoints"
    if chosen and chosen not in found:
        return False, f"ComfyUI has no checkpoint named {chosen} (COMFY_MODEL); it has: {', '.join(found[:5])}"
    return True, f"ComfyUI at {url()} ({chosen or found[0]})"


def dims(size: str) -> Tuple[int, int]:
    """Requested size (OpenAI terms) -> the size the local model is good at."""
    try:
        w, h = (int(x) for x in str(size).lower().split("x"))
    except ValueError:
        w, h = 1536, 1024
    key, default = (("COMFY_LANDSCAPE", "1216x832") if w > h else
                    ("COMFY_PORTRAIT", "832x1216") if h > w else ("COMFY_SQUARE", "1024x1024"))
    try:
        return tuple(int(x) for x in os.environ.get(key, default).lower().split("x"))
    except ValueError:
        return tuple(int(x) for x in default.split("x"))


def values(prompt: str, quality: str, size: str, avoid: str = "") -> Dict[str, Any]:
    from image_gen import FORGE_NEGATIVE
    w, h = dims(size)
    steps = int(os.environ.get("COMFY_STEPS", "6"))
    if quality == "low":
        steps = max(3, steps - 2)
    elif quality == "high":
        steps += 2
    return {
        "prompt": prompt,
        "negative": ", ".join(x for x in (avoid, os.environ.get("COMFY_NEGATIVE", FORGE_NEGATIVE)) if x),
        "seed": secrets.randbelow(2 ** 32), "width": w, "height": h, "steps": steps,
        "cfg": float(os.environ.get("COMFY_CFG", "2")),
        "sampler": os.environ.get("COMFY_SAMPLER", "dpmpp_sde"),
        "scheduler": os.environ.get("COMFY_SCHEDULER", "karras"),
        "guidance": float(os.environ.get("COMFY_GUIDANCE") or 3.5),
    }


def _fill(node: Any, v: Dict[str, Any]) -> Any:
    if isinstance(node, dict):
        return {k: _fill(x, v) for k, x in node.items()}
    if isinstance(node, list):
        return [_fill(x, v) for x in node]
    if isinstance(node, str):
        whole = re.fullmatch(r"\{\{(\w+)\}\}", node.strip())
        if whole and whole.group(1) in v:
            return v[whole.group(1)]
        return re.sub(r"\{\{(\w+)\}\}", lambda m: str(v.get(m.group(1), m.group(0))), node)
    return node


def workflow(prompt: str, quality: str, size: str, avoid: str = "") -> Tuple[Dict[str, Any], str, int, int]:
    """The graph for one picture -> (graph, model name, w, h)."""
    v = values(prompt, quality, size, avoid)
    custom = os.environ.get("COMFY_WORKFLOW", "").strip()
    if custom:
        try:
            template = json.loads(Path(custom).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise ComfyError(f"can't read COMFY_WORKFLOW {custom}: {e}") from e
        v["model"] = os.environ.get("COMFY_MODEL", "").strip()
        return _fill(template, v), v["model"] or Path(custom).stem, v["width"], v["height"]
    v["model"] = model()
    positive = ["2", 0]
    graph = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": v["model"]}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": v["prompt"], "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": v["negative"], "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage",
              "inputs": {"width": v["width"], "height": v["height"], "batch_size": 1}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "PreviewImage", "inputs": {"images": ["6", 0]}},
    }
    if os.environ.get("COMFY_GUIDANCE"):            # Flux: its guidance, on the prompt
        graph["8"] = {"class_type": "FluxGuidance",
                      "inputs": {"conditioning": ["2", 0], "guidance": v["guidance"]}}
        positive = ["8", 0]
    graph["5"] = {"class_type": "KSampler", "inputs": {
        "model": ["1", 0], "positive": positive, "negative": ["3", 0], "latent_image": ["4", 0],
        "seed": v["seed"], "steps": v["steps"], "cfg": v["cfg"], "sampler_name": v["sampler"],
        "scheduler": v["scheduler"], "denoise": 1.0}}
    return graph, v["model"], v["width"], v["height"]


def run(graph: Dict[str, Any], timeout: float) -> bytes:
    """Queue the graph, wait for it, and return its first picture's bytes."""
    queued = _call("/prompt", {"prompt": graph, "client_id": "gm-table-" + secrets.token_hex(4)})
    prompt_id = queued.get("prompt_id")
    if not prompt_id:
        raise ComfyError("ComfyUI took no picture: " + json.dumps(queued)[:200])
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(POLL_SECONDS)
        entry = (_call("/history/" + prompt_id) or {}).get(prompt_id)
        if not entry:
            continue
        state = entry.get("status") or {}
        if state.get("status_str") == "error":
            why = next((m[1].get("exception_message") for m in state.get("messages") or []
                        if m and m[0] == "execution_error"), None)
            raise ComfyError("ComfyUI failed: " + (why or "the graph stopped with an error").strip())
        for out in (entry.get("outputs") or {}).values():
            for img in out.get("images") or []:
                q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img.get("subfolder", ""),
                                            "type": img.get("type", "output")})
                with _open(urllib.request.Request(url() + "/view?" + q), 120) as r:
                    return r.read()
        if state.get("completed"):
            raise ComfyError("ComfyUI finished without a picture (does the workflow end in an image node?)")
    raise ComfyError(f"ComfyUI didn't finish the picture in {timeout:.0f} s")


def generate(prompt: str, quality: str, size: str, avoid: str = "") -> Tuple[bytes, str, str]:
    """One picture -> (png bytes, model label, WxH)."""
    from gpu_turn import gpu_turn
    graph, name, w, h = workflow(prompt, quality, size, avoid)
    with gpu_turn("pictures"):
        data = run(graph, float(os.environ.get("COMFY_TIMEOUT", "600")))
    return data, "comfyui:" + name, f"{w}x{h}"


def release_gpu() -> bool:
    """Models off the graphics card, so something else can use it (ComfyUI's /free)."""
    try:
        _call("/free", {"unload_models": True, "free_memory": True}, timeout=30)
        return True
    except ComfyError:
        return False


def warm_up() -> bool:
    """Read the picture model in now (one tiny throwaway picture), then free the card."""
    from gpu_turn import gpu_turn
    if not status()[0] or os.environ.get("COMFY_WORKFLOW"):
        return False
    graph, _, _, _ = workflow("warm-up", "low", "64x64")
    graph["4"]["inputs"].update(width=64, height=64)
    graph["5"]["inputs"]["steps"] = 1
    try:
        with gpu_turn("pictures"):
            run(graph, float(os.environ.get("COMFY_TIMEOUT", "600")))
            release_gpu()
        return True
    except ComfyError:
        return False
