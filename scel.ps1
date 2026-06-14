#Requires -Version 5.1
# ============================================================================
#   SCEL — Security Chaos Engineering Lab
#   Portable local launcher for Windows (PowerShell 5.1+)
#
#   Usage:
#       .\scel.ps1           start all services (default)
#       .\scel.ps1 start     same as above
#       .\scel.ps1 stop      stop all running SCEL services
#       .\scel.ps1 status    show which services are running
#       .\scel.ps1 demo      start services + run full before/after demo
#
#   If script execution is blocked, run via the provided scel.bat wrapper,
#   or run once: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
#
#   ⚠  SCEL is an intentionally vulnerable local lab.
#      Do NOT expose it on a public network or remote server.
# ============================================================================

param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "stop", "status", "demo")]
    [string]$Command = "start"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$ProjectDir = $PSScriptRoot
$PidFile    = Join-Path $ProjectDir ".scel_pids_win.json"
$LogDir     = Join-Path $ProjectDir "logs"

# ── Color helpers ─────────────────────────────────────────────────────────────
function Write-Col {
    param([string]$Text, [ConsoleColor]$Color = [ConsoleColor]::White)
    Write-Host $Text -ForegroundColor $Color
}

# ── Python detection (first match wins) ───────────────────────────────────────
function Find-Python {
    # 1. .venv in project root
    $p = Join-Path $ProjectDir ".venv\Scripts\python.exe"
    if (Test-Path $p) { return $p }

    # 2. Active conda env
    if ($env:CONDA_PREFIX) {
        $p = Join-Path $env:CONDA_PREFIX "python.exe"
        if (Test-Path $p) { return $p }
    }

    # 3. Common conda locations
    $condaDirs = @(
        "$env:USERPROFILE\miniconda3",
        "$env:USERPROFILE\anaconda3",
        "$env:LOCALAPPDATA\miniconda3",
        "C:\miniconda3",
        "C:\ProgramData\miniconda3",
        "$env:USERPROFILE\Downloads\miniconda3"
    )
    foreach ($dir in $condaDirs) {
        $p = Join-Path $dir "python.exe"
        if (Test-Path $p) { return $p }
    }

    # 4. System Python (py launcher → python3 → python)
    foreach ($cmd in @("py", "python3", "python")) {
        $found = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($found) { return $found.Source }
    }

    return $null
}

# ── TCP port check ────────────────────────────────────────────────────────────
function Test-LocalPort {
    param([int]$Port)
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", $Port)
        $tcp.Close()
        return $true
    } catch { return $false }
}

