# C2 Framework Enhancement — Walkthrough

## What Was Done

### 1. Enhanced Encryption Module — [crypto.py](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/encryption/crypto.py)
- **AES-GCM** encrypt/decrypt (kept from original, now supports optional custom keys)
- **PBKDF2** key derivation — [derive_key(password, salt)](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/encryption/crypto.py#16-32) for generating secure keys from passwords
- **HMAC-SHA256** signing — [sign_message()](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/encryption/crypto.py#69-79) / [verify_signature()](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/encryption/crypto.py#81-91) for message integrity
- **Convenience functions** — [secure_encrypt()](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/encryption/crypto.py#95-106) (encrypt + sign) and [secure_decrypt()](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/encryption/crypto.py#108-116) (verify + decrypt)

### 2. Communication Protocol — [protocol.py](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/communication/protocol.py) *(new)*
- [build_message(type, payload)](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/communication/protocol.py#22-42) — wraps data in encrypted JSON envelopes with timestamp + HMAC
- [parse_message(raw)](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/communication/protocol.py#44-72) — verifies signature, decrypts, and returns structured data
- [encrypt_payload()](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/communication/protocol.py#76-88) / [decrypt_payload()](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/communication/protocol.py#90-100) — helpers for HTTP endpoint communication

### 3. FastAPI Server — [server_async.py](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/server/server_async.py) *(rewritten)*
**New DB tables**: [LogDB](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/server/server_async.py#74-81) for activity logging, expanded [AgentDB](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/server/server_async.py#45-54) (ip_address, registered_at), [CommandDB](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/server/server_async.py#56-63) (timestamp, status), [OutputDB](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/server/server_async.py#65-72) (command, timestamp)

**21 API routes** including:
| Endpoint | Method | Purpose |
|---|---|---|
| `/register` | POST | Agent registration |
| `/heartbeat` | POST | Agent heartbeat |
| `/command` | POST | Send command to agent |
| `/broadcast` | POST | Command all agents |
| `/get_command/{id}` | GET | Agent fetches pending command |
| `/send_output` | POST | Agent sends output |
| `/agents` | GET | List all agents + status |
| `/outputs` | GET | View command outputs |
| `/history` | GET | Command/output history |
| `/logs` | GET | Activity log feed |
| `/upload` | POST | File upload from agent |
| `/download/{file}` | GET | File download to agent |
| `/agent/{id}` | DELETE | Remove agent |
| `/dashboard` | GET | Dashboard stats JSON |
| `/dashboard_page` | GET | Serve HTML dashboard |

### 4. C2 Agent — [agent.py](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/agent/agent.py) *(rewritten)*
- **Persistent agent ID** — survives restarts (saved to `.agent_id` file)
- **Heartbeat thread** — pings server every 10s
- **Command polling** — fetches and executes commands every 5s
- **Built-in commands**: `sysinfo`, `whoami`, `pwd`, `ls`, `cd`, `ps`, `env`, `net`, `download`, `upload`, `help`, `exit`
- **Shell fallback** — unknown commands run as OS shell commands
- **Retry logic** — exponential backoff on connection failures
- CLI args support: `python agent.py --server http://192.168.1.100:8000`

### 5. Dashboard — [dashboard.html](file:///c:/Users/Ramashish%20Gupta/OneDrive/Documents/GitHub/c2-framework-project/dashboard/dashboard.html) *(new)*
Dark-themed cybersecurity command center with:
- Stats cards (total/online/offline agents, pending commands)
- Live agents table with CMD and remove buttons
- Command panel with broadcast or per-agent targeting
- Terminal-style output console
- Activity logs feed
- Auto-refreshes every 5 seconds

![Dashboard Screenshot](c2_dashboard_bottom_1773673278945.png)

---

## Verification Results

| Test | Result |
|---|---|
| Crypto: encrypt → decrypt round-trip | ✅ PASSED |
| Crypto: PBKDF2 key derivation | ✅ PASSED |
| Crypto: HMAC sign → verify | ✅ PASSED |
| Crypto: secure_encrypt → secure_decrypt | ✅ PASSED |
| Protocol: build → parse message | ✅ PASSED |
| Protocol: encrypt → decrypt payload | ✅ PASSED |
| Server: import + route count (21 routes) | ✅ PASSED |
| Server: all endpoints return 200 OK | ✅ PASSED |
| Dashboard: renders in browser | ✅ PASSED |

![Dashboard Recording](dashboard_verification_1773673225221.webp)

---

## How to Run

```bash
# 1. Install dependencies
pip install cryptography fastapi uvicorn sqlalchemy python-multipart requests

# 2. Start the server
cd c2-framework-project
python -m uvicorn server.server_async:app --host 0.0.0.0 --port 8000

# 3. Open dashboard
# Visit: http://localhost:8000/dashboard_page

# 4. Start agent (in another terminal)
cd c2-framework-project
python agent/agent.py --server http://127.0.0.1:8000
```
