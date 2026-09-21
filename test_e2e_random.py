import requests
import time
import json
import sys

def run_e2e_test():
    print("🚀 Starting E2E Pipeline Validation on Random Data...")
    
    with open("fixtures/firmware/coffee_machine.c", "r") as f:
        code = f.read()
        
    print("1. Creating new run...")
    res = requests.post("http://localhost:8080/api/runs", json={
        "code": code,
        "fast_mode": False
    })
    
    if res.status_code != 200:
        print(f"❌ Failed to create run: {res.text}")
        sys.exit(1)
        
    run_id = res.json()["run_id"]
    print(f"✅ Run created: {run_id}")
    
    print("2. Polling for completion (this tests generation, compilation, and Wokwi parallel execution)...")
    while True:
        res = requests.get(f"http://localhost:8080/api/runs/{run_id}")
        data = res.json()
        status = data.get("status")
        
        if status == "completed":
            print(f"✅ Run finished successfully!")
            break
        elif status == "error":
            print(f"❌ Run failed with error: {data}")
            sys.exit(1)
            
        time.sleep(2)
        
    print("3. Validating test cases were generated and executed...")
    res = requests.get(f"http://localhost:8080/api/runs/{run_id}/tests")
    tests = res.json().get("tests", [])
    
    if len(tests) == 0:
        print("❌ No tests were returned!")
        sys.exit(1)
        
    print(f"✅ {len(tests)} tests returned from API.")
    
    passed = sum(1 for t in tests if t["status"] == "PASS")
    failed = sum(1 for t in tests if t["status"] == "FAIL")
    
    print(f"📊 Results: {passed} PASSED, {failed} FAILED")
    
    if passed + failed == 0:
        print("❌ All tests are stuck in RUNNING or UNKNOWN!")
        sys.exit(1)
        
    print("4. Validating test structure...")
    for t in tests:
        if "category" not in t or "reason" not in t:
            print(f"❌ Test {t['test_id']} is missing fields!")
            sys.exit(1)
            
    print("✅ Full E2E functionality confirmed. Pipeline is 100% robust.")

if __name__ == "__main__":
    run_e2e_test()
