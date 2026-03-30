"""
C2 Multi-Agent Launcher
Spawns 10 simulated agents with unique identities as subprocesses.
All agents connect to the same C2 server.

Usage:
    python scripts/launch_agents.py
    python scripts/launch_agents.py --server http://192.168.1.100:8000
    python scripts/launch_agents.py --count 5
"""

import os
import sys
import time
import uuid
import signal
import argparse
import subprocess

# ── Agent Profiles ─────────────────────────────────────────────

AGENT_PROFILES = [
    {
        "hostname": "WORKSTATION-01",
        "username": "john.smith",
        "os_name": "Windows 11",
        "ip": "192.168.1.101",
    },
    {
        "hostname": "DEVBOX-02",
        "username": "sarah.dev",
        "os_name": "Ubuntu 22.04",
        "ip": "192.168.1.102",
    },
    {
        "hostname": "LAPTOP-03",
        "username": "mike.jones",
        "os_name": "Windows 10",
        "ip": "192.168.1.103",
    },
    {
        "hostname": "SERVER-04",
        "username": "root",
        "os_name": "CentOS 9",
        "ip": "10.0.0.51",
    },
    {
        "hostname": "MACBOOK-05",
        "username": "alex.mac",
        "os_name": "macOS 14",
        "ip": "192.168.1.105",
    },
    {
        "hostname": "FINANCE-06",
        "username": "jessica.fin",
        "os_name": "Windows 11",
        "ip": "10.0.1.20",
    },
    {
        "hostname": "DBSERVER-07",
        "username": "admin",
        "os_name": "Debian 12",
        "ip": "10.0.0.52",
    },
    {
        "hostname": "HR-PC-08",
        "username": "priya.hr",
        "os_name": "Windows 10",
        "ip": "192.168.1.108",
    },
    {
        "hostname": "WEBSERVER-09",
        "username": "www-data",
        "os_name": "Ubuntu 22.04",
        "ip": "10.0.0.53",
    },
    {
        "hostname": "TESTBOX-10",
        "username": "qa.test",
        "os_name": "Kali Linux",
        "ip": "192.168.1.110",
    },
]

# ── Banner ───────────────────────────────────────────────────

BANNER = r"""
╔════════════════════════════════════════════════════════════════╗
║            C2 FRAMEWORK — MULTI-AGENT LAUNCHER                ║
║                   Spawning 10 Agents                          ║
╚════════════════════════════════════════════════════════════════╝
"""


def main():
    parser = argparse.ArgumentParser(description="Launch multiple C2 agents")
    parser.add_argument("--server", default="http://127.0.0.1:8000", help="C2 server URL")
    parser.add_argument("--count", type=int, default=10, help="Number of agents to launch (max 10)")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay (seconds) between agent launches")
    parser.add_argument("--encrypted", action="store_true", help="Use encrypted communication")
    args = parser.parse_args()

    count = min(args.count, len(AGENT_PROFILES))
    profiles = AGENT_PROFILES[:count]

    print(BANNER)
    print(f"  Server:      {args.server}")
    print(f"  Agents:      {count}")
    print(f"  Encrypted:   {args.encrypted}")
    print(f"  Launch delay: {args.delay}s")
    print()

    # Path to agent.py
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    agent_script = os.path.join(project_root, "agent", "agent.py")

    if not os.path.exists(agent_script):
        print(f"  [ERROR] Agent script not found: {agent_script}")
        sys.exit(1)

    processes = []

    # Generate unique agent IDs
    for i, profile in enumerate(profiles, 1):
        agent_id = str(uuid.uuid4())

        cmd = [
            sys.executable, agent_script,
            "--server", args.server,
            "--id", agent_id,
            "--hostname", profile["hostname"],
            "--username", profile["username"],
            "--os-name", profile["os_name"],
            "--ip", profile["ip"],
        ]
        if args.encrypted:
            cmd.append("--encrypted")

        print(f"  [{i:02d}/{count:02d}] Launching {profile['hostname']} "
              f"({profile['username']}@{profile['os_name']}) [{profile['ip']}]")
        print(f"          ID: {agent_id}")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=project_root,
        )
        processes.append((profile["hostname"], proc))

        if i < count:
            time.sleep(args.delay)

    print()
    print(f"  ✅ All {count} agents launched successfully!")
    print()
    print("  ┌─────────────────────────────────────────────────────┐")
    print("  │  Press Ctrl+C to stop all agents                   │")
    print("  └─────────────────────────────────────────────────────┘")
    print()

    # Wait for Ctrl+C, then terminate all agents
    try:
        while True:
            # Check if any process has exited
            for hostname, proc in processes:
                if proc.poll() is not None:
                    print(f"  [!] Agent {hostname} exited (code: {proc.returncode})")
            time.sleep(5)
    except KeyboardInterrupt:
        print()
        print("  ⏹️  Stopping all agents...")
        for hostname, proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"  [✓] Stopped {hostname}")
            except Exception:
                proc.kill()
                print(f"  [!] Force-killed {hostname}")
        print()
        print("  All agents stopped. Goodbye!")


if __name__ == "__main__":
    main()