function Wait-ForPort {
    param([int]$Port, [int]$Retries = 25)
    for ($i = 0; $i -lt $Retries; $i++) {
        if (Test-LocalPort $Port) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Get-PidOnPort {
    param([int]$Port)
    $lines = netstat -ano 2>$null | Select-String "\s+(?:0\.0\.0\.0|127\.0\.0\.1):$Port\s+.*LISTENING"
    if ($lines) {
        $fields = ($lines | Select-Object -First 1) -split '\s+'
        return $fields[-1]
    }
    return $null
}

function Stop-PortProcess {
    param([int]$Port)
    $pid = Get-PidOnPort $Port
    if ($pid -and $pid -ne "0") {
        try { Stop-Process -Id ([int]$pid) -Force -ErrorAction SilentlyContinue } catch {}
        Write-Col "  Freed port $Port (pid $pid)" Green
    }
}

# ── Banner ────────────────────────────────────────────────────────────────────
function Show-Banner {
    Write-Col ""
    Write-Col "╔══════════════════════════════════════════════════════════╗" Cyan
    Write-Col "║  ⚡ SCEL — Security Chaos Engineering Lab              ║" Cyan
    Write-Col "║  Local Lab Mode — NOT for public deployment            ║" Cyan
    Write-Col "╚══════════════════════════════════════════════════════════╝" Cyan
    Write-Col ""
}

# ── Start ─────────────────────────────────────────────────────────────────────
function Start-SCEL {
    Show-Banner

    $python = Find-Python
    if (-not $python) {
        Write-Col "ERROR: Python not found." Red
        Write-Col "  Install Python 3.10+ from python.org, or activate a venv/conda environment." White
        exit 1
    }
    Write-Col "  Python : $python" Green

    # App junction (Bug 1 workaround — auto-managed by launcher)
    $appLink = Join-Path $ProjectDir "app"
    if (-not (Test-Path $appLink)) {
        Write-Col "  Creating 'app' junction → Target_webapp..." Yellow
        $result = cmd /c "mklink /J `"$appLink`" `"$ProjectDir\Target_webapp`"" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Col "  WARNING: Could not create junction. Try running as Administrator." Yellow
        }
    }

    if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

    # Free ports if in use
    foreach ($port in @(5000, 5001, 5002)) { Stop-PortProcess $port }

    Write-Col ""
    Write-Col "  Starting services in separate windows..." Yellow

    # ── Target Webapp (port 5000) ────────────────────────────────────────────
    $webappLog = Join-Path $LogDir "webapp.log"
    $webappCmd = "& { `$host.ui.RawUI.WindowTitle='SCEL - Target Webapp [:5000]'; " +
                 "Set-Location '$ProjectDir'; " +
                 "& '$python' -m app.app 2>&1 | Tee-Object -FilePath '$webappLog'; " +
                 "Write-Host 'Press Enter to close...'; Read-Host }"
    $webappProc = Start-Process powershell -ArgumentList "-NoExit", "-Command", $webappCmd -PassThru
    Write-Col "  [OK] Target Webapp       pid=$($webappProc.Id)  -> http://localhost:5000" Green

    # ── Metrics Dashboard (port 5001) ────────────────────────────────────────
    $metricsLog = Join-Path $LogDir "metrics.log"
    $metricsCmd = "& { `$host.ui.RawUI.WindowTitle='SCEL - Metrics Dashboard [:5001]'; " +
                  "Set-Location '$ProjectDir\Metrics'; " +
                  "& '$python' app.py 2>&1 | Tee-Object -FilePath '$metricsLog'; " +
                  "Write-Host 'Press Enter to close...'; Read-Host }"
    $metricsProc = Start-Process powershell -ArgumentList "-NoExit", "-Command", $metricsCmd -PassThru
    Write-Col "  [OK] Metrics Dashboard   pid=$($metricsProc.Id)  -> http://localhost:5001" Green

    # ── Engine API (port 5002) ───────────────────────────────────────────────
    $engineLog = Join-Path $LogDir "engine.log"
    $engineCmd = "& { `$host.ui.RawUI.WindowTitle='SCEL - Engine API [:5002]'; " +
                 "Set-Location '$ProjectDir\Attack_Engine'; " +
                 "& '$python' engine_api.py 2>&1 | Tee-Object -FilePath '$engineLog'; " +
                 "Write-Host 'Press Enter to close...'; Read-Host }"
    $engineProc = Start-Process powershell -ArgumentList "-NoExit", "-Command", $engineCmd -PassThru
    Write-Col "  [OK] Engine API          pid=$($engineProc.Id)  -> http://localhost:5002" Green

    # Save PIDs
    @{ webapp=$webappProc.Id; metrics=$metricsProc.Id; engine=$engineProc.Id } |
        ConvertTo-Json | Set-Content -Path $PidFile

    # Health check
    Write-Col ""
    Write-Col "  Waiting for services to come online..." Yellow
    if (Wait-ForPort 5002 25) {
        Write-Col "  All services ready." Green
    } else {
        Write-Col "  Services may still be starting — check logs\ if anything looks wrong." Yellow
    }

    # Open browser
    Start-Process "http://localhost:5001"

    Write-Col ""
    Write-Col "╔══════════════════════════════════════════════════════════╗" Cyan
    Write-Col "║  Services running in separate PowerShell windows.       ║" Cyan
    Write-Col "║                                                          ║" Cyan
    Write-Col "║  Logs:  logs\webapp.log   (Target App)                  ║" Cyan
    Write-Col "║         logs\metrics.log  (Dashboard)                   ║" Cyan
    Write-Col "║         logs\engine.log   (Engine API)                  ║" Cyan
    Write-Col "║                                                          ║" Cyan
    Write-Col "║  Stop:  .\scel.ps1 stop                                 ║" Cyan
    Write-Col "╚══════════════════════════════════════════════════════════╝" Cyan
    Write-Col ""
}

# ── Stop ──────────────────────────────────────────────────────────────────────
function Stop-SCEL {
    if (Test-Path $PidFile) {
        $saved = Get-Content $PidFile | ConvertFrom-Json
        foreach ($prop in @("webapp", "metrics", "engine")) {
            $pid = [int]$saved.$prop
            try {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Col "  Stopped pid $pid ($prop)" Green
            } catch {}
        }
        Remove-Item $PidFile -Force
    }
    # Fallback: free by port
    foreach ($port in @(5000, 5001, 5002)) { Stop-PortProcess $port }
    Write-Col "  SCEL services stopped." Green
}

# ── Status ────────────────────────────────────────────────────────────────────
function Show-Status {
    Write-Col ""
    Write-Col "SCEL Service Status" White
    Write-Col "─────────────────────────────────────" DarkGray
    $labels = @{ 5000 = "Target Webapp     "; 5001 = "Metrics Dashboard "; 5002 = "Engine API        " }
    foreach ($port in @(5000, 5001, 5002)) {
        if (Test-LocalPort $port) {
            Write-Col "  [UP]   $($labels[$port])  port $port" Green
        } else {
            Write-Col "  [DOWN] $($labels[$port])  port $port" Red
        }
    }
    Write-Col ""
}

# ── Demo ──────────────────────────────────────────────────────────────────────
function Start-Demo {
    Start-SCEL
    $python = Find-Python
    Write-Col "  Waiting 3 s for services to settle before demo..." Yellow
    Start-Sleep -Seconds 3
    Write-Col "  Running full before/after demo..." Yellow
    Push-Location (Join-Path $ProjectDir "Attack_Engine")
    & $python run_demo.py --phase both --clear-db
    Pop-Location
}

# ── Entry point ───────────────────────────────────────────────────────────────
switch ($Command) {
    "start"  { Start-SCEL  }
    "stop"   { Stop-SCEL   }
    "status" { Show-Status }
    "demo"   { Start-Demo  }
}
