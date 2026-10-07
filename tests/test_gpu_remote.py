"""The host laptop's GPU, lent to a game hosted elsewhere (lib/gpu_server.py and
lib/gpu_remote.py): pictures made over the network."""

import base64
import threading
from http.server import ThreadingHTTPServer

import pytest

from lib import image_gen  # noqa: F401  (puts lib/ on the path, as the game does)
from tests.test_image_forge import PNG, forge  # noqa: F401  (a fake Forge)

import gpu_remote
import gpu_server


@pytest.fixture
def laptop(forge, monkeypatch):
    """gm-gpu-server.sh running next to the fake Forge, and this side pointed at it."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), gpu_server.make_handler(gpu_server.Jobs(), "s3cret"))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.delenv("IMAGE_BACKEND", raising=False)
    monkeypatch.setenv("GPU_SERVER_URL", f"http://127.0.0.1:{httpd.server_address[1]}")
    monkeypatch.setenv("GPU_SERVER_PASSWORD", "s3cret")
    monkeypatch.setattr(gpu_remote, "POLL_SECONDS", 0.02)
    gpu_remote._health.update(at=0.0, value=None)
    yield forge
    httpd.shutdown()
    httpd.server_close()


def test_pictures_are_painted_on_the_laptop(laptop):
    assert image_gen.backend() == "remote"
    ok, source, why = image_gen.images_status()
    assert (ok, source) == (True, "remote") and "host's GPU" in why
    out = image_gen.generate_image("A cozy tavern at night", title="The Crooked Lantern")
    sent = laptop["seen"]["requests"][0]
    # The laptop's Forge gets the same request a local one would.
    assert (sent["width"], sent["height"], sent["steps"]) == (1216, 832, 6)
    assert "ink and watercolor" in sent["prompt"]
    assert open(out["path"], "rb").read() == PNG and out["cost"] == 0.0


def test_a_wrong_password_is_refused(laptop, monkeypatch):
    monkeypatch.setenv("GPU_SERVER_PASSWORD", "guess")
    with pytest.raises(gpu_remote.GpuRemoteError, match="password"):
        gpu_remote.run("warmup")
    gpu_remote._health.update(at=0.0, value=None)
    assert image_gen.images_status()[0] is False


def test_no_laptop_means_no_pictures_not_a_crash(monkeypatch):
    monkeypatch.delenv("IMAGE_BACKEND", raising=False)
    monkeypatch.setenv("GPU_SERVER_URL", "http://127.0.0.1:9")          # nothing listening
    gpu_remote._health.update(at=0.0, value=None)
    ok, source, why = image_gen.images_status()
    assert (ok, source) == (False, "remote") and "isn't answering" in why


def test_the_laptop_never_forwards_its_own_jobs(monkeypatch):
    """A laptop whose .env also names a GPU server still uses its own card."""
    monkeypatch.setenv("GPU_SERVER_URL", "http://127.0.0.1:9")
    monkeypatch.delenv("IMAGE_BACKEND", raising=False)
    seen = []
    monkeypatch.setattr(gpu_server.image_gen, "_forge_generate", lambda *a: seen.append(a) or (PNG, "m", "64x64"))
    result = gpu_server.run_job("image", {"prompt": "x"})
    assert seen and base64.b64decode(result["image"]) == PNG


def test_the_laptop_does_pictures_only(laptop):
    assert "composer" not in gpu_server.health()
    with pytest.raises(ValueError, match="unknown job kind"):
        gpu_server.run_job("compose", {"prompt": "x", "seconds": 1})


def test_a_laptop_that_goes_away_mid_job_is_given_up_quickly(laptop, monkeypatch):
    """The tunnel or the laptop dies while a picture is painting: fail in seconds,
    not after the whole job timeout."""
    import time
    monkeypatch.setattr(gpu_remote, "LOST_AFTER_SECONDS", 0.2)
    real = gpu_remote._call

    def flaky(method, path, data=None, timeout=30):
        if method == "GET" and path.startswith("/jobs/"):
            raise gpu_remote.GpuRemoteError("the GPU server answered 530: error")
        return real(method, path, data, timeout)

    monkeypatch.setattr(gpu_remote, "_call", flaky)
    started = time.time()
    with pytest.raises(gpu_remote.GpuRemoteError, match="lost the laptop"):
        gpu_remote.run("warmup", timeout=600)
    assert time.time() - started < 5
