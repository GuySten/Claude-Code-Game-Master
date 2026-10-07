# /host-setup - Get this computer ready to host the online table

The host runs this on the computer that hosts the game (a Linux/WSL laptop, a Mac, or
Windows). Do every step yourself with your tools; ask the host only where a step needs
them: a choice, a login, or a password you cannot type. Every step is safe to repeat:
check first, change only what is missing. Never print a password or token. Report as you
go, one line per step.

## 1. The program

Run the `/setup` steps (Python, `uv sync`, `.env`, permissions, the dice check). If they
already pass, say so and move on.

## 2. Where campaigns are kept

Ask: "Do you keep your campaigns in a git repository (for example a private GitHub repo)?"

- **Yes:** get its URL and branch from the host. If `gh` is installed, check
  `gh auth status`; if not logged in, ask the host to run `! gh auth login` in this
  prompt. Clone it next to the game folder (`git clone <url> ../<repo-name>`) unless it is
  already there (then `git pull`), and check out the branch. Set
  `GM_WORLD_STATE_BASE=<absolute path of the clone>` in `.env`.
- **No:** keep the default (`world-state/` in the game folder) and say so.

Then list the campaigns found (`bash tools/gm-campaign.sh list`).

## 3. Pictures

Look for a picture program on this computer, in this order:

1. **Forge** answering at `http://127.0.0.1:7860` (`curl -s http://127.0.0.1:7860/sdapi/v1/sd-models`).
2. **Forge installed but not running:** a `webui.sh` (Linux/WSL/Mac) in `~/forge`,
   `~/stable-diffusion-webui-forge`, or `webui-user.bat` on Windows. Start it in the
   background with `--api` (Linux/WSL: `cd ~/forge && nohup ./webui.sh --api > ~/forge.log 2>&1 &`),
   then wait (a minute or two) until the models URL above answers. If it fails, show the
   last lines of its log.
3. **ComfyUI** answering at `http://127.0.0.1:8188` (`/system_stats`).

Found Forge: set `IMAGE_BACKEND=forge` in `.env`. Found ComfyUI: `IMAGE_BACKEND=comfyui`.
In both cases remove any `GPU_SERVER_URL=` line from `.env` (this computer paints
itself). Found neither: ask whether to set Forge up now (GAME-NIGHT.md, "Local pictures with Forge"; on Linux/WSL clone
`https://github.com/lllyasviel/stable-diffusion-webui-forge` to `~/forge` and run `./webui.sh --api` once)
or play without pictures (`IMAGE_BACKEND=off`; the game plays fine in words).

## 4. Music (optional)

Check the orchestra: `bash tools/gm-music.sh scores` (its last line says whether it is set
up). If it isn't, offer `bash tools/gm-music.sh setup` (about 215 MB of recorded
instruments, no GPU; the game picks music from its library without it). Don't run it
without a yes.

## 5. The tunnel (friends outside your home network)

Check `cloudflared --version`. If missing, install it without admin rights where you can:

- Linux/WSL: `mkdir -p ~/.local/bin && curl -fsSL -o ~/.local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 && chmod +x ~/.local/bin/cloudflared`
  (make sure `~/.local/bin` is on PATH).
- Mac: `brew install cloudflared`. Windows: `winget install --id Cloudflare.cloudflared`.

## 6. Tonight's table

Ask which campaign to play (from step 2's list) and switch to it
(`bash tools/gm-campaign.sh switch "<name>"`). If it has no languages chosen yet, ask which
languages the table plays in (`bash tools/gm-table.sh languages en he`, English alone by
default).

Then open the table and its tunnel:

```bash
bash tools/gm-table.sh start
nohup cloudflared tunnel --url http://localhost:8765 > /tmp/table-tunnel.log 2>&1 &
```

Wait until the log shows the `https://….trycloudflare.com` link (a few seconds), then show
the host what to send the players:

```
================================================================
  🎲 THE TABLE IS OPEN
================================================================
  Link for your players:  https://….trycloudflare.com
  Table code:             <code from gm-table.sh start>

  Keep this window open. Players open the link, enter the code,
  and pick or create their character.
================================================================
```

## 7. Hand off to the game

Run `/gm` and continue the chosen campaign: the table is already open, so go straight to
the game loop in CLAUDE.md ("Online table"): `bash tools/gm-table.sh wait`, narrate with
`say`, and so on.

At the end of the night, when the host says to stop: save the session as usual, stop the
tunnel (`pkill -f "cloudflared tunnel --url http://localhost:8765"`) and the table
(`bash tools/gm-table.sh stop`), and if the campaigns live in a git repository, commit
and push them there.
