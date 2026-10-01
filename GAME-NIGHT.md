# Game Night — setting up an adventure for your group

Claude is the Game Master. One person, **the host**, runs the game on their computer;
everyone else just opens a link in their browser. Players can type or **speak** (English or
Hebrew), **hear the story read aloud**, and the music follows the scene by itself.

- [What your table gets](#what-your-table-gets)
- [The recommended setup at a glance](#the-recommended-setup-at-a-glance)
- [One-time setup (host)](#one-time-setup-host)
- [Each game night (host)](#each-game-night-host)
- [Message to send your friends](#message-to-send-your-friends)
- [Player guide](#player-guide) · [מדריך לשחקנים](#מדריך-לשחקנים)
- [Host cheat sheet](#host-cheat-sheet)
- [Troubleshooting](#troubleshooting)

---

## What your table gets

Everything below works with the basic install. The items marked *optional* need one extra
setup step on the host's computer, and the game plays fine without them.

- **Play from anywhere, in English or Hebrew.** Each player reads, speaks and hears the game in
  their own language; the GM translates the other players' actions.
- **Voice.** Speak your actions; hear the story read aloud (Hebrew in a natural voice).
- **A fair, shared table.** Every die roll is public, with the DC set before the dice land.
  Rounds: the GM answers when everyone has acted, or a minute after the first player did, with
  a countdown for the rest. Mistyped? Fix your action until the GM reads it (always at least 5 seconds).
- **The story, told as it happens.** Narration appears in step with the voice, and HP changes
  land when the story reaches you.
- **Characters.** Roll one at the table; open your full character sheet, in your own language;
  level up from it.
- **Music.** Mood music for every scene, a theme for every villain, battle music for bosses.
  *Optional:* composed themes for main villains and bosses, and a heroic anthem for every player
  character ([step 6](#one-time-setup-host)).
- **Pictures** *(optional)*: places, villains, bosses, treasures, a portrait for every character
  and for the NPCs you keep meeting, collected in a gallery ([step 5](#one-time-setup-host)).
- **Between the players.** A private table-talk chat the GM never sees; a Narrator to ask "what
  happened again?"; hover cards on the names in the story and on every player, which open
  instantly. All of them show only what that player already knows.

---

## The recommended setup at a glance

| Part of the game | Model | Why |
|---|---|---|
| **The GM** — the Claude Code session you play in | **Opus** | Tells the story, follows the rules, keeps the world consistent, writes good Hebrew |
| **Story helpers** — plots, NPCs, places, new characters, rules rulings | **Sonnet** | Need judgment, but run in the background, so faster and cheaper is better |
| **Lookup helpers** — monster stats, spells, gear, loot, image prompts | **Haiku** | Simple, quick jobs |
| **The Narrator and hover cards** — reminding players of the story | **Haiku** | Quick, and can't change the game. Uses your Claude Code login; nothing to set up |
| **Book import** — reading a whole PDF once | **Opus** | Happens once, and it shapes the whole campaign |

The whole recipe, start to finish (each step is explained below):

```bash
git clone https://github.com/GuySten/claude-code-game-master.git
cd claude-code-game-master
./install.sh                          # choose 1) Core only, unless you'll import a book
bash tools/gm-models.sh recommended   # the model set above — run once
bash tools/gm-music-library.sh fetch  # music for every mood
claude                                # then type /gm and say "my friends are joining online"
```

Optional extras, any time later: **pictures** (an OpenAI key, or the free local Forge:
[step 5](#one-time-setup-host)) and **composed music** (`bash tools/gm-music-compose.sh setup`:
[step 6](#one-time-setup-host)).

On **Windows**, the same in PowerShell — no WSL needed:

```powershell
git clone https://github.com/GuySten/claude-code-game-master.git
cd claude-code-game-master
powershell -ExecutionPolicy Bypass -File install.ps1   # also sets the recommended models
uv run python lib/music_library.py fetch                # music for every mood
claude                                                  # then type /gm
```

---

## One-time setup (host)

You need: a Windows, Mac or Linux computer,
[Claude Code](https://docs.anthropic.com/en/docs/claude-code) signed in, and `git`
(on Windows, [Git for Windows](https://git-scm.com/download/win) — Claude Code needs it too).

**1. Get the game and install it**

```bash
git clone https://github.com/GuySten/claude-code-game-master.git
cd claude-code-game-master
./install.sh
```

**On Windows** (natively — no WSL), in PowerShell:

```powershell
git clone https://github.com/GuySten/claude-code-game-master.git
cd claude-code-game-master
powershell -ExecutionPolicy Bypass -File install.ps1
```

It installs what's missing (Git for Windows, uv), the game, and the recommended models.
Afterwards, run the game's `bash tools/...` commands from Claude Code or from **Git Bash**
(Start menu), not plain PowerShell — that's where `bash` means the right thing.

The installer asks what to install:

- **1) Core only** — pick this unless you plan to import a book. Everything for playing
  together works: worlds, characters, the online table, voice, music.
- **2) Core + RAG** — adds importing a PDF/book and smarter memory search. Larger download
  (PyTorch, CPU-only build). You can add it later with `uv sync --extra rag`.

**2. Set the recommended models**

```bash
bash tools/gm-models.sh recommended
```

You should see:

```
✓ Preset 'recommended': Best balance: a top-quality GM, quick helpers in the background.
  GM: opus  ·  story helpers: sonnet  ·  lookup helpers: haiku  ·  book import: opus
```

This does two things:

- **The helpers** — each helper agent gets its model (they already come set this way with
  the game, so this just makes sure).
- **The GM** — saves Opus as the model Claude Code starts with in this folder
  (`.claude/settings.local.json`). This part is **yours only**: it is not in git, so a fresh
  copy of the game doesn't have it until you run the command. Run it once per computer.

Prefer a menu? Start `claude` in the folder and type `/models`. Changed your mind later?
`bash tools/gm-models.sh budget` (Sonnet GM, Haiku helpers — cheapest that still plays well),
`premium` (Opus nearly everywhere — best quality, costs the most), or `recommended` to come
back. `bash tools/gm-models.sh` on its own shows what runs where right now.

**3. Get the music library (recommended)**

```bash
bash tools/gm-music-library.sh fetch
```

Downloads 25 tracks sorted by mood (tavern, travel, mystery, dread, combat, boss, sad,
victory…) into `music/`. Claude picks from them automatically. Without it the table still has
built-in generated sounds for every mood. Credits are shown on screen and in
`music/CREDITS.md` (the license requires them).

Want your own music? Drop `.mp3`/`.ogg` files into `music/` and put the mood in the file
name — `battle-drums.mp3`, `tavern-night.ogg`, `creepy-crypt.mp3`. A file named after a
villain (`grimaldi.mp3`, `grimaldi-boss.mp3`) becomes that villain's theme.

**4. Install a tunnel (only for friends outside your home network)**

Install [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)
(free, no account; on a Mac: `brew install cloudflared`; on Windows:
`winget install --id Cloudflare.cloudflared`). It gives your table an `https://`
link that works from anywhere. **The microphone also needs that https link** — so even
friends on your Wi-Fi need it if they want to talk instead of type.

**5. Pictures (optional)**

The GM can illustrate the adventure: new places, villains, big moments. The players see each
picture on their screens, drawn in one locked art style, with recurring characters looking the
same every time. Without a picture source the game simply plays in words. There are two ways
to make the pictures:

- **OpenAI** (best quality, about $0.04 a picture): put `OPENAI_API_KEY=sk-...` in `.env`.
- **Your own computer** (free and private, needs an NVIDIA graphics card with 6 GB or more,
  e.g. a GTX 1060): a local Stable Diffusion program called **Forge**. Set it up below.

*Local pictures with Forge (Windows + NVIDIA). This is for a 6 GB card like a GTX 1060.*

1. **Update the NVIDIA driver** (GeForce Experience, or nvidia.com → Drivers).
2. **Download Forge**: on the [Forge GitHub page](https://github.com/lllyasviel/stable-diffusion-webui-forge),
   find the **one-click package** download in the README. **GTX 10-series cards (like the 1060)
   need a package built with CUDA 12.1 or 12.4**: newer CUDA 12.8 builds no longer support
   them. Extract it with [7-Zip](https://www.7-zip.org/) into a short path such as `C:\forge`.
3. **Run `update.bat`** once, then **`run.bat`**. The first start downloads a few GB and opens
   `http://127.0.0.1:7860` in your browser. Close it again (the console window too).
4. **Turn on the API** that the game talks to: open `webui\webui-user.bat` in Notepad and
   change the `COMMANDLINE_ARGS` line to:
   ```bat
   set COMMANDLINE_ARGS=--api
   ```
5. **Get the model.** On [Civitai](https://civitai.com) search for **DreamShaper XL**, pick the
   version labelled **Lightning** (DPM++ SDE), and download the `.safetensors` file (about
   6.5 GB). Put it in `webui\models\Stable-diffusion\`. It suits fantasy art, portraits and
   landscapes, and the Lightning version needs only a few steps, which keeps a laptop GPU fast.
6. **Try it in Forge**: run `run.bat` and pick the model in the top-left **Checkpoint** box.
   Use these settings: **Sampling method** DPM++ SDE, **Schedule type** Karras, **Sampling
   steps** 6, **CFG Scale** 2, **Width × Height** 1216 × 832. Type *a cozy fantasy tavern at
   night* and press Generate. The first picture also loads the model, so it can take a few
   minutes. After that, expect roughly 30–60 seconds each on a GTX 1060.
7. **Point the game at Forge**: add this line to `.env` in the game folder:
   ```
   IMAGE_BACKEND=forge
   ```
   The game's defaults match the settings from step 6. They are listed with the other
   options below.
8. **Check it from the game** (Forge must be running):
   ```bash
   bash tools/gm-image.sh generate --title "Test" --prompt "a cozy fantasy tavern at night, warm lantern light"
   ```
   It prints an `open: file://...` link and "made locally (free)". Then restart Claude Code.
   When a session starts, the GM's notes say `Scene images: ENABLED (local Forge ...)`.

**Every game night, start Forge (`run.bat`) before `claude`.** You can close the browser tab
it opens; the console window has to stay open. If Forge isn't running, the game simply plays
without pictures.

Optional `.env` settings for Forge (the defaults suit DreamShaper XL Lightning):

| Setting | Default | What it does |
|---|---|---|
| `FORGE_URL` | `http://127.0.0.1:7860` | Where Forge listens |
| `FORGE_MODEL` | (whatever Forge has loaded) | Checkpoint to use, as named in Forge's Checkpoint box |
| `FORGE_STEPS` | `6` | Sampling steps (the GM's "low" quality uses 2 fewer, "high" 2 more) |
| `FORGE_CFG` | `2` | CFG scale |
| `FORGE_SAMPLER` / `FORGE_SCHEDULER` | `DPM++ SDE` / `Karras` | Sampler and schedule type |
| `FORGE_LANDSCAPE` / `FORGE_PORTRAIT` / `FORGE_SQUARE` | `1216x832` / `832x1216` / `1024x1024` | Picture sizes |
| `FORGE_TIMEOUT` | `600` | Seconds to wait for one picture |

**Too slow, "out of memory", or only 8 GB of RAM?** Use a smaller SD 1.5 model instead
(with 8 GB of RAM, use it from the start: the picture and music models both stay in RAM all
evening, and DreamShaper XL is too big to share): **DreamShaper 8** from
Civitai (about 2 GB), with:
```
FORGE_MODEL=dreamshaper_8
FORGE_LANDSCAPE=768x512
FORGE_PORTRAIT=512x768
FORGE_SQUARE=512x512
FORGE_STEPS=25
FORGE_CFG=7
FORGE_SAMPLER=DPM++ 2M
```
(Use the model's name exactly as Forge shows it.)

**Set the art style** once per campaign (new campaigns get one when the world is created).
Ask the GM *"lock an art style for this campaign"*, or run:
```bash
bash tools/gm-image.sh chronicler --name "Astreus" --style "ink-and-watercolor fantasy illustration" --persona "a wry court scholar"
```

**What gets painted** (all of it in the background, so the story never waits):

- **Scenes.** The GM illustrates big moments as it sees fit: a reveal, a vista, a styled
  flourish. Players can ask for one too ("show me that!").
- **Portraits.** Every player character gets one a minute or two after they join. It's shown to
  everyone, then sits at the top of their character sheet and next to their name in the party
  panel. **Recurring NPCs** get one too: once the story has named someone three times (the
  innkeeper you keep visiting, a rival), their portrait is painted and shown to everyone. The GM
  can paint one sooner (`bash tools/gm-image.sh portrait "<name>"`; you can too).
- **Places.** When the party arrives somewhere the GM has described, the table paints it and
  shows it to everyone (`bash tools/gm-image.sh location "<name>"` paints one on demand).
- **Foes.** When a notable enemy steps in, they're painted as their music starts. A boss gets an
  epic portrait with a red glow, and when a fight turns into a boss fight the boss version is
  painted. A foe met before reappears at once.
- **Treasures.** Important loot (a magic sword, an artifact) is painted when it's found, shown
  with a gold glow, and appears beside the item on the owner's character sheet.

Players find all of it in the **🖼** gallery next to the location name: *Places*, *People*,
*Foes* and *Treasures*, listing only what they've already seen.

To keep characters on-model, every PC and NPC needs a stored appearance. Ask the GM *"write
appearances for everyone in the party"*: characters created on the join page don't have one yet.

**6. Composed music (optional)**

Your own local AI composer (MusicGen) can write music for the moments that matter. It
needs an NVIDIA graphics card for reasonable speed (a GTX 1060 works); the music on
every other occasion comes from the library and the built-in sounds as before.

- **Main villains** get their own composed theme (the GM marks them).
- **Bosses** get a composed battle theme: thundering drums, brass, choir.
- **Every player character** gets a heroic anthem. When they do something truly heroic,
  it plays for everyone, and then the scene's music comes back.

Everything is composed in the background while you play: a theme takes a minute or two on
a GPU. Until it's ready, the built-in theme plays, and then the composed one takes over.

Set it up once, in Git Bash in the game folder (Windows) or a terminal (Mac/Linux):

```bash
bash tools/gm-music-compose.sh setup     # its own environment, about 3 GB (the game stays CPU-only)
bash tools/gm-music-compose.sh test      # composes one 30-second piece and times it
```

`test` also downloads the model the first time (about 2.5 GB), then prints how long your
computer took and a link to listen. That tells you what to expect: if a 30-second piece took
90 seconds, a villain's theme takes about a minute and a half.

- **No NVIDIA card?** `setup --cpu` works on any computer, but each piece takes several
  minutes. The music still arrives, just later.
- **Pictures and music take turns on the GPU; both models stay in RAM.** When the table
  starts, it loads both into RAM in the background, one after the other: first Forge's
  picture model (Forge paints one tiny throwaway picture), then the music model. After
  that nothing is read from disk again. The music model is released when the table stops;
  Forge's when you close Forge's window. Only one model sits on the graphics card at a time: before each music piece, Forge
  is asked to move its model off the card into RAM. The composer then uses the card and
  moves its own model back to RAM when the piece is done. The next picture moves Forge's
  model back by itself, in a few seconds. Pictures wait for a piece in progress, and music
  waits for a picture.
- **How much RAM:** the music model takes about 1.2 GB of RAM while it waits. With 8 GB of
  RAM, use the smaller **DreamShaper 8** picture model (about 2 GB, settings in **5.
  Pictures**): DreamShaper XL (about 6.5 GB) plus the music model doesn't fit next to
  Windows, the browser and Claude Code.
- **Volume:** every composed piece is brought up to the same loudness as ordinary music.
  Pieces composed before that was added can be very quiet; fix them once with
  `bash tools/gm-music-compose.sh normalize`.
- **Compose ahead of time** (optional): `bash tools/gm-music-compose.sh theme "Grimaldi" --boss
  --look "a rotting circus ringmaster"`, or `anthem "Pip"`. `status` lists what's composed.
- **Turn it off**: `MUSIC_COMPOSE=off` in `.env`. **Uninstall**: `bash tools/gm-music-compose.sh remove`.

The model's license (CC BY-NC 4.0) allows this for a home game, but not selling the music.

---

## Each game night (host)

**1. Start Claude Code in the game folder**

```bash
cd claude-code-game-master
git pull            # pick up the latest version
claude
```

Using local pictures (Forge)? Start Forge's `run.bat` first and wait until its console shows
the `127.0.0.1:7860` address. The composer, if you set it up, needs nothing: the table starts
it by itself. When the table opens, it loads Forge's picture model and then the music model
into RAM, in the background (a minute or so from an SSD). They stay there all evening and
take turns on the graphics card, so the first portrait doesn't wait on the disk.

**Check the GM is on Opus:** type `/model`. It should show **Opus**. If it doesn't (a new
computer, or you switched to try something), run `/models` and pick **Recommended**, or
just `/model opus` for tonight.

**Optional — faster replies:** type `/fast`. The GM stays Opus but answers noticeably
quicker, which matters when four people are waiting on every reply. It costs about twice
as much per reply; type `/fast` again to turn it off.

**2. Start the adventure**

Type `/gm`. Pick **New Adventure** (create a world, import a book, or a quick one-shot) or
continue a saved campaign. Then tell Claude:

> My friends are joining online tonight.

Claude opens the table and shows you a **link** and a **table code** (like `ember-482`).
(Manual way: `bash tools/gm-table.sh start`.)

**3. Open the tunnel** (skip if everyone is on your Wi-Fi and will only type)

In a second terminal window:

```bash
cloudflared tunnel --url http://localhost:8765
```

It prints a link like `https://something-random.trycloudflare.com`. Keep this window open
all night — closing it disconnects remote players. The link changes every time you run it.

**4. Send your friends the link and the code** — see the message below.

**5. Join yourself** — open `http://localhost:8765` in your own browser and take a seat like
everyone else. Keep the Claude Code window open; that's where your GM lives.

**6. Play.** Claude waits for everyone's actions (the round: until everyone has acted, or a
minute after the first player did), rolls the dice in public, keeps the sheets, and posts the
story to every screen. Talk to Claude in the terminal only for out-of-game things ("pause",
"take it slower", "let's end at the next rest"). Want longer rounds tonight?
`bash tools/gm-table.sh round 120` (or `round off`). A player who's away for a while holds up
nobody for more than a minute, but you can free their seat: `bash tools/gm-table.sh free "Name"`.

> **Tip:** Claude Code asks permission before running commands. When it asks to run
> `bash tools/...` during the game, choose the option to allow it without asking again, or
> the story will pause on every turn.

**7. End the night** — tell Claude *"let's stop here for tonight."* It saves the session
(characters, the world, what happened, the cliffhanger), says goodbye at the table, and
closes it. Next time: `/gm` → pick the campaign → *"my friends are joining online"* — and
everyone takes the same seats again. Close Forge's console window too: that frees the RAM
its picture model was using (the music model is freed when the table closes).

---

## Message to send your friends

Copy, fill in the link and code, and send:

> 🎲 **D&D tonight!** Open this link in **Chrome, Edge or Safari** (phone or computer):
> **LINK**
> Table code: **CODE**
> Pick a character, make your own (a name and one line is enough), or tap 🎲 to roll one.
> Type what you do, or tap 🎤 and say it. Tap 🔊 to hear the story read aloud. 💬 is a chat
> for us players (the GM can't see it), and 📖 reminds you what happened if you forget.
> Headphones recommended. For Hebrew, tap **עברית** at the top.

> 🎲 **ערב D&D!** פתחו את הקישור ב-**Chrome, Edge או Safari** (בטלפון או במחשב):
> **LINK**
> קוד השולחן: **CODE**
> בחרו דמות, צרו אחת משלכם (מספיקים שם ושורה אחת), או לחצו 🎲 כדי להטיל דמות. כתבו מה אתם
> עושים, או לחצו 🎤 ותגידו את זה. לחצו 🔊 כדי לשמוע את הסיפור בקול. 💬 הוא צ'אט רק לנו השחקנים
> (מנהל המשחק לא רואה), ו-📖 מזכיר מה קרה אם שכחתם. מומלץ אוזניות. לאנגלית לחצו **English** למעלה.

---

## Player guide

**Joining**

1. **Open the link** in Chrome, Edge or Safari (phone or computer) and enter the **table code**.
2. **Choose who you are.** Tap a free character, or make one: a name and one line ("a dwarf
   cleric who lost her faith"). **Nameless traveler** works too; the world will name you. Or
   tap **🎲 Roll a character**: fair dice roll your abilities (4d6, lowest die dropped) and
   suggest a race, class, name and concept, which you can change. Everyone sees what you
   rolled, and how many tries it took.

**Playing**

3. **Act.** Type what your character does and press Enter, or tap **🎤**, speak, and it sends
   when you stop talking (untick *Send when I stop talking* to check the text first). Talk
   the way you would at a table: *"I sneak up behind the guard and try to grab his keys."*
   A typo, or the microphone misheard you? Tap **✏️** on your message to fix it. You can until
   the GM starts playing it out (you always get at least 5 seconds): once it reads the round
   (or rolls dice), the ✏️ goes away.
4. **Rounds.** When the first player acts, a one-minute countdown starts above the text box.
   The GM answers once everyone has acted, or when the minute is up. In the last 15 seconds
   it turns red and chimes for whoever hasn't acted yet. Nothing ticks while the table is on a
   break: the countdown starts only with the first action. A character who can't act
   (unconscious, stunned, dead…) isn't waited for.
5. **While the GM works**, the bar above the text box shows what it's doing (reading your
   actions, rolling dice, updating the sheets, writing the story) and roughly how long is
   left. It learns this table's pace, so it gets more accurate as you play.
6. **The story is told as it happens.** New narration appears a few words at a time, in step
   with the voice when 🔊 is on. Tap it to see the rest at once. The party panel moves with the
   story: a hit lands on your HP bar when the text reaches your name, not before.
7. **Every die roll is public.** The table itself rolls and shows each roll to everyone the
   moment the GM sees it: who rolled, for what, and the DC or AC, which is set before the dice
   land ("🎯 Pip — Stealth · DC 15 · 🎲 [12] + 5 = 17 ✓"). A hidden roll shows as "the GM
   rolled in secret".
8. **Secrets.** Tick **Only the GM sees this** to whisper to the GM. Purple messages are
   whispers only you can see.

**Your character**

9. **Your sheet.** Tap **📜 My sheet**, or any character in the party panel, for the full
   sheet: portrait, abilities, skills, features, spells, equipment (with pictures of special
   treasures) and conditions. It follows the story too, and whatever just changed flashes. It's
   in your language: in Hebrew, what's written on it is translated (the very first time it can
   show English for a few seconds).
10. **Levelling up.** When you earn a level, **⬆** appears next to your name. Open your sheet
    and tap **Level up**: roll your hit die at the table (or take the average), pick your
    ability increases when your class gets them, and tell the GM what you'd like (a subclass,
    spells, a feat). The GM adds the new class features.

**Sight and sound**

11. **Listen.** **🔊** reads the story aloud. Hebrew is read by a natural voice that the host's
    computer makes (🌐 Hila or Avri); English uses your device's voice. **🎵** turns the
    music on or off. The volume, reading speed and voices are in the party panel (tap
    **Party** on a phone). Music follows the scene; villains have their own themes, bosses
    get battle music, and when you do something truly heroic your own anthem may play.
12. **Pictures** (when the host has them on). Places, villains, bosses and important
    treasures are painted as you meet them, every character gets a portrait, and so does an
    NPC you keep meeting. ⚔ marks a foe, 💀 a boss (bigger, glowing red), 💎 a treasure. Tap
    **🖼** next to the location at the top for the gallery: *Places*, *People*, *Foes*,
    *Treasures*.

**Between the players**

13. **Table talk.** The chat column (or **💬 Chat** on a smaller screen) is just for the
    players: plan, joke, argue. The GM never sees it. It isn't saved, so it clears when the
    host restarts the table.
14. **Forgot something?** Ask the **📖 Narrator** tab beside it: *"Who gave us the key? What did
    the oracle say?"* It answers privately from what *you* have seen in the story, and it can't
    change the game or reveal secrets. Names underlined with dots in the story (people,
    places, factions) work the same way: hover over one, or tap it on a phone, for a card of
    what you know, with their picture. So do the players' names, in the party panel and on
    their messages. Cards are prepared as the story is told, so they open at once.
15. **Language.** **עברית / English** switches the whole page, your microphone, and the language
    the GM answers you in. You read everything in your language, including the other players'
    actions, which the GM translates (marked 🌐; tap **show original** to see what they wrote).
16. **Refreshing** the page keeps your seat. To switch devices, tap **Leave seat** first (or ask
    the host to free it).

## מדריך לשחקנים

**הצטרפות**

1. **פתחו את הקישור** ב-Chrome, Edge או Safari (בטלפון או במחשב) והכניסו את **קוד השולחן**.
2. **בחרו מי אתם.** לחצו על דמות פנויה, או צרו אחת: שם ושורה אחת ("גמדה כוהנת שאיבדה את
   אמונתה"). אפשר גם **נווד/ת בלי שם**: העולם כבר ייתן לכם שם. או לחצו **🎲 הטלת דמות**:
   קוביות הוגנות מטילות את התכונות שלכם (4d6, הקובייה הנמוכה נזרקת) ומציעות גזע, מקצוע, שם
   ותיאור, שאפשר לשנות. כולם רואים מה הטלתם, וכמה ניסיונות זה לקח.

**משחק**

3. **פעלו.** כתבו מה הדמות עושה ולחצו Enter, או לחצו **🎤**, דברו, וההודעה תישלח כשתסיימו לדבר
   (בטלו את *לשלוח כשאני מסיים/ת לדבר* כדי לבדוק את הטקסט קודם). דברו כמו ליד שולחן אמיתי:
   *"אני מתגנב מאחורי השומר ומנסה לחטוף לו את המפתחות."* טעות הקלדה, או שהמיקרופון לא הבין
   אתכם? לחצו **✏️** על ההודעה כדי לתקן. אפשר עד שמנהל המשחק מתחיל לטפל בה: ברגע שהוא קורא
   את הסבב (או מטיל קוביות), ה־✏️ נעלם. תמיד יש לפחות 5 שניות.
4. **סבבים.** כשהשחקן הראשון פועל, מתחילה ספירה לאחור של דקה מעל תיבת הטקסט. מנהל המשחק עונה
   כשכולם פעלו, או כשהדקה נגמרת. ב-15 השניות האחרונות היא מאדימה ומצלצלת למי שעוד לא פעל.
   בזמן הפסקה שום דבר לא סופר: הספירה מתחילה רק עם הפעולה הראשונה. השולחן לא מחכה לדמות
   שאינה יכולה לפעול (מחוסרת הכרה, המומה, מתה…).
5. **בזמן שמנהל המשחק עובד**, הפס מעל תיבת הטקסט מראה מה הוא עושה (קורא את הפעולות, מטיל
   קוביות, מעדכן את הדפים, כותב את הסיפור) וכמה זמן נשאר בערך. הוא לומד את הקצב של השולחן
   הזה, כך שההערכה נעשית מדויקת יותר במהלך המשחק.
6. **הסיפור מסופר בזמן אמת.** קטע חדש מופיע מילה אחרי מילה, ובקצב הקול כש-🔊 פועל. לחצו עליו
   כדי לראות את כולו מיד. פאנל החבורה זז יחד עם הסיפור: מכה נוחתת על פס החיים שלכם כשהטקסט
   מגיע לשם שלכם, לא לפני כן.
7. **כל הטלת קובייה גלויה.** השולחן עצמו מטיל ומראה כל הטלה לכולם ברגע שמנהל המשחק רואה
   אותה: מי הטיל, בשביל מה, ודרגת הקושי או דרגת השריון, שנקבעת לפני שהקובייה נוחתת
   ("🎯 Pip — התגנבות · דרגת קושי 15 · 🎲 [12] + 5 = 17 ✓"). הטלה נסתרת מופיעה כ"מנהל המשחק
   הטיל קובייה בסתר".
8. **סודות.** סמנו **רק מנהל המשחק יראה** כדי ללחוש למנהל המשחק. הודעות סגולות הן לחישות שרק
   אתם רואים.

**הדמות שלכם**

9. **הדף שלכם.** לחצו **📜 הדף שלי**, או על כל דמות בפאנל החבורה, כדי לראות את הדף המלא: דיוקן,
   תכונות, מיומנויות, יכולות, לחשים, ציוד (עם תמונות של אוצרות מיוחדים) ומצבים. גם הוא
   מתעדכן יחד עם הסיפור, ומה שהשתנה עכשיו מהבהב. הדף בשפה שלכם: בעברית, מה שכתוב בו מתורגם
   (בפעם הראשונה ממש הוא עשוי להופיע באנגלית לכמה שניות).
10. **עלייה בדרגה.** כשאתם מרוויחים דרגה מופיע **⬆** ליד השם שלכם. פתחו את הדף ולחצו **עלייה
    בדרגה**: הטילו את קוביית החיים ליד השולחן (או קחו את הממוצע), בחרו שיפורי תכונות כשהמקצוע
    מקבל אותם, וכתבו למנהל המשחק מה תרצו (תת־מקצוע, לחשים, הישג). מנהל המשחק מוסיף את יכולות
    המקצוע החדשות.

**מראה וקול**

11. **הקשיבו.** **🔊** מקריא את הסיפור. את העברית מקריא קול טבעי שהמחשב של המארח מייצר (🌐 הילה
    או אברי); אנגלית מוקראת בקול של המכשיר. **🎵** מפעיל ומכבה את המוזיקה. עוצמה, מהירות הקראה
    וקולות נמצאים בפאנל החבורה (בטלפון: לחצו **החבורה**). המוזיקה הולכת אחרי הסצנה; לנבלים יש
    מנגינה משלהם, לבוסים מוזיקת קרב, וכשאתם עושים משהו הרואי באמת, ייתכן שההמנון שלכם יתנגן.
12. **תמונות** (כשהמארח הפעיל אותן). מקומות, נבלים, בוסים ואוצרות חשובים מצוירים כשאתם פוגשים
    אותם, לכל דמות יש דיוקן, וגם לדמות משנה שחוזרת שוב ושוב. ⚔ מסמן אויב, 💀 בוס (גדול יותר,
    עם זוהר אדום), 💎 אוצר. לחצו **🖼** ליד שם המקום למעלה כדי לפתוח את הגלריה: *מקומות*,
    *דמויות*, *אויבים*, *אוצרות*.

**בין השחקנים**

13. **שיחת שולחן.** עמודת הצ'אט (או **💬 צ'אט** במסך קטן) היא רק לשחקנים: לתכנן, לצחוק,
    להתווכח. מנהל המשחק לא רואה אותה. היא לא נשמרת, ולכן נמחקת כשהמארח מפעיל את השולחן מחדש.
14. **שכחתם משהו?** שאלו את לשונית **📖 המספר** שלידה: *"מי נתן לנו את המפתח? מה אמרה האורקל?"*
    הוא עונה בפרטיות ממה *שאתם* ראיתם בסיפור, ולא יכול לשנות את המשחק או לגלות סודות. שמות
    המסומנים בקו מנוקד בסיפור (דמויות, מקומות, פלגים) עובדים אותו דבר: העבירו עליהם את העכבר,
    או הקישו עליהם בטלפון, ותקבלו כרטיס של מה שאתם יודעים, עם התמונה. כך גם השמות של השחקנים,
    בפאנל החבורה ועל ההודעות שלהם. הכרטיסים מוכנים מראש בזמן שהסיפור מסופר, ולכן נפתחים מיד.
15. **שפה.** **English / עברית** מחליף את כל הדף, את המיקרופון ואת השפה שבה מנהל המשחק עונה לכם.
    הכול מופיע בשפה שלכם, כולל הפעולות של השחקנים האחרים, שמנהל המשחק מתרגם (מסומן ב-🌐; לחצו
    **הצג מקור** כדי לראות מה הם כתבו).
16. **רענון** הדף שומר לכם את המקום. כדי לעבור למכשיר אחר, לחצו קודם **עזיבת המושב** (או בקשו
    מהמארח לפנות אותו).

---

## Host cheat sheet

You rarely need these — Claude runs them — but they're yours to use:

| Command | What it does |
|---|---|
| `bash tools/gm-table.sh start` / `stop` | Open / close the table |
| `bash tools/gm-table.sh status` | Link, code, who's seated, unread actions |
| `bash tools/gm-table.sh free "Name"` | Free a seat (player switching devices) |
| `bash tools/gm-table.sh round 90` · `round off` | How long the GM waits for everyone once the first player acts (default 60 s) |
| `bash tools/gm-table.sh alias "Marta" "מרתה"` | Another spelling of a name, so its hover card works in Hebrew too (the table usually learns these by itself) |
| `bash tools/gm-table.sh music list` | What plays for each mood, and the enemy themes |
| `bash tools/gm-table.sh music --mood tavern` | Force a mood's music right now |
| `bash tools/gm-table.sh music theme "Grimaldi" waltz.mp3` | Give a villain their own track |
| `bash tools/gm-table.sh music auto off` | Stop Claude from changing the music |
| `bash tools/gm-player.sh party` | Every player character and their stats |
| `bash tools/gm-music-library.sh fetch` | Download (or re-download) the music library |
| `bash tools/gm-image.sh generate --title "Test" --prompt "..."` | Make a picture now (checks the image setup) |
| `bash tools/gm-image.sh portrait "Name"` · `location "Place"` | Paint a character's portrait (recurring NPCs get one by themselves) · a place, now |
| `bash tools/gm-image.sh enemy "Name" --boss` · `item "Thing"` | Paint a foe (epic for a boss) · a treasure, now |
| `bash tools/gm-image.sh log` | Every picture made so far (and the OpenAI spend) |
| `bash tools/gm-music-compose.sh test` · `status` | Time the local composer · what it has composed |
| `bash tools/gm-music-compose.sh normalize` | Make this campaign's older, quiet composed music as loud as the rest |
| `bash tools/gm-music-compose.sh theme "Name" --boss` · `anthem "PC"` | Compose a villain's (boss) theme · a hero's anthem ahead of time |
| `bash tools/gm-models.sh [preset]` | Which models run the game (recommended · budget · premium · inherit) |
| `/model` · `/fast` (inside Claude Code) | Check or switch the GM's model now · faster GM replies |

---

## Troubleshooting

**The GM says "the players are still acting".** That's the round: the GM may answer only when
everyone has acted or a minute after the first action. If someone has left for the night,
`bash tools/gm-table.sh free "Name"`; to switch rounds off, `bash tools/gm-table.sh round off`.

**The Narrator only quotes the story instead of answering.** It answers through the host's
Claude Code (`claude` must work in a terminal on the host, signed in). If it can't reach it, it
falls back to quoting the story lines that match. `NARRATOR_BACKEND=off` in `.env` turns the
model off on purpose; `ANTHROPIC_API_KEY` is an alternative to the Claude Code login.

**A name isn't underlined in Hebrew narration.** The table learns Hebrew spellings of the
campaign's names by itself, a few seconds after each message (with the Narrator's model). If a
name still isn't underlined, either the GM never recorded that character or place (ask: *"record
Marta as an NPC"*), or the spelling wasn't caught: `bash tools/gm-table.sh alias "Marta" "מרתה"`.

**Hover cards or the sheet's Hebrew are slow, or the sheet stays in English.** Both use the
Narrator's model (the host's Claude Code login). A card is prepared after each message and
kept, so it normally opens at once; the first card of a name nobody hovered can take 5–10
seconds. If the host's `claude` isn't signed in, cards quote the story instead and the sheet
stays as written.

**My portrait isn't on my sheet.** Portraits need pictures turned on (Forge or OpenAI). The
table waits about 3 minutes for the GM to describe a new character's look, then paints them
(30–60 s on a laptop). If a try failed it waits 15 minutes before the next. To find out why at
once, ask the GM to run `bash tools/gm-image.sh portrait "<your character>"`: it paints the
portrait or says what's wrong (often *"Can't reach Forge"*: start `run.bat`).

**No composed music.** Run `bash tools/gm-music-compose.sh check`. It should name your GPU
(`"device": "cuda"`). *"no kernel image is available"* means the PyTorch build doesn't support the
card: run `bash tools/gm-music-compose.sh remove`, then `setup --cpu`. Composing happens in the
background, so a first theme can take a few minutes to arrive; until then the built-in theme plays.

**Composed music is too quiet.** New pieces come out at a normal loudness. For older ones, run
`bash tools/gm-music-compose.sh normalize` once (it fixes every composed piece in the campaign).

**No pictures with Forge.** The GM's session notes say why (`Scene images: DISABLED (...)`):
- *"Forge isn't answering"*: start `run.bat`, wait until the console shows the
  `127.0.0.1:7860` address, then start a new Claude Code session.
- *"Forge has no API"*: `--api` is missing from `COMMANDLINE_ARGS` in `webui\webui-user.bat`.
- *"no kernel image is available"* in Forge's console: the package's CUDA version is too new
  for a GTX 10-series card. Use a CUDA 12.1 or 12.4 package.
- *Out of memory*: close games and browsers using the GPU, plug the laptop in, or switch to
  the SD 1.5 settings in **5. Pictures**.

**The computer strains when the table starts, or pictures and music are very slow.** The
table reads both AI models into RAM at the start (a few GB). Open Task Manager → Performance
while it does:
- *Disk at 100% for minutes*: the models are on a slow or failing hard drive. Move the game
  folder, Forge and the downloaded models (`C:\Users\<you>\.cache\huggingface`) to an SSD.
  [CrystalDiskInfo](https://crystalmark.info/en/software/crystaldiskinfo/) shows a drive's
  health; back up `world-state/` at once if it says *Caution* or *Bad*.
- *Memory above 90%*: use DreamShaper 8 (see **5. Pictures**) and close other programs.
- *"GPU 1" (the NVIDIA card) idle while music composes, CPU at 100%*: the composer isn't
  using the card; run `bash tools/gm-music-compose.sh check` (it should say `"device": "cuda"`).
  The Intel graphics never run the AI models, so its setting doesn't matter.
- The table's window prints `[art] Forge's picture model is loaded` and `[compose] the music
  model is loaded` when each is ready. `[art] Forge warm-up: ...` means Forge wasn't ready
  yet; the first picture then loads the model instead (slower, nothing breaks).

**Friends can't open the link.** On another network they need the tunnel's `https://…`
link, not the Wi-Fi one, and the `cloudflared` window must stay open. On the same Wi-Fi, a
firewall may block port 8765 — use the tunnel link instead.

**The 🎤 button says it needs a secure link.** Use the tunnel's `https://` link (or
`localhost` on the host's computer). Firefox can't do voice input — use Chrome, Edge or
Safari. If the browser asked for microphone permission and it was refused, allow it from
the icon in the address bar.

**Hebrew is read with an English-sounding voice.** The table normally reads Hebrew with a
natural voice made on the host's computer. That needs the host to be online and to have
pulled the update (`git pull`, then restart the table; `uv` installs `edge-tts` by itself).
Check that "Hebrew voice" in the side panel offers 🌐 Hila / Avri. If the page says the
online voice isn't reachable, it uses the device's own voice and tries again two minutes
later. To give a device its own Hebrew voice as a backup:
- Windows: Settings → Time & language → Language & region → add Hebrew (with speech).
- Mac / iPhone: Settings → Accessibility → Spoken Content → Voices → Hebrew.
- Android: Settings → Text-to-speech → Google speech engine → install Hebrew voice data.

**No music.** Tap anywhere on the page once (browsers block sound until you touch the page)
and check **🎵** is on and the music volume isn't at zero.

**"<Name> is already being played."** That seat is open somewhere else (another tab or
device). The host runs `bash tools/gm-table.sh free "Name"`.

**Windows: friends on the Wi-Fi can't connect.** The first time the table opens, Windows
asks whether Python may accept connections — allow it for private networks. Missed it?
Windows Security → Firewall → "Allow an app through firewall" → Python. Or use the tunnel
link, which needs none of this.

**Windows: `$'\r': command not found`.** The scripts got Windows line endings (a copy made
before this fix). Run `install.ps1` again — it repairs them.

**"Port already in use."** Something else is on 8765: `bash tools/gm-table.sh start --port 8800`
(and use 8800 in the tunnel command).

**The GM is quiet.** Claude may be waiting on a permission prompt in the terminal — check
the Claude Code window. If it seems stuck, tell it: *"keep running the table."*

**The GM feels slow.** Turn on `/fast`. Check `/model` says Opus, not a bigger model —
the most capable models write richer prose but can take minutes per reply, which is too slow
for a live table.

**The story feels flat or forgets things.** Check `/model` — if the GM is on Sonnet or Haiku
(for example after trying the budget preset), go back with `bash tools/gm-models.sh recommended`
and restart Claude Code (or `/model opus` right away).
