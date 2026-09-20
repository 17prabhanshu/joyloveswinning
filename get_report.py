import requests
import json
import time

resp = requests.post("http://localhost:8080/api/runs", json={"code": open("fixtures/firmware/fan_controller.c").read()})
run_id = resp.json()["run_id"]
print(f"Started run {run_id}")

while True:
    st = requests.get(f"http://localhost:8080/api/runs/{run_id}").json()["status"]
    if st in ["completed", "failed"]: break
    time.sleep(1)

report = requests.get(f"http://localhost:8080/api/runs/{run_id}/report").text
print("="*40)
print(report)
