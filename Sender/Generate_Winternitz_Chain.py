import os
import hashlib
import argparse

CHAIN_LENGTH = 100
HASH_FUNCTION = hashlib.sha256


def generate_winternitz_chain(output_dir, debug=False):
    os.makedirs(output_dir, exist_ok=True)

    x0 = os.urandom(32)
    chain = [x0]

    if debug:
        print(f"x_0 (private key): {x0.hex()}")

    for i in range(1, CHAIN_LENGTH + 1):
        next_point = HASH_FUNCTION(chain[-1]).digest()
        chain.append(next_point)

        if debug:
            print(f"x_{i}: {next_point.hex()}")

        if chain[i] != HASH_FUNCTION(chain[i - 1]).digest():
            raise RuntimeError(f"Error: x_{i} was not generated correctly from x_{i - 1}")

    public_key = chain[-1]

    try:
        with open(os.path.join(output_dir, "private_key.bin"), "wb") as f:
            f.write(x0)

        with open(os.path.join(output_dir, "winternitz_chain.bin"), "wb") as f:
            for element in chain:
                f.write(element)

        with open(os.path.join(output_dir, "public_key.bin"), "wb") as f:
            f.write(public_key)

    except OSError as e:
        print(f"File writing error: {e}")
        exit(1)

    if debug:
        print("Winternitz chain generated and verified.")
        print("Public key (x_N) is the last chain point.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a Winternitz Chain")
    parser.add_argument("--output-dir", default="/home/SN1/heartbeat_keys", help="Output directory for key files")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    try:
        generate_winternitz_chain(args.output_dir, args.debug)
    except Exception as e:
        print(f"An error occurred during chain generation: {e}")
        exit(1)
