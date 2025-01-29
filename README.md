# Heartbeat Program

---

## Overview
This repository contains a **heartbeat program** that demonstrates secure communication between a sender and a receiver using a **Winternitz chain** for cryptographic authentication. The program consists of three Python scripts:

1. **`winternitz_chain.py`**: Generates a Winternitz chain, private key, and public key.
2. **`sender.py`**: Sends heartbeat messages to the receiver using the Winternitz chain for authentication.
3. **`receiver.py`**: Receives and validates heartbeat messages using the Winternitz chain and public key.

The program ensures the integrity and authenticity of heartbeat messages by leveraging cryptographic hashing and a one-way chain structure.

---

## How It Works
1. **Winternitz Chain Generation**:
   - The `winternitz_chain.py` script generates a private key (`x0`) and constructs a Winternitz chain by repeatedly applying a hash function (SHA-256).
   - The last element of the chain is the public key, which is used by the receiver to validate messages.

2. **Sending Heartbeats**:
   - The `sender.py` script sends periodic heartbeat messages to the receiver.
   - Each message includes:
     - A payload (e.g., `"Heartbeat i"`).
     - A point from the Winternitz chain (`w_i`).
     - An authenticator (a hash of the payload and `w_i`).

3. **Receiving and Validating Heartbeats**:
   - The `receiver.py` script listens for incoming heartbeat messages.
   - It validates each message by:
     - Verifying the Winternitz chain point (`w_i`) using the public key.
     - Recomputing the authenticator and comparing it to the received authenticator.

---

## Prerequisites
- Python 3.x
- Basic understanding of cryptographic concepts (hashing, public/private keys).

---

## Steps to Run the Program

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/heartbeat-program.git
   cd heartbeat-program

   
