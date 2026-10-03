#!/usr/bin/env python3
"""The online table, hosted by Claude from a cloud session (CLOUD-TABLE.md).

A cloud session can't take incoming connections, so players can't reach the
table server directly. Instead the players' page (table_page.html with
table_cloud.js) runs as a claude.ai Artifact, and this module is the GM
session's half of the relay. The table server runs here exactly as it does at
home (``gm-table.sh start``), and the GM plays with the same commands.

    page OUT                 Build the Artifact's page
    pull DIR                 Replay the players' requests (saved from the Artifact's
                             "rq" collection into DIR/rq/) into the table server
    media                    Pictures and music the table shows that aren't uploaded yet
    uploaded FILE=URL ...    Record where uploaded files live in the Artifact
    push OUT [--full]        What the players should see now, as "gm" documents:
                             prints the ArtifactData batch writes for them
    sync DIR OUT             pull, then push: one step per wake
    status                   The Artifact, the last request seen, what to do next
    set-url URL              Remember the Artifact's link
    set-session ID           The GM's session: pages message it directly to wake it

The relay keeps its state in <campaign>/table/cloud/bridge.json. It never reads
the players' "chat" collection: their table talk is theirs (CLAUDE.md).
"""

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from campaign_manager import CampaignManager  # noqa: E402

LIB = Path(__file__).resolve().parent
PROJECT_ROOT = LIB.parent
DOC_BYTES = 200_000            # under the database's 256 KiB per document
BATCH_WRITES, BATCH_BYTES = 50, 900_000
FULL_EVERY = 100               # a full snapshot this often keeps a late joiner's load small
CLOCK_SLACK_MS = 10 * 60 * 1000  # players' clocks differ: look this far back, dedupe by id
KEEP_IDS = 1000
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")
AUDIO_EXT = (".mp3", ".ogg", ".wav", ".m4a", ".flac", ".opus")
# What the page asks and only gets an answer to through the GM's relay.
PLAYER_POSTS = {"/api/claim", "/api/create", "/api/roll-character", "/api/say", "/api/edit",
                "/api/narrator", "/api/level-up", "/api/lang", "/api/leave"}


