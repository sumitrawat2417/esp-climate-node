#!/usr/bin/env bash
set -e

echo "==================================================="
echo "  ESP-ClimateNode: 1-Click Firmware Deployer"
echo "==================================================="
echo ""

# -------------------------------------------------------------
# Dependency Check (Auto-install mpremote & esptool if missing)
# -------------------------------------------------------------
if ! python3 -c "import mpremote" &>/dev/null; then
    echo "[*] 'mpremote' not found. Installing via pip..."
    python3 -m pip install mpremote
fi

if ! python3 -c "import esptool" &>/dev/null; then
    echo "[*] 'esptool' not found. Installing via pip..."
    python3 -m pip install esptool
fi

# -------------------------------------------------------------
# Automatic Serial Port Detection (Linux & macOS)
# -------------------------------------------------------------
detect_serial_ports() {
    local detected=()

    # 1. Try python's serial tools if available
    if python3 -c "import serial.tools.list_ports" &>/dev/null; then
        while IFS= read -r line; do
            [ -n "$line" ] && detected+=("$line")
        done < <(python3 -c "import serial.tools.list_ports; [print(p.device) for p in serial.tools.list_ports.comports()]")
    fi

    # 2. Fallback to /dev pattern matching if python list was empty
    if [ ${#detected[@]} -eq 0 ]; then
        # Linux standard USB-UART devices
        for p in /dev/ttyUSB* /dev/ttyACM*; do
            [ -e "$p" ] && detected+=("$p")
        done
        # macOS standard USB-UART devices
        for p in /dev/cu.usbserial* /dev/cu.wchusbserial* /dev/cu.SLAB_USBtoUART* /dev/cu.usbmodem*; do
            [ -e "$p" ] && detected+=("$p")
        done
    fi

    echo "${detected[@]}"
}

echo "[*] Scanning for connected ESP8266 devices..."
read -ra PORTS <<< "$(detect_serial_ports)"

PORT=""

if [ ${#PORTS[@]} -eq 1 ]; then
    AUTO_PORT="${PORTS[0]}"
    echo "[+] Found ESP8266 on: $AUTO_PORT"
    read -rp "Press Enter to use [$AUTO_PORT], or enter custom port: " USER_INPUT
    PORT="${USER_INPUT:-$AUTO_PORT}"

elif [ ${#PORTS[@]} -gt 1 ]; then
    echo "[!] Multiple serial ports detected:"
    for i in "${!PORTS[@]}"; do
        echo "    [$((i+1))] ${PORTS[$i]}"
    done
    read -rp "Select device number (1-${#PORTS[@]}) or enter custom path: " CHOICE
    if [[ "$CHOICE" =~ ^[0-9]+$ ]] && [ "$CHOICE" -ge 1 ] && [ "$CHOICE" -le ${#PORTS[@]} ]; then
        PORT="${PORTS[$((CHOICE-1))]}"
    else
        PORT="$CHOICE"
    fi

else
    echo "[-] No active USB-UART devices automatically detected."
    read -rp "Please enter serial port manually (e.g. /dev/ttyUSB0 or /dev/cu.usbserial-*): " PORT
fi

if [ -z "$PORT" ]; then
    echo "[ERROR] No serial port selected. Exiting..."
    exit 1
fi

echo "[*] Using port: $PORT"
echo ""

# -------------------------------------------------------------
# Deployment Action Selection
# -------------------------------------------------------------
echo "Select an action:"
echo "  [1] Upload firmware files only (boot.py, config.py, main.py, web/)"
echo "  [2] Flash fresh MicroPython binary + Upload firmware"
read -rp "Enter choice (1 or 2) [default 1]: " ACTION
ACTION="${ACTION:-1}"

if [ "$ACTION" = "2" ]; then
    read -rp "Enter path to MicroPython .bin firmware: " BIN_FILE
    if [ ! -f "$BIN_FILE" ]; then
        echo "[ERROR] Firmware file not found: $BIN_FILE"
        exit 1
    fi
    echo ""
    echo "[*] Erasing flash on $PORT..."
    python3 -m esptool --port "$PORT" erase_flash

    echo "[*] Writing MicroPython binary..."
    python3 -m esptool --port "$PORT" --baud 460800 write_flash --flash_size=detect 0 "$BIN_FILE"

    echo "[*] Firmware flashed! Waiting 2 seconds for boot..."
    sleep 2
fi

echo ""
echo "[*] Uploading firmware files from firmware/ to ESP8266..."
python3 -m mpremote connect "$PORT" cp -r firmware/* :

echo "[*] Resetting microcontroller..."
python3 -m mpremote connect "$PORT" reset

echo ""
echo "==================================================="
echo "  Deployment Complete!"
echo "  Connect to Wi-Fi: ESP-Climate-Node"
echo "  Open dashboard  : http://192.168.4.1"
echo "==================================================="
