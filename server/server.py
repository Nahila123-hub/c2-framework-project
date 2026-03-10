from flask import Flask, request, jsonify

app = Flask(__name__)

agents = []

@app.route("/")
def home():
    return "C2 Server is running"

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    agents.append(data)
    return jsonify({"message": "Agent registered successfully"}), 200

@app.route("/agents", methods=["GET"])
def get_agents():
    return jsonify(agents), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)