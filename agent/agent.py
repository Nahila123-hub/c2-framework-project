import socket
import uuid
import requests

SERVER_URL = "http://127.0.0.1:5000/register"

def get_agent_data():
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)

    agent_data = {
        "agent_id": str(uuid.uuid4()),
        "hostname": hostname,
        "ip": ip,
        "status": "active"
    }
    return agent_data

def register_agent():
    data = get_agent_data()
    try:
        response = requests.post(SERVER_URL, json=data)
        print("Status Code:", response.status_code)
        print("Response:", response.json())
    except requests.exceptions.RequestException as e:
        print("Error while connecting to server:", e)

if __name__ == "__main__":
    register_agent()
