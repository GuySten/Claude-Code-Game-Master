#!/usr/bin/env python3
"""Pictures and composed music made on ANOTHER computer's graphics card.

When the game runs somewhere without a GPU (a computer without a graphics card),
the host's own laptop can still do the painting and the composing: it runs
``bash tools/gm-gpu-server.sh`` (lib/gpu_server.py) next to Forge, behind an
https tunnel, and this machine sends it jobs.

    GPU_SERVER_URL=https://something.trycloudflare.com
    GPU_SERVER_PASSWORD=the password gm-gpu-server.sh printed

A job is submitted, then fetched when it's done (``run``): a tunnel drops any
single request that takes longer than about 100 seconds, and a picture on a
laptop GPU, or a piece of music, can take longer than that.
"""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

POLL_SECONDS = 2.0
# The laptop unreachable this long while a job runs (its tunnel closed, WSL or the
# laptop went down): give up instead of waiting out the whole job timeout.
LOST_AFTER_SECONDS = 45.0


class GpuRemoteError(Exception):
    pass


def url() -> str:
    return os.environ.get("GPU_SERVER_URL", "").strip().rstrip("/")


def enabled() -> bool:
    return bool(url())


def _call(method: str, path: str, data: Optional[dict] = None, timeout: float = 30) -> Dict[str, Any]:
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url() + path, data=body, method=method, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + os.environ.get("GPU_SERVER_PASSWORD", ""),
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise GpuRemoteError("the GPU server refused the password: check GPU_SERVER_PASSWORD") from e
        try:
            detail = json.loads(e.read().decode("utf-8")).get("error") or ""
        except Exception:
            detail = ""
        raise GpuRemoteError(f"the GPU server answered {e.code}: {detail or 'error'}") from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise GpuRemoteError(f"can't reach the GPU server at {url()} — is the laptop's "
                             f"gm-gpu-server.sh and its tunnel running? ({getattr(e, 'reason', e)})") from e


_health: Dict[str, Any] = {"at": 0.0, "value": None}


def health(max_age: float = 30) -> Optional[Dict[str, Any]]:
    """What the laptop can do now ({forge, forge_why, composer, device}); None if it
    doesn't answer. Cached for ``max_age`` seconds: the table asks often."""
    if not enabled():
        return None
    if time.time() - _health["at"] < max_age:
        return _health["value"]
    try:
        value = _call("GET", "/health", timeout=8)
    except GpuRemoteError:
        value = None
    _health.update(at=time.time(), value=value)
    return value


def run(kind: str, payload: Optional[dict] = None, timeout: float = 1800) -> Dict[str, Any]:
    """Run one job on the laptop and return its result (raises GpuRemoteError)."""
    if not enabled():
        raise GpuRemoteError("GPU_SERVER_URL is not set")
    job = _call("POST", "/jobs", {"kind": kind, "payload": payload or {}})
    job_id = job.get("id")
    if not job_id:
        raise GpuRemoteError(job.get("error") or "the GPU server took no job")
    deadline = time.time() + timeout
    lost_since = None
    while time.time() < deadline:
        time.sleep(POLL_SECONDS)
        try:
            state = _call("GET", "/jobs/" + job_id, timeout=30)
            lost_since = None
        except GpuRemoteError as e:
            # A dropped poll: the job keeps running there. Gone for long: give up.
            lost_since = lost_since or time.time()
            if time.time() - lost_since >= LOST_AFTER_SECONDS:
                raise GpuRemoteError(f"lost the laptop's GPU server during the {kind} job: {e}") from e
            continue
        if state.get("status") == "done":
            return state.get("result") or {}
        if state.get("status") == "failed":
            raise GpuRemoteError(state.get("error") or "the job failed on the laptop")
    raise GpuRemoteError(f"the laptop didn't finish the {kind} job in {timeout:.0f} s")
