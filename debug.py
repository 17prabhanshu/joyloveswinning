import requests

run_id = "run_8d98e07b"
res = requests.get(f"http://localhost:8080/api/runs/{run_id}/tests")
tests = res.json().get("tests", [])

for t in tests:
    print(t["test_id"], t["status"])
