@echo off
setlocal enabledelayedexpansion

:: Guarantee execution from project root directory regardless of how it was launched
cd /d "%~dp0\.."

echo ===================================================
echo   ESP-ClimateNode: 1-Click Firmware Deployer
echo ===================================================
echo.

:: -------------------------------------------------------------
:: Dependency Check (Auto-install mpremote & esptool if missing)
:: -------------------------------------------------------------
python -c "import mpremote" >nul 2>nul
if errorlevel 1 (
    echo [*] 'mpremote' not found. Installing via pip...
    python -m pip install mpremote pyserial
    if errorlevel 1 (
        echo [ERROR] Failed to install mpremote. Check internet connection.
        pause
        exit /b 1
    )
)

python -c "import esptool" >nul 2>nul
if errorlevel 1 (
    echo [*] 'esptool' not found. Installing via pip...
    python -m pip install esptool
)

:: -------------------------------------------------------------
:: Intelligent Serial Port Detection (Prioritizes USB devices)
:: -------------------------------------------------------------
echo [*] Connected serial devices:
python -c "import serial.tools.list_ports; [print(f'     -> {p.device}: {p.description}') for p in serial.tools.list_ports.comports()]" 2>nul
echo.

set "AUTO_PORT="
for /f "usebackq tokens=*" %%p in (`python -c "import serial.tools.list_ports; usb = [p.device for p in serial.tools.list_ports.comports() if any(k in (p.description + p.hwid).upper() for k in ['USB', 'CH340', 'CP210', 'FTDI', 'UART'])]; print(usb[0] if usb else '')" 2^>nul`) do (
    set "AUTO_PORT=%%p"
)

set "INPUT_PORT="
set "COM_PORT="

if defined AUTO_PORT (
    for /f "tokens=1" %%a in ("!AUTO_PORT!") do set "COM_PORT=%%a"
    echo [+] Auto-detected ESP8266 on: !COM_PORT!
    set /p "INPUT_PORT=Press Enter to use [!COM_PORT!], or enter custom port: "
) else (
    set /p "INPUT_PORT=Enter your ESP8266 COM Port (e.g. COM6): "
)

if defined INPUT_PORT (
    for /f "tokens=1" %%a in ("!INPUT_PORT!") do set "COM_PORT=%%a"
)

if "!COM_PORT!"=="" (
    echo [ERROR] No COM port specified. Exiting...
    pause
    exit /b 1
)

echo [*] Target port selected: !COM_PORT!
echo.

:: -------------------------------------------------------------
:: Deployment Action Selection
:: -------------------------------------------------------------
echo Select an action:
echo   [1] Smart Differential Sync [Only writes modified files - saves flash wear]
echo   [2] Flash fresh MicroPython binary + Upload firmware
echo.
set "ACTION=1"
set /p ACTION="Enter option (1 or 2) [default 1]: "

if "!ACTION!"=="2" (
    set /p BIN_FILE="Enter path to MicroPython .bin firmware: "
    if not exist "!BIN_FILE!" (
        echo [ERROR] Firmware file not found: !BIN_FILE!
        pause
        exit /b 1
    )
    echo.
    echo [*] Erasing flash memory on !COM_PORT!...
    python -m esptool --port !COM_PORT! erase_flash
    if errorlevel 1 (
        echo [ERROR] Flash erase failed. Check cable and port.
        pause
        exit /b 1
    )
    echo.
    echo [*] Writing MicroPython binary...
    python -m esptool --port !COM_PORT! --baud 460800 write_flash --flash_size=detect 0 "!BIN_FILE!"
    if errorlevel 1 (
        echo [ERROR] Firmware flash failed.
        pause
        exit /b 1
    )
    echo [*] Firmware flashed successfully! Waiting 2 seconds for boot...
    timeout /t 2 /nobreak >nul
)

echo.
echo [*] Executing Smart Differential Sync on !COM_PORT!...
python scripts\sync.py !COM_PORT!
if errorlevel 1 goto TransferError

echo.
echo ===================================================
echo   Deployment Successful!
echo   Connect to Wi-Fi: ESP-Climate-Node
echo   Open dashboard  : http://climate.local
echo   Alternative IP  : http://192.168.4.1
echo ===================================================
pause
exit /b 0

:TransferError
echo.
echo [ERROR] Sync or transfer failed on !COM_PORT!!
echo Troubleshooting Suggestions:
echo   1. Ensure Thonny IDE or any open Serial Monitor is CLOSED.
echo   2. Press the physical RST button on the ESP8266 and try again.
echo   3. Unplug and replug the USB cable.
echo.
pause
exit /b 1
