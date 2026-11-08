# ==============================================================================
# ESP-ClimateNode: Core Application Engine
# ==============================================================================
# Manages non-blocking sensor sampling, physiological comfort calculations,
# and the asynchronous HTTP web server serving live telemetry & REST APIs.
# ==============================================================================

import gc
import math
import time
import ujson as json
import usocket as socket
import machine
import dht
import config

# ==============================================================================
# 1. System State & In-Memory Cache
# ==============================================================================
start_ticks = time.ticks_ms()

state = {
    "temperature": 0.0,
    "humidity": 0.0,
    "heat_index": 0.0,
    "dew_point": 0.0,
    "sensor_ok": False,
    "uptime_seconds": 0,
    "read_count": 0,
    "read_errors": 0,
    "last_read_ms": 0
}

# ==============================================================================
# 2. Mathematical Calculations (Heat Index & Dew Point)
# ==============================================================================
def compute_heat_index(temp_c, hum):
    """
    Computes Heat Index ('Feels Like' apparent temperature) using the NOAA
    Rothfusz regression model. Input in °C, output in °C.
    """
    # Convert Celsius to Fahrenheit
    tf = temp_c * 1.8 + 32.0

    # Test simplified Steadman formula first
    hi_simple = 0.5 * (tf + 61.0 + ((tf - 68.0) * 1.2) + (hum * 0.094))

    # If simple formula exceeds 80°F, use full 9-parameter regression
    if (hi_simple + tf) / 2.0 >= 80.0:
        hi = (-42.379 +
              (2.04901523 * tf) +
              (10.14333127 * hum) -
              (0.22475541 * tf * hum) -
              (0.00683783 * tf * tf) -
              (0.05481717 * hum * hum) +
              (0.00122874 * tf * tf * hum) +
              (0.00085282 * tf * hum * hum) -
              (0.00000199 * tf * tf * hum * hum))

        # Adjustments for dry & humid extremes
        if hum < 13.0 and 80.0 <= tf <= 112.0:
            adj = ((13.0 - hum) / 4.0) * math.sqrt((17.0 - abs(tf - 95.0)) / 17.0)
            hi -= adj
        elif hum > 85.0 and 80.0 <= tf <= 87.0:
            adj = ((hum - 85.0) / 10.0) * ((87.0 - tf) / 5.0)
            hi += adj
    else:
        hi = hi_simple

    # Convert back to Celsius and round
    hi_c = (hi - 32.0) / 1.8
    return round(hi_c, 1)


def compute_dew_point(temp_c, hum):
    """
    Computes Dew Point temperature in °C using the Magnus-Tetens approximation.
    Valid for temperatures between 0°C and 60°C.
    """
    if hum <= 0.0:
        return temp_c

    a = 17.27
    b = 237.7
    try:
        alpha = ((a * temp_c) / (b + temp_c)) + math.log(hum / 100.0)
        dew_point = (b * alpha) / (a - alpha)
        return round(dew_point, 1)
    except Exception:
        return temp_c


# ==============================================================================
# 3. Sensor Interfacing & Decoupled Polling
# ==============================================================================
# Initialize DHT22 on designated GPIO pin
sensor_pin = machine.Pin(config.SENSOR_PIN, machine.Pin.IN)
sensor = dht.DHT22(sensor_pin)

def sample_sensor():
    """
    Reads physical DHT22 sensor, applies calibration offsets,
    calculates derived environmental metrics, and updates the in-memory cache.
    Guaranteed non-crashing on hardware timeouts or parity errors.
    """
    now = time.ticks_ms()
    state["last_read_ms"] = now
    state["uptime_seconds"] = time.ticks_diff(now, start_ticks) // 1000

    try:
        sensor.measure()
        raw_temp = sensor.temperature()
        raw_hum = sensor.humidity()

        # Apply calibration offsets from config.py
        cal_temp = round(raw_temp + config.TEMP_OFFSET_C, 1)
        cal_hum = round(raw_hum + config.HUM_OFFSET_PCT, 1)

        # Clamp humidity to physical range
        cal_hum = max(0.0, min(100.0, cal_hum))

        # Compute apparent metrics
        hi = compute_heat_index(cal_temp, cal_hum)
        dp = compute_dew_point(cal_temp, cal_hum)

        # Update cache
        state["temperature"] = cal_temp
        state["humidity"] = cal_hum
        state["heat_index"] = hi
        state["dew_point"] = dp
        state["sensor_ok"] = True
        state["read_count"] += 1

        print("[SENSOR] Read OK: {:.1f}°C, {:.1f}% RH (HI: {:.1f}°C, DP: {:.1f}°C)".format(
            cal_temp, cal_hum, hi, dp))

    except OSError as err:
        state["read_errors"] += 1
        print("[SENSOR-WARN] DHT22 bus error (OSError {}). Retrying next cycle...".format(err))
        # Keep previous valid readings in cache so web UI doesn't blank out


