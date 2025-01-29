import os
import hashlib

CHAIN_LENGTH = 10  
HASH_FUNCTION = hashlib.sha256  # Use SHA-256

# Generate  private key x0 as a random 256-bit number
x0 = os.urandom(32)  # 32 bytes = 256 bits
chain = [x0]  # Start the chain with the private key

print(f"x_0 (private key): {x0.hex()}")

# Generate and verify the Winternitz chain
for i in range(1, CHAIN_LENGTH + 1):
    next_point = HASH_FUNCTION(chain[-1]).digest()  
    chain.append(next_point)
    print(f"x_{i}: {next_point.hex()}")

    # Ensure x_(i+1) equals hash(x_i)
    if chain[i] != HASH_FUNCTION(chain[i - 1]).digest():
        print(f"Error: x_{i} was not generated correctly from x_{i - 1}")
    else:
        print(f"x_{i} generated correctly from x_{i - 1}")

# Store the public key (last element of the chain)
public_key = chain[-1]

# Save the private key, chain, and public key to files
with open("private_key.bin", "wb") as f:
    f.write(x0)

with open("winternitz_chain.bin", "wb") as f:
    for element in chain:
        f.write(element)

with open("public_key.bin", "wb") as f:
    f.write(public_key)

print("Winternitz chain generated and verified.")
print("Public key (x_N) is the last chain point.")

