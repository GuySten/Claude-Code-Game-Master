#!/usr/bin/env python3
"""
The online table — let every player join from their own computer.

One host runs Claude Code as the GM. ``gm-table.sh start`` launches this small
web server (standard library only, no extra installs). Each player opens the
link in a browser, enters the table code, and either takes an existing player
character or creates a new one (seated via the same ``join`` path as
``gm-player.sh join``). Players type actions; the GM reads them with
``gm-table.sh wait`` / ``inbox`` and posts narration back with
``gm-table.sh say``. Every browser sees the story live.

The server is the ONLY writer of the table log, so the GM-side commands talk
to it over localhost (authenticated with a host key kept in
``<campaign>/table/server.json``) rather than touching files directly.

Files (all under ``<campaign>/table/``):
  log.jsonl     every message (player actions, GM narration, joins)
  seats.json    browser seat token -> player character name
  gm-cursor     id of the last message the GM has read
  server.json   port, table code, host key, pid (written by `serve`)
"""

import argparse
import hmac
import json
import os
import secrets
import signal
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).parent))

import party_roster
from campaign_manager import CampaignManager
from character_schema import to_flat

MAX_TEXT = 4000            # longest single message (GM narration can be long)
MAX_PLAYER_TEXT = 1200     # longest player action
MAX_BODY = 16 * 1024
DEFAULT_PORT = 8765
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".webp": "image/webp", ".gif": "image/gif"}
CODE_WORDS = ["ember", "raven", "lantern", "goblin", "dragon", "tavern", "rune",
              "owlbear", "mimic", "dagger", "torch", "crypt", "griffin", "potion"]


def table_dir(campaign_dir) -> Path:
    return Path(campaign_dir).resolve() / "table"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


# ============================================================ table state ====

