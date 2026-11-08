#!/usr/bin/env python3
"""
ESP-ClimateNode: Smart Differential Flash Synchronizer
Calculates on-chip SHA-256 hashes and only flashes files that have changed.
Eliminates unnecessary flash erase/write cycles to maximize ESP8266 SPI flash lifespan.
"""

import os
import sys
import hashlib
import subprocess

# Device firmware files mapped to ESP8266 target paths
SYNC_FILES = [
    ("firmware/boot.py", "boot.py"),
    ("firmware/config.py", "config.py"),
    ("firmware/main.py", "main.py"),
    ("firmware/web/index.html", "web/index.html")
]

DEVICE_HASH_SCRIPT = """
import os, uhashlib, ubinascii
files = ['boot.py', 'config.py', 'main.py', 'web/index.html']
for p in files:
    try:
        h = uhashlib.sha256()
        with open(p, 'rb') as f:
            while True:
                c = f.read(256)
                if not c:
                    break
                h.update(c)
        print(p + '=' + ubinascii.hexlify(h.digest()).decode())
    except Exception:
        print(p + '=MISSING')
"""

def compute_local_hash(file_path):
    """Computes SHA-256 hash of a local file."""
    if not os.path.exists(file_path):
        return None
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def get_remote_hashes(port):
    """Queries ESP8266 to compute remote hashes in a single non-writing pass."""
    cmd = [
        sys.executable, "-m", "mpremote", "connect", port,
        "exec", DEVICE_HASH_SCRIPT.strip()
    ]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=True
        )
        remote_hashes = {}
        for line in result.stdout.strip().splitlines():
            if "=" in line:
                path, h = line.split("=", 1)
                remote_hashes[path.strip()] = h.strip()
        return remote_hashes
    except Exception as e:
        # If hash script fails (e.g. initial clean board without files), return empty
        return {}


def main():
    if len(sys.argv) < 2:
        print("[ERROR] Missing port argument. Usage: sync.py <COM_PORT>")
        sys.exit(1)

    port = sys.argv[1]
    print(f"[*] Querying ESP8266 on {port} for existing file checksums...")

    remote_hashes = get_remote_hashes(port)

    files_written = 0
    files_skipped = 0

    print("[*] Differential Sync Analysis:")

    for local_path, remote_path in SYNC_FILES:
        if not os.path.exists(local_path):
            continue

        local_hash = compute_local_hash(local_path)
        remote_hash = remote_hashes.get(remote_path)

        if remote_hash and local_hash == remote_hash:
            print(f"  [=] {remote_path:<16} : UP-TO-DATE (Skipped - 0 flash writes)")
            files_skipped += 1
        else:
            action = "NEW FILE" if not remote_hash or remote_hash == "MISSING" else "MODIFIED"
            print(f"  [^] {remote_path:<16} : {action} -> Writing to flash...")

            # Ensure parent directory exists on remote if needed
            if "/" in remote_path:
                remote_dir = remote_path.rsplit("/", 1)[0]
                mkdir_cmd = [
                    sys.executable, "-m", "mpremote", "connect", port,
                    "mkdir", f":{remote_dir}"
                ]
                subprocess.run(mkdir_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Upload modified file
            upload_cmd = [
                sys.executable, "-m", "mpremote", "connect", port,
                "cp", local_path, f":{remote_path}"
            ]
            res = subprocess.run(upload_cmd)
            if res.returncode == 0:
                files_written += 1
            else:
                print(f"  [!] Failed to upload {remote_path}")
                sys.exit(1)

    print("-" * 50)
    if files_written == 0:
        print("[+] Flash Memory Preserved: All files identical. Zero writes performed.")
    else:
        print(f"[+] Sync Complete: {files_written} file(s) updated, {files_skipped} file(s) preserved.")

    # Soft reset to start updated firmware
    print("[*] Resetting microcontroller...")
    subprocess.run([sys.executable, "-m", "mpremote", "connect", port, "reset"], stdout=subprocess.DEVNULL)
    print("[+] Device ready!")


if __name__ == "__main__":
    main()

