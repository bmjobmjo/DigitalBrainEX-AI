"""
Build script for DigitalBrainEX AI v2.1.0 release binaries.
Executes PyInstaller sequentially for the main executable and installer setup,
logging progress to both stdout and dist/build.log.
"""
import os
import sys
import subprocess
import time
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(ROOT_DIR, "dist", "build.log")

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_step(title, cmd):
    log(f"=== Starting Step: {title} ===")
    log(f"Command: {' '.join(cmd)}")
    start = time.time()
    
    proc = subprocess.Popen(
        cmd,
        cwd=ROOT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    last_log_time = time.time()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        for line in iter(proc.stdout.readline, ""):
            f.write(line)
            now = time.time()
            if ("INFO: Building" in line or "INFO: Creating base_library" in line or
                "INFO: Looking for dynamic libraries" in line or "INFO: Building EXE" in line or
                "INFO: Appending archive" in line or "INFO: Checking" in line or
                now - last_log_time > 15):
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {line.strip()}", flush=True)
                last_log_time = now

    proc.wait()
    duration = time.time() - start
    if proc.returncode != 0:
        log(f"FAILED: {title} exited with code {proc.returncode} after {duration:.1f}s")
        sys.exit(proc.returncode)
    log(f"SUCCESS: {title} finished in {duration:.1f}s")

def main():
    os.makedirs(os.path.join(ROOT_DIR, "dist"), exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== DigitalBrainEX AI Build Session Started: {datetime.now()} ===\n")

    # Step 1: Main App Binary
    run_step("Build DigitalBrainEX.exe", [sys.executable, "-m", "PyInstaller", "DigitalBrainEX.spec", "--noconfirm"])
    app_exe = os.path.join(ROOT_DIR, "dist", "DigitalBrainEX.exe")
    if not os.path.exists(app_exe):
        log("ERROR: dist/DigitalBrainEX.exe not found!")
        sys.exit(1)
    app_size_mb = os.path.getsize(app_exe) / (1024 * 1024)
    log(f"dist/DigitalBrainEX.exe generated successfully ({app_size_mb:.2f} MB)")

    # Step 2: Installer Setup Binary
    run_step("Build DigitalBrainEX_Setup.exe", [sys.executable, "-m", "PyInstaller", "DigitalBrainEX_Setup.spec", "--noconfirm"])
    setup_exe = os.path.join(ROOT_DIR, "dist", "DigitalBrainEX_Setup.exe")
    if not os.path.exists(setup_exe):
        log("ERROR: dist/DigitalBrainEX_Setup.exe not found!")
        sys.exit(1)
    setup_size_mb = os.path.getsize(setup_exe) / (1024 * 1024)
    log(f"dist/DigitalBrainEX_Setup.exe generated successfully ({setup_size_mb:.2f} MB)")

    log("=== ALL RELEASE BINARIES BUILT SUCCESSFULLY ===")

if __name__ == "__main__":
    main()
