import os
import sys
import time
import requests
from pathlib import Path
import shutil

CACHE_DIR = Path(__file__).parent.parent / ".llm_cache"
BASE_URL = "http://localhost:8080/api"
FIRMWARE_PATH = Path(__file__).parent.parent / "fixtures" / "firmware" / "fan_controller.c"

def main():
    print("=== JOY Golden Run Recorder ===")
    
    # 1. Check if server is running
    try:
        requests.get(f"http://localhost:8080/health")
    except requests.exceptions.ConnectionError:
        print("ERROR: FastAPI server is not running on port 8080.")
        print("Please run `ps3-agent ui --port 8080` in another terminal first.")
        sys.exit(1)

    # 2. Clear cache? Optional, let's keep it to accumulate.
    if CACHE_DIR.exists() and "--clear" in sys.argv:
        print("Clearing old LLM cache...")
        shutil.rmtree(CACHE_DIR)
        
    print("\n1. Starting Golden Run against fan_controller.c...")
    with open(FIRMWARE_PATH, "r") as f:
        code = f.read()
        
    resp = requests.post(f"{BASE_URL}/runs", json={"code": code})
    if resp.status_code != 200:
        print(f"Failed to start run: {resp.text}")
        sys.exit(1)
        
    run_id = resp.json()["run_id"]
    print(f"Run started: {run_id}")
    
    # 3. Poll until finished
    print("2. Polling for agent completion (this may take 20-30 seconds)...")
    while True:
        resp = requests.get(f"{BASE_URL}/runs/{run_id}")
        status = resp.json()["status"]
        if status in ["completed", "failed", "stopped"]:
            break
        time.sleep(2)
        sys.stdout.write(".")
        sys.stdout.flush()
        
    print(f"\nRun completed with status: {status}")
    
    # 4. Trigger Analysis on all failures
    print("\n3. Triggering Root Cause Analysis on failures to populate cache...")
    failures_resp = requests.get(f"{BASE_URL}/runs/{run_id}/failures")
    failures = failures_resp.json().get("failures", [])
    
    if not failures:
        print("No failures detected! This is unexpected for the vulnerable fan_controller.")
    else:
        for f in failures:
            test_id = f["scenario"]["test_id"]
            print(f"  -> Analyzing failure {test_id}...")
            requests.get(f"{BASE_URL}/runs/{run_id}/tests/{test_id}/analysis")
            
    # 5. Trigger Patching
    print("\n4. Triggering Auto-Patch Generation...")
    requests.post(f"{BASE_URL}/runs/{run_id}/patch", json={"fixes": ["Fix boundary conditions"]})
    
    # 6. Verify Cache
    if CACHE_DIR.exists():
        cache_size = len(list(CACHE_DIR.glob("*.db"))) + len(list(CACHE_DIR.glob("*.sqlite")))
        # Actually diskcache creates a diskcache.db
        print(f"\nSUCCESS! Golden run recorded. Cache directory contains data.")
        print("You can now safely restart the server with DEMO_REPLAY_MODE=1")
    else:
        print("\nWARNING: Cache directory not found. Did the LLMGateway cache properly?")

if __name__ == "__main__":
    main()
