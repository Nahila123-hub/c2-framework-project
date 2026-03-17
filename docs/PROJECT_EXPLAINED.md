# C2 Framework — Complete Code Documentation

## Project Overview

This is a **Command and Control (C2) Framework** built for educational purposes. It lets a central server control multiple remote agents. The system has 5 main components:

```
                    ┌──────────────────────┐
                    │   DASHBOARD (HTML)   │  ◄── You monitor everything here
                    │   dashboard.html     │
                    └──────────┬───────────┘
                               │ HTTP (fetch API)
                               ▼
┌──────────────────────────────────────────────────────────┐
│                   C2 SERVER (FastAPI)                     │
│                   server_async.py                         │
│  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌────────────┐  │
│  │ Register │  │ Commands │  │ Output │  │   Logs     │  │
│  │ Agents   │  │ Queue    │  │ Store  │  │   Store    │  │
│  └─────────┘  └──────────┘  └────────┘  └────────────┘  │
│                     SQLite Database                       │
└──────────────────────┬───────────────────────────────────┘
                       │ HTTP (requests library)
                       ▼
              ┌─────────────────┐
              │   AGENT (Python) │  ◄── Runs on target machine
              │   agent.py       │
              └────────┬────────┘
                       │ uses
                       ▼
              ┌─────────────────┐
              │  ENCRYPTION      │  ◄── Secures all data
              │  crypto.py       │
              └────────┬────────┘
                       │ used by
                       ▼
              ┌─────────────────┐
              │  PROTOCOL        │  ◄── Message format layer
              │  protocol.py     │
              └─────────────────┘
```

---

## File-by-File Explanation

---

### 1. `encryption/crypto.py` — Encryption Module

**Purpose:** Handles all encryption, decryption, key generation, and message signing.

**Libraries Used:**
- `cryptography` — for AES-GCM encryption and PBKDF2 key derivation
- `hmac` + `hashlib` — for HMAC-SHA256 message signing

**How It Works:**

The module has two keys defined at the top:
```python
SECRET_KEY = b'0123456789abcdef'    # 16-byte AES key for encryption
HMAC_KEY = b'c2-hmac-signing-key-2024'   # Key for signing messages
```

**Functions:**

| Function | Input | Output | What It Does |
|---|---|---|---|
| `derive_key(password, salt)` | A password string + optional salt | (key, salt) tuple | Generates a secure 128-bit AES key from a human password using **PBKDF2-HMAC-SHA256** with 100,000 iterations. If no salt is given, it creates a random 16-byte salt |
| `encrypt_message(message, key)` | Bytes to encrypt + optional key | Base64 string | Encrypts using **AES-GCM**. Generates a random 12-byte nonce, encrypts the data, prepends the nonce to the ciphertext, then base64-encodes everything |
| `decrypt_message(encoded, key)` | Base64 string + optional key | Original bytes | Reverses the encryption — base64-decodes, separates the 12-byte nonce, then AES-GCM decrypts |
| `sign_message(data, key)` | Bytes to sign | Hex string (64 chars) | Creates an **HMAC-SHA256** hash of the data — a digital signature proving the message hasn't been tampered with |
| `verify_signature(data, sig, key)` | Bytes + signature string | True/False | Recalculates HMAC and compares with the given signature using `hmac.compare_digest` (timing-safe comparison) |
| `secure_encrypt(message)` | Bytes | Dict `{ciphertext, signature}` | **Combines** encryption + signing in one call — first encrypts, then signs the ciphertext |
| `secure_decrypt(ciphertext, sig)` | Ciphertext + signature | Original bytes | **Combines** verify + decrypt — first verifies signature, then decrypts. Raises `ValueError` if tampered |

**Encryption Flow:**
```
Original Message
       │
       ▼
  [AES-GCM Encrypt]  ──►  nonce + ciphertext
       │
       ▼
  [Base64 Encode]  ──►  base64 string
       │
       ▼
  [HMAC-SHA256 Sign]  ──►  signature hex string
       │
       ▼
  Output: { ciphertext: "...", signature: "..." }
```