# ==============================================================================
# 4. HTTP Server & Request Dispatcher
# ==============================================================================
CAPTIVE_PROBE_PATHS = [
    "/generate_204",
    "/gen_204",
    "/hotspot-detect.html",
    "/ncsi.txt",
    "/connecttest.txt",
    "/canonical.html",
    "/library/test/success.html"
]

def parse_http_request(raw_request):
    """Extracts HTTP method and path from raw client socket buffer."""
    try:
        first_line = raw_request.split(b"\r\n", 1)[0]
        parts = first_line.split()
        if len(parts) >= 2:
            return parts[0].decode("utf-8"), parts[1].decode("utf-8")
    except Exception:
        pass
    return "GET", "/"


def stream_file(client_sock, file_path, content_type="text/html"):
    """Streams a file from flash memory in small chunks to protect RAM heap."""
    try:
        with open(file_path, "rb") as f:
            header = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: {}; charset=utf-8\r\n"
                "Cache-Control: no-cache, no-store, must-revalidate\r\n"
                "Connection: close\r\n\r\n"
            ).format(content_type)
            client_sock.sendall(header.encode("utf-8"))

            while True:
                chunk = f.read(config.FILE_CHUNK_SIZE)
                if not chunk:
                    break
                client_sock.sendall(chunk)
    except OSError:
        # Fallback if file not found
        send_fallback_dashboard(client_sock)


def send_fallback_dashboard(client_sock):
    """Inline minimal dashboard if web/index.html is missing."""
    body = (
        "<!DOCTYPE html><html><head><title>ESP-ClimateNode</title>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<style>body{font-family:sans-serif;padding:2rem;text-align:center;background:#111;color:#fff}"
        "h1{color:#38bdf8}.box{background:#222;padding:1.5rem;border-radius:12px;margin:1rem auto;max-width:320px}</style>"
        "</head><body><h1>ESP-ClimateNode</h1>"
        "<div class='box'><h2>{:.1f}&deg;C</h2><p>Temperature</p></div>"
        "<div class='box'><h2>{:.1f}%</h2><p>Humidity</p></div>"
        "<p><small>Uptime: {}s | Free RAM: {} bytes</small></p>"
        "<script>setTimeout(()=>location.reload(),3000)</script>"
        "</body></html>"
    ).format(state["temperature"], state["humidity"], state["uptime_seconds"], gc.mem_free())

    response = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "Content-Length: {}\r\n"
        "Connection: close\r\n\r\n{}"
    ).format(len(body), body)
    client_sock.sendall(response.encode("utf-8"))


def send_json(client_sock, payload, status_code="200 OK"):
    """Sends JSON response with CORS headers."""
    body = json.dumps(payload)
    response = (
        "HTTP/1.1 {}\r\n"
        "Content-Type: application/json; charset=utf-8\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "Content-Length: {}\r\n"
        "Connection: close\r\n\r\n{}"
    ).format(status_code, len(body), body)
    client_sock.sendall(response.encode("utf-8"))


def send_redirect(client_sock, location="http://192.168.4.1/"):
    """Sends 302 Found redirect for captive portal detection."""
    response = (
        "HTTP/1.1 302 Found\r\n"
        "Location: {}\r\n"
        "Content-Length: 0\r\n"
        "Connection: close\r\n\r\n"
    ).format(location)
    client_sock.sendall(response.encode("utf-8"))


