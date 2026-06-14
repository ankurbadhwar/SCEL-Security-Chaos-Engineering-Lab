#!/usr/bin/env bash
# ============================================================================
#   SCEL — Security Chaos Engineering Lab
#   Portable local launcher (Linux / macOS)
#
#   Usage:
#       ./scel.sh           start all services (default)
#       ./scel.sh start     same as above
#       ./scel.sh stop      stop all running SCEL services
#       ./scel.sh status    show which services are running
#       ./scel.sh demo      start services + run full before/after demo
#
#   ⚠  SCEL is an intentionally vulnerable local lab.
#      Do NOT expose it on a public network or remote server.
# ============================================================================

# ── Project root = directory containing this script ─────────────────────────
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$PROJECT_DIR/.scel_pids"
LOG_DIR="$PROJECT_DIR/logs"

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

# ── Python detection (first match wins) ──────────────────────────────────────
find_python() {
    # 1. Active virtual env
    if [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
        echo "$VIRTUAL_ENV/bin/python"; return 0
    fi
    # 2. .venv inside project root
    if [[ -x "$PROJECT_DIR/.venv/bin/python" ]]; then
        echo "$PROJECT_DIR/.venv/bin/python"; return 0
    fi
    # 3. Conda active env
    if [[ -n "${CONDA_PREFIX:-}" && -x "$CONDA_PREFIX/bin/python" ]]; then
        echo "$CONDA_PREFIX/bin/python"; return 0
    fi
    # 4. Common conda install directories
    for dir in "$HOME/miniconda3" "$HOME/anaconda3" "$HOME/Downloads/miniconda3" \
               "/opt/miniconda3" "/opt/anaconda3"; do
        if [[ -x "$dir/bin/python" ]]; then
            echo "$dir/bin/python"; return 0
        fi
    done
    # 5. System python
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            echo "$(command -v "$cmd")"; return 0
        fi
    done
    return 1
}

# ── Wait until an HTTP endpoint responds ─────────────────────────────────────
wait_for_url() {
    local url="$1" retries="${2:-25}"
    for ((i=0; i<retries; i++)); do
        if curl -sf --max-time 1 "$url" &>/dev/null; then return 0; fi
        sleep 1
    done
    return 1
}

# ── Free a port if something is already listening on it ──────────────────────
free_port() {
    local port="$1"
    local pid
    # lsof may not be installed — fall back silently
    pid=$(lsof -ti:"$port" 2>/dev/null || true)
    if [[ -n "$pid" ]]; then
        echo -e "${YELLOW}  Freeing port $port (pid $pid)...${NC}"
        kill "$pid" 2>/dev/null || true
        sleep 0.5
    fi
}

# ── Banner ───────────────────────────────────────────────────────────────────
print_banner() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  ⚡ SCEL — Security Chaos Engineering Lab              ║${NC}"
    echo -e "${CYAN}║  Local Lab Mode — NOT for public deployment            ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ── start ────────────────────────────────────────────────────────────────────
cmd_start() {
    print_banner

    local PYTHON
    PYTHON="$(find_python)" || {
        echo -e "${RED}ERROR: Python not found.${NC}"
        echo "  Install Python 3.10+, or activate a venv/conda environment first."
        exit 1
    }
    echo -e "  ${GREEN}Python :${NC} $PYTHON"

    # Ensure app symlink exists (Bug 1 workaround — auto-managed by launcher)
    if [[ ! -e "$PROJECT_DIR/app" ]]; then
        echo -e "${YELLOW}  Creating 'app' → Target_webapp symlink...${NC}"
        ln -sfn Target_webapp "$PROJECT_DIR/app"
    fi

    mkdir -p "$LOG_DIR"

    # Free our ports before starting
    for port in 5000 5001 5002; do free_port "$port"; done

    echo ""
    echo -e "${YELLOW}  Starting services...${NC}"

    # ── Target Webapp (port 5000) ────────────────────────────────────────────
    (cd "$PROJECT_DIR" && "$PYTHON" -m app.app >> "$LOG_DIR/webapp.log" 2>&1) &
    WEBAPP_PID=$!
    echo -e "  ${GREEN}[✓]${NC} Target Webapp       pid=$WEBAPP_PID  →  http://localhost:5000"

    # ── Metrics Dashboard (port 5001) ────────────────────────────────────────
    (cd "$PROJECT_DIR/Metrics" && "$PYTHON" app.py >> "$LOG_DIR/metrics.log" 2>&1) &
    METRICS_PID=$!
    echo -e "  ${GREEN}[✓]${NC} Metrics Dashboard   pid=$METRICS_PID  →  http://localhost:5001"

    # ── Engine API (port 5002) ───────────────────────────────────────────────
    (cd "$PROJECT_DIR/Attack_Engine" && "$PYTHON" engine_api.py >> "$LOG_DIR/engine.log" 2>&1) &
    ENGINE_PID=$!
    echo -e "  ${GREEN}[✓]${NC} Engine API          pid=$ENGINE_PID  →  http://localhost:5002"

    # Save PIDs for stop command
    echo "$WEBAPP_PID $METRICS_PID $ENGINE_PID" > "$PID_FILE"

    # Health check
    echo ""
    echo -e "${YELLOW}  Waiting for services to come online...${NC}"
    if wait_for_url "http://localhost:5002/api/health" 25; then
        echo -e "${GREEN}  All services ready.${NC}"
    else
        echo -e "${YELLOW}  Services may still be starting. Check logs/ if anything is wrong.${NC}"
    fi

    # Open browser (try common openers in order)
    for opener in xdg-open open firefox chromium-browser chromium google-chrome; do
        if command -v "$opener" &>/dev/null; then
            "$opener" "http://localhost:5001" &>/dev/null & break
        fi
    done

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  Services are running in the background.                ║${NC}"
    echo -e "${CYAN}║                                                          ║${NC}"
    echo -e "${CYAN}║  Logs:  logs/webapp.log   (Target App)                  ║${NC}"
    echo -e "${CYAN}║         logs/metrics.log  (Dashboard)                   ║${NC}"
    echo -e "${CYAN}║         logs/engine.log   (Engine API)                  ║${NC}"
    echo -e "${CYAN}║                                                          ║${NC}"
    echo -e "${CYAN}║  Stop:  ./scel.sh stop                                  ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ── stop ─────────────────────────────────────────────────────────────────────
cmd_stop() {
    local stopped=0

    if [[ -f "$PID_FILE" ]]; then
        read -ra PIDS < "$PID_FILE"
        for pid in "${PIDS[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null && echo -e "${GREEN}  Stopped pid $pid${NC}"
                stopped=1
            fi
        done
        rm -f "$PID_FILE"
    fi

    # Fallback: free by port (handles cases where PIDs drifted)
    for port in 5000 5001 5002; do
        local pid
        pid=$(lsof -ti:"$port" 2>/dev/null || true)
        if [[ -n "$pid" ]]; then
            kill "$pid" 2>/dev/null && echo -e "${GREEN}  Freed port $port${NC}"
            stopped=1
        fi
    done

    if ((stopped)); then
        echo -e "${GREEN}  SCEL services stopped.${NC}"
    else
        echo -e "${YELLOW}  No running SCEL services found.${NC}"
    fi
}

# ── status ───────────────────────────────────────────────────────────────────
cmd_status() {
    echo ""
    echo -e "${BOLD}SCEL Service Status${NC}"
    echo "────────────────────────────────────"

    declare -A LABELS=(
        [5000]="Target Webapp      "
        [5001]="Metrics Dashboard  "
        [5002]="Engine API         "
    )

    for port in 5000 5001 5002; do
        # Try curl as a port check; lsof as fallback for PID
        if curl -sf --max-time 0.5 "http://localhost:$port" &>/dev/null || \
           curl -sf --max-time 0.5 "http://localhost:$port/api/health" &>/dev/null; then
            pid=$(lsof -ti:"$port" 2>/dev/null || echo "?")
            echo -e "  ${GREEN}●${NC} ${LABELS[$port]}  port $port  pid ${pid:-?}"
        else
            echo -e "  ${RED}○${NC} ${LABELS[$port]}  port $port  (not running)"
        fi
    done
    echo ""
}

# ── demo ─────────────────────────────────────────────────────────────────────
cmd_demo() {
    cmd_start
    local PYTHON
    PYTHON="$(find_python)"
    echo ""
    echo -e "${YELLOW}  Waiting 3 s for services to settle before demo...${NC}"
    sleep 3
    echo -e "${YELLOW}  Running full before/after demo...${NC}"
    echo ""
    (cd "$PROJECT_DIR/Attack_Engine" && "$PYTHON" run_demo.py --phase both --clear-db)
}

# ── Entry point ───────────────────────────────────────────────────────────────
case "${1:-start}" in
    start)   cmd_start  ;;
    stop)    cmd_stop   ;;
    status)  cmd_status ;;
    demo)    cmd_demo   ;;
    *)
        echo -e "Usage: $0 {start|stop|status|demo}"
        echo ""
        echo "  start   Start all 3 services in the background (default)"
        echo "  stop    Stop all running SCEL services"
        echo "  status  Show which services are running"
        echo "  demo    Start services then run the full attack demo"
        exit 1
        ;;
esac
