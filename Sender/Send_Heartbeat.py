import hashlib
import socket
import time
import os
import argparse

HASH_FUNCTION = hashlib.sha256


def load_chain(chain_file):
    with open(chain_file, "rb") as f:
        chain_data = f.read()
    if len(chain_data) % 32 != 0:
        raise ValueError("Invalid chain length. Data size must be a multiple of 32 bytes.")
    chain_points = [chain_data[i * 32:(i + 1) * 32] for i in range(len(chain_data) // 32)]
    return chain_points


def send_heartbeat(sock, server_address, client_id, chain_points, i):
    if i >= len(chain_points):
        print("Error: Chain exhausted. Cannot send more heartbeats.")
        return False

    timestamp = str(time.time()).encode()
    w_i = chain_points[-(i + 1)]

    payload = client_id.encode() + b"|" + timestamp + b"|" + str(i).encode()

    # Authenticator: H(payload || w_i)
    authenticator = HASH_FUNCTION(payload + w_i).digest()

    message = payload + b"||" + w_i + b"||" + authenticator

    try:
        sock.sendto(message, server_address)
        print(f"Sent heartbeat {i} - Timestamp: {timestamp.decode()}")
    except Exception as e:
        print(f"Failed to send heartbeat {i}: {e}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Send heartbeats using a Winternitz chain")
    parser.add_argument("--receiver-ip", default="10.42.0.1", help="Receiver IP address")
    parser.add_argument("--receiver-port", type=int, default=5001, help="Receiver UDP port")
    parser.add_argument("--chain-file", default="/home/pi/heartbeat_keys/winternitz_chain.bin", help="Winternitz chain file path")
    parser.add_argument("--client-id", default="CLIENT_ID_PLACEHOLDER", help="Unique client ID")
    parser.add_argument("--interval", type=float, default=1.0, help="Heartbeat interval in seconds")
    args = parser.parse_args()

    try:
        chain_points = load_chain(args.chain_file)
        print(f"Loaded Winternitz chain with {len(chain_points)} points.")
    except Exception as e:
        print(f"Failed to load chain: {e}")
        return

    server_address = (args.receiver_ip, args.receiver_port)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for i in range(1, len(chain_points)):
            if not send_heartbeat(sock, server_address, args.client_id, chain_points, i):
                break
            time.sleep(args.interval)

    print("Heartbeat sequence completed or chain exhausted.")


if __name__ == "__main__":
    main()

