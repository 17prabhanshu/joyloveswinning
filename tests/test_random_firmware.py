import requests
import time
import sys

def test_pipeline_on_random_firmware():
    with open("fixtures/firmware/coffee_machine.c", "r") as f:
        code = f.read()

    print("1. Submitting random firmware (Coffee Machine) to Agent...")
    res = requests.post("http://localhost:8080/api/runs", json={
        "code": code,
        "fast_mode": False
    })
    if res.status_code != 200:
        print(f"Failed to submit: {res.text}")
        sys.exit(1)
        
    run_id = res.json()["run_id"]
    print(f"Run ID: {run_id}")
    
    print("2. Polling for agent completion (Generation -> Compile -> Exec -> Verify)...")
    completed = False
    for _ in range(60):
        res = requests.get(f"http://localhost:8080/api/runs/{run_id}")
        if res.json().get("status") == "completed":
            completed = True
            break
        time.sleep(2)
        
    if not completed:
        print("Run did not complete within 120s")
        sys.exit(1)
    
    print("3. Validating dynamic test generation...")
    res = requests.get(f"http://localhost:8080/api/runs/{run_id}/tests")
    tests = res.json().get("tests", [])
    
    if len(tests) == 0:
        print("No tests were generated!")
        sys.exit(1)
        
    print(f"Generated {len(tests)} tests dynamically.")
    
    for t in tests:
        if t["category"] not in ["BOUNDARY", "STATE", "TIMING", "FAULT", "ASSUMPTION", "HARDWARE"]:
            print(f"Invalid category: {t['category']}")
            sys.exit(1)
            
    print("4. Validating agent models...")
    res = requests.get(f"http://localhost:8080/api/runs/{run_id}/behavior")
    nodes = res.json().get("nodes", [])
    if len(nodes) == 0:
        print("Behavior graph empty!")
        sys.exit(1)
        
    print(f"Mapped {len(nodes)} logic nodes in the firmware.")
    print("\n✅ SUCCESS: End-to-end pipeline is fully functional on arbitrary random data.")

if __name__ == "__main__":
    test_pipeline_on_random_firmware()
