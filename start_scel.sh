#!/bin/bash
# ============================================================================
#   SCEL - Security Chaos Engineering Lab
#   One-click launcher — opens 4 components in a tmux session
# ============================================================================

PROJECT_DIR="/home/bloop/Downloads/SCEL-Security-Chaos-Engineering-Lab"
CONDA_ENV="/home/bloop/Downloads/miniconda3"
PYTHON="$CONDA_ENV/bin/python"
SESSION_NAME="scel_demo"

# ── Colors for output ───────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================================================
#   MAIN
# ============================================================================

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   SCEL - Security Chaos Engineering Lab                  ║${NC}"
echo -e "${CYAN}║   Starting all components (tmux mode)                    ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ── Check conda env exists ──────────────────────────────────────────────────
if [ ! -f "$PYTHON" ]; then
    echo -e "${RED}ERROR: Conda Python not found at $PYTHON${NC}"
    echo "Install Miniconda: bash /home/bloop/Downloads/miniconda.sh -b -p $CONDA_ENV"
    exit 1
fi

if ! command -v tmux &> /dev/null; then
    echo -e "${RED}ERROR: tmux is not installed. Please install it (e.g., sudo apt install tmux)${NC}"
    exit 1
fi

# ── Check symlink exists ────────────────────────────────────────────────────
if [ ! -L "$PROJECT_DIR/app" ]; then
    echo -e "${YELLOW}Creating 'app' symlink → Target_webapp ...${NC}"
    ln -sfn Target_webapp "$PROJECT_DIR/app"
fi

# Kill existing session if it exists
tmux kill-session -t $SESSION_NAME 2>/dev/null

echo -e "${YELLOW}Starting services in tmux session '$SESSION_NAME'...${NC}"

# ── Terminal 1: Target Web Application (port 5000) ──────────────────────────
WEBAPP_CMD="echo -e '\033[1;33m  SCEL — Target Web Application\033[0m'; echo '  Port: 5000'; echo ''; cd $PROJECT_DIR && export PATH=$CONDA_ENV/bin:\$PATH && $PYTHON -m app.app; echo ''; echo 'Press Enter to close...'; read"

tmux new-session -d -s $SESSION_NAME -n "SCEL" "bash -c \"$WEBAPP_CMD\""

# ── Terminal 2: Metrics Dashboard (port 5001) ───────────────────────────────
METRICS_CMD="echo -e '\033[1;33m  SCEL — Metrics Dashboard\033[0m'; echo '  Port: 5001'; echo '  Open in browser: http://localhost:5001'; echo ''; cd $PROJECT_DIR/Metrics && export PATH=$CONDA_ENV/bin:\$PATH && $PYTHON app.py; echo ''; echo 'Press Enter to close...'; read"

tmux split-window -h -t $SESSION_NAME:0 "bash -c \"$METRICS_CMD\""

# ── Terminal 3: Attack Simulation Engine ────────────────────────────────────
ATTACK_CMD="echo -e '\033[1;33m  SCEL — Attack Simulation Engine\033[0m'; echo ''; cd $PROJECT_DIR/Attack_Engine && export PATH=$CONDA_ENV/bin:\$PATH && $PYTHON run_demo.py --clear-db; echo ''; echo -e '\033[1;32m  Demo complete! Results saved to:\033[0m'; echo '    - attack_results.db'; echo '    - results_summary.json'; echo ''; echo 'Press Enter to close...'; read"

tmux split-window -v -t $SESSION_NAME:0.0 "bash -c \"$ATTACK_CMD\""

# ── Terminal 4: Engine API Server (port 5002) ────────────────────────────────
ENGINE_CMD="echo -e '\033[1;33m  SCEL — Engine API Server\033[0m'; echo '  Port: 5002'; echo ''; cd $PROJECT_DIR/Attack_Engine && export PATH=$CONDA_ENV/bin:\$PATH && $PYTHON engine_api.py; echo ''; echo 'Press Enter to close...'; read"

tmux split-window -v -t $SESSION_NAME:0.2 "bash -c \"$ENGINE_CMD\""

# Adjust pane layout to 4 even panes
tmux select-layout -t $SESSION_NAME tiled

# ── Done ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   All 4 components launched!                             ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║   [Pane 1] Target Webapp     → http://localhost:5000      ║${NC}"
echo -e "${GREEN}║   [Pane 2] Metrics Dashboard → http://localhost:5001      ║${NC}"
echo -e "${GREEN}║   [Pane 3] Attack Engine     → running demo...           ║${NC}"
echo -e "${GREEN}║   [Pane 4] Engine API        → http://localhost:5002      ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║   Attaching to tmux session...                           ║${NC}"
echo -e "${GREEN}║   (Press Ctrl+B, then D to detach)                       ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
sleep 2

tmux attach-session -t $SESSION_NAME
