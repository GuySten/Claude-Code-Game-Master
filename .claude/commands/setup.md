# /setup - Automatic Installation

Run this command to install GM Claude dependencies. This runs automatically on first launch.

## Steps

1. **Check Python version**
   ```bash
   python3 --version
   ```
   Verify Python 3.11+ is installed. If not, inform the user:
   "Python 3.11+ is required. Install from: https://www.python.org/downloads/"

2. **Create virtual environment if missing**
   ```bash
   [ -d ".venv" ] || python3 -m venv .venv
   ```

3. **Install dependencies (including RAG for document import)**

   Try uv first (faster), fall back to pip. Install with RAG extras for full functionality:
   ```bash
   if command -v uv &> /dev/null; then
       uv sync --extra rag
   else
       source .venv/bin/activate && pip install --upgrade pip
       # CPU-only PyTorch first (pip ignores pyproject's [tool.uv.sources]); not needed on macOS
       [ "$(uname -s)" = "Darwin" ] || pip install torch --index-url https://download.pytorch.org/whl/cpu
       pip install -e '.[rag]'
   fi
   ```

   Note: This installs sentence-transformers and chromadb for document import, with the
   CPU-only build of PyTorch (configured in pyproject.toml; no CUDA download).

4. **Create .env if missing**
   ```bash
   if [ ! -f ".env" ]; then
       cat > .env << 'EOF'
   # GM Claude Configuration
   DEFAULT_CAMPAIGN_NAME="My Campaign"
   DEFAULT_STARTING_LOCATION="Thornwick"
   EOF
   fi
   ```

5. **Set script permissions**
   ```bash
   chmod +x tools/*.sh tools/*.py lib/*.py
   ```

6. **Verify installation**
   ```bash
   uv run python lib/dice.py "1d20"
   ```

   If the dice roll works, installation is complete.

---

## Setup Complete → Hand Off to /gm

Installation is the only job of this command. `/gm` is the single front door for
everything that follows — do NOT re-implement a campaign/import/new-game menu here.
`/gm` already lists saved campaigns and offers **New Adventure** (Create World →
`/new-game`, Import Document → `/import`, or One-Shot).

After install succeeds, display:

```
================================================================
  ✅ GM CLAUDE IS READY
================================================================

  Run /gm to begin.

  • Pick up a saved campaign, or
  • Start a New Adventure: create a world, import a book,
    or jump into a quick one-shot.
================================================================
```

Then route into `/gm` (its STEP 0 handles campaign selection, new-vs-import, and
returning players in one place).
