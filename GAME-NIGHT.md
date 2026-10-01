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

---

## Each game night (host)

**1. Start Claude Code in the game folder**

```bash
cd claude-code-game-master
git pull            # pick up the latest version
claude
```

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
   name you.
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
   whispers only you can see.
6. **Language.** **עברית / English** switches the whole page, your microphone, and the
   language the GM answers you in. You read everything in your language: the story, and
   the other players' actions too — the GM translates them (marked 🌐; tap
   **show original** to see what they wrote).
7. **While the GM works**, a bar above the text box shows what it's doing (reading your
   actions, rolling dice, updating the sheets, writing the story) and roughly how long is
   left. The estimate comes from how long this table's GM really took on recent turns, so it
   gets more accurate as you play.
8. **Every die roll is public.** The table itself rolls the dice and shows each roll to
   everyone the moment the GM sees it — who rolled, for what, and the DC or AC, which is
   set before the dice land ("🎯 Pip — Stealth · DC 15 · 🎲 [12] + 5 = 17 ✓"). A secret
   roll (say, a hidden enemy) shows up as "the GM rolled in secret".
9. The side panel shows everyone's **HP**. Refreshing the page keeps your seat. To switch
   devices, tap **Leave seat** first (or ask the host to free it).

## מדריך לשחקנים

1. **פתחו את הקישור** ב-Chrome, Edge או Safari והכניסו את **קוד השולחן**.
2. **בחרו מי אתם** — לחצו על דמות פנויה, או צרו דמות: שם ושורה אחת ("גמדה כוהנת שאיבדה
   את אמונתה"). אפשר גם "נווד/ת בלי שם" — העולם כבר ייתן לכם שם.
3. **פעלו.** כתבו מה הדמות עושה ולחצו Enter — או לחצו **🎤**, דברו, וההודעה תישלח כשתסיימו
   לדבר (בטלו את "לשלוח כשאני מסיים/ת לדבר" אם אתם רוצים לבדוק את הטקסט קודם). דברו כמו ליד
   שולחן אמיתי: *"אני מתגנב מאחורי השומר ומנסה לחטוף לו את המפתחות."* טעות הקלדה, או
   שהמיקרופון לא הבין אתכם? לחצו **✏️** על ההודעה כדי לתקן — אפשר עד שמנהל המשחק עונה עליה.
4. **הקשיבו.** **🔊** מקריא את הסיפור. את העברית מקריא קול טבעי שהמחשב של המארח מייצר
   (🌐 הילה או אברי); אנגלית מוקראת בקול של המכשיר. **🎵** מפעיל ומכבה את המוזיקה. עוצמה,
   מהירות הקראה וקולות נמצאים בפאנל הצד (בטלפון: לחצו **החבורה**).
5. **סודות.** סמנו **"רק מנהל המשחק יראה"** כדי ללחוש למנהל המשחק. הודעות סגולות הן לחישות
   שרק אתם רואים.
6. **שפה.** **English / עברית** מחליף את כל הדף, את המיקרופון ואת השפה שבה מנהל המשחק עונה
   לכם. הכול מופיע בשפה שלכם: הסיפור, וגם הפעולות של השחקנים האחרים — מנהל המשחק מתרגם אותן
   (מסומן ב-🌐; לחצו **הצג מקור** כדי לראות מה הם כתבו).
7. **בזמן שמנהל המשחק עובד**, פס מעל תיבת הטקסט מראה מה הוא עושה (קורא את הפעולות, מטיל
   קוביות, מעדכן את הדפים, כותב את הסיפור) וכמה זמן נשאר בערך. ההערכה מבוססת על כמה זמן
   מנהל המשחק של השולחן הזה באמת לקח בתורות האחרונים, כך שהיא נעשית מדויקת יותר במהלך המשחק.
8. **כל הטלת קובייה גלויה.** השולחן עצמו מטיל את הקוביות ומראה כל הטלה לכולם ברגע שמנהל
   המשחק רואה אותה — מי הטיל, בשביל מה, ודרגת הקושי או דרגת השריון, שנקבעת לפני שהקובייה
   נוחתת ("🎯 Pip — התגנבות · דרגת קושי 15 · 🎲 [12] + 5 = 17 ✓"). הטלה סודית (למשל אויב
   נסתר) מופיעה כ"מנהל המשחק הטיל קובייה בסתר".
9. בפאנל הצד רואים את **נקודות החיים** של כולם. רענון הדף שומר לכם את המקום. כדי לעבור
   למכשיר אחר, לחצו קודם **עזיבת המושב** (או בקשו מהמארח לפנות אותו).

---

## Host cheat sheet

You rarely need these — Claude runs them — but they're yours to use:

| Command | What it does |
|---|---|
| `bash tools/gm-table.sh start` / `stop` | Open / close the table |
| `bash tools/gm-table.sh status` | Link, code, who's seated, unread actions |
| `bash tools/gm-table.sh free "Name"` | Free a seat (player switching devices) |
| `bash tools/gm-table.sh music list` | What plays for each mood, and the enemy themes |
| `bash tools/gm-table.sh music --mood tavern` | Force a mood's music right now |
| `bash tools/gm-table.sh music theme "Grimaldi" waltz.mp3` | Give a villain their own track |
| `bash tools/gm-table.sh music auto off` | Stop Claude from changing the music |
| `bash tools/gm-player.sh party` | Every player character and their stats |
| `bash tools/gm-music-library.sh fetch` | Download (or re-download) the music library |
| `bash tools/gm-models.sh [preset]` | Which models run the game (recommended · budget · premium · inherit) |
| `/model` · `/fast` (inside Claude Code) | Check or switch the GM's model now · faster GM replies |

---

## Troubleshooting

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
