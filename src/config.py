# ==============================================================================
# ESP-ClimateNode: System Configuration
# ==============================================================================
# Central configuration file for device parameters, Wi-Fi SoftAP settings,
# hardware pin assignments, and sensor calibration offsets.
# ==============================================================================

# --- Device Metadata ---
DEVICE_NAME = "ESP-ClimateNode"
FIRMWARE_VERSION = "1.0.0"

# --- Wi-Fi Soft Access Point (SoftAP) Configuration ---
# The ESP8266 acts as a standalone Wi-Fi hotspot.
WIFI_SSID = "ESP-Climate-Node"
# Leave empty string "" for an open, unencrypted network (ideal for instant access).
# Set to an 8+ character string to enable WPA2-PSK security (e.g. "climate1234").
WIFI_PASSWORD = ""
WIFI_CHANNEL = 6            # 2.4 GHz RF channel (1 - 11)
WIFI_MAX_CONNECTIONS = 4    # Maximum concurrent client associations (saves RAM)

# Static IP settings for the SoftAP gateway
AP_IP = "192.168.4.1"
AP_SUBNET = "255.255.255.0"
AP_GATEWAY = "192.168.4.1"
AP_DNS = "192.168.4.1"

# --- Sensor Hardware Configuration ---
# On NodeMCU and Wemos D1 Mini:
# GPIO4 corresponds to physical pin D2.
SENSOR_PIN = 4

# Polling Interval (in seconds)
# IMPORTANT: The DHT22 requires at least 2.0 seconds between consecutive reads.
# Polling faster will cause hardware bus timeouts (OSError: 110).
SENSOR_POLL_INTERVAL_S = 2.5

# Calibration Offsets
# Add or subtract offsets to calibrate against a reference instrument.
TEMP_OFFSET_C = 0.0         # Example: -0.5 to lower reading by 0.5°C
HUM_OFFSET_PCT = 0.0        # Example: +2.0 to raise humidity by 2%

# --- Web Server & REST API Settings ---
SERVER_PORT = 80            # Standard HTTP port
SOCKET_TIMEOUT_S = 0.5      # Non-blocking socket timeout
FILE_CHUNK_SIZE = 512       # Stream chunk size in bytes to prevent RAM fragmentation

# Client-side UI polling recommendation (in milliseconds)
CLIENT_POLL_INTERVAL_MS = 3000

# Captive Portal Simulation
# When enabled, intercepts OS probe URLs (/generate_204, /hotspot-detect.html, etc.)
# and redirects them to http://192.168.4.1/ for instant dashboard launch.
ENABLE_CAPTIVE_PORTAL = True

