#!/usr/bin/env bash
set -e

# Guarantee execution from project root
cd "$(dirname "$0")/.."

echo "==================================================="
echo "  ESP-ClimateNode: 1-Click Firmware Deployer"
echo "==================================================="
echo ""

# -------------------------------------------------------------
# Dependency Check (Auto-install mpremote & esptool if missing)
# -------------------------------------------------------------
if ! python3 -c "import mpremote" &>/dev/null; then
    echo "[*] 'mpremote' not found. Installing via pip..."
    python3 -m pip install mpremote pyserial
fi

if ! python3 -c "import esptool" &>/dev/null; then
    echo "[*] 'esptool' not found. Installing via pip..."
    python3 -m pip install esptool
fi

# -------------------------------------------------------------
# Automatic Serial Port Detection (Linux & macOS)
# -------------------------------------------------------------
echo "[*] Scanning for connected serial devices..."
python3 -c "import serial.tools.list_ports; [print(f'     -> {p.device}: {p.description}') for p in serial.tools.list_ports.comports()]" 2>/dev/null || true
echo ""

AUTO_PORT=$(python3 -c "import serial.tools.list_ports; usb = [p.device for p in serial.tools.list_ports.comports() if any(k in (p.description + p.hwid).upper() for k in ['USB', 'CH340', 'CP210', 'FTDI', 'UART'])]; print(usb[0] if usb else '')" 2>/dev/null || true)

if [ -n "$AUTO_PORT" ]; then
    echo "[+] Auto-detected ESP8266 on: $AUTO_PORT"
    read -rp "Press Enter to use [$AUTO_PORT], or enter custom port: " USER_INPUT
    PORT="${USER_INPUT:-$AUTO_PORT}"
else
    read -rp "Enter your ESP8266 serial port (e.g. /dev/ttyUSB0): " PORT
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
echo "[*] Transferring firmware files to ESP8266 root filesystem..."
echo "  - Uploading boot.py..."
python3 -m mpremote connect "$PORT" cp firmware/boot.py :boot.py

echo "  - Uploading config.py..."
python3 -m mpremote connect "$PORT" cp firmware/config.py :config.py

echo "  - Uploading main.py..."
python3 -m mpremote connect "$PORT" cp firmware/main.py :main.py

if [ -f "firmware/web/index.html" ]; then
    echo "  - Uploading web/index.html..."
    python3 -m mpremote connect "$PORT" mkdir :web 2>/dev/null || true
    python3 -m mpremote connect "$PORT" cp firmware/web/index.html :web/index.html
fi

echo ""
echo "[*] Resetting microcontroller..."
python3 -m mpremote connect "$PORT" reset

echo ""
echo "==================================================="
echo "  Deployment Complete!"
echo "  Connect to Wi-Fi: ESP-Climate-Node"
echo "  Open dashboard  : http://192.168.4.1"
echo "==================================================="