class TableState:
    """Messages + seats for one campaign table. Thread-safe; single process."""

    def __init__(self, campaign_dir: Path, world_state_base: str):
        self.campaign_dir = Path(campaign_dir).resolve()
        self.base = world_state_base
        self.dir = table_dir(self.campaign_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.dir / "log.jsonl"
        self.seats_path = self.dir / "seats.json"
        self.cursor_path = self.dir / "gm-cursor"
        self.lock = threading.Lock()
        self.messages: List[Dict[str, Any]] = []
        if self.log_path.exists():
            for line in self.log_path.read_text(encoding="utf-8").splitlines():
                try:
                    self.messages.append(json.loads(line))
                except ValueError:
                    continue
        self.seats: Dict[str, str] = self._read_json(self.seats_path, {})
        try:
            self.gm_cursor = int(self.cursor_path.read_text().strip())
        except (OSError, ValueError):
            self.gm_cursor = self.messages[-1]["id"] if self.messages else 0

    @staticmethod
    def _read_json(path: Path, default):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return default

    def _write_seats(self) -> None:
        tmp = self.seats_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.seats, indent=2), encoding="utf-8")
        tmp.replace(self.seats_path)

    # --- messages ---
    def append(self, kind: str, text: str, pc: Optional[str] = None,
               to: Optional[str] = None, image: Optional[str] = None) -> Dict[str, Any]:
        with self.lock:
            msg = {"id": (self.messages[-1]["id"] + 1) if self.messages else 1,
                   "ts": _now(), "kind": kind, "text": text}
            if pc:
                msg["pc"] = pc
            if to:
                msg["to"] = to
            if image:
                msg["image"] = image
            self.messages.append(msg)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
            return msg

    def visible_to(self, msg: Dict[str, Any], pc: Optional[str]) -> bool:
        """Private messages (GM whispers, a player's aside to the GM) are seen
        only by the PC they concern."""
        to = msg.get("to")
        if not to:
            return True
        return pc is not None and party_roster._same_name(to, pc)

    def since(self, after: int, pc: Optional[str]) -> List[Dict[str, Any]]:
        with self.lock:
            return [m for m in self.messages if m["id"] > after and self.visible_to(m, pc)]

    def gm_unread(self, mark: bool) -> List[Dict[str, Any]]:
        with self.lock:
            unread = [m for m in self.messages
                      if m["id"] > self.gm_cursor and m["kind"] in ("player", "system")]
            if mark and self.messages:
                self.gm_cursor = self.messages[-1]["id"]
                self.cursor_path.write_text(str(self.gm_cursor))
            return unread

    def waiting_on(self) -> List[str]:
        """Seated PCs who have not acted since the GM last spoke."""
        with self.lock:
            last_gm = max((m["id"] for m in self.messages if m["kind"] == "gm"), default=0)
            acted = {party_roster.slugify(m.get("pc", "")) for m in self.messages
                     if m["id"] > last_gm and m["kind"] == "player"}
            seated = []
            for name in dict.fromkeys(self.seats.values()):
                if party_roster.slugify(name) not in acted:
                    seated.append(name)
            return seated

    # --- seats ---
    def pc_for(self, token: Optional[str]) -> Optional[str]:
        if not token:
            return None
        with self.lock:
            name = self.seats.get(token)
        if name and party_roster.find_pc(self.campaign_dir, name) is None:
            return None  # the PC left the table (or died and was replaced)
        return name

    def claimed_by_anyone(self, name: str) -> bool:
        return any(party_roster._same_name(n, name) for n in self.seats.values())

    def claim(self, name: str) -> Dict[str, Any]:
        path = party_roster.find_pc(self.campaign_dir, name)
        if path is None:
            return {"ok": False, "error": f"No player character named {name}."}
        real = (party_roster._read(path) or {}).get("name", name)
        with self.lock:
            if self.claimed_by_anyone(real):
                return {"ok": False, "error": f"{real} is already being played. Ask the "
                                              f"host to free the seat if that was you."}
            token = secrets.token_urlsafe(18)
            self.seats[token] = real
            self._write_seats()
        return {"ok": True, "token": token, "pc": real}

    def release(self, token: str) -> Optional[str]:
        with self.lock:
            name = self.seats.pop(token, None)
            self._write_seats()
        return name

    def free(self, name: str) -> bool:
        with self.lock:
            tokens = [t for t, n in self.seats.items() if party_roster._same_name(n, name)]
            for t in tokens:
                del self.seats[t]
            self._write_seats()
        return bool(tokens)

    # --- party view ---
    def party(self) -> List[Dict[str, Any]]:
        out = []
        for path, raw in party_roster.all_pcs(self.campaign_dir):
            c = to_flat(raw)
            hp = c.get("hp") or {}
            out.append({
                "name": c.get("name", path.stem),
                "lead": path.name == party_roster.LEAD_FILE,
                "level": c.get("level", 1),
                "race": c.get("race", ""), "class": c.get("class", ""),
                "concept": c.get("concept", ""),
                "hp": hp.get("current", 0), "hp_max": hp.get("max", 0),
                "status": c.get("status", "alive"),
                "conditions": c.get("conditions", []),
                "claimed": self.claimed_by_anyone(c.get("name", "")),
            })
        return out

    def overview(self) -> Dict[str, Any]:
        o = self._read_json(self.campaign_dir / "campaign-overview.json", {})
        return {"campaign": o.get("campaign_name") or self.campaign_dir.name,
                "location": (o.get("player_position") or {}).get("current_location"),
                "time": o.get("time_of_day")}

    def create_pc(self, mode: str, name: str, concept: str) -> Dict[str, Any]:
        from identity_onboarding import IdentityOnboarding
        onboarding = IdentityOnboarding(self.base)
        if mode == "nameless":
            result = onboarding.join("nameless")
        else:
            result = onboarding.join("original", name=name, concept=concept)
        if not result.get("success"):
            return {"ok": False, "error": result.get("error", "could not create character")}
        return {"ok": True, "pc": result["character"].get("name", name)}


# ============================================================ HTTP layer =====

