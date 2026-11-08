#!/usr/bin/env bash
set -e

echo "==================================================="
echo "  ESP-ClimateNode: 1-Click Firmware Deployer"
echo "==================================================="
echo ""

read -rp "Enter serial port (e.g. /dev/ttyUSB0 or /dev/cu.usbserial-*): " PORT
if [ -z "$PORT" ]; then
    echo "[ERROR] No port provided. Exiting..."
    exit 1
fi

echo ""
echo "Select an action:"
echo "[1] Upload firmware files only (boot.py, config.py, main.py, web/)"
echo "[2] Flash new MicroPython binary + Upload firmware"
read -rp "Enter choice (1 or 2): " ACTION

if [ "$ACTION" = "2" ]; then
    read -rp "Enter path to MicroPython .bin firmware: " BIN_FILE
    if [ ! -f "$BIN_FILE" ]; then
        echo "[ERROR] File not found: $BIN_FILE"
        exit 1
    fi
    echo "[*] Erasing flash on $PORT..."
    esptool.py --port "$PORT" erase_flash
    echo "[*] Writing MicroPython binary..."
    esptool.py --port "$PORT" --baud 460800 write_flash --flash_size=detect 0 "$BIN_FILE"
    echo "[*] Firmware flashed! Waiting 2 seconds..."
    sleep 2
fi

echo "[*] Uploading files from firmware/ to ESP8266..."
mpremote connect "$PORT" cp -r firmware/* :

echo "[*] Resetting microcontroller..."
mpremote connect "$PORT" reset

echo ""
echo "==================================================="
echo "  Deployment Complete!"
echo "  Connect to Wi-Fi: ESP-Climate-Node"
echo "  Open dashboard  : http://192.168.4.1"
echo "==================================================="
