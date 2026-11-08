@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   ESP-ClimateNode: 1-Click Firmware Deployer
echo ===================================================
echo.

:: 1. Prompt for COM Port
set /p COM_PORT="Enter your ESP8266 COM Port (e.g. COM3): "
if "%COM_PORT%"=="" (
    echo [ERROR] No COM port specified. Exiting...
    pause
    exit /b 1
)

echo.
echo Select an action:
echo [1] Upload firmware files only (boot.py, config.py, main.py, web/)
echo [2] Flash new MicroPython binary + Upload firmware
echo.
set /p ACTION="Enter option (1 or 2): "

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
        echo [ERROR] Flash erase failed. Check connections.
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
    echo [ERROR] File transfer failed. Ensure Thonny or other serial monitors are closed.
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
