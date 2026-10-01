# Game Night — setting up an adventure for your group

Claude is the Game Master. One person, **the host**, runs the game on their computer;
everyone else just opens a link in their browser. Players can type or **speak** (English or
Hebrew), **hear the story read aloud**, and the music follows the scene by itself.

- [The recommended setup at a glance](#the-recommended-setup-at-a-glance)
- [One-time setup (host)](#one-time-setup-host)
- [Each game night (host)](#each-game-night-host)
- [Message to send your friends](#message-to-send-your-friends)
- [Player guide](#player-guide) · [מדריך לשחקנים](#מדריך-לשחקנים)
- [Host cheat sheet](#host-cheat-sheet)
- [Troubleshooting](#troubleshooting)

---

## The recommended setup at a glance

| Part of the game | Model | Why |
|---|---|---|
| **The GM** — the Claude Code session you play in | **Opus** | Tells the story, follows the rules, keeps the world consistent, writes good Hebrew |
| **Story helpers** — plots, NPCs, places, new characters, rules rulings | **Sonnet** | Need judgment, but run in the background, so faster and cheaper is better |
| **Lookup helpers** — monster stats, spells, gear, loot, image prompts | **Haiku** | Simple, quick jobs |
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
same every time. There are two ways to make the pictures:

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

**Too slow, or "out of memory"?** Use a smaller SD 1.5 model instead: **DreamShaper 8** from
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
**Portraits.** Every player character gets a portrait. With the table open it's drawn in the
background a minute or two after they join and shown to everyone; then it sits at the top of
their character sheet and next to their name in the party panel. For an important NPC, or a PC
made outside the table, the GM runs `bash tools/gm-image.sh portrait "<name>"` (you can too).

**Places.** Every important place gets a picture too. When the party arrives somewhere the GM
has described, the table paints it in the background and shows it to everyone. Tap **🖼**
next to the location name at the top of the page to see it again, along with every place
you've been. The GM can paint any place with `bash tools/gm-image.sh location "<name>"`.

**Foes and treasures.** When a notable enemy steps in, the table paints them and shows them
as their music starts. A boss gets an epic portrait with a red glow, and when a fight turns
into a boss fight the boss version is painted. Important loot (a magic sword, an artifact) is
painted when it's found, shown with a gold glow, and appears beside the item on the owner's
character sheet. All of it is collected in the 🖼 gallery, which has Places, Foes and
Treasures tabs.

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
- **Pictures and music share the GPU.** If the card's memory is full (Forge holding its model),
  the composer switches to the CPU for that piece: slower, but nothing breaks.
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

Using local pictures (Forge)? Start Forge's `run.bat` first.

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

**6. Play.** Claude waits for everyone's actions, rolls the dice, keeps the sheets, and
posts the story to every screen. Talk to Claude in the terminal only for out-of-game things
("pause", "take it slower", "let's end at the next rest").

> **Tip:** Claude Code asks permission before running commands. When it asks to run
> `bash tools/...` during the game, choose the option to allow it without asking again, or
> the story will pause on every turn.

**7. End the night** — tell Claude *"let's stop here for tonight."* It saves the session
(characters, the world, what happened, the cliffhanger), says goodbye at the table, and
closes it. Next time: `/gm` → pick the campaign → *"my friends are joining online"* — and
everyone takes the same seats again.

---

## Message to send your friends

Copy, fill in the link and code, and send:

> 🎲 **D&D tonight!** Open this link in **Chrome, Edge or Safari** (phone or computer):
> **LINK**
> Table code: **CODE**
> Pick a character or make your own (a name and one line about them is enough). Type what
> you do, or tap 🎤 and say it. Tap 🔊 to hear the story read aloud. Headphones recommended.
> For Hebrew, tap **עברית** at the top.

> 🎲 **ערב D&D!** פתחו את הקישור ב-**Chrome, Edge או Safari** (בטלפון או במחשב):
> **LINK**
> קוד השולחן: **CODE**
> בחרו דמות או צרו אחת משלכם (מספיקים שם ושורה אחת על הדמות). כתבו מה אתם עושים, או
> לחצו 🎤 ותגידו את זה. לחצו 🔊 כדי לשמוע את הסיפור בקול. מומלץ אוזניות.
> לאנגלית לחצו **English** למעלה.

---

## Player guide

1. **Open the link** in Chrome, Edge or Safari and enter the **table code**.
2. **Choose who you are** — tap a free character, or create one: a name and one line
   ("a dwarf cleric who lost her faith"). "Nameless traveler" works too — the world will
   name you. Or tap **🎲 Roll a character**: fair dice roll your abilities (4d6, lowest
   dropped) and suggest a race, class, name and concept you can change. Everyone sees what
   you rolled, and how many tries it took.
3. **Act.** Type what your character does and press Enter — or tap **🎤**, speak, and it
   sends when you stop talking (untick "Send when I stop talking" to check the text first).
   Talk the way you'd talk at a table: *"I sneak up behind the guard and try to grab his
   keys."* Typo, or the microphone misheard you? Tap **✏️** on your message to fix it —
   you can until the GM answers it.
4. **Listen.** **🔊** reads the story aloud. Hebrew is read by a natural voice that the
   host's computer makes (🌐 Hila or Avri); English uses your device's voice. **🎵**
   turns the music on/off. The volume, reading speed and voices are in the side panel (tap
   **Party** on a phone).
5. **Secrets.** Tick **"Only the GM sees this"** to whisper to the GM. Purple messages are
   whispers only you can see. **Table talk** (the chat column, or **💬 Chat** on a smaller
   screen) is just for the players: plan, joke, argue. The GM never sees it. It isn't saved,
   so it clears when the host restarts the table. Forgot who gave you the key, or what the
   oracle said? Ask the **📖 Narrator** tab beside it. It answers from what *you* have seen
   in the story so far, privately, and it can't change the game or reveal secrets.
6. **Language.** **עברית / English** switches the whole page, your microphone, and the
   language the GM answers you in. You read everything in your language: the story, and
   the other players' actions too — the GM translates them (marked 🌐; tap
   **show original** to see what they wrote).
7. **Rounds.** When the first player acts, a one-minute countdown starts above the text box.
   The GM answers once everyone has acted, or when the minute is up. In the last 15 seconds
   it turns red and chimes for whoever hasn't acted yet. Nothing ticks while the table is on
   a break: the countdown only starts with the first action. A character who can't act
   (unconscious, stunned, dead…) isn't waited for.
8. **While the GM works**, a bar above the text box shows what it's doing (reading your
   actions, rolling dice, updating the sheets, writing the story) and roughly how long is
   left. The estimate comes from how long this table's GM really took on recent turns, so it
   gets more accurate as you play.
9. **Every die roll is public.** The table itself rolls the dice and shows each roll to
   everyone the moment the GM sees it — who rolled, for what, and the DC or AC, which is
   set before the dice land ("🎯 Pip — Stealth · DC 15 · 🎲 [12] + 5 = 17 ✓"). A secret
   roll (say, a hidden enemy) shows up as "the GM rolled in secret".
10. **The story is told as it happens.** New narration appears a few words at a time, in step
   with the voice when 🔊 is on. Tap it to see the rest at once. The side panel shows
   everyone's **HP**, and it changes with the story: a hit lands on your HP bar when the text
   reaches your name, not before.
11. **Your character sheet.** Tap **📜 My sheet**, or any character in the side panel, for
   the full sheet: a portrait (when pictures are on), abilities, skills, features, spells,
   equipment, conditions. The **🖼** next to the location at the top shows the places you've
   been. It updates
   with the story too, and what just changed flashes. When you earn a level, **⬆** appears:
   open your sheet and tap **Level up**. Roll your hit die at the table (or take the average),
   pick your ability increases when your class gets them, and tell the GM what you'd like
   (a subclass, spells, a feat). The GM adds the new class features.
12. Refreshing the page keeps your seat. To switch devices, tap **Leave seat** first (or ask
   the host to free it).

## מדריך לשחקנים

1. **פתחו את הקישור** ב-Chrome, Edge או Safari והכניסו את **קוד השולחן**.
2. **בחרו מי אתם** — לחצו על דמות פנויה, או צרו דמות: שם ושורה אחת ("גמדה כוהנת שאיבדה
   את אמונתה"). אפשר גם "נווד/ת בלי שם" — העולם כבר ייתן לכם שם. או לחצו **🎲 הטלת דמות**:
   קוביות הוגנות מטילות את התכונות שלכם (4d6, הנמוכה נזרקת) ומציעות גזע, מקצוע, שם ותיאור
   שאפשר לשנות. כולם רואים מה הטלתם, וכמה ניסיונות זה לקח.
3. **פעלו.** כתבו מה הדמות עושה ולחצו Enter — או לחצו **🎤**, דברו, וההודעה תישלח כשתסיימו
   לדבר (בטלו את "לשלוח כשאני מסיים/ת לדבר" אם אתם רוצים לבדוק את הטקסט קודם). דברו כמו ליד
   שולחן אמיתי: *"אני מתגנב מאחורי השומר ומנסה לחטוף לו את המפתחות."* טעות הקלדה, או
   שהמיקרופון לא הבין אתכם? לחצו **✏️** על ההודעה כדי לתקן — אפשר עד שמנהל המשחק עונה עליה.
4. **הקשיבו.** **🔊** מקריא את הסיפור. את העברית מקריא קול טבעי שהמחשב של המארח מייצר
   (🌐 הילה או אברי); אנגלית מוקראת בקול של המכשיר. **🎵** מפעיל ומכבה את המוזיקה. עוצמה,
   מהירות הקראה וקולות נמצאים בפאנל הצד (בטלפון: לחצו **החבורה**).
5. **סודות.** סמנו **"רק מנהל המשחק יראה"** כדי ללחוש למנהל המשחק. הודעות סגולות הן לחישות
   שרק אתם רואים. **שיחת שולחן** (עמודת הצ'אט, או **💬 צ'אט** במסך קטן) היא רק לשחקנים:
   לתכנן, לצחוק, להתווכח. מנהל המשחק לא רואה אותה. היא לא נשמרת, ולכן נמחקת כשהמארח מפעיל
   את השולחן מחדש. שכחתם מי נתן לכם את המפתח, או מה אמרה האורקל? שאלו את לשונית
   **📖 המספר** שלידה. הוא עונה ממה *שאתם* ראיתם בסיפור עד עכשיו, בפרטיות, ולא יכול לשנות את
   המשחק או לגלות סודות.
6. **שפה.** **English / עברית** מחליף את כל הדף, את המיקרופון ואת השפה שבה מנהל המשחק עונה
   לכם. הכול מופיע בשפה שלכם: הסיפור, וגם הפעולות של השחקנים האחרים — מנהל המשחק מתרגם אותן
   (מסומן ב-🌐; לחצו **הצג מקור** כדי לראות מה הם כתבו).
7. **סבבים.** כשהשחקן הראשון פועל, מתחילה ספירה לאחור של דקה מעל תיבת הטקסט. מנהל המשחק עונה
   כשכולם פעלו, או כשהדקה נגמרת. ב-15 השניות האחרונות היא מאדימה ומצלצלת למי שעוד לא פעל. בזמן
   הפסקה שום דבר לא סופר: הספירה מתחילה רק עם הפעולה הראשונה. השולחן לא מחכה לדמות שאינה
   יכולה לפעול (מחוסרת הכרה, המומה, מתה…).
8. **בזמן שמנהל המשחק עובד**, פס מעל תיבת הטקסט מראה מה הוא עושה (קורא את הפעולות, מטיל
   קוביות, מעדכן את הדפים, כותב את הסיפור) וכמה זמן נשאר בערך. ההערכה מבוססת על כמה זמן
   מנהל המשחק של השולחן הזה באמת לקח בתורות האחרונים, כך שהיא נעשית מדויקת יותר במהלך המשחק.
9. **כל הטלת קובייה גלויה.** השולחן עצמו מטיל את הקוביות ומראה כל הטלה לכולם ברגע שמנהל
   המשחק רואה אותה — מי הטיל, בשביל מה, ודרגת הקושי או דרגת השריון, שנקבעת לפני שהקובייה
   נוחתת ("🎯 Pip — התגנבות · דרגת קושי 15 · 🎲 [12] + 5 = 17 ✓"). הטלה סודית (למשל אויב
   נסתר) מופיעה כ"מנהל המשחק הטיל קובייה בסתר".
10. **הסיפור מסופר בזמן אמת.** קטע חדש מופיע מילה אחרי מילה, ובקצב הקול כש-🔊 פועל. לחצו
   עליו כדי לראות את כולו מיד. בפאנל הצד רואים את **נקודות החיים** של כולם, והן משתנות יחד
   עם הסיפור: מכה נוחתת על פס החיים שלכם כשהטקסט מגיע לשם שלכם, לא לפני כן.
11. **דף הדמות.** לחצו **📜 הדף שלי**, או על כל דמות בפאנל הצד, כדי לראות את הדף המלא:
   דיוקן (כשהתמונות פועלות), תכונות, מיומנויות, יכולות, לחשים, ציוד ומצבים. ה-**🖼** ליד
   שם המקום למעלה מציג את המקומות שביקרתם בהם. גם הוא מתעדכן יחד עם הסיפור, ומה שהשתנה
   מהבהב. כשאתם מרוויחים דרגה מופיע **⬆**: פתחו את הדף ולחצו **עלייה בדרגה**. הטילו את קוביית
   החיים ליד השולחן (או קחו את הממוצע), בחרו שיפורי תכונות כשהמקצוע מקבל אותם, וכתבו למנהל
   המשחק מה תרצו (תת־מקצוע, לחשים, הישג). מנהל המשחק מוסיף את יכולות המקצוע החדשות.
12. רענון הדף שומר לכם את המקום. כדי לעבור למכשיר אחר, לחצו קודם **עזיבת המושב** (או בקשו
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
| `bash tools/gm-table.sh music list` | What plays for each mood, and the enemy themes |
| `bash tools/gm-table.sh music --mood tavern` | Force a mood's music right now |
| `bash tools/gm-table.sh music theme "Grimaldi" waltz.mp3` | Give a villain their own track |
| `bash tools/gm-table.sh music auto off` | Stop Claude from changing the music |
| `bash tools/gm-player.sh party` | Every player character and their stats |
| `bash tools/gm-music-library.sh fetch` | Download (or re-download) the music library |
| `bash tools/gm-image.sh generate --title "Test" --prompt "..."` | Make a picture now (checks the image setup) |
| `bash tools/gm-image.sh log` | Every picture made so far (and the OpenAI spend) |
| `bash tools/gm-music-compose.sh test` · `status` | Time the local composer · what it has composed |
| `bash tools/gm-models.sh [preset]` | Which models run the game (recommended · budget · premium · inherit) |
| `/model` · `/fast` (inside Claude Code) | Check or switch the GM's model now · faster GM replies |

---

## Troubleshooting

**No composed music.** Run `bash tools/gm-music-compose.sh check`. It should name your GPU
(`"device": "cuda"`). *"no kernel image is available"* means the PyTorch build doesn't support the
card: run `bash tools/gm-music-compose.sh remove`, then `setup --cpu`. Composing happens in the
background, so a first theme can take a few minutes to arrive; until then the built-in theme plays.

**No pictures with Forge.** The GM's session notes say why (`Scene images: DISABLED (...)`):
- *"Forge isn't answering"*: start `run.bat`, wait until the console shows the
  `127.0.0.1:7860` address, then start a new Claude Code session.
- *"Forge has no API"*: `--api` is missing from `COMMANDLINE_ARGS` in `webui\webui-user.bat`.
- *"no kernel image is available"* in Forge's console: the package's CUDA version is too new
  for a GTX 10-series card. Use a CUDA 12.1 or 12.4 package.
- *Out of memory*: close games and browsers using the GPU, plug the laptop in, or switch to
  the SD 1.5 settings in **5. Pictures**.

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
