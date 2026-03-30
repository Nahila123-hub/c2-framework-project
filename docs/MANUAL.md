# C2 Framework — Operations Manual

> **Version:** 3.0 | **Last Updated:** March 2026

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Project Structure](#2-project-structure)
3. [Quick Start (One Command)](#3-quick-start)
4. [Step-by-Step Launch](#4-step-by-step-launch)
5. [Dashboard Guide](#5-dashboard-guide)
6. [Agent Commands Reference](#6-agent-commands)
7. [Configuration](#7-configuration)
8. [Multi-Agent Launcher](#8-multi-agent-launcher)
9. [Encryption & Security](#9-encryption--security)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.8+ | Core runtime |
| pip | Latest | Package manager |
| Git | Any | Version control |

### Install Python Dependencies

Open a terminal in the project root and run:

```bash
pip install fastapi uvicorn sqlalchemy requests cryptography pydantic
```

**Optional** (for screenshot command):
```bash
pip install Pillow
```

### Verify Installation

```bash
python --version            # Should show 3.8+
python -c "import fastapi"  # Should exit silently (no error)
python -c "import cryptography"  # Should exit silently
```

---

## 2. Project Structure

```
c2-framework-project/
├── agent/
│   ├── agent.py            # C2 Agent (connects to server, executes commands)
│   └── .agent_id            # Auto-generated unique agent ID
├── communication/
│   └── protocol.py          # Encrypted message protocol layer
├── dashboard/
│   └── dashboard.html       # Web dashboard (served by server)
├── data/
│   └── c2server.db          # SQLite database (auto-created)
├── docs/
│   └── MANUAL.md            # ← This file
├── encryption/
│   └── crypto.py            # AES-256-GCM encryption + HMAC signing
├── logs/
│   ├── agent.log            # Agent activity log
│   └── server.log           # Server activity log
├── scripts/
│   ├── launch_agents.py     # Spawns 10 simulated agents
│   ├── run_all.bat          # One-click Windows launcher
│   └── run_all.sh           # One-click Linux/Mac launcher
├── server/
│   └── server_async.py      # FastAPI C2 server (async)
├── tests/
│   └── test_all.py          # Unit tests for all modules
└── README.md
```

---

## 3. Quick Start

### Windows (Recommended)

**Double-click** `scripts/run_all.bat` or run from Command Prompt:

```cmd
cd c2-framework-project
scripts\run_all.bat
```

This will:
1. ✅ Start the C2 Server on `http://127.0.0.1:8000`
2. ✅ Open the Dashboard in your browser
3. ✅ Launch 10 simulated agents with unique identities

### Linux / macOS

```bash
cd c2-framework-project
chmod +x scripts/run_all.sh
./scripts/run_all.sh
```

### Login to Dashboard

When the dashboard opens, enter the **API Key**:

```
c2-default-api-key-change-me
```

*(This is the default key — see [Configuration](#7-configuration) to change it)*

---

## 4. Step-by-Step Launch

If you prefer to run each component individually:

### Step 1: Start the Server

```bash
cd c2-framework-project
python -m uvicorn server.server_async:app --host 127.0.0.1 --port 8000 --reload
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Started reloader process
```

### Step 2: Open the Dashboard

Open a browser and go to:
```
http://127.0.0.1:8000/dashboard_page
```

Login with the API key: `c2-default-api-key-change-me`

### Step 3: Launch Agents

**Option A — Launch 10 simulated agents:**
```bash
python scripts/launch_agents.py
```

**Option B — Launch a single real agent:**
```bash
python agent/agent.py --server http://127.0.0.1:8000
```

**Option C — Launch with encryption:**
```bash
python agent/agent.py --server http://127.0.0.1:8000 --encrypted
```

**Option D — Launch a custom agent:**
```bash
python agent/agent.py --server http://127.0.0.1:8000 --hostname MY-PC --username admin --os-name "Windows 11" --ip 10.0.0.100
```

### Step 4: Send Commands

From the dashboard:
1. Select a target agent (or "Broadcast All")
2. Type a command (e.g., `sysinfo`)
3. Choose priority (Normal / High / Urgent)
4. Click **SEND ▶**
5. Watch the output appear in the **Output Console**

---

## 5. Dashboard Guide

### Dashboard Layout

| Section | Description |
|---------|-------------|
| **Stats Cards** | Total agents, Online count, Offline count, Pending commands |
| **Connected Agents** | Table of all registered agents with status |
| **Send Command** | Command input with target selection and priority |
| **Activity Logs** | Real-time log of all events (register, command, output) |
| **Output Console** | Terminal-style display of command results |

### Agent Table Actions

| Button | Action |
|--------|--------|
| **CMD** | Quick-select this agent as command target |
| **🔍** | Open agent detail modal (info + command history + tags) |
| **✕** | Delete agent and all its data |

### Agent Detail Modal

Double-click any agent row (or click 🔍) to see:
- Full Agent ID, hostname, username, OS, IP, status
- **Tags** — edit comma-separated tags (e.g., `windows,finance,hq`)
- **Command History** — last 30 commands and their outputs

### Export Logs

Click **📥 JSON** or **📥 CSV** in the Activity Logs panel to download all logs.

---

## 6. Agent Commands

| Command | Description |
|---------|-------------|
| `sysinfo` | Detailed system information |
| `whoami` | Current user@hostname |
| `pwd` | Current working directory |
| `ls [path]` | List directory contents |
| `cd <path>` | Change working directory |
| `ps` | List running processes |
| `env` | Show environment variables |
| `net` | Network configuration (ipconfig/ifconfig) |
| `diskinfo` | Disk usage statistics |
| `screenshot` | Capture screen (requires Pillow) |
| `persist` | Add agent to system startup |
| `download <file>` | Exfiltrate file from agent to server |
| `upload <file>` | Download file from server to agent |
| `help` | Show available commands |
| `exit` | Shutdown the agent |
| *anything else* | Executed as a shell command |

### Broadcast vs. Single Target

- **Single Target**: Select specific agent → command runs on that agent only
- **Broadcast**: Select "📢 Broadcast (All Agents)" → command runs on ALL agents
- **Group Command** (API only): Use `/group_command` endpoint with a tag filter

---

## 7. Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `C2_API_KEY` | `c2-default-api-key-change-me` | API authentication key |
| `C2_AES_KEY` | *(dev fallback)* | AES-256 encryption key (32 bytes) |
| `C2_HMAC_KEY` | *(dev fallback)* | HMAC signing key (32 bytes) |

### Set Custom API Key

**Windows:**
```cmd
set C2_API_KEY=my-super-secret-key-2026
```

**Linux/Mac:**
```bash
export C2_API_KEY=my-super-secret-key-2026
```

### Agent Configuration (in `agent/agent.py`)

| Setting | Default | Description |
|---------|---------|-------------|
| `HEARTBEAT_INTERVAL` | 10 seconds | How often agent sends heartbeat |
| `COMMAND_POLL_INTERVAL` | 5 seconds | How often agent checks for commands |
| `DEFAULT_SERVER` | `http://127.0.0.1:8000` | Default server URL |

### Server Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Host | `127.0.0.1` | Bind address |
| Port | `8000` | Listening port |
| Online timeout | 30 seconds | Agent considered offline after this |

---

## 8. Multi-Agent Launcher

### Basic Usage

```bash
python scripts/launch_agents.py
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--server <url>` | `http://127.0.0.1:8000` | Server URL |
| `--count <n>` | `10` | Number of agents (max 10) |
| `--delay <sec>` | `1.0` | Delay between launches |
| `--encrypted` | Off | Use encrypted communication |

### Examples

```bash
# Launch 5 agents with encryption
python scripts/launch_agents.py --count 5 --encrypted

# Launch 10 agents to remote server
python scripts/launch_agents.py --server http://192.168.1.100:8000

# Quick launch with minimal delay
python scripts/launch_agents.py --delay 0.2
```

### Agent Profiles

The 10 simulated agents have these identities:

| # | Hostname | User | OS | IP |
|---|----------|------|----|----|
| 1 | WORKSTATION-01 | john.smith | Windows 11 | 192.168.1.101 |
| 2 | DEVBOX-02 | sarah.dev | Ubuntu 22.04 | 192.168.1.102 |
| 3 | LAPTOP-03 | mike.jones | Windows 10 | 192.168.1.103 |
| 4 | SERVER-04 | root | CentOS 9 | 10.0.0.51 |
| 5 | MACBOOK-05 | alex.mac | macOS 14 | 192.168.1.105 |
| 6 | FINANCE-06 | jessica.fin | Windows 11 | 10.0.1.20 |
| 7 | DBSERVER-07 | admin | Debian 12 | 10.0.0.52 |
| 8 | HR-PC-08 | priya.hr | Windows 10 | 192.168.1.108 |
| 9 | WEBSERVER-09 | www-data | Ubuntu 22.04 | 10.0.0.53 |
| 10 | TESTBOX-10 | qa.test | Kali Linux | 192.168.1.110 |

---

## 9. Encryption & Security

### How Encryption Works

```
Agent                          Server
  │                               │
  │  1. Encrypt payload (AES-256-GCM)
  │  2. Sign ciphertext (HMAC-SHA256)
  │  3. Send {ciphertext, signature}
  │ ─────────────────────────────►│
  │                               │  4. Verify signature
  │                               │  5. Decrypt payload
  │                               │
  │  6. Encrypt response          │
  │ ◄─────────────────────────────│
  │  7. Verify + Decrypt          │
```

### Encrypted vs. Unencrypted Mode

| Feature | Unencrypted | Encrypted (`--encrypted`) |
|---------|-------------|---------------------------|
| Endpoints | `/register`, `/heartbeat`, etc. | `/secure/register`, `/secure/heartbeat`, etc. |
| Data format | Plain JSON | `{ciphertext, signature}` |
| Security | None | AES-256-GCM + HMAC-SHA256 |
| Anti-replay | No | 5-minute window |

### Protocol Layer (`protocol.py`)

The protocol wraps messages in a JSON envelope:
```json
{
    "version": "2.0",
    "msg_type": "command",
    "timestamp": 1710000000,
    "ciphertext": "base64-encoded-AES-encrypted-data",
    "signature": "HMAC-SHA256-hex-signature"
}
```

---

## 10. Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'fastapi'` | Run `pip install fastapi uvicorn sqlalchemy requests cryptography` |
| `Connection refused` on agent | Make sure server is running first |
| Dashboard shows 0 agents | Wait ~10 seconds after launching agents for registration |
| `Address already in use` (port 8000) | Kill existing process: `netstat -ano \| findstr 8000` then `taskkill /F /PID <PID>` |
| Agent shows "offline" | Agent heartbeat may have timed out (>30s). Restart the agent. |
| `Invalid API key` on dashboard | Enter: `c2-default-api-key-change-me` (or your custom key) |
| Encryption errors | Ensure both server and agent use the same keys (env vars) |

### View Logs

```bash
# Server logs
type logs\server.log        # Windows
cat logs/server.log          # Linux/Mac

# Agent logs
type logs\agent.log          # Windows
cat logs/agent.log           # Linux/Mac
```

### Reset Everything

To start fresh, delete the database and logs:

```bash
# Windows
del data\c2server.db
del logs\*.log

# Linux/Mac
rm data/c2server.db
rm logs/*.log
```

### Run Tests

```bash
cd c2-framework-project
python -m pytest tests/test_all.py -v
```

---

## API Endpoints Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | No | Server status |
| POST | `/auth/login` | No | Validate API key |
| POST | `/register` | No | Register agent |
| POST | `/heartbeat` | No | Agent heartbeat |
| GET | `/get_command/{id}` | No | Agent polls for command |
| POST | `/command` | Key | Send command to agent |
| POST | `/broadcast` | Key | Send command to all agents |
| POST | `/group_command` | Key | Send command to tag group |
| POST | `/send_output` | No | Agent sends output |
| GET | `/agents` | Key | List all agents |
| GET | `/outputs` | Key | Get command outputs |
| GET | `/history` | Key | Command history |
| GET | `/logs` | Key | Activity logs |
| GET | `/logs/export` | Key | Export logs (JSON/CSV) |
| POST | `/agent/tags` | Key | Update agent tags |
| DELETE | `/agent/{id}` | Key | Delete agent |
| GET | `/dashboard` | Key | Dashboard stats (JSON) |
| GET | `/dashboard_page` | No | Dashboard HTML page |
| POST | `/upload` | No | Upload file |
| GET | `/download/{file}` | No | Download file |
| POST | `/secure/*` | No | Encrypted equivalents |

---

*Built with ❤️ — C2 Framework Educational Project*