def make_handler(state: TableState, code: str, host_key: str):
    page = (Path(__file__).parent / "table_page.html").read_text(encoding="utf-8")

    class Handler(BaseHTTPRequestHandler):
        server_version = "GMTable/1.0"

        def log_message(self, fmt, *args):  # keep the host's terminal quiet
            pass

        # --- helpers ---
        def _send(self, status: int, body: bytes, ctype: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data: Any, status: int = 200) -> None:
            self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")

        def _err(self, msg: str, status: int = 400) -> None:
            self._json({"ok": False, "error": msg}, status)

        def _body(self) -> Dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise ValueError("request too large")
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(data, dict):
                raise ValueError("expected a JSON object")
            return data

        def _code_ok(self, supplied: Optional[str]) -> bool:
            return hmac.compare_digest(str(supplied or "").strip().lower(), code.lower())

        def _is_host(self) -> bool:
            return hmac.compare_digest(self.headers.get("X-Host-Key", ""), host_key)

        # --- routes ---
        def do_GET(self):
            url = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            if url.path in ("/", "/index.html"):
                return self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
            if url.path.startswith("/images/"):
                if not self._code_ok(q.get("code")):
                    return self._err("bad table code", 403)
                return self._image(url.path[len("/images/"):])
            if url.path.startswith("/api/gm/"):
                if not self._is_host():
                    return self._err("host only", 403)
                if url.path == "/api/gm/pending":
                    return self._json({"ok": True,
                                       "unread": len(state.gm_unread(mark=False)),
                                       "waiting_on": state.waiting_on(),
                                       "seated": sorted(set(state.seats.values()))})
                return self._err("not found", 404)
            if not self._code_ok(q.get("code")):
                return self._err("bad table code", 403)
            me = state.pc_for(q.get("token"))
            if url.path == "/api/info":
                return self._json({"ok": True, "me": me, "party": state.party(),
                                   "waiting_on": state.waiting_on(), **state.overview()})
            if url.path == "/api/messages":
                try:
                    after = int(q.get("after", 0))
                except ValueError:
                    after = 0
                return self._json({"ok": True, "me": me, "messages": state.since(after, me)})
            return self._err("not found", 404)

        def do_POST(self):
            url = urlparse(self.path)
            try:
                data = self._body()
            except (ValueError, UnicodeDecodeError) as e:
                return self._err(str(e))
            if url.path.startswith("/api/gm/"):
                if not self._is_host():
                    return self._err("host only", 403)
                return self._gm(url.path, data)
            if not self._code_ok(data.get("code")):
                return self._err("bad table code", 403)

            if url.path == "/api/claim":
                result = state.claim(str(data.get("pc", "")))
                if result["ok"]:
                    state.append("system", f"{result['pc']} takes their seat at the table.",
                                 pc=result["pc"])
                return self._json(result, 200 if result["ok"] else 409)

            if url.path == "/api/create":
                name = " ".join(str(data.get("name", "")).split())[:60]
                concept = " ".join(str(data.get("concept", "")).split())[:200]
                mode = "nameless" if data.get("mode") == "nameless" else "original"
                if mode == "original" and not name:
                    return self._err("Give your character a name.")
                created = state.create_pc(mode, name, concept)
                if not created["ok"]:
                    return self._json(created, 409)
                result = state.claim(created["pc"])
                if result["ok"]:
                    line = f"A new player joins: {created['pc']}"
                    line += f" — {concept}." if concept else "."
                    state.append("system", line, pc=created["pc"])
                return self._json(result, 200 if result["ok"] else 409)

            me = state.pc_for(data.get("token"))
            if url.path == "/api/say":
                if not me:
                    return self._err("Take a seat first.", 403)
                text = str(data.get("text", "")).strip()
                if not text:
                    return self._err("Say something.")
                if len(text) > MAX_PLAYER_TEXT:
                    return self._err(f"Keep it under {MAX_PLAYER_TEXT} characters.")
                private = bool(data.get("private"))
                msg = state.append("player", text, pc=me, to=me if private else None)
                return self._json({"ok": True, "message": msg})

            if url.path == "/api/leave":
                name = state.release(str(data.get("token", "")))
                if name:
                    state.append("system", f"{name} steps away from the table.", pc=name)
                return self._json({"ok": True})
            return self._err("not found", 404)

        def _gm(self, path: str, data: Dict[str, Any]):
            if path == "/api/gm/inbox":
                return self._json({"ok": True, "messages": state.gm_unread(mark=True),
                                   "waiting_on": state.waiting_on()})
            if path == "/api/gm/say":
                text = str(data.get("text", "")).strip()
                image = data.get("image")
                if image:
                    image = Path(str(image)).name
                    if not (state.campaign_dir / "images" / image).is_file():
                        return self._err(f"no image named {image} in the campaign's images/")
                if not text and not image:
                    return self._err("nothing to say")
                if len(text) > MAX_TEXT * 4:
                    return self._err("narration too long; split it into beats")
                to = data.get("to")
                if to:
                    path_ = party_roster.find_pc(state.campaign_dir, str(to))
                    if path_ is None:
                        return self._err(f"no player character named {to}")
                    to = (party_roster._read(path_) or {}).get("name", to)
                msg = state.append("gm", text, to=to or None, image=image)
                return self._json({"ok": True, "message": msg})
            if path == "/api/gm/free":
                freed = state.free(str(data.get("pc", "")))
                return self._json({"ok": True, "freed": freed})
            return self._err("not found", 404)

        def _image(self, name: str):
            name = Path(name).name
            path = state.campaign_dir / "images" / name
            ctype = IMAGE_TYPES.get(path.suffix.lower())
            if not ctype or not path.is_file():
                return self._err("not found", 404)
            return self._send(200, path.read_bytes(), ctype)

    return Handler