---

### 2. `communication/protocol.py` — Communication Protocol

**Purpose:** Provides a structured message format (envelope) for all communication between the agent and server.

**How It Works:**

Every message is wrapped in a JSON envelope that looks like this:
```json
{
    "msg_type": "heartbeat",
    "timestamp": 1710612000,
    "ciphertext": "base64_encrypted_payload...",
    "signature": "hmac_sha256_hex_string..."
}
```

**Functions:**

| Function | What It Does |
|---|---|
| `build_message(msg_type, payload)` | Takes a message type (like `"register"`, `"heartbeat"`, `"command"`) and a payload dict. Encrypts the payload, signs it, wraps everything in a JSON envelope with a timestamp |
| `parse_message(raw_message)` | Takes a JSON envelope string. Verifies the HMAC signature, decrypts the payload, and returns `{msg_type, timestamp, payload}`. Raises `ValueError` if the message has been tampered with |
| `encrypt_payload(payload)` | Simpler version — just encrypts a dict and returns `{ciphertext, signature}` for use with HTTP endpoints |
| `decrypt_payload(data)` | Reverses `encrypt_payload` — verifies signature and decrypts back to original dict |

**Message Flow:**
```
Agent wants to send data:
  payload = {"hostname": "PC-01", "user": "admin"}
       │
       ▼
  build_message("register", payload)
       │
       ▼
  JSON envelope with encrypted + signed data
       │
  ─── sent over HTTP ───
       │
       ▼
  Server receives JSON envelope
       │
       ▼
  parse_message(raw)
       │
       ▼
  Verified + decrypted payload
```

---

### 3. `server/server_async.py` — C2 Server (FastAPI)

**Purpose:** The central brain of the C2 framework. It manages agents, stores commands, receives outputs, serves the dashboard, and logs all activity.

**Framework:** FastAPI (async Python web framework)
**Database:** SQLite (stored at `data/c2server.db`)
**ORM:** SQLAlchemy

#### Database Tables

| Table | Columns | Purpose |
|---|---|---|
| `agents` | agent_id, hostname, username, os_name, ip_address, registered_at, last_seen | Stores all registered agents and their info |
| `commands` | id, agent_id, command, timestamp, status | Queue of commands waiting to be picked up by agents. Status is `pending` → `sent` |
| `outputs` | id, agent_id, command, output, timestamp | Stores the output that agents send back after executing commands |
| `logs` | id, timestamp, agent_id, event_type, detail | Records every activity (registration, commands, outputs, uploads) |

#### All API Endpoints (21 Routes)

##### Agent Management
| Endpoint | Method | What It Does |
|---|---|---|
| `GET /` | GET | Returns `{"message": "C2 Server Running", "version": "2.0"}` — confirms server is alive |
| `POST /register` | POST | Agent sends its info (hostname, username, OS, IP). Server stores it in the `agents` table. If already registered, updates the info and marks re-registration |
| `POST /heartbeat` | POST | Agent sends `{agent_id}` every 10 seconds. Server updates `last_seen` timestamp. This is how the server knows if an agent is online or offline |
| `GET /agents` | GET | Returns list of ALL agents with their details and online/offline status. An agent is "online" if `last_seen` was within the last 30 seconds |
| `GET /status` | GET | Returns a simple dict of `{agent_id: "online"/"offline"}` for all agents |
| `DELETE /agent/{agent_id}` | DELETE | Completely removes an agent and all its commands, outputs, and logs from the database |

##### Command System
| Endpoint | Method | What It Does |
|---|---|---|
| `POST /command` | POST | Operator sends `{agent_id, command}`. The command is stored in the database with status `"pending"` |
| `POST /broadcast` | POST | Sends the same command to ALL registered agents at once |
| `GET /get_command/{agent_id}` | GET | The agent polls this endpoint. If there's a pending command, the server returns it and marks status as `"sent"`. If no command, returns empty string |

