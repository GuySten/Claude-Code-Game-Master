# install.ps1 - GM Claude setup for Windows (no WSL needed)
#
# Run in PowerShell from the game folder:
#     powershell -ExecutionPolicy Bypass -File install.ps1
#     powershell -ExecutionPolicy Bypass -File install.ps1 -Extras rag   # also book import
#
# What it does (each step is skipped if already done):
#   1. Git for Windows - Claude Code on Windows runs its commands through Git Bash,
#      and so do the game's tools (bash tools/gm-*.sh)
#   2. uv - the Python package manager (it also downloads Python itself if needed)
#   3. The game's Python dependencies (core, or core + book import)
#   4. .env and the recommended model set
#   5. A quick check that the tools run, plus Claude Code
#
# This file is ASCII only on purpose: Windows PowerShell 5.1 misreads UTF-8 scripts.

param(
    [ValidateSet("", "core", "rag")]
    [string]$Extras = ""
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Step($text) { Write-Host ""; Write-Host "== $text ==" -ForegroundColor Cyan }
function Ok($text)   { Write-Host "  [ok] $text" -ForegroundColor Green }
function Warn($text) { Write-Host "  [!]  $text" -ForegroundColor Yellow }
function Info($text) { Write-Host "       $text" -ForegroundColor DarkGray }
function Have($name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }

Write-Host ""
Write-Host "================================================================" -ForegroundColor Blue
Write-Host "          GM Claude - Windows setup" -ForegroundColor Blue
Write-Host "================================================================" -ForegroundColor Blue

# ---------------------------------------------------------------------------
Step "1/5  Git for Windows (Git Bash)"
# ---------------------------------------------------------------------------
if (-not (Have "git")) {
    if (Have "winget") {
        Info "Installing Git for Windows with winget..."
        winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
        Warn "Git was installed. Close this window, open a NEW PowerShell, and run install.ps1 again."
        exit 0
    }
    Warn "Git for Windows is required. Install it from https://git-scm.com/download/win and run install.ps1 again."
    exit 1
}
$gitExe = (Get-Command git).Source
$gitRoot = Split-Path (Split-Path $gitExe -Parent) -Parent
$bash = Join-Path $gitRoot "bin\bash.exe"
if (-not (Test-Path $bash)) {
    Warn "Found git ($gitExe) but not Git Bash ($bash). Reinstall Git for Windows with its default options."
    exit 1
}
Ok "Git Bash: $bash"

# Keep the shell scripts' Unix line endings in this checkout (see .gitattributes).
$crlfScripts = Get-ChildItem -Path "tools", ".claude\hooks" -Filter *.sh -Recurse |
    Where-Object { (Get-Content -Raw -Path $_.FullName) -match "`r`n" }
if ($crlfScripts) {
    Info "Fixing Windows line endings in the shell scripts..."
    foreach ($f in $crlfScripts) {
        $text = (Get-Content -Raw -Path $f.FullName) -replace "`r`n", "`n"
        [System.IO.File]::WriteAllText($f.FullName, $text)
    }
    Ok "Shell scripts use Unix line endings"
}

# ---------------------------------------------------------------------------
Step "2/5  uv (Python package manager)"
# ---------------------------------------------------------------------------
if (-not (Have "uv")) {
    Info "Installing uv (https://docs.astral.sh/uv/)..."
    powershell -ExecutionPolicy Bypass -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
    if (-not (Have "uv")) {
        Warn "uv was installed but is not on PATH yet. Open a NEW PowerShell and run install.ps1 again."
        exit 1
    }
}
Ok ("uv " + (uv --version))

# ---------------------------------------------------------------------------
Step "3/5  Python dependencies"
# ---------------------------------------------------------------------------
if ($Extras -eq "") {
    Write-Host "  What to install:"
    Write-Host "    1) Core only   - everything for playing together (recommended)"
    Write-Host "    2) Core + RAG  - adds importing a book (PDF); bigger download (CPU-only PyTorch)"
    $choice = Read-Host "  Choice [1-2] (default: 1)"
    if ($choice -eq "2") { $Extras = "rag" } else { $Extras = "core" }
}
if ($Extras -eq "rag") { uv sync --extra rag } else { uv sync }
if ($LASTEXITCODE -ne 0) { Warn "uv sync failed (see above)."; exit 1 }
Ok "Dependencies installed ($Extras)"

# ---------------------------------------------------------------------------
Step "4/5  Settings"
# ---------------------------------------------------------------------------
$env:PYTHONUTF8 = "1"
if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
    Ok "Created .env"
}
uv run python lib/model_presets.py recommended | Out-Null
Ok "Recommended models: Opus GM, Sonnet story helpers, Haiku lookups (change with /models)"

# ---------------------------------------------------------------------------
Step "5/5  Check"
# ---------------------------------------------------------------------------
$roll = uv run python lib/dice.py "1d20"
if ($LASTEXITCODE -eq 0) { Ok "Python tools work: $roll" } else { Warn "The dice roller failed." }

& $bash tools/gm-campaign.sh list | Out-Null
if ($LASTEXITCODE -eq 0) { Ok "The game's bash tools run in Git Bash" }
else { Warn "bash tools/gm-campaign.sh failed in Git Bash - see the output above." }

if (Have "claude") {
    Ok "Claude Code found"
} else {
    Warn "Claude Code not found. Install it: https://docs.anthropic.com/en/docs/claude-code"
}

Write-Host ""
Write-Host "Done. Next:" -ForegroundColor Green
Write-Host "  - Optional music library:  uv run python lib/music_library.py fetch"
Write-Host "  - Start playing:           claude   (then type /gm)"
Write-Host "  - Hosting friends online: the first time the table opens, Windows asks whether"
Write-Host "    to allow Python through the firewall - allow it on private networks."
Write-Host "  - Run the game's commands from Claude Code or from 'Git Bash' (Start menu),"
Write-Host "    not plain PowerShell: for example  bash tools/gm-table.sh status"