# ============================================================ host side ======

def _lan_ip() -> str:
    """Best guess at this machine's LAN address (no packet is sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def _active_campaign() -> tuple:
    mgr = CampaignManager()
    camp = mgr.get_active_campaign_dir()
    if camp is None:
        sys.exit("[ERROR] No active campaign. Pick one with gm-campaign.sh switch <name>.")
    return Path(camp).resolve(), str(mgr.world_state_dir)


def _server_info(campaign_dir: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads((table_dir(campaign_dir) / "server.json").read_text())
    except (OSError, ValueError):
        return None


def _alive(pid: Optional[int]) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError):
        return False


def serve(port: int, bind: str, code: Optional[str]) -> None:
    campaign_dir, base = _active_campaign()
    info = _server_info(campaign_dir)
    if info and _alive(info.get("pid")) and info.get("pid") != os.getpid():
        sys.exit(f"[ERROR] The table is already open (pid {info['pid']}, port {info['port']}). "
                 f"Use gm-table.sh stop first.")
    code = (code or f"{secrets.choice(CODE_WORDS)}-{secrets.randbelow(900) + 100}").lower()
    host_key = secrets.token_urlsafe(24)
    state = TableState(campaign_dir, base)
    httpd = ThreadingHTTPServer((bind, port), make_handler(state, code, host_key))
    httpd.daemon_threads = True
    lan = _lan_ip()
    record = {"port": port, "bind": bind, "code": code, "host_key": host_key,
              "pid": os.getpid(), "started": _now(),
              "local_url": f"http://localhost:{port}/",
              "lan_url": f"http://{lan}:{port}/"}
    info_path = table_dir(campaign_dir) / "server.json"
    info_path.write_text(json.dumps(record, indent=2))
    try:
        os.chmod(info_path, 0o600)
    except OSError:
        pass
    print(f"TABLE OPEN for campaign '{campaign_dir.name}'")
    print(f"  On this computer:   {record['local_url']}")
    print(f"  Same Wi-Fi/network: {record['lan_url']}")
    print(f"  Table code:         {code}")
    print("  Over the internet:  expose this port with a tunnel (see gm-table.sh help)")
    sys.stdout.flush()

    def _shutdown(*_):
        threading.Thread(target=httpd.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, _shutdown)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        current = _server_info(campaign_dir)
        if current and current.get("pid") == os.getpid():
            info_path.unlink(missing_ok=True)


def _call(campaign_dir: Path, method: str, path: str, data: Optional[dict] = None) -> dict:
    info = _server_info(campaign_dir)
    if not info or not _alive(info.get("pid")):
        sys.exit("[ERROR] The table is not open. Start it with: bash tools/gm-table.sh start")
    req = urllib.request.Request(
        f"http://127.0.0.1:{info['port']}{path}", method=method,
        data=json.dumps(data).encode("utf-8") if data is not None else None,
        headers={"X-Host-Key": info["host_key"], "Content-Type": "application/json"})
    # The host talks to its own server directly, never through an HTTP proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except ValueError:
            return {"ok": False, "error": f"HTTP {e.code}"}
    except urllib.error.URLError as e:
        sys.exit(f"[ERROR] Could not reach the table server: {e.reason}")


def _print_messages(messages: List[dict], waiting_on: List[str]) -> None:
    if not messages:
        print("(no new player messages)")
    for m in messages:
        if m["kind"] == "system":
            print(f"[#{m['id']} JOIN/LEAVE] {m['text']}")
        else:
            aside = " (private, to GM only)" if m.get("to") else ""
            print(f"[#{m['id']} {m.get('pc', '?')}{aside}] {m['text']}")
    if waiting_on:
        print(f"Still waiting on: {', '.join(waiting_on)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Online table for remote players")
    sub = parser.add_subparsers(dest="action")

    p = sub.add_parser("serve", help="Run the table server in the foreground")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--bind", default="0.0.0.0", help="Address to listen on (default all)")
    p.add_argument("--code", help="Table code players must enter (default: random)")

    sub.add_parser("status", help="Is the table open? URLs, code, seats")
    sub.add_parser("inbox", help="Print unread player messages and mark them read")

    w = sub.add_parser("wait", help="Block until players act, then print their messages")
    w.add_argument("--timeout", type=int, default=540, help="Give up after N seconds")
    w.add_argument("--settle", type=float, default=4.0,
                   help="After the first message, wait this long for others to chime in")
    w.add_argument("--all", action="store_true",
                   help="Wait until EVERY seated player has acted (or timeout)")

    s = sub.add_parser("say", help="Post GM narration to every player's screen")
    s.add_argument("text", nargs="?", help="The narration (or use --stdin)")
    s.add_argument("--stdin", action="store_true", help="Read the narration from stdin")
    s.add_argument("--to", help="Whisper to one player character only")
    s.add_argument("--image", help="Attach an image from the campaign's images/ folder")

    f = sub.add_parser("free", help="Free a player's seat so they can rejoin from another device")
    f.add_argument("pc")

    sub.add_parser("stop", help="Close the table")

    args = parser.parse_args()
    if args.action == "serve":
        return serve(args.port, args.bind, args.code)

    campaign_dir, _ = _active_campaign()

    if args.action == "status":
        info = _server_info(campaign_dir)
        if not info or not _alive(info.get("pid")):
            print("The table is closed. Open it with: bash tools/gm-table.sh start")
            return
        pending = _call(campaign_dir, "GET", "/api/gm/pending")
        print(f"TABLE OPEN (pid {info['pid']}) for campaign '{campaign_dir.name}'")
        print(f"  On this computer:   {info['local_url']}")
        print(f"  Same Wi-Fi/network: {info['lan_url']}")
        print(f"  Table code:         {info['code']}")
        print(f"  Seated players:     {', '.join(pending.get('seated') or []) or '(nobody yet)'}")
        print(f"  Unread actions:     {pending.get('unread', 0)}")
        return

    if args.action == "inbox":
        r = _call(campaign_dir, "POST", "/api/gm/inbox", {})
        return _print_messages(r.get("messages", []), r.get("waiting_on", []))

    if args.action == "wait":
        deadline = time.time() + args.timeout
        first_seen = None
        while time.time() < deadline:
            r = _call(campaign_dir, "GET", "/api/gm/pending")
            if r.get("unread"):
                if args.all:
                    if not r.get("waiting_on"):
                        break
                else:
                    first_seen = first_seen or time.time()
                    if time.time() - first_seen >= args.settle or not r.get("waiting_on"):
                        break
            time.sleep(1.0)
        r = _call(campaign_dir, "POST", "/api/gm/inbox", {})
        if not r.get("messages"):
            print(f"(no player messages after {args.timeout}s — run wait again)")
            return
        return _print_messages(r["messages"], r.get("waiting_on", []))

    if args.action == "say":
        text = sys.stdin.read() if args.stdin else (args.text or "")
        r = _call(campaign_dir, "POST", "/api/gm/say",
                  {"text": text.strip(), "to": args.to, "image": args.image})
        if not r.get("ok"):
            sys.exit(f"[ERROR] {r.get('error')}")
        m = r["message"]
        print(f"POSTED #{m['id']}" + (f" (whisper to {m['to']})" if m.get("to") else
                                       " to the whole table"))
        return

    if args.action == "free":
        r = _call(campaign_dir, "POST", "/api/gm/free", {"pc": args.pc})
        print(f"Freed {args.pc}'s seat." if r.get("freed") else f"{args.pc} had no seat.")
        return

    if args.action == "stop":
        info = _server_info(campaign_dir)
        if not info or not _alive(info.get("pid")):
            print("The table is already closed.")
            (table_dir(campaign_dir) / "server.json").unlink(missing_ok=True)
            return
        os.kill(int(info["pid"]), signal.SIGTERM)
        for _ in range(50):
            if not _alive(info["pid"]):
                break
            time.sleep(0.1)
        print("The table is closed.")
        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