##### Output & History
| Endpoint | Method | What It Does |
|---|---|---|
| `POST /send_output` | POST | Agent sends back `{agent_id, command, output}` after executing a command. Stored in the `outputs` table |
| `GET /outputs` | GET | Returns the latest 100 command outputs (newest first) |
| `GET /history` | GET | Returns command/output history. Can filter by `?agent_id=xxx` for a specific agent |

##### File Operations
| Endpoint | Method | What It Does |
|---|---|---|
| `POST /upload` | POST | Agent uploads a file (multipart form). File is saved in the `data/` folder |
| `GET /download/{filename}` | GET | Agent downloads a file from the `data/` folder |

##### Logs & Dashboard
| Endpoint | Method | What It Does |
|---|---|---|
| `GET /logs` | GET | Returns the latest activity log entries. Use `?limit=50` to control how many |
| `GET /dashboard` | GET | Returns JSON stats: total agents, online count, offline count, pending commands |
| `GET /dashboard_page` | GET | Serves the `dashboard.html` file directly in the browser |

#### How the Server Handles a Command

```
1. Operator types "whoami" in dashboard → POST /command {agent_id, "whoami"}
2. Server stores command in DB with status="pending"
3. Agent polls GET /get_command/{agent_id}
4. Server returns {"command": "whoami"}, sets status="sent"
5. Agent executes whoami, gets output "admin@PC-01"
6. Agent sends POST /send_output {agent_id, "whoami", "admin@PC-01"}
7. Server stores output in DB
8. Dashboard auto-refreshes and shows the output in the terminal
```

#### Online/Offline Detection
```
Agent sends heartbeat every 10 seconds → POST /heartbeat
Server records last_seen = current timestamp

When checking status:
  if (current_time - last_seen < 30 seconds) → ONLINE (green badge)
  else → OFFLINE (red badge)
```

---

### 4. `agent/agent.py` — C2 Agent

**Purpose:** The client-side program that runs on the target machine. It connects to the server, reports system info, listens for commands, and sends back results.

**Class: `C2Agent`**

#### Agent Lifecycle

```
┌─────────────────┐
│  1. START        │  python agent.py --server http://server:8000
└────────┬────────┘
         ▼
┌─────────────────┐
│  2. LOAD ID      │  Reads from .agent_id file (or creates new UUID)
└────────┬────────┘
         ▼
┌─────────────────┐
│  3. REGISTER     │  POST /register with hostname, username, OS, IP
│                  │  Retries with exponential backoff (5s → 10s → 20s → ... → 60s max)
└────────┬────────┘
         ▼
┌─────────────────┐
│  4. HEARTBEAT    │  Background thread sends POST /heartbeat every 10s
│  (Thread)        │
└────────┬────────┘
         ▼
┌─────────────────┐
│  5. POLL LOOP    │  Main thread polls GET /get_command every 5s
│                  │  If command found → execute → send output back
│                  │  If "exit" command → shutdown
└─────────────────┘
```

