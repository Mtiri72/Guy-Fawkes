import socket
import threading
import os
import time
import hashlib
from datetime import datetime
from cassandra.cluster import Cluster

# Configuration
TCP_PORT = 5000
UDP_PORT = 5001
HEARTBEAT_TIMEOUT = 7  # seconds
LOGFILE = "./logs/ap_server.log"
COORDINATOR_IP = "10.30.2.153"
COORDINATOR_PORT = 5050
HASH_FUNCTION = hashlib.sha256

# Logging
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"{timestamp} - {message}"
    print(log_message)
    log_dir = os.path.dirname(LOGFILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    with open(LOGFILE, "a") as f:
        f.write(log_message + "\n")

# Cassandra setup
cluster = Cluster(["127.0.0.1"])
session = cluster.connect()
session.execute("""
    CREATE KEYSPACE IF NOT EXISTS swarm
    WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
""")
session.set_keyspace("swarm")
session.execute("""
    CREATE TABLE IF NOT EXISTS node_keys (
        node_uuid text PRIMARY KEY,
        public_key blob
    )
""")
session.execute("TRUNCATE node_keys")
log("[DB] node_keys table truncated on startup")

# Global state
last_heartbeat_time = {}
last_valid_chain_point = {}  # Now stores {'current': bytes, 'previous': bytes}
lock = threading.Lock()

# Inform coordinator that a node is dead
def notify_coordinator_dead_node(node_uuid):
    try:
        message = f"NODE_DEAD|{node_uuid}"
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(message.encode(), (COORDINATOR_IP, COORDINATOR_PORT))
        sock.close()
        log(f"[NOTIFY] Sent dead node info to coordinator for {node_uuid}")
    except Exception as e:
        log(f"[ERROR] Failed to notify coordinator: {e}")

# TCP server: key registration
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

        with lock:
            session.execute("""
                INSERT INTO node_keys (node_uuid, public_key) VALUES (%s, %s)
            """, (client_id, public_key))
            last_valid_chain_point[client_id] = {"current": public_key[:], "previous": None}

        conn.sendall(b"ACK")
        log(f"[KEY RECEIVED] Public key from {client_id} stored in Cassandra")

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

# UDP server: heartbeat processing
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
                chain_state = last_valid_chain_point.get(client_id)

                if chain_state is None:
                    result = session.execute("SELECT public_key FROM node_keys WHERE node_uuid = %s", (client_id,))
                    row = result.one()
                    if row is None:
                        log(f"[ALERT] Heartbeat from unknown client {client_id}!")
                        continue
                    chain_state = {"current": row.public_key[:], "previous": None}
                    last_valid_chain_point[client_id] = chain_state

                expected1 = HASH_FUNCTION(w_i).digest()
                expected2 = HASH_FUNCTION(HASH_FUNCTION(w_i).digest()).digest()

                if expected1 == chain_state["current"]:
                    # Valid chain step
                    chain_state["previous"] = chain_state["current"][:]
                    chain_state["current"] = w_i[:]
                    last_heartbeat_time[client_id] = time.time()
                    log(f"[HEARTBEAT] Valid heartbeat from {client_id} at {timestamp} (Counter: {counter})")

                elif chain_state["previous"] and expected2 == chain_state["previous"]:
                    # One skipped packet
                    chain_state["current"] = w_i[:]
                    last_heartbeat_time[client_id] = time.time()
                    log(f"[HEARTBEAT] VALID with one skipped: {client_id} at {timestamp} (Counter: {counter})")
                    log(f"[WARNING] Missed a packet from {client_id}, resynchronized using fallback.")

                else:
                    log(f"[ALERT] Invalid Winternitz chain point from {client_id}!\nExpected: {expected1.hex()}\nActual: {chain_state['current'].hex()}\nW_i: {w_i.hex()}")

        except Exception as e:
            log(f"[ERROR] Failed to process heartbeat from {addr}: {e}")

# Heartbeat timeout checker
def heartbeat_monitor():
    while True:
        time.sleep(1)
        with lock:
            current_time = time.time()
            expired_clients = [cid for cid, last_time in last_heartbeat_time.items() if current_time - last_time > HEARTBEAT_TIMEOUT]

            for client_id in expired_clients:
                log(f"[ALERT] Client {client_id} is considered DEAD (no heartbeat for > {HEARTBEAT_TIMEOUT}s)")
                try:
                    session.execute("DELETE FROM node_keys WHERE node_uuid = %s", (client_id,))
                    log(f"[DB] Deleted client {client_id} from Cassandra")
                except Exception as e:
                    log(f"[ERROR] Failed to delete client {client_id} from Cassandra: {e}")

                notify_coordinator_dead_node(client_id)
                del last_heartbeat_time[client_id]
                del last_valid_chain_point[client_id]

# Main entry point
if __name__ == "__main__":
    tcp_thread = threading.Thread(target=tcp_server, daemon=True)
    udp_thread = threading.Thread(target=udp_server, daemon=True)
    monitor_thread = threading.Thread(target=heartbeat_monitor, daemon=True)

    tcp_thread.start()
    udp_thread.start()
    monitor_thread.start()

    log("Access Point Server is running with Cassandra DB. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Server shutting down.")

