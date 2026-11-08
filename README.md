# ESP-ClimateNode: Standalone Temperature & Humidity Monitor

[![MicroPython](https://img.shields.io/badge/Firmware-MicroPython%20v1.20+-blue.svg)](https://micropython.org/)
[![Hardware](https://img.shields.io/badge/Hardware-ESP8266%20%7C%20DHT22-orange.svg)](https://www.espressif.com/en/products/socs/esp8266)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Phase%201%3A%20In%20Development-yellow.svg)]()

> A lightweight, offline-first IoT environmental monitoring node built with an **ESP8266** microcontroller and a **DHT22** sensor using **MicroPython**.

---

## 📖 Overview

**ESP-ClimateNode** is an edge-computing environmental telemetry station designed to operate completely independently of external Wi-Fi networks, home routers, or cloud backends.

When powered on, the ESP8266 broadcasts its own self-hosted **Soft Access Point (SoftAP)** and runs an embedded HTTP server. Users connect directly from any smartphone, tablet, or PC to access a locally hosted, real-time web dashboard. The frontend polls data asynchronously using JavaScript's modern `fetch()` API, updating temperature, humidity, heat index, and dew point metrics dynamically without page reloads.

```
+--------------------+        +-----------------------------+        +---------------------------+
|    DHT22 Sensor    | -----> |   ESP8266 (MicroPython)     | -----> |   Client Web Browser      |
| Temp & Hum Sensing |        |   SoftAP: 192.168.4.1       |        |   Real-Time DOM Dashboard |
| (Single-Wire Bus)  |        |   Async HTTP Socket Server  |        |   (JavaScript fetch API)  |
+--------------------+        +-----------------------------+        +---------------------------+
```

---

## ✨ Key Features

* **100% Offline-First Architecture:** No internet, router configuration, cloud subscription, or API keys required.
* **Plug-and-Play SoftAP:** Broadcasts a standalone Wi-Fi network (`ESP-Climate-Node`) with onboard DHCP.
* **Decoupled Sensor Sampling:** DHT22 measurements run in a non-blocking background loop to prevent timing conflicts and `ETIMEDOUT` errors during concurrent web requests.
* **Real-Time Web Dashboard:** Embedded single-page web application served directly from flash memory with zero external CDN dependencies.
* **Derived Environmental Metrics:** Automatically computes **Heat Index** (apparent "feels like" temperature via the NOAA regression formula) and **Dew Point** (Magnus-Tetens formula).
* **Embedded REST API:** Exposes lightweight JSON endpoints (`/api/data` and `/api/status`) with CORS enabled.
* **RAM & Resource Optimized:** Engineered specifically for the ESP8266's constrained ~40 KB MicroPython heap with proactive garbage collection.

---

## 🛠️ Hardware Requirements & Pinout

### Bill of Materials
* **1x** ESP8266 Development Board (NodeMCU v2/v3 or Wemos D1 Mini)
* **1x** DHT22 / AM2302 Digital Temperature & Humidity Sensor
* **1x** 10kΩ Pull-Up Resistor (¼W, not required if using a 3-pin breakout board)
* **1x** Solderless Breadboard & Dupont Jumper Wires
* **1x** Micro-USB cable & 5V Power Source (USB port or power bank)

### Wiring Table
| ESP8266 NodeMCU Pin | Wemos D1 Mini Pin | DHT22 Sensor Pin | Description |
| :---: | :---: | :---: | :--- |
| **3V3** | **3V3** | Pin 1 (`VCC`) | 3.3V DC Power Rail |
| **D2 (GPIO4)** | **D2 (GPIO4)** | Pin 2 (`DATA`) | Single-Wire Serial Bus |
| — | — | Pin 3 (`NC`) | Not Connected |
| **GND** | **G** | Pin 4 (`GND`) | Ground Reference |

> **Note:** For bare 4-pin DHT22 sensors, connect a **10kΩ pull-up resistor** between `VCC` (Pin 1) and `DATA` (Pin 2).

---

## 🗂️ Project Structure

```text
esp-climate-node/
├── boot.py               # Hardware bootloader, SoftAP setup & network config
├── config.py             # User settings (SSID, AP password, GPIO pins, intervals)
├── main.py               # Core application: sensor reader & async HTTP server
├── web/
│   └── index.html        # Embedded responsive dashboard (HTML5, CSS3, JS)
├── .gitignore            # Git exclusion rules
└── README.md             # Project documentation & quickstart
```

---

## 🚀 Quickstart Guide

### 1. Flash MicroPython Firmware
Erase the flash memory and flash the latest stable ESP8266 MicroPython binary:
```bash
# 1. Install esptool
pip install esptool

# 2. Erase flash memory (replace COM3 with your serial port)
esptool.py --port COM3 erase_flash

# 3. Flash MicroPython firmware
esptool.py --port COM3 --baud 460800 write_flash --flash_size=detect 0 esp8266-latest.bin
```

### 2. Upload Code to Board
Using **Thonny IDE** or `mpremote`:
```bash
pip install mpremote
mpremote connect COM3 cp boot.py :boot.py
mpremote connect COM3 cp config.py :config.py
mpremote connect COM3 cp main.py :main.py
mpremote connect COM3 mkdir :web
mpremote connect COM3 cp web/index.html :web/index.html
mpremote connect COM3 reset
```

### 3. Connect & Monitor
1. On your phone or laptop, join the Wi-Fi network: **`ESP-Climate-Node`**.
2. Open your web browser and navigate to:
   ```
   http://192.168.4.1
   ```
3. Live climate metrics will update dynamically every 3 seconds!

---

## 📡 REST API Reference

| Endpoint | Method | Response Type | Description |
| :--- | :---: | :---: | :--- |
| `/` | `GET` | `text/html` | Serves the standalone web dashboard. |
| `/api/data` | `GET` | `application/json` | Returns real-time temperature, humidity, heat index, and dew point. |
| `/api/status` | `GET` | `application/json` | Returns device health, heap memory stats, and uptime. |

### Sample `/api/data` Payload:
```json
{
  "temperature": 24.6,
  "humidity": 58.2,
  "heat_index": 25.1,
  "dew_point": 15.9,
  "sensor_ok": true,
  "uptime_seconds": 182
}
```

---

## 🗺️ Roadmap

- [x] Architecture design & system specification
- [x] Initial project repository & `.gitignore` structure
- [ ] Core firmware implementation (`boot.py`, `config.py`, `main.py`)
- [ ] Embedded responsive dashboard (`web/index.html`)
- [ ] Captive portal probe interception (`/generate_204`, `/hotspot-detect.html`)
- [ ] Circular flash buffer logging for 24h min/max history

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
