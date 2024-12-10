import hashlib
import socket
import time

# Load Winternitz chain from file
with open("winternitz_chain.bin", "rb") as f:
    chain_data = f.read()

CHAIN_LENGTH = 10
HASH_FUNCTION = hashlib.sha256
chain_points = [chain_data[i * 32:(i + 1) * 32] for i in range(CHAIN_LENGTH + 1)]

# Initialize socket
receiver_ip = "10.30.2.236"
receiver_port = 5000
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_heartbeat(i):
    payload = f"Heartbeat {i}".encode()
    w_i = chain_points[CHAIN_LENGTH - i]
    next_w_i = chain_points[CHAIN_LENGTH - i - 1] if i < CHAIN_LENGTH else b""

    # Concatenate payload and next_w_i (in bytes) and hash
    combined = payload + w_i  # Fix here to use w_i instead of next_w_i
    authenticator = HASH_FUNCTION(combined).digest()

    # Debugging output
    print(f"\n--- Heartbeat {i} ---")
    print(f"Payload: {payload}")
    print(f"w_i (chain point): {w_i.hex()}")
    print(f"Combined for hashing: {combined}")
    print(f"Authenticator: {authenticator.hex()}")

    # Send the message
    message = payload + b"||" + w_i + b"||" + authenticator
    sock.sendto(message, (receiver_ip, receiver_port))
    print(f"Sent heartbeat {i}")

# Send heartbeats in intervals
for i in range(1, CHAIN_LENGTH + 1):
    send_heartbeat(i)
    time.sleep(1)
