import socket
import uuid
import requests
import getpass
import platform

from encryption.crypto import encrypt_message
from communication.protocol import create_packet

SERVER_URL = "http://127.0.0.1:8000/register"


def get_agent_data():

    hostname = socket.gethostname()

    agent_data = {
        "agent_id": str(uuid.uuid4()),
        "hostname": hostname,
        "username": getpass.getuser(),
        "os": platform.system(),
        "status": "active"
    }

    return agent_data


def register_agent():

    data = get_agent_data()

    # create structured packet
    packet = create_packet("register", data)

    # encrypt packet
    encrypted_payload = encrypt_message(packet)

    try:

        response = requests.post(
            SERVER_URL,
            json={"payload": encrypted_payload}
        )

        print("Status Code:", response.status_code)

        try:
            print("Response:", response.json())
        except:
            print("Server Response:", response.text)

    except requests.exceptions.RequestException as e:
        print("Error while connecting to server:", e)


if __name__ == "__main__":
    register_agent()