// table_cloud.js: the online table's page, served from a claude.ai Artifact.
//
// When Claude hosts the game from a cloud session (CLOUD-TABLE.md) nothing can
// connect to the machine the table server runs on. So the page (table_page.html,
// unchanged) talks to this transport instead of to the server, and the GM
// session relays (lib/cloud_table.py):
//
//   GM -> players   the Artifact's database: collection "gm" holds snapshots of
//                   what the table server would answer (messages, party, sheets,
//                   cards, answers to requests). Pages follow it live.
//   players -> GM   collection "rq": one document per request the page makes
//                   (an action, a seat, a roll...). The HOST's own page (the
//                   Artifact's owner) watches "rq" and wakes the GM's session
//                   (published as "wake") through the host's "Claude Code
//                   Remote" connector. Other players' pages never publish
//                   anything: a new page version would reload every open view.
//   players' chat   collection "chat", written and read by the players' pages only.
//
// It sets window.tableTransport before the page's own script runs.
(function () {
  "use strict";
  const BLANK = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==";
  const RESPONSE_WAIT_MS = 4 * 60 * 1000;
  const st = {
    msgs: new Map(), rev: 0, pub: null, views: {}, seats: {}, sheets: {}, sheetTr: {},
    lore: {}, narr: {}, resp: {}, media: {}, chat: [], wake: null,
  };
  let db = null, mcp = null, readOnly = false, readyResolve;
  let isHost = Promise.resolve(false);
  const ready = new Promise((r) => { readyResolve = r; });
  const waiters = new Map();          // request id -> resolve(response)

  const norm = (s) => String(s || "").trim().replace(/\s+/g, " ").toLowerCase();
  const rid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  const session = {
    get(k) { try { return JSON.parse(sessionStorage.getItem("gmcloud." + k)); } catch (e) { return null; } },
    set(k, v) { try { v == null ? sessionStorage.removeItem("gmcloud." + k)
                                : sessionStorage.setItem("gmcloud." + k, JSON.stringify(v)); } catch (e) {} },
  };

  // ---------------------------------------------------- a small notice ---
  let pill = null, pillTimer = 0;
  function notice(text, ms) {
    if (!pill) {
      pill = document.createElement("div");
      pill.setAttribute("role", "status");
      pill.style.cssText = "position:fixed;left:50%;bottom:calc(84px + env(safe-area-inset-bottom,0px));" +
        "transform:translateX(-50%);z-index:50;max-width:min(92vw,420px);padding:8px 14px;border-radius:999px;" +
        "background:var(--panel,#fffaf0);color:var(--ink,#2b2620);border:1px solid var(--line,#e2d8c6);" +
        "font:14px/1.3 system-ui,sans-serif;box-shadow:0 2px 10px rgba(0,0,0,.15);text-align:center";
      document.body.appendChild(pill);
    }
    clearTimeout(pillTimer);
    pill.textContent = text || "";
    pill.hidden = !text;
    if (text && ms) pillTimer = setTimeout(() => { pill.hidden = true; }, ms);
  }
  const outstanding = new Map();      // request id -> when it was sent
  const PENDING_MAX_MS = 5 * 60 * 1000;
  function updatePending() {
    if (readOnly) return;
    notice(outstanding.size ? "⏳ Sent to the GM — it reaches the table in a moment" : "");
  }

  // ------------------------------------------- what the GM published ---
  function apply(doc) {
    (doc.msgs || []).forEach((m) => {
      st.msgs.set(m.id, m);
      st.rev = Math.max(st.rev, m.rev || 0);
    });
    if (typeof doc.rev === "number") st.rev = Math.max(st.rev, doc.rev);
    if (doc.pub) st.pub = doc.pub;
    if (doc.wake) st.wake = doc.wake;
    Object.assign(st.views, doc.views || {});
    Object.assign(st.seats, doc.seats || {});
    Object.assign(st.sheets, doc.sheets || {});
    Object.assign(st.sheetTr, doc.sheet_tr || {});
    Object.assign(st.narr, doc.narrator || {});
    Object.assign(st.media, doc.media || {});
    Object.entries(doc.lore || {}).forEach(([pc, cards]) => { st.lore[pc] = Object.assign(st.lore[pc] || {}, cards); });
    Object.entries(doc.responses || {}).forEach(([id, r]) => {
      st.resp[id] = r;
      if (outstanding.delete(id)) { savePending(); updatePending(); }
      const w = waiters.get(id);
      if (w) { waiters.delete(id); w(r); }
    });
  }

  async function connect() {
    const use = window.claude && window.claude.use;
    if (!use) { readOnly = true; return readyResolve(); }
    let user;
    [db, mcp, user] = await Promise.all([use("db"), use("mcp").catch(() => null),
                                         use("user").catch(() => null)]);
    isHost = user ? user.isOwner().catch(() => false) : Promise.resolve(false);
    if (!db) { readOnly = true; return readyResolve(); }
    let base = 0;
    try {
      const last = await db.collection("gm").orderBy("seq", "desc").limit(1).get();
      if (!last.empty) base = last.docs[0].data().base || 0;
    } catch (e) {}
    const seen = new Set();
    let first = true;
    db.collection("gm").where("seq", ">=", base).orderBy("seq").onSnapshot((snap) => {
      const fresh = snap.docs.filter((d) => !seen.has(d.id));
      fresh.sort((a, b) => (a.data().seq || 0) - (b.data().seq || 0));
      fresh.forEach((d) => { seen.add(d.id); apply(d.data() || {}); });
      if (first) { first = false; resumePending(); readyResolve(); }
    }, () => { if (first) { first = false; readyResolve(); } });
    db.collection("chat").orderBy("t").onSnapshot((snap) => {
      st.chat = snap.docs.map((d, i) => Object.assign({ id: i + 1 }, d.data(), { id: i + 1 })).slice(-200);
    }, () => {});
    if (await isHost) relay();
  }
  // The host's page: every player's request that the GM hasn't answered wakes the
  // GM's session (again after a while, should a wake have been missed).
  function relay() {
    const woke = new Map();             // request id -> when we last woke the GM for it
    let latest = [];
    const check = () => {
      const now = Date.now();
      const due = latest.filter((r) => r && r.id && !st.resp[r.id] && now - (r.t || 0) < 15 * 60 * 1000
                                       && now - (woke.get(r.id) || 0) > 90 * 1000);
      if (!due.length) return;
      due.forEach((r) => woke.set(r.id, now));
      wakeSession(true);
    };
    db.collection("rq").where("t", ">", Date.now() - 15 * 60 * 1000).onSnapshot((snap) => {
      latest = snap.docs.map((d) => d.data());
      check();
    }, () => {});
    setInterval(check, 20 * 1000);
  }
  // After a reload: our requests still unanswered once the GM's answers have loaded
  // (a ring lost to someone else's, or to the reload itself). Recent ones ring
  // again, once; anything older than a few minutes is dropped, not re-sent forever.
  function resumePending() {
    const now = Date.now();
    const pending = (session.get("pending") || []).filter((p) => p && p.id && !st.resp[p.id]
                                                          && now - p.t < PENDING_MAX_MS);
    pending.forEach((p) => outstanding.set(p.id, p.t));
    savePending();
    if (pending.length) { updatePending(); ring(); }
  }
  function savePending() {
    session.set("pending", Array.from(outstanding, ([id, t]) => ({ id, t })));
  }
  connect().catch(() => { readOnly = true; readyResolve(); });

  // --------------------------------------------------- to the GM ---
  let ringTimer = 0, lastWake = 0, wakeOff = false;
  async function wakeSession(force) {
    // Only the host's own page can reach the GM's session, through their "Claude
    // Code Remote" connector (anyone else would just be asked for a connector).
    if (!mcp || wakeOff || !st.wake || !st.wake.session_id || !(await isHost)) return;
    if (!force && Date.now() - lastWake < 8000) return;
    lastWake = Date.now();
    try {
      await mcp.callTool("Claude Code Remote", "send_message", {
        session_id: st.wake.session_id,
        message: "Cloud table: players' requests are waiting in the Artifact (collection rq). " +
                 "Run the turn loop from CLOUD-TABLE.md (For the GM: Each wake).",
      });
    } catch (e) {
      const code = e && e.code;
      if (code && code !== "upstream_error" && code !== "rate_limited") wakeOff = true;
    }
  }
  function ring() {
    clearTimeout(ringTimer);
    // (another player's request reaches the GM through the host's page)
    ringTimer = setTimeout(() => wakeSession(), 400);
  }

  async function send(path, body, client) {
    const id = rid();
    const clean = Object.assign({}, body || {});
    delete clean.code; delete clean.token;
    try {
      await db.collection("rq").doc(id).set({ id, t: Date.now(), path, body: clean, client: client || "" });
    } catch (e) {
      readOnly = true;
      notice("You can watch this table. To play, ask the host to give you edit access.");
      throw e;
    }
    outstanding.set(id, Date.now());
    savePending();
    updatePending();
    ring();
    return id;
  }
  function answer(id) {
    if (st.resp[id]) return Promise.resolve(st.resp[id]);
    return new Promise((resolve) => {
      waiters.set(id, resolve);
      setTimeout(() => {
        if (waiters.delete(id)) resolve({ ok: false, error: "The GM hasn't picked this up yet. Try again in a minute." });
      }, RESPONSE_WAIT_MS);
    });
  }

  // ------------------------------------------- the page's requests ---
  function infoFor(me) {
    const v = (me && st.views[me] && st.views[me].info) || st.pub || { party: [] };
    const out = Object.assign({}, v, { ok: true, me: me || null, tts: false, server_now: Date.now() / 1000 });
    // A track whose file hasn't reached the Artifact yet: silence until it has. The
    // page only (re)starts music when the track changes, so it must never see a
    // track it can't load.
    const m = out.music;
    if (m && m.kind === "file" && m.src && !st.media["music/" + m.src]) out.music = {};
    return out;
  }
  const visible = (m, me) => !m.to || (me && norm(m.to) === norm(me));
  const sheetKey = (me, pc) => norm(me) + "|" + norm(pc);

  async function api(path, body, ctx) {
    await ready;
    const u = new URL(path, "https://table.invalid");
    const q = u.searchParams, p = u.pathname;
    const token = (ctx && ctx.token) || "";
    const me = (token && st.seats[token]) || null;
    if (!db) return { ok: false, error: "Open this table signed in to claude.ai to play." };

    if (!body) {
      if (p === "/api/info") return infoFor(me);
      if (p === "/api/messages") {
        const after = +q.get("after") || 0, rev = +q.get("rev") || 0;
        const messages = Array.from(st.msgs.values())
          .filter((m) => visible(m, me) && (m.id > after || (rev && (m.rev || 0) > rev)))
          .sort((a, b) => a.id - b.id);
        return { ok: true, me, rev: st.rev, messages };
      }
      if (!me) return { ok: false, error: "Take a seat first." };
      if (p === "/api/narrator") return { ok: true, entries: st.narr[me] || [] };
      if (p === "/api/chat") {
        const after = +q.get("after") || 0;
        return { ok: true, messages: st.chat.filter((m) => m.id > after) };
      }
      if (p === "/api/lore") {
        const card = (st.lore[me] || {})[norm(q.get("term"))];
        return card ? Object.assign({ ok: true }, card) : { ok: false, error: "Nothing known about that yet." };
      }
      if (p === "/api/sheet") {
        const s = st.sheets[sheetKey(me, q.get("pc"))];
        return s ? Object.assign({ ok: true }, s) : { ok: false, error: "No such character." };
      }
      if (p === "/api/sheet-tr") {
        const s = st.sheetTr[sheetKey(me, q.get("pc"))];
        return s ? Object.assign({ ok: true }, s) : { ok: false, error: "Not translated yet." };
      }
      return { ok: false, error: "not found" };
    }

    if (readOnly) return { ok: false, error: "You can watch this table. To play, ask the host to give you edit access." };
    if (p === "/api/chat") {          // the players' own table talk: never through the GM
      if (!me) return { ok: false, error: "Take a seat first." };
      const text = String(body.text || "").replace(/\s+/g, " ").trim();
      if (!text) return { ok: false, error: "Say something." };
      const doc = { t: Date.now(), pc: me, text: text.slice(0, 500) };
      await db.collection("chat").doc(rid()).set(doc);
      return { ok: true, message: Object.assign({ id: st.chat.length + 1 }, doc) };
    }
    if (p === "/api/create" || p === "/api/claim") {
      const client = "c_" + rid() + rid();
      const r = await answer(await send(p, body, client));
      if (r.ok && r.pc) st.seats[client] = r.pc;
      return r;
    }
    if (p === "/api/say") {
      if (!me) return { ok: false, error: "Take a seat first." };
      await send(p, body, token);
      return { ok: true, message: { id: 0, kind: "player", pc: me, text: body.text } };
    }
    if (p === "/api/lang" || p === "/api/edit" || p === "/api/leave") {
      await send(p, body, token);
      return { ok: true };
    }
    // Rolling a character, the Narrator, levelling up: the table's answer, when it comes.
    return answer(await send(p, body, token));
  }

  function media(dir, name) {
    return st.media[dir + "/" + name] || (dir === "images" ? BLANK : "");
  }

  // Inside an Artifact the browser refuses the microphone and confirm() dialogs:
  // no push-to-talk button that can't work, and "Leave seat" leaves.
  try { window.SpeechRecognition = undefined; window.webkitSpeechRecognition = undefined; } catch (e) {}
  const hide = document.createElement("style");
  hide.textContent = "#mic, label:has(> #autosend) { display: none !important; }";
  document.head.appendChild(hide);
  window.confirm = () => true;

  window.tableTransport = { code: "cloud", api, media };
})();
