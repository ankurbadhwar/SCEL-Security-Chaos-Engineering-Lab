#!/bin/bash
# ============================================================================
#   SCEL - Security Chaos Engineering Lab
#   One-click launcher — opens 3 terminals and runs everything
# ============================================================================

PROJECT_DIR="/home/bloop/Downloads/SCEL-Security-Chaos-Engineering-Lab"
CONDA_ENV="/home/bloop/Downloads/miniconda3"
PYTHON="$CONDA_ENV/bin/python"

# ── Colors for output ───────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ── Detect available terminal emulator ──────────────────────────────────────
detect_terminal() {
    for term in alacritty xfce4-terminal gnome-terminal konsole x-terminal-emulator xterm; do
        if command -v "$term" &> /dev/null; then
            echo "$term"
            return
        fi
    done
    echo ""
}

# ── Launch a command in a new terminal window ───────────────────────────────
launch_in_terminal() {
    local title="$1"
    local cmd="$2"
    local terminal="$3"

    case "$terminal" in
        alacritty)
            alacritty --title "$title" -e bash -c "$cmd" &
            ;;
        xfce4-terminal)
            xfce4-terminal --title="$title" -e "bash -c '$cmd'" &
            ;;
        gnome-terminal)
            gnome-terminal --title="$title" -- bash -c "$cmd" &
            ;;
        konsole)
            konsole -p tabtitle="$title" -e bash -c "$cmd" &
            ;;
        x-terminal-emulator)
            x-terminal-emulator -T "$title" -e bash -c "$cmd" &
            ;;
        xterm)
            xterm -T "$title" -e bash -c "$cmd" &
            ;;
        *)
            echo -e "${RED}ERROR: No terminal emulator found!${NC}"
            echo "Install one: sudo apt install xterm"
            exit 1
            ;;
    esac
}

# ============================================================================
#   MAIN
# ============================================================================

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   SCEL - Security Chaos Engineering Lab                  ║${NC}"
echo -e "${CYAN}║   Starting all components...                             ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ── Check conda env exists ──────────────────────────────────────────────────
if [ ! -f "$PYTHON" ]; then
    echo -e "${RED}ERROR: Conda Python not found at $PYTHON${NC}"
    echo "Install Miniconda: bash /home/bloop/Downloads/miniconda.sh -b -p $CONDA_ENV"
    exit 1
fi

# ── Check symlink exists ────────────────────────────────────────────────────
if [ ! -L "$PROJECT_DIR/app" ]; then
    echo -e "${YELLOW}Creating 'app' symlink → Target_webapp ...${NC}"
    ln -sfn Target_webapp "$PROJECT_DIR/app"
fi

# ── Detect terminal ─────────────────────────────────────────────────────────
TERM_EMU=$(detect_terminal)
if [ -z "$TERM_EMU" ]; then
    echo -e "${RED}ERROR: No terminal emulator found!${NC}"
    echo "Install one: sudo apt install xterm"
    exit 1
fi
echo -e "${GREEN}Using terminal: $TERM_EMU${NC}"
echo ""

# ── Terminal 1: Target Web Application (port 5000) ──────────────────────────
echo -e "${YELLOW}[1/3] Starting Target Web Application (port 5000)...${NC}"

WEBAPP_CMD="
echo '══════════════════════════════════════════════════════════'
echo '  SCEL — Target Web Application'
echo '  Port: 5000'
echo '══════════════════════════════════════════════════════════'
echo ''
cd $PROJECT_DIR
export PATH=$CONDA_ENV/bin:\$PATH
$PYTHON -m app.app
echo ''
echo 'Press Enter to close...'
read
"

launch_in_terminal "SCEL - Target Webapp" "$WEBAPP_CMD" "$TERM_EMU"

# ── Wait for webapp to start ────────────────────────────────────────────────
echo -e "${CYAN}   Waiting 4 seconds for webapp to start...${NC}"
sleep 4

# ── Terminal 2: Metrics Dashboard (port 5001) ───────────────────────────────
echo -e "${YELLOW}[2/3] Starting Metrics Dashboard (port 5001)...${NC}"

METRICS_CMD="
echo '══════════════════════════════════════════════════════════'
echo '  SCEL — Metrics Dashboard'
echo '  Port: 5001'
echo '  Open in browser: http://localhost:5001'
echo '══════════════════════════════════════════════════════════'
echo ''
cd $PROJECT_DIR/Metrics
export PATH=$CONDA_ENV/bin:\$PATH
$PYTHON app.py
echo ''
echo 'Press Enter to close...'
read
"

launch_in_terminal "SCEL - Metrics Dashboard" "$METRICS_CMD" "$TERM_EMU"

# ── Wait for dashboard to start ─────────────────────────────────────────────
echo -e "${CYAN}   Waiting 3 seconds for dashboard to start...${NC}"
sleep 3

# ── Terminal 3: Attack Simulation Engine ────────────────────────────────────
echo -e "${YELLOW}[3/3] Launching Attack Simulation Engine...${NC}"

ATTACK_CMD="
echo '══════════════════════════════════════════════════════════'
echo '  SCEL — Attack Simulation Engine'
echo '══════════════════════════════════════════════════════════'
echo ''
cd $PROJECT_DIR/Attack_Engine
export PATH=$CONDA_ENV/bin:\$PATH
$PYTHON run_demo.py --clear-db
echo ''
echo '══════════════════════════════════════════════════════════'
echo '  Demo complete! You can review the results above.'
echo '  Results saved to:'
echo '    - attack_results.db  (SQLite)'
echo '    - results_summary.json'
echo '══════════════════════════════════════════════════════════'
echo ''
echo 'Press Enter to close...'
read
"

launch_in_terminal "SCEL - Attack Engine" "$ATTACK_CMD" "$TERM_EMU"

# ── Terminal 4: Engine API Server (port 5002) ────────────────────────────────
echo -e "${YELLOW}[4/4] Starting Engine API Server (port 5002)...${NC}"

ENGINE_CMD="
echo '══════════════════════════════════════════════════════════'
echo '  SCEL — Engine API Server'
echo '  Port: 5002'
echo '══════════════════════════════════════════════════════════'
echo ''
cd $PROJECT_DIR/Attack_Engine
export PATH=$CONDA_ENV/bin:\$PATH
$PYTHON engine_api.py
echo ''
echo 'Press Enter to close...'
read
"

launch_in_terminal "SCEL - Engine API" "$ENGINE_CMD" "$TERM_EMU"

# ── Done ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   All 4 components launched!                             ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║   Terminal 1: Target Webapp     → http://localhost:5000   ║${NC}"
echo -e "${GREEN}║   Terminal 2: Metrics Dashboard → http://localhost:5001   ║${NC}"
echo -e "${GREEN}║   Terminal 3: Attack Engine     → running demo...        ║${NC}"
echo -e "${GREEN}║   Terminal 4: Engine API        → http://localhost:5002   ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║   Close terminals to stop the servers.                   ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
