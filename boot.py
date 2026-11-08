# ==============================================================================
# ESP-ClimateNode: System Bootloader
# ==============================================================================
# Runs once at hardware reset prior to main.py.
# Prepares system memory hygiene and silences vendor OS debug output on UART0.
# Application logic and network services are managed in main.py.
# ==============================================================================

import gc

# 1. Silence low-level vendor OS debug messages on UART0
try:
    import esp
    esp.osdebug(None)
except (ImportError, AttributeError):
    pass

# 2. Enable automatic garbage collection & run initial memory sweep
gc.enable()
gc.collect()
