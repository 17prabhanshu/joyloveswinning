import requests
res = requests.get("http://localhost:8080/api/runs")
runs = res.json().get("runs", [])
if runs:
    run_id = runs[0]["run_id"]
    tests = requests.get(f"http://localhost:8080/api/runs/{run_id}/tests").json().get("tests", [])
    if tests:
        print(tests[0].keys())
        print(tests[0])
