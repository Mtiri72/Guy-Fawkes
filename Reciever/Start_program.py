import socket
import threading
import os
import time
import hashlib
from datetime import datetime

# Configuration
TCP_PORT = 5000
UDP_PORT = 5001
HEARTBEAT_TIMEOUT = 7  # seconds
KEY_STORAGE_DIR = "./clients_keys"
LOGFILE = "./logs/ap_server.log"
HASH_FUNCTION = hashlib.sha256

# Global state to track clients
last_heartbeat_time = {}
last_valid_chain_point = {}
lock = threading.Lock()

# Logging function
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"{timestamp} - {message}"
    print(log_message)
    with open(LOGFILE, "a") as f:
        f.write(log_message + "\n")


# -------------------------------
# TCP Server for Public Key Registration
# -------------------------------
def handle_tcp_client(conn, addr):
    try:
        data = conn.recv(4096)
        if not data:
            return

        try:
            decoded = data.decode()
            client_id, public_key_hex = decoded.split("|", 1)
            public_key = bytes.fromhex(public_key_hex)
        except ValueError:
            log(f"[ERROR] Invalid data from {addr}: {data}")
            return

        os.makedirs(KEY_STORAGE_DIR, exist_ok=True)
        key_path = os.path.join(KEY_STORAGE_DIR, f"{client_id}.bin")
        with open(key_path, "wb") as f:
            f.write(public_key)

        with lock:
            last_valid_chain_point[client_id] = public_key

        conn.sendall(b"ACK")
        log(f"[KEY RECEIVED] Public key from {client_id} stored at {key_path}")

    except Exception as e:
        log(f"[ERROR] TCP handler error from {addr}: {e}")
    finally:
        conn.close()


def tcp_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", TCP_PORT))
    server.listen(5)
    log(f"TCP Server started on port {TCP_PORT}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_tcp_client, args=(conn, addr)).start()


# -------------------------------
# UDP Server for Heartbeats & Verification
# -------------------------------
def udp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    log(f"UDP Server started on port {UDP_PORT}")

    while True:
        data, addr = sock.recvfrom(4096)

        try:
            parts = data.split(b"||")
            if len(parts) != 3:
                log(f"[ERROR] Malformed heartbeat packet from {addr}")
                continue

            payload, w_i, authenticator = parts
            client_id, timestamp, counter = payload.decode().split("|")

            with lock:
                if client_id not in last_valid_chain_point:
                    log(f"[ALERT] Heartbeat from unknown client {client_id}!")
                    continue

                # Validate Winternitz chain point (w_(i+1) == H(w_i))
                expected_previous_point = HASH_FUNCTION(w_i).digest()
                if expected_previous_point != last_valid_chain_point[client_id]:
                    log(f"[ALERT] Invalid Winternitz chain point from {client_id}!")
                    continue

                # Validate authenticator
                expected_authenticator = HASH_FUNCTION(payload + w_i).digest()
                if expected_authenticator != authenticator:
                    log(f"[ALERT] Invalid authenticator from {client_id}!")
                    continue

                # If valid:
                last_valid_chain_point[client_id] = w_i
                last_heartbeat_time[client_id] = time.time()

                log(f"[HEARTBEAT] Valid heartbeat from {client_id} at {timestamp} (Counter: {counter})")

        except Exception as e:
            log(f"[ERROR] Failed to process heartbeat from {addr}: {e}")


# -------------------------------
# Dead Client Detector
# -------------------------------
def heartbeat_monitor():
    while True:
        time.sleep(1)
        with lock:
            current_time = time.time()
            for client_id, last_time in list(last_heartbeat_time.items()):
                if current_time - last_time > HEARTBEAT_TIMEOUT:
                    log(f"[ALERT] Client {client_id} is considered DEAD (no heartbeat for > {HEARTBEAT_TIMEOUT}s)")
                    del last_heartbeat_time[client_id]
                    del last_valid_chain_point[client_id]


# -------------------------------
# Main Entry Point
# -------------------------------
if __name__ == "__main__":
    os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)

    tcp_thread = threading.Thread(target=tcp_server, daemon=True)
    udp_thread = threading.Thread(target=udp_server, daemon=True)
    monitor_thread = threading.Thread(target=heartbeat_monitor, daemon=True)

    tcp_thread.start()
    udp_thread.start()
    monitor_thread.start()

    log("Access Point Server is running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Server shutting down.")