class Bridge:
    def __init__(self, campaign_dir: Path):
        self.campaign_dir = Path(campaign_dir).resolve()
        self.dir = self.campaign_dir / "table" / "cloud"
        self.path = self.dir / "bridge.json"
        try:
            self.state = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.state = {}
        for k, v in (("tokens", {}), ("done_ids", []), ("after", 0), ("seq", 0), ("base", 0),
                     ("msg_max", 0), ("rev", 0), ("hashes", {}), ("media", {}), ("outbox", {})):
            self.state.setdefault(k, v)

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    # ------------------------------------------------ the table server ---
    def server(self) -> Dict[str, Any]:
        try:
            return json.loads((self.campaign_dir / "table" / "server.json").read_text())
        except (OSError, ValueError):
            sys.exit("[ERROR] The table is not open. Start it with: bash tools/gm-table.sh start")

    def call(self, method: str, path: str, data: Optional[dict] = None, token: Optional[str] = None,
             query: Optional[dict] = None, host: bool = False, timeout: float = 30) -> Dict[str, Any]:
        info = self.server()
        if method == "GET":
            params = {"code": info["code"], **({"token": token} if token else {}), **(query or {})}
            path = path + "?" + urllib.parse.urlencode(params)
            body = None
        else:
            body = json.dumps({**(data or {}), "code": info["code"],
                               **({"token": token} if token else {})}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if host:
            headers["X-Host-Key"] = info["host_key"]
        req = urllib.request.Request(f"http://127.0.0.1:{info['port']}{path}", data=body,
                                     method=method, headers=headers)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode("utf-8"))
            except ValueError:
                return {"ok": False, "error": f"HTTP {e.code}"}
        except (urllib.error.URLError, OSError) as e:
            return {"ok": False, "error": f"the table server didn't answer ({getattr(e, 'reason', e)})"}

    def seated(self) -> Dict[str, str]:
        """client token -> PC for every page that holds a seat now."""
        try:
            seats = json.loads((self.campaign_dir / "table" / "seats.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            seats = {}
        return {c: seats[s] for c, s in self.state["tokens"].items() if s in seats}

    # ------------------------------------------------------ requests in ---
    def pull(self, directory: Path) -> List[str]:
        """Replay the saved requests into the table server, oldest first. Returns a
        line per request for the GM."""
        reqs = []
        for f in sorted(Path(directory).glob("**/*.json")):
            try:
                doc = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(doc, dict) and isinstance(doc.get("data"), dict) and "path" not in doc:
                doc = doc["data"]                   # a saved document wrapped with its metadata
            if isinstance(doc, dict) and doc.get("id") and doc.get("path"):
                reqs.append(doc)
        reqs.sort(key=lambda r: (r.get("t") or 0, str(r["id"])))
        done = set(self.state["done_ids"])
        lines = []
        for r in reqs:
            rid = str(r["id"])
            if rid in done:
                continue
            done.add(rid)
            self.state["done_ids"].append(rid)
            self.state["after"] = max(self.state["after"], int(r.get("t") or 0))
            lines.append(self._relay(rid, r))
        del self.state["done_ids"][:-KEEP_IDS]
        self.save()
        return lines

    def _reseat(self, path: str, body: Dict[str, Any], viewer: str) -> Optional[str]:
        """The same person asking again for the character they play, from a new tab
        (a reload, another device): free the old tab's seat so this one takes it.
        Returns the PC, or None unless this viewer is the one who played it last."""
        name = str(body.get("pc") or body.get("name") or "").strip()
        if not viewer or not name or self.state.setdefault("owners", {}).get(_norm(name)) != viewer:
            return None
        party = self.call("GET", "/api/info").get("party") or []
        pc = next((p.get("name") for p in party if _norm(p.get("name")) == _norm(name)), None)
        if not pc:
            return None
        held = [c for c, seated in self.seated().items() if _norm(seated) == _norm(pc)]
        if held:
            self.call("POST", "/api/gm/free", {"pc": pc}, host=True)
            for c in held:
                self.state["tokens"].pop(c, None)
        return pc

    def _relay(self, rid: str, r: Dict[str, Any]) -> str:
        path, client = str(r["path"]), str(r.get("client") or "")
        viewer = str(r.get("viewer") or "")
        body = r.get("body") if isinstance(r.get("body"), dict) else {}
        body = {k: v for k, v in body.items() if k not in ("code", "token")}
        if path in ("/api/create", "/api/claim"):
            again = self._reseat(path, body, viewer)
            if again:                          # (their own character: take it back)
                path, body = "/api/claim", {"pc": again}
        if path not in PLAYER_POSTS:
            resp = {"ok": False, "error": "not found"}
        else:
            token = None if path in ("/api/create", "/api/claim") else self.state["tokens"].get(client)
            if path == "/api/leave":
                body["token"] = token or ""
            resp = self.call("POST", path, body, token=token,
                             timeout=180 if path in ("/api/narrator", "/api/level-up") else 30)
            if path in ("/api/create", "/api/claim") and resp.get("ok") and resp.get("token"):
                self.state["tokens"][client] = resp["token"]
                if viewer:                     # who plays it: theirs to take back
                    self.state.setdefault("owners", {})[_norm(resp.get("pc"))] = viewer
                resp = {**resp, "token": client}
            if path == "/api/leave":
                self.state["tokens"].pop(client, None)
        self.state["outbox"][rid] = resp
        who = (resp.get("pc") if path in ("/api/create", "/api/claim") else None) or \
            self.seated().get(client) or "someone"
        what = {"/api/say": "acts", "/api/create": "joins", "/api/claim": "takes a seat",
                "/api/roll-character": "rolls a character", "/api/narrator": "asks the Narrator",
                "/api/level-up": "levels up", "/api/lang": "sets their language",
                "/api/edit": "fixes their action", "/api/leave": "leaves"}.get(path, path)
        note = "" if resp.get("ok") else f" — refused: {resp.get('error')}"
        return f"[{who}] {what}{note}"

    def next_query(self) -> Dict[str, Any]:
        """The ArtifactData query that fetches requests not relayed yet."""
        return {"where": [["t", ">", max(0, int(self.state["after"]) - CLOCK_SLACK_MS)]],
                "order_by": {"field": "t", "direction": "asc"}, "limit": 1000}

    def round_note(self) -> str:
        p = self.call("GET", "/api/gm/pending", host=True)
        if not p.get("ok"):
            return "Table: " + str(p.get("error"))
        rnd = p.get("round") or {}
        if not p.get("unread"):
            return "Nothing for the GM yet."
        if rnd.get("open") or rnd.get("settling"):
            until = time.strftime("%H:%M:%S UTC", time.gmtime(rnd.get("deadline") or time.time()))
            waiting = ", ".join(rnd.get("waiting_on") or []) or "a typo grace period"
            return (f"ROUND OPEN until {until} (waiting on {waiting}). Push, then end the turn; "
                    f"if no one else acts, a check-in at {until} closes it.")
        return "ROUND READY — run: bash tools/gm-table.sh wait"

    # ------------------------------------------------- what players see ---
    def snapshot(self, everything: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """(what the pages should show, the message marks to remember). Messages are
        the ones new or changed since the last push, or all of them (``everything``)."""
        seats = self.seated()
        by_pc: Dict[str, str] = {}
        for client, pc in seats.items():
            by_pc.setdefault(pc, self.state["tokens"][client])
        items: Dict[str, Dict[str, Any]] = {k: {} for k in
                                            ("views", "narrator", "sheets", "sheet_tr", "lore", "ui")}
        msgs: Dict[int, Dict[str, Any]] = {}
        after, rev = (0, 0) if everything else (self.state["msg_max"], self.state["rev"])
        pub = self.call("GET", "/api/info")
        pub.pop("ok", None)
        pub.pop("me", None)
        # Every language the adventure is played in: a player who switches finds
        # their cards, sheets and the page's own words already there.
        langs = [x["code"] for x in pub.get("languages") or [] if x.get("code")] or ["en"]
        for lang in langs:
            ui = self.call("GET", "/api/ui", query={"lang": lang}, timeout=10)
            if ui.get("ok") and lang not in ("en", "he") and ui.get("strings"):
                items["ui"][lang] = ui["strings"]
        top_rev = self.state["rev"]
        for token in [None] + list(by_pc.values()):
            got = self.call("GET", "/api/messages", token=token, query={"after": after, "rev": rev})
            for m in got.get("messages") or []:
                msgs[m["id"]] = m
            top_rev = max(top_rev, int(got.get("rev") or 0))
        for pc, token in by_pc.items():
            info = self.call("GET", "/api/info", token=token)
            info.pop("ok", None)
            terms = {lang: self.call("GET", "/api/info", token=token, query={"lang": lang}).get("lore_terms")
                     or [] for lang in langs}
            items["views"][pc] = {"info": info, "terms": terms}
            items["narrator"][pc] = self.call("GET", "/api/narrator", token=token).get("entries") or []
            for member in info.get("party") or []:
                name = member.get("name")
                if not name:
                    continue
                key = f"{_norm(pc)}|{_norm(name)}"
                sheet = self.call("GET", "/api/sheet", token=token, query={"pc": name})
                if sheet.get("ok"):
                    sheet.pop("ok")
                    items["sheets"][key] = sheet
                for lang in langs:
                    tr = self.call("GET", "/api/sheet-tr", token=token,
                                   query={"pc": name, "lang": lang}, timeout=60)
                    if tr.get("ok") and tr.get("tr"):
                        tr.pop("ok")
                        items["sheet_tr"][f"{key}|{lang}"] = tr
            for lang in langs:
                cards = {}
                for term in terms[lang]:
                    word = term.get("term") if isinstance(term, dict) else term
                    if not word:
                        continue
                    card = self.call("GET", "/api/lore", token=token,
                                     query={"term": word, "lang": lang}, timeout=4)
                    if card.get("ok"):
                        card.pop("ok")
                        cards[_norm(word)] = card
                items["lore"][f"{pc}|{lang}"] = cards
        full = {"pub": pub, "seats": {c: seats.get(c) for c in self.state["tokens"]},
                "msgs": msgs, "rev": top_rev, **items}
        return full, {"msg_max": max([self.state["msg_max"]] + list(msgs)), "rev": top_rev}

    def referenced_media(self, full: Dict[str, Any]) -> Dict[str, Path]:
        """'images/x.png' / 'music/y.ogg' -> the file, for everything shown."""
        found: Dict[str, Path] = {}
        for key, value in _walk(full):
            if not isinstance(value, str):
                continue
            low = value.lower()
            if key in ("image", "portrait") and low.endswith(IMAGE_EXT):
                f = self.campaign_dir / "images" / Path(value).name
                if f.is_file():
                    found["images/" + value] = f
            elif key in ("src", "track", "file") and low.endswith(AUDIO_EXT):
                f = self.find_music(value)
                if f:
                    found["music/" + value] = f
        return found

    def find_music(self, name: str) -> Optional[Path]:
        direct = [self.campaign_dir / "music" / name, PROJECT_ROOT / "music" / name]
        for f in direct:
            if f.is_file():
                return f
        wanted = Path(name).name.lower()
        for d in (self.campaign_dir / "music", PROJECT_ROOT / "music",
                  self.campaign_dir / "music" / "themes", self.campaign_dir / "music" / "anthems"):
            if d.is_dir():
                for f in sorted(d.iterdir()):
                    if f.is_file() and f.name.lower() == wanted:
                        return f
        return None

    def missing_media(self, full: Optional[Dict[str, Any]] = None) -> Dict[str, Path]:
        full = full if full is not None else self.snapshot(everything=True)[0]
        return {k: f for k, f in self.referenced_media(full).items()
                if self.state["media"].get(k, {}).get("sha") != _sha_file(f)}

    def record_uploads(self, pairs: Iterable[str]) -> List[str]:
        """FILE=URL pairs from an asset upload -> remembered under every key that
        file is shown as."""
        done = []
        wanted = self.referenced_media(self.snapshot(everything=True)[0])
        for pair in pairs:
            file, _, url = pair.partition("=")
            path = Path(file).resolve()
            if not url or not path.is_file():
                sys.exit(f"[ERROR] expected FILE=URL with an existing file, got: {pair}")
            keys = [k for k, f in wanted.items() if f.resolve() == path] or \
                   [("music/" if path.suffix.lower() in AUDIO_EXT else "images/") + path.name]
            for k in keys:
                self.state["media"][k] = {"url": url, "sha": _sha_file(path)}
                done.append(k)
        self.save()
        return done

    def push(self, out_dir: Path, full_push: bool = False, anyway: bool = False) -> List[List[Dict[str, Any]]]:
        """Write this turn's "gm" documents into out_dir; return the batches of
        ArtifactData writes that store them."""
        first = self.state["seq"] + 1
        full_push = full_push or self.state["seq"] == 0 or first - self.state["base"] >= FULL_EVERY
        full, marks = self.snapshot(everything=full_push)
        missing = self.missing_media(full)
        if missing and not anyway:
            raise MediaMissing(missing)
        hashes = {} if full_push else dict(self.state["hashes"])
        parts: List[Tuple[str, Any, Any]] = []      # (field, key, value)
        if full_push or _changed(hashes, "pub", full["pub"]):
            parts.append(("pub", None, full["pub"]))
        wake = {"session_id": self.state["session"]} if self.state.get("session") else None
        if wake and (full_push or _changed(hashes, "wake", wake)):
            parts.append(("wake", None, wake))
        for c, pc in full["seats"].items():
            if _changed(hashes, "seat|" + c, pc):
                parts.append(("seats", c, pc))
        for mid in sorted(full["msgs"]):
            parts.append(("msgs", None, full["msgs"][mid]))
        for field in ("views", "narrator", "sheets", "sheet_tr", "lore", "ui"):
            for k, v in full[field].items():
                if _changed(hashes, f"{field}|{k}", v):
                    parts.append((field, k, v))
        for k, rec in self.state["media"].items():
            if _changed(hashes, "media|" + k, rec["url"]):
                parts.append(("media", k, rec["url"]))
        for rid, resp in self.state["outbox"].items():
            parts.append(("responses", rid, resp))

        docs: List[Dict[str, Any]] = []
        cur: Dict[str, Any] = {}
        size = 0
        for field, key, value in parts:
            n = len(json.dumps(value, ensure_ascii=False).encode("utf-8")) + 64
            if cur and size + n > DOC_BYTES:
                docs.append(cur)
                cur, size = {}, 0
            if field == "msgs":
                cur.setdefault("msgs", []).append(value)
            elif key is None:
                cur[field] = value
            else:
                cur.setdefault(field, {})[key] = value
            size += n
        if cur or not docs:
            docs.append(cur)
        base = first if full_push else self.state["base"]
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        writes = []
        for i, doc in enumerate(docs):
            seq = first + i
            doc.update(seq=seq, base=base, at=time.time(), full=full_push)
            f = out_dir / f"gm-{seq:08d}.json"
            f.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            writes.append({"op": "set", "collection": "gm", "doc_id": f"s{seq:08d}",
                           "file_path": str(f.resolve()), "_bytes": f.stat().st_size})
        self.state.update(seq=first + len(docs) - 1, base=base, hashes=hashes, outbox={}, **marks)
        self.save()
        batches, cur_b, cur_n = [], [], 0
        for w in writes:
            n = w.pop("_bytes")
            if cur_b and (len(cur_b) >= BATCH_WRITES or cur_n + n > BATCH_BYTES):
                batches.append(cur_b)
                cur_b, cur_n = [], 0
            cur_b.append(w)
            cur_n += n
        if cur_b:
            batches.append(cur_b)
        return batches


class MediaMissing(Exception):
    def __init__(self, missing: Dict[str, Path]):
        super().__init__(f"{len(missing)} file(s) to upload first")
        self.missing = missing


def _norm(s: Any) -> str:
    return " ".join(str(s or "").split()).lower()


def _walk(value: Any, key: str = "") -> Iterable[Tuple[str, Any]]:
    if isinstance(value, dict):
        for k, v in value.items():
            yield k, v
            yield from _walk(v, k)
    elif isinstance(value, list):
        for v in value:
            yield from _walk(v, key)


def _sha(value: Any) -> str:
    return hashlib.sha1(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
                        .encode("utf-8")).hexdigest()[:16]


def _sha_file(path: Path) -> str:
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()[:16]


def _changed(hashes: Dict[str, str], key: str, value: Any) -> bool:
    h = _sha(value)
    if hashes.get(key) == h:
        return False
    hashes[key] = h
    return True


# ------------------------------------------------------------ the page ---
def build_page() -> str:
    """table_page.html as an Artifact's content: its title, styles and body, with
    table_cloud.js running before the page's own script."""
    html = (LIB / "table_page.html").read_text(encoding="utf-8")
    strings = json.loads((LIB / "table_strings.json").read_text(encoding="utf-8"))
    html = html.replace("/*TABLE_STRINGS*/", json.dumps(strings, ensure_ascii=False) + " || ", 1)
    head = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
    body = re.search(r"<body[^>]*>(.*)</body>", html, re.S).group(1)
    title = re.search(r"<title>.*?</title>", head, re.S).group(0)
    styles = "\n".join(re.findall(r"<style>.*?</style>", head, re.S))
    shim = "<script>\n" + (LIB / "table_cloud.js").read_text(encoding="utf-8") + "\n</script>\n"
    at = body.index("<script>")
    return f"{title}\n{styles}\n{body[:at]}{shim}{body[at:]}"


def _campaign_dir() -> Path:
    import os
    camp = CampaignManager(os.environ.get("GM_WORLD_STATE_BASE", "world-state")).get_active_campaign_dir()
    if camp is None:
        sys.exit("[ERROR] No active campaign. Run /gm first (or gm-campaign.sh switch <name>).")
    return Path(camp)


def main() -> None:
    ap = argparse.ArgumentParser(description="The online table, hosted from a cloud session")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("page").add_argument("out")
    sub.add_parser("pull").add_argument("dir")
    sub.add_parser("media")
    up = sub.add_parser("uploaded")
    up.add_argument("pairs", nargs="+", metavar="FILE=URL")
    pu = sub.add_parser("push")
    pu.add_argument("out")
    pu.add_argument("--full", action="store_true", help="Send everything again (a page shows something stale)")
    pu.add_argument("--anyway", action="store_true", help="Push even though some media isn't uploaded")
    sy = sub.add_parser("sync")
    sy.add_argument("dir")
    sy.add_argument("out")
    sub.add_parser("status")
    sub.add_parser("set-url").add_argument("url")
    sub.add_parser("set-session").add_argument("session_id")
    args = ap.parse_args()

    if args.cmd == "page":
        Path(args.out).write_text(build_page(), encoding="utf-8")
        print(f"Page written: {args.out}")
        return
    bridge = Bridge(_campaign_dir())
    if args.cmd == "set-session":
        bridge.state["session"] = args.session_id
        bridge.save()
        print(f"Pages will wake session {args.session_id} directly (next push)")
    elif args.cmd == "set-url":
        bridge.state["url"] = args.url
        bridge.save()
        print(f"Artifact: {args.url}")
    elif args.cmd == "pull":
        lines = bridge.pull(Path(args.dir))
        print("\n".join(lines) if lines else "No new requests.")
        print(bridge.round_note())
    elif args.cmd == "media":
        missing = bridge.missing_media()
        for k, f in missing.items():
            print(f"{f}\t{k}")
        if not missing:
            print("Everything shown is uploaded.")
    elif args.cmd == "uploaded":
        for k in bridge.record_uploads(args.pairs):
            print(f"recorded {k}")
    elif args.cmd in ("push", "sync"):
        if args.cmd == "sync":
            lines = bridge.pull(Path(args.dir))
            print("\n".join(lines) if lines else "No new requests.")
        try:
            batches = bridge.push(Path(args.out), getattr(args, "full", False), getattr(args, "anyway", False))
        except MediaMissing as e:
            print("[UPLOAD FIRST] the table shows files the players can't load yet. Upload them as "
                  "assets of the Artifact, record each with `gm-cloud.sh uploaded FILE=URL`, then push:")
            for k, f in e.missing.items():
                print(f"  {f}\t({k})")
            sys.exit(3)
        print(f"{sum(len(b) for b in batches)} document(s) for collection \"gm\" "
              f"(seq {bridge.state['seq']}). ArtifactData batch writes:")
        for b in batches:
            print(json.dumps(b))
        if args.cmd == "sync":
            print(bridge.round_note())
        print("Next requests query: " + json.dumps(bridge.next_query()))
    elif args.cmd == "status":
        print(f"Artifact: {bridge.state.get('url') or '(not set: gm-cloud.sh set-url URL)'}")
        print(f"Seated pages: {len(bridge.seated())} · gm documents: {bridge.state['seq']}")
        print("Requests query (ArtifactData query, collection \"rq\"): " + json.dumps(bridge.next_query()))
        print(bridge.round_note())


if __name__ == "__main__":
    main()
