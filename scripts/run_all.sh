#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  C2 Framework — Run All (Server + Dashboard + 10 Agents)
#  Usage: chmod +x run_all.sh && ./run_all.sh
# ═══════════════════════════════════════════════════════════════

set -e

echo ""
echo " ╔════════════════════════════════════════════════════════════╗"
echo " ║         C2 FRAMEWORK — FULL STACK LAUNCHER                ║"
echo " ║     Server + Dashboard + 10 Simulated Agents              ║"
echo " ╚════════════════════════════════════════════════════════════╝"
echo ""

# ── Set project root ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# ── Check Python ──
if ! command -v python3 &> /dev/null; then
    echo " [ERROR] Python3 is not installed."
    echo " Please install Python 3.8+ first."
    exit 1
fi

# ── Create directories ──
mkdir -p data logs

# ── Cleanup function ──
PIDS=()
cleanup() {
    echo ""
    echo " ⏹️  Shutting down all components..."
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo " [✓] Stopped PID $pid"
        fi
    done
    echo " All components stopped. Goodbye!"
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── 1. Start Server ──
echo " [1/3] Starting C2 Server (FastAPI + Uvicorn)..."
echo "       URL: http://127.0.0.1:8000"
echo ""
python3 -m uvicorn server.server_async:app --host 127.0.0.1 --port 8000 --reload &
PIDS+=($!)
sleep 4

# ── 2. Open Dashboard ──
echo " [2/3] Opening Dashboard in browser..."
echo "       URL: http://127.0.0.1:8000/dashboard_page"
echo ""
if command -v xdg-open &> /dev/null; then
    xdg-open "http://127.0.0.1:8000/dashboard_page" 2>/dev/null &
elif command -v open  &> /dev/null; then
    open "http://127.0.0.1:8000/dashboard_page" 2>/dev/null &
fi
sleep 2

# ── 3. Launch Agents ──
echo " [3/3] Launching 10 Simulated Agents..."
echo ""
python3 scripts/launch_agents.py --server http://127.0.0.1:8000 --delay 0.5 &
PIDS+=($!)

echo ""
echo " ═══════════════════════════════════════════════════════════════"
echo "  ✅  ALL COMPONENTS STARTED!"
echo " ═══════════════════════════════════════════════════════════════"
echo ""
echo "  Server:    http://127.0.0.1:8000"
echo "  Dashboard: http://127.0.0.1:8000/dashboard_page"
echo "  API Docs:  http://127.0.0.1:8000/docs"
echo ""
echo "  Default API Key: c2-default-api-key-change-me"
echo ""
echo "  Press Ctrl+C to stop everything."
echo ""

# Wait for all background processes
wait