#### Agent ID Persistence
The agent saves its UUID to a file called `.agent_id` in the `agent/` folder. This means:
- If you restart the agent, it keeps the **same ID** (doesn't create a duplicate in the server)
- The server recognizes it as the same agent
- If you delete `.agent_id`, the agent will get a new identity

#### Built-in Commands

| Command | What It Does |
|---|---|
| `sysinfo` | Returns full system info: hostname, username, OS, IP, architecture, processor, Python version |
| `whoami` | Returns `username@hostname` |
| `pwd` | Returns current working directory |
| `ls [path]` | Lists files and folders with sizes. Default is current directory |
| `cd <path>` | Changes the agent's working directory |
| `ps` | Lists running processes (uses `tasklist` on Windows, `ps aux` on Linux) |
| `env` | Shows environment variables |
| `net` | Shows network configuration (`ipconfig` on Windows, `ifconfig` on Linux) |
| `download <file>` | Sends a file FROM the agent machine TO the server (file exfiltration) |
| `upload <file>` | Pulls a file FROM the server TO the agent machine |
| `help` | Shows the list of all available commands |
| `exit` | Gracefully shuts down the agent |
| `<anything else>` | Runs as a **shell command** (e.g., `dir`, `cat /etc/passwd`, `netstat -an`) with 30-second timeout |

#### Command Execution Flow

```
Agent polls: GET /get_command/abc-123
                │
                ▼
         Command: "whoami"
                │
                ▼
     execute_command("whoami")
                │
                ▼
     Routes to handle_whoami()
                │
                ▼
     Returns: "admin@DESKTOP-PC"
                │
                ▼
     POST /send_output {agent_id, "whoami", "admin@DESKTOP-PC"}
```

For unknown commands (like `ipconfig /all`):
```
     execute_command("ipconfig /all")
                │
                ▼
     Not a built-in → execute_shell("ipconfig /all")
                │
                ▼
     subprocess.run("ipconfig /all", shell=True, timeout=30)
                │
                ▼
     Returns stdout + stderr (limited to 5000 chars)
```

---

### 5. `dashboard/dashboard.html` — Web Dashboard

**Purpose:** A real-time web interface to monitor and control all agents from your browser.

**Technology:** Single HTML file with embedded CSS + JavaScript (no frameworks needed)

**Design:** Dark theme with cyberpunk/hacker aesthetic — dark navy background, neon green/cyan accents, monospace fonts (JetBrains Mono)

#### Dashboard Sections

**① Header Bar** (top, sticky)
- C2 logo + "COMMAND CENTER" title
- "SERVER ONLINE" status with animated pulsing green dot

**② Stats Cards** (4 cards in a row)
- **Total Agents** (cyan) — total number of agents that ever registered
- **Online** (green) — agents that sent a heartbeat in the last 30 seconds
- **Offline** (red) — agents that haven't sent a heartbeat in 30+ seconds
- **Pending Commands** (orange) — commands queued but not yet picked up by agents
- Values animate with a scale effect when they change

**③ Connected Agents Table**
- Shows: Agent ID, Hostname, Username, OS, IP, Status (green/red badge), Last Seen
- **CMD button** — Selects that agent in the command dropdown
- **✕ button** — Removes the agent (with confirmation)

**④ Send Command Panel**
- **Target Agent dropdown** — Select a specific agent OR "Broadcast (All Agents)"
- **Command input** — Type any command (press Enter or click SEND)
- Shows list of built-in commands below the input

**⑤ Activity Logs Panel**
- Shows timestamped events: registrations, commands sent, outputs received, file uploads, broadcasts
- Color-coded by type (cyan = register, purple = command, green = output, orange = upload, red = broadcast)

**⑥ Output Console** (bottom, full width)
- Terminal-style display showing command outputs from agents
- Shows: timestamp, agent ID, command that was run, and the output
- Has a CLEAR button to reset the console

#### How the Dashboard Works (JavaScript)

The dashboard uses the browser's `fetch()` API to talk to the server:

```
Every 5 seconds, the dashboard calls:
  ├── GET /dashboard     → Updates the 4 stat cards
  ├── GET /agents        → Updates the agents table + dropdown
  ├── GET /outputs       → Adds new outputs to the terminal
  └── GET /logs?limit=30 → Updates the activity logs
```

**Auto-refresh:** `setInterval(refreshAll, 5000)` runs all 4 API calls every 5 seconds

**Send command flow:**
```
User types "sysinfo" in input → clicks SEND
    │
    ├── If target = "broadcast" → POST /broadcast {"command": "sysinfo"}
    │
    └── If target = specific agent → POST /command {"agent_id": "...", "command": "sysinfo"}
    │
    ▼
Dashboard immediately refreshes stats and logs
After 5 seconds, output appears in the terminal (agent processed and responded)
```

---

## How Everything Works Together

### Complete Flow: From Starting the Server to Seeing Output

```
STEP 1: Start the Server
    $ python -m uvicorn server.server_async:app --host 0.0.0.0 --port 8000
    → Server starts on port 8000
    → SQLite database created at data/c2server.db

STEP 2: Open the Dashboard
    → Visit http://localhost:8000/dashboard_page
    → Dashboard loads, shows 0 agents

STEP 3: Start the Agent
    $ python agent/agent.py --server http://127.0.0.1:8000
    → Agent generates UUID and saves to .agent_id
    → Agent sends POST /register with system info
    → Server stores agent in database
    → Dashboard shows 1 agent (ONLINE, green badge)

STEP 4: Agent Starts Working
    → Agent starts heartbeat thread (POST /heartbeat every 10s)
    → Agent starts polling for commands (GET /get_command every 5s)

STEP 5: Send a Command
    → In dashboard, type "sysinfo" and click SEND
    → Server stores command with status="pending"
    → Dashboard shows "1" in Pending Commands card

STEP 6: Agent Executes
    → Agent's next poll picks up the command
    → Agent runs sysinfo handler
    → Agent sends output back via POST /send_output
    → Dashboard shows output in the terminal console
    → Activity logs show the command and output events
```

---

## Technologies Used

| Technology | Where Used | Purpose |
|---|---|---|
| **Python 3** | Server, Agent, Crypto, Protocol | Main programming language |
| **FastAPI** | Server | Async web framework for REST API |
| **Uvicorn** | Server | ASGI server to run FastAPI |
| **SQLAlchemy** | Server | ORM for SQLite database |
| **SQLite** | Server | Lightweight database (single file) |
| **Pydantic** | Server | Data validation for API requests |
| **cryptography** | Crypto module | AES-GCM encryption and PBKDF2 |
| **requests** | Agent | HTTP client to talk to the server |
| **HTML/CSS/JS** | Dashboard | Web interface (single file) |
| **JetBrains Mono** | Dashboard | Monospace font for terminal look |

---

## How to Run

### Prerequisites
```bash
pip install cryptography fastapi uvicorn sqlalchemy python-multipart requests
```

### Step 1: Start the Server
```bash
cd c2-framework-project
python -m uvicorn server.server_async:app --host 0.0.0.0 --port 8000
```

### Step 2: Open Dashboard
Open your browser and go to: `http://localhost:8000/dashboard_page`

### Step 3: Start Agent (in a new terminal)
```bash
cd c2-framework-project
python agent/agent.py --server http://127.0.0.1:8000
```

### Step 4: Send Commands
Use the dashboard to send commands like `sysinfo`, `whoami`, `ls`, `ps`, etc.

---

## Project File Structure

```
c2-framework-project/
│
├── server/
│   ├── server_async.py      ← Main C2 server (FastAPI + SQLite)
│   └── server.py            ← Old Flask server (legacy, not used)
│
├── agent/
│   ├── agent.py             ← C2 agent program
│   └── .agent_id            ← Auto-generated agent UUID (created at runtime)
│
├── encryption/
│   └── crypto.py            ← AES-GCM encryption + HMAC signing
│
├── communication/
│   └── protocol.py          ← Message envelope protocol
│
├── dashboard/
│   └── dashboard.html       ← Web dashboard (HTML + CSS + JS)
│
├── data/
│   └── c2server.db          ← SQLite database (created at runtime)
│
├── docs/
│   └── PROJECT_EXPLAINED.md ← This file — full documentation
│
├── logs/                    ← Reserved for future log files
├── tests/                   ← Reserved for test scripts
├── scripts/                 ← Reserved for utility scripts
│
├── README.md                ← Project overview
└── .gitignore
```

---

## Disclaimer

This project is developed **only for educational and research purposes** in a controlled environment. It should be used only in authorized lab setups and never for unauthorized or harmful activities.
