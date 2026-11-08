@echo off
setlocal enabledelayedexpansion

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
    python -m pip install mpremote
    if errorlevel 1 (
        echo [ERROR] Failed to install mpremote. Check your internet connection.
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
:: Automatic Serial Port Detection (Windows)
:: -------------------------------------------------------------
echo [*] Scanning for connected serial devices...

set "PORT_COUNT=0"
set "DETECTED_PORT="
set "ALL_PORTS="

for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -Command "[System.IO.Ports.SerialPort]::GetPortNames()"`) do (
    set /a PORT_COUNT+=1
    set "DETECTED_PORT=%%i"
    set "ALL_PORTS=!ALL_PORTS! %%i"
)

if %PORT_COUNT% EQU 1 (
    if /i "!DETECTED_PORT!"=="COM1" (
        echo [!] Notice: Only COM1 detected. On many desktop PCs, COM1 is a motherboard port.
        echo     If your ESP8266 is connected via USB, make sure you use a data cable or install CH340 / CP2102 drivers.
    )
    echo [+] Detected serial port: !DETECTED_PORT!
    set /p "USER_PORT=Press Enter to use [!DETECTED_PORT!], or type a different port: "
    if "!USER_PORT!"=="" (
        set "COM_PORT=!DETECTED_PORT!"
    ) else (
        set "COM_PORT=!USER_PORT!"
    )
) else if %PORT_COUNT% GTR 1 (
    echo [!] Multiple serial ports detected:!ALL_PORTS!
    echo.
    set /p "COM_PORT=Enter your ESP8266 COM Port [e.g. COM3]: "
) else (
    echo [-] No COM ports automatically detected.
    echo     Please verify your ESP8266 is plugged in with a USB data cable.
    set /p "COM_PORT=Enter your ESP8266 COM Port manually [e.g. COM3]: "
)

if "%COM_PORT%"=="" (
    echo [ERROR] No COM port specified. Exiting...
    pause
    exit /b 1
)

echo [*] Using port: %COM_PORT%
echo.

:: -------------------------------------------------------------
:: Deployment Action Selection
:: -------------------------------------------------------------
echo Select an action:
echo   [1] Upload firmware files only [boot.py, config.py, main.py, web/]
echo   [2] Flash fresh MicroPython binary + Upload firmware
echo.
set "ACTION=1"
set /p ACTION="Enter option 1 or 2 [default 1]: "

if "%ACTION%"=="2" (
    set /p BIN_FILE="Enter path to MicroPython .bin firmware: "
    if not exist "!BIN_FILE!" (
        echo [ERROR] Firmware file not found: !BIN_FILE!
        pause
        exit /b 1
    )
    echo.
    echo [*] Erasing flash memory on %COM_PORT%...
    python -m esptool --port %COM_PORT% erase_flash
    if errorlevel 1 (
        echo [ERROR] Flash erase failed. Check cable and port.
        pause
        exit /b 1
    )
    echo.
    echo [*] Writing MicroPython binary...
    python -m esptool --port %COM_PORT% --baud 460800 write_flash --flash_size=detect 0 "!BIN_FILE!"
    if errorlevel 1 (
        echo [ERROR] Firmware flash failed.
        pause
        exit /b 1
    )
    echo [*] Firmware flashed successfully! Waiting 2 seconds for boot...
    timeout /t 2 /nobreak >nul
)

echo.
echo [*] Uploading firmware files from firmware/ to ESP8266 root...
python -m mpremote connect %COM_PORT% cp -r firmware/* :
if errorlevel 1 (
    echo.
    echo [ERROR] File transfer failed.
    echo Suggestions:
    echo   1. Close Thonny IDE or any open Serial Monitors.
    echo   2. Verify that %COM_PORT% is the correct USB-to-UART port.
    echo   3. Press the physical RST button on the ESP8266 and try again.
    pause
    exit /b 1
)

echo.
echo [*] Resetting microcontroller...
python -m mpremote connect %COM_PORT% reset

echo.
echo ===================================================
echo   Deployment Complete!
echo   Connect to Wi-Fi: ESP-Climate-Node
echo   Open dashboard  : http://192.168.4.1
echo ===================================================
pause
