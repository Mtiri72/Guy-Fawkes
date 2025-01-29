import hashlib
import socket

# Receiver configuration
HASH_FUNCTION = hashlib.sha256
CHAIN_LENGTH = 10

# Initialize socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 5000))
print("Listening for heartbeat messages...")

# Load public key (last element in the chain)
with open("public_key.bin", "rb") as f:
    public_key = f.read()
    print(f"Loaded public key (x_N): {public_key.hex()}")

previous_w_i = public_key

while True:
    data, _ = sock.recvfrom(1024)
    print(f"\nReceived message: {data}")

    try:
        payload, received_w_i, received_authenticator = data.split(b"||")
    except ValueError:
        print("Error: Incorrectly formatted data.")
        continue

    print(f"Parsed payload: {payload}")
    print(f"Parsed w_i: {received_w_i.hex()}")
    print(f"Parsed authenticator: {received_authenticator.hex()}")

    # Validate Winternitz chain point
    calculated_w_i = HASH_FUNCTION(received_w_i).digest()
    if calculated_w_i != previous_w_i:
        print("Invalid Winternitz chain point!")
    else:
        print("Winternitz chain point is valid.")
        previous_w_i = received_w_i  # Update previous_w_i to received_w_i

    # Generate expected authenticator and compare
    combined = payload + received_w_i  # Use received_w_i instead of previous_w_i
    expected_authenticator = HASH_FUNCTION(combined).digest()

    # Debugging output
    print(f"Combined for hashing (receiver): {combined}")
    print(f"Expected authenticator: {expected_authenticator.hex()}")
    print(f"Received authenticator: {received_authenticator.hex()}")

    if expected_authenticator != received_authenticator:
        print("Invalid authenticator!")
    else:
        print("Authenticator is valid.")
