import json
import hashlib


def create_packet(packet_type, data):

    packet = {
        "type": packet_type,
        "data": data
    }

    message = json.dumps(packet).encode()

    return message


def parse_packet(packet_bytes):

    packet = json.loads(packet_bytes.decode())

    return packet["type"], packet["data"]


def generate_hash(message):

    return hashlib.sha256(message).hexdigest()