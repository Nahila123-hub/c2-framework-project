@echo off
REM ═══════════════════════════════════════════════════════════════
REM  C2 Framework — Run All (Server + Dashboard + 10 Agents)
REM  Usage: Double-click this file or run from Command Prompt
REM ═══════════════════════════════════════════════════════════════

echo.
echo  ╔════════════════════════════════════════════════════════════╗
echo  ║         C2 FRAMEWORK — FULL STACK LAUNCHER                ║
echo  ║     Server + Dashboard + 10 Simulated Agents              ║
echo  ╚════════════════════════════════════════════════════════════╝
echo.

REM ── Set project root ──
set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

REM ── Check Python ──
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed or not in PATH.
    echo  Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM ── Create required directories ──
if not exist "data" mkdir data
if not exist "logs" mkdir logs

echo  [1/3] Starting C2 Server (FastAPI + Uvicorn)...
echo        URL: http://127.0.0.1:8000
echo.
start "C2 Server" cmd /k "cd /d %PROJECT_ROOT% && python -m uvicorn server.server_async:app --host 127.0.0.1 --port 8000 --reload"

echo  Waiting 4 seconds for server to start...
timeout /t 4 /nobreak >nul

echo.
echo  [2/3] Opening Dashboard in browser...
echo        URL: http://127.0.0.1:8000/dashboard_page
echo.
start "" http://127.0.0.1:8000/dashboard_page

timeout /t 2 /nobreak >nul

echo  [3/3] Launching 10 Simulated Agents...
echo.
start "C2 Agents" cmd /k "cd /d %PROJECT_ROOT% && python scripts/launch_agents.py --server http://127.0.0.1:8000 --delay 0.5"

echo.
echo  ═══════════════════════════════════════════════════════════════
echo   ✅  ALL COMPONENTS STARTED!
echo  ═══════════════════════════════════════════════════════════════
echo.
echo   ┌──────────────────────────────────────────────────────────┐
echo   │  Server:    http://127.0.0.1:8000                       │
echo   │  Dashboard: http://127.0.0.1:8000/dashboard_page        │
echo   │  API Docs:  http://127.0.0.1:8000/docs                  │
echo   │                                                          │
echo   │  Default API Key: c2-default-api-key-change-me           │
echo   │                                                          │
echo   │  Close the Server window to stop everything.             │
echo   │  Close the Agents window to stop all agents.             │
echo   └──────────────────────────────────────────────────────────┘
echo.
pause
