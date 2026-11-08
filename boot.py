# ==============================================================================
# ESP-ClimateNode: Hardware & Network Bootloader
# ==============================================================================
# Runs automatically at power-on / hardware reset prior to main.py.
# Configures system memory, disables STA interface, and initializes SoftAP.
# ==============================================================================

import gc
import network
import time
import config

# 1. Disable low-level vendor OS debug messages on UART0 (clean serial output)
try:
    import esp
    esp.osdebug(None)
except (ImportError, AttributeError):
    pass

# 2. Enable automatic garbage collection & perform clean boot sweep
gc.enable()
gc.collect()

def init_softap():
    """Configures and activates the standalone Wi-Fi SoftAP interface."""
    print("=" * 50)
    print(" [BOOT] Initializing {} v{}".format(config.DEVICE_NAME, config.FIRMWARE_VERSION))
    print(" [BOOT] Free heap on startup: {} bytes".format(gc.mem_free()))
    print("=" * 50)

    # Disable Station (client) mode to avoid scanning / power waste
    sta = network.WLAN(network.STA_IF)
    if sta.active():
        sta.active(False)

    # Activate Soft Access Point (AP) mode
    ap = network.WLAN(network.AP_IF)
    ap.active(True)

    # Configure Static IP gateway: (IP, Subnet, Gateway, DNS)
    try:
        ap.ifconfig((config.AP_IP, config.AP_SUBNET, config.AP_GATEWAY, config.AP_DNS))
    except Exception as e:
        print(" [BOOT-WARN] Could not set static ifconfig:", e)

    # Configure AP security & wireless parameters
    try:
        if config.WIFI_PASSWORD and len(config.WIFI_PASSWORD) >= 8:
            ap.config(
                essid=config.WIFI_SSID,
                password=config.WIFI_PASSWORD,
                authmode=network.AUTH_WPA2_PSK,
                channel=config.WIFI_CHANNEL
            )
            security_type = "WPA2-PSK"
        else:
            ap.config(
                essid=config.WIFI_SSID,
                authmode=network.AUTH_OPEN,
                channel=config.WIFI_CHANNEL
            )
            security_type = "Open (No Password)"
    except Exception as e:
        print(" [BOOT-ERR] Failed to configure SoftAP parameters:", e)
        security_type = "Default"

    # Allow network radio to stabilize
    time.sleep(0.5)

    ip_info = ap.ifconfig()
    print(" [WIFI] SoftAP Active & Broadcasting!")
    print("        SSID       : {}".format(config.WIFI_SSID))
    print("        Security   : {}".format(security_type))
    print("        Channel    : {}".format(config.WIFI_CHANNEL))
    print("        IP Address : {}".format(ip_info[0]))
    print("        Subnet     : {}".format(ip_info[1]))
    print("=" * 50)

    return ap

# Execute network startup
ap_interface = init_softap()
gc.collect()
