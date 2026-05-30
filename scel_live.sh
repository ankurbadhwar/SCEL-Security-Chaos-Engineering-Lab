#!/bin/bash
# ============================================================================
#   SCEL - Security Chaos Engineering Lab
#   API-Driven Mode — no automatic attack demo
#
#   Starts 3 services in a tmux session and waits for dashboard/API commands:
#     - Target Webapp   → http://localhost:5000
#     - Metrics Dashboard → http://localhost:5001  (trigger attacks from here)
#     - Engine API      → http://localhost:5002  (REST control plane)
#
#   Attacks are triggered ONLY via the Metrics Dashboard or Engine API.
#   Nothing runs automatically.
# ============================================================================

PROJECT_DIR="/home/bloop/Downloads/SCEL-Security-Chaos-Engineering-Lab"
CONDA_ENV="/home/bloop/Downloads/miniconda3"
PYTHON="$CONDA_ENV/bin/python"
SESSION_NAME="scel_live"

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================================
#   MAIN
# ============================================================================

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   SCEL — Security Chaos Engineering Lab                  ║${NC}"
echo -e "${CYAN}║   API-Driven Mode (tmux)                                 ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ── Checks ───────────────────────────────────────────────────────────────────
if [ ! -f "$PYTHON" ]; then
    echo -e "${RED}ERROR: Conda Python not found at $PYTHON${NC}"
    exit 1
fi

if ! command -v tmux &> /dev/null; then
    echo -e "${RED}ERROR: tmux is not installed. Please install it (e.g., sudo apt install tmux)${NC}"
    exit 1
fi

if [ ! -L "$PROJECT_DIR/app" ]; then
    echo -e "${YELLOW}Creating 'app' symlink → Target_webapp ...${NC}"
    ln -sfn Target_webapp "$PROJECT_DIR/app"
fi

# Kill existing session if it exists
tmux kill-session -t $SESSION_NAME 2>/dev/null

echo -e "${YELLOW}Starting services in tmux session '$SESSION_NAME'...${NC}"

# ── Target Webapp (Pane 0) ───────────────────────────────────────────────────
WEBAPP_CMD="echo -e '\033[1;33m  SCEL — Target Web Application\033[0m'; echo '  Port: 5000   →   http://localhost:5000'; echo ''; cd $PROJECT_DIR && export PATH=$CONDA_ENV/bin:\$PATH && $PYTHON -m app.app; echo ''; echo 'Press Enter to close...'; read"

tmux new-session -d -s $SESSION_NAME -n "SCEL" "bash -c \"$WEBAPP_CMD\""

# ── Metrics Dashboard (Pane 1) ───────────────────────────────────────────────
METRICS_CMD="echo -e '\033[1;33m  SCEL — Metrics Dashboard\033[0m'; echo '  Port: 5001   →   http://localhost:5001'; echo ''; cd $PROJECT_DIR/Metrics && export PATH=$CONDA_ENV/bin:\$PATH && $PYTHON app.py; echo ''; echo 'Press Enter to close...'; read"

tmux split-window -h -t $SESSION_NAME:0 "bash -c \"$METRICS_CMD\""

# ── Engine API (Pane 2) ──────────────────────────────────────────────────────
ENGINE_CMD="echo -e '\033[1;33m  SCEL — Engine API Server\033[0m'; echo '  Port: 5002   →   http://localhost:5002'; echo ''; cd $PROJECT_DIR/Attack_Engine && export PATH=$CONDA_ENV/bin:\$PATH && $PYTHON engine_api.py; echo ''; echo 'Press Enter to close...'; read"

tmux split-window -v -t $SESSION_NAME:0.1 "bash -c \"$ENGINE_CMD\""

# Adjust pane layout
tmux select-layout -t $SESSION_NAME tiled

# ── Open Browser ─────────────────────────────────────────────────────────────
(
    sleep 3
    if command -v xdg-open &> /dev/null; then
        xdg-open "http://localhost:5001" &
    elif command -v firefox &> /dev/null; then
        firefox "http://localhost:5001" &
    elif command -v chromium-browser &> /dev/null; then
        chromium-browser "http://localhost:5001" &
    fi
) &

echo -e "${GREEN}Services started! Attaching to tmux session...${NC}"
echo -e "${GREEN}(Press Ctrl+B, then D to detach from tmux and leave services running)${NC}"
sleep 2

tmux attach-session -t $SESSION_NAME
