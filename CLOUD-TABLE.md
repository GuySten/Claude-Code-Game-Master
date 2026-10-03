# Cloud Table: Claude hosts the game

Normally the host runs the game on their own computer and friends open a link to it
([GAME-NIGHT.md](GAME-NIGHT.md)). With the Cloud Table, the game runs in a **Claude Code
cloud session** (claude.ai/code) instead, and nobody's computer has to stay on as the
server. Players get the same table page: the party panel, character sheets, fair dice,
music, pictures, hover cards, the Narrator and the players' chat.

- [How it works](#how-it-works)
- [What you need](#what-you-need)
- [Pictures and music from your laptop's GPU](#pictures-and-music-from-your-laptops-gpu)
- [Each game night](#each-game-night)
- [What's different from hosting at home](#whats-different-from-hosting-at-home)
- [For the GM: the turn loop](#for-the-gm-the-turn-loop)

---

## How it works

A cloud session can't accept incoming connections, so players can't open a link to it.
Instead:

- **The table is a claude.ai Artifact**: a private web page the host shares with the
  players. It is the same page as at home (`lib/table_page.html`), with a small transport
  (`lib/table_cloud.js`) in place of the server connection.
- **Players → GM.** When a player acts (or takes a seat, rolls a character, asks the
  Narrator), the page saves the request in the Artifact's database and makes a tiny
  update to the Artifact. That update wakes the GM's session.
- **GM → players.** The session runs the table server exactly as at home
  (`gm-table.sh start`), replays the players' requests into it, and writes what each
  player should see back to the Artifact's database (`tools/gm-cloud.sh`). Open pages
  follow the database live.
- **Campaign saves** go to a private git repository of your own (for example
  `dnd-campaigns`), through `GM_WORLD_STATE_BASE`. The cloud session's disk is temporary.
- **Pictures and music** are made on your laptop's graphics card, if you want them:
  the session sends the jobs to a small server on your laptop (below).

## What you need

- A claude.ai account with Claude Code on the web, and this repository in the session.
- A private repository for the campaign saves, added to the session too.
- Players: a claude.ai account each. Share the table Artifact with them with **edit**
  access (its Share menu): edit access is what lets their page send actions. Anyone
  with view access can watch.
- Optional: a laptop with an NVIDIA GPU for pictures and composed music.

## Pictures and music from your laptop's GPU

The laptop does the same work it does at home ([GAME-NIGHT.md](GAME-NIGHT.md), steps 5
and 6). Set those up first: Forge with `--api` and a model, and the music composer.
Then, on the laptop, in the game folder:

```bash
bash tools/gm-gpu-server.sh                       # prints a password; keep the window open
cloudflared tunnel --url http://localhost:7861    # in a second window; prints an https link
```

Give the GM the two lines to put in the session's `.env`:

```
GPU_SERVER_URL=https://something-random.trycloudflare.com
GPU_SERVER_PASSWORD=the password gm-gpu-server.sh printed
```

- **The password protects your GPU.** Anyone with the link and the password can make
  pictures and music on it. To keep the same password every night, put
  `GPU_SERVER_PASSWORD=...` in the laptop's `.env`.
- **The link changes** each time cloudflared starts a quick tunnel. A free named Cloudflare
  tunnel gives a fixed one.
- **Start Forge first** (`run.bat`), then `gm-gpu-server.sh`. Its first lines say whether
  Forge and the composer are ready.
- Jobs run one at a time and take turns on the card, as at home. A tunnel drops any
  request longer than about 100 seconds, so the session submits a job and collects it
  when it's done.

Without the laptop, the game plays fine in words, with the music library and the built-in
sounds.

## Each game night

1. Laptop (optional): Forge, `gm-gpu-server.sh` and the tunnel, as above.
2. In the cloud session, tell Claude: *"Host the cloud table tonight"* (with the GPU
   link and password if the laptop is on). Claude starts the table and publishes or
   reopens the Artifact.
3. Share the Artifact with the players (edit access). They open it, pick or create a
   character, and play.
4. End the night as usual: *"let's stop here for tonight."* Claude saves the session and
   commits the campaign to your private repository.

## What's different from hosting at home

- **A short delay.** A player's action reaches the GM when the session wakes up, and the
  story arrives when the GM has written it: usually well under a minute, plus the time
  the GM spends on the turn. The page shows "Sent to the GM" meanwhile.
- **No microphone.** The browser doesn't allow it inside an Artifact. Typing works as
  usual. Reading aloud uses the browser's own voices: on Microsoft Edge they include a
  natural Hebrew voice.
- **Pages refresh** when another player sends an action. What you were typing is kept.
- **The players' chat** is stored in the Artifact's database. The GM never reads it, as at
  home.

## For the GM: the turn loop

Everything below runs in the cloud session. `gm-cloud.sh` keeps its state in
`<campaign>/table/cloud/`. `$WORK` is a scratch folder.

**Setup (once per session):**

1. Campaign storage: clone the saves repository and set `GM_WORLD_STATE_BASE` to it in
   `.env`, with the GPU lines if the host gave them. Then `/gm` as usual.
2. `bash tools/gm-table.sh start` (the same server as at home; its link isn't used).
3. `bash tools/gm-cloud.sh page $WORK/table.html` and publish that file as an Artifact
   with capabilities `{"artifact": {}, "db": {}, "assets": {}}`. Use the same Artifact
   every night: publish to its URL. Then `bash tools/gm-cloud.sh set-url <url>`.
4. `bash tools/gm-cloud.sh push $WORK/out`, and store the printed documents with ONE
   ArtifactData `batch` per printed line.

**Each wake** (a player's page updated the Artifact, or a check-in):

1. ArtifactData `query` on collection `rq` with the query `gm-cloud.sh` printed last
   (`status` prints it again), `out_dir: $WORK/saved`.
2. `bash tools/gm-cloud.sh sync $WORK/saved $WORK/out`: replays the requests into the
   table, then prints the batch writes (store them) and the round:
   - `ROUND READY`: `gm-table.sh wait` and play the turn exactly as in CLAUDE.md
     (`say`, `--mood`, rolls...). Then `gm-cloud.sh push $WORK/out` and store the batch.
   - `ROUND OPEN until …`: end the turn. If nobody else acts, a check-in at that time
     (send_later) closes the round.
   - `Nothing for the GM yet.`: a seat, a roll, a Narrator question. The batch already
     carries the answer.
3. `[UPLOAD FIRST]` instead of writes: upload the listed files as assets of the Artifact
   (Artifact publish with `asset: true`), record each with
   `gm-cloud.sh uploaded FILE=URL`, then push again.
4. At the end of the night, commit and push the saves repository.

Never read the `chat` collection: the players' table talk is theirs.