def handle_http_client(client_sock):
    """Processes incoming HTTP client socket connection."""
    try:
        client_sock.settimeout(config.SOCKET_TIMEOUT_S)
        raw_request = client_sock.recv(1024)
        if not raw_request:
            return

        method, path = parse_http_request(raw_request)

        # Captive portal probe interception
        if config.ENABLE_CAPTIVE_PORTAL and (path in CAPTIVE_PROBE_PATHS):
            send_redirect(client_sock)
            return

        # Route: Serve Dashboard SPA
        if path == "/" or path == "/index.html":
            stream_file(client_sock, "web/index.html", "text/html")

        # Route: Real-time Telemetry JSON
        elif path == "/api/data":
            telemetry_payload = {
                "temperature": state["temperature"],
                "humidity": state["humidity"],
                "heat_index": state["heat_index"],
                "dew_point": state["dew_point"],
                "sensor_ok": state["sensor_ok"],
                "uptime_seconds": state["uptime_seconds"],
                "read_count": state["read_count"],
                "read_errors": state["read_errors"]
            }
            send_json(client_sock, telemetry_payload)

        # Route: System Diagnostics JSON
        elif path == "/api/status":
            status_payload = {
                "device": config.DEVICE_NAME,
                "version": config.FIRMWARE_VERSION,
                "chip": "ESP8266EX",
                "free_heap_bytes": gc.mem_free(),
                "uptime_seconds": state["uptime_seconds"],
                "wifi_ssid": config.WIFI_SSID,
                "ip_address": config.AP_IP,
                "read_errors": state["read_errors"]
            }
            send_json(client_sock, status_payload)

        # Route: Not Found / Captive Fallback
        else:
            if getattr(config, "ENABLE_CAPTIVE_PORTAL", True) and not path.startswith("/api/"):
                send_redirect(client_sock, "/")
            else:
                send_json(client_sock, {"error": "Endpoint not found", "path": path}, "404 Not Found")

    except Exception as e:
        print("[HTTP-ERR] Error handling client request:", e)
    finally:
        try:
            client_sock.close()
        except Exception:
            pass
        # Perform garbage collection after each client disconnect to keep heap clean
        gc.collect()


# ==============================================================================
# 5. Main Application Event Loop
# ==============================================================================
def start_server():
    """Initializes listening TCP & UDP sockets and runs the cooperative event loop."""
    addr = socket.getaddrinfo("0.0.0.0", config.SERVER_PORT)[0][-1]
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(addr)
    server_sock.listen(2)
    server_sock.settimeout(0.05)  # Fast 50ms cooperative timeout

    # Initialize non-blocking DNS server for friendly local domain resolution & captive portal
    dns_server = None
    if getattr(config, "ENABLE_DNS_SERVER", True):
        try:
            from dnsserver import DNSServer
            dns_port = getattr(config, "DNS_PORT", 53)
            dns_server = DNSServer(ip=config.AP_IP, port=dns_port)
        except Exception as e:
            print(" [DNS-WARN] Could not initialize DNS server:", e)

    domain_str = getattr(config, "DOMAIN_NAME", "climate.local")
    print("=" * 50)
    print(" [SERVER] HTTP Server active on:")
    print("          - http://{}:{}".format(config.AP_IP, config.SERVER_PORT))
    print("          - http://{}/".format(domain_str))
    print(" [SERVER] Ready for client connections.")
    print("=" * 50)

    # Initial sensor read
    sample_sensor()
    last_sensor_sample = time.ticks_ms()
    poll_interval_ms = int(config.SENSOR_POLL_INTERVAL_S * 1000)

    while True:
        try:
            # 1. Drain pending DNS queries (Captive / Custom Domain resolution)
            if dns_server:
                for _ in range(3):
                    dns_server.process()

            # 2. Periodic Sensor Polling (Decoupled from HTTP requests)
            now = time.ticks_ms()
            if time.ticks_diff(now, last_sensor_sample) >= poll_interval_ms:
                sample_sensor()
                last_sensor_sample = now

            # 3. Check for incoming HTTP client connections
            try:
                client_sock, client_addr = server_sock.accept()
                handle_http_client(client_sock)
            except OSError:
                # Socket timeout (no client pending), continue loop
                pass

        except KeyboardInterrupt:
            print("\n[STOP] Server stopped by user.")
            break
        except Exception as e:
            print("[LOOP-ERR] Unexpected error in event loop:", e)
            time.sleep(0.5)

    server_sock.close()
    if dns_server:
        dns_server.close()


# Launch main engine directly on boot
start_server()

