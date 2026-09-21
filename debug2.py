import requests

res = requests.get("http://localhost:8080/api/runs/run_8d98e07b")
print("Run Status:", res.json()["status"])

res = requests.get("http://localhost:8080/api/runs/run_8d98e07b/events")
events = res.json()["events"]
for e in events:
    if e["action"] == "EXECUTE" or "PLAN" in e["action"]:
        print(e["timestamp"], e["agent"], e["reason"])
