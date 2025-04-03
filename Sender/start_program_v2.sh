#!/bin/bash

SSID="AP01"
BSSID="10:5B:AD:4D:75:6F"
PASSWORD="123456123"

LOGFILE="ap_connection.log"
AP_IP="10.42.0.1"
PUBKEY_PORT="5000"
HEARTBEAT_PORT="5001"
WIFI_INTERFACE="wlan0"

KEY_DIR="/home/SmartNode01/Heartbeats_protocol/heartbeat_keys"
PRIVATE_KEY="$KEY_DIR/private_key.bin"
PUBLIC_KEY="$KEY_DIR/public_key.bin"
CHAIN_FILE="$KEY_DIR/winternitz_chain.bin"

CLIENT_ID=$(hostname)

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOGFILE"
}

cleanup() {
    log "Cleaning up: terminating heartbeat sender and deleting key/chain files..."
    pkill -f Send_Heartbeat.py
    rm -f "$PRIVATE_KEY" "$PUBLIC_KEY" "$CHAIN_FILE"
}

trap cleanup EXIT

log "Starting AP search..."

while true; do
    AVAILABLE_AP=$(nmcli -t -f SSID,BSSID dev wifi list | grep -w "$SSID")

    if [[ -n "$AVAILABLE_AP" ]]; then
        BSSID_FOUND=$(echo "$AVAILABLE_AP" | awk -F: '{print $2}')
        log "Access point found with BSSID: $BSSID_FOUND. Attempting to connect..."

        if [[ -n "$BSSID" ]]; then
            log "Using predefined BSSID: $BSSID"
            nmcli dev wifi connect "$SSID" bssid "$BSSID" password "$PASSWORD"
        else
            log "No predefined BSSID. Connecting to detected BSSID: $BSSID_FOUND"
            nmcli dev wifi connect "$SSID" bssid "$BSSID_FOUND" password "$PASSWORD"
        fi

        while true; do
            IP_ADDRESS=$(nmcli -g IP4.ADDRESS device show "$WIFI_INTERFACE" | cut -d'/' -f1)
            if [[ -n "$IP_ADDRESS" ]]; then
                log "Connection successful. IP Address: $IP_ADDRESS"

                log "Regenerating Winternitz Chain and keys for fresh session..."
                rm -f "$PRIVATE_KEY" "$PUBLIC_KEY" "$CHAIN_FILE"
                mkdir -p "$KEY_DIR"
                if python3 Generate_Winternitz_Chain.py --output-dir "$KEY_DIR"; then
                    log "Winternitz Chain and keys generated successfully."
                else
                    log "Failed to generate keys. Exiting..."
                    exit 1
                fi

                PUBLIC_KEY_HEX=$(xxd -p "$PUBLIC_KEY" | tr -d '\n')
                log "Public key (hex): $PUBLIC_KEY_HEX"

                log "Sending public key (ID: $CLIENT_ID) to Access Point on port $PUBKEY_PORT..."

                ACK=$(echo "${CLIENT_ID}|${PUBLIC_KEY_HEX}" | nc $AP_IP $PUBKEY_PORT)

                if [[ "$ACK" == "ACK" ]]; then
                    log "Public key successfully received and acknowledged by AP."

                    log "Running Send_Heartbeat.py..."
                    if python3 Send_Heartbeat.py --client-id "$CLIENT_ID" --chain-file "$CHAIN_FILE" --receiver-ip "$AP_IP" --receiver-port "$HEARTBEAT_PORT"; then
                        log "Heartbeat transmission started successfully."
                    else
                        log "Failed to start heartbeat transmission."
                        exit 1
                    fi

                    while true; do
                        CURRENT_IP=$(nmcli -g IP4.ADDRESS device show "$WIFI_INTERFACE" | cut -d'/' -f1)
                        if [[ -z "$CURRENT_IP" ]]; then
                            log "Connection lost! Triggering key cleanup..."
                            cleanup
                            break
                        fi
                        sleep 5
                    done
                else
                    log "Failed to receive ACK from AP. Public key transmission failed."
                fi

                exit 0
            fi
            sleep 2
        done
    fi
    sleep 5
done

