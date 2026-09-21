from ps3_agent.api.server import active_runs
import sys

run_id = "run_8d98e07b"
if run_id not in active_runs:
    print("Run not found in memory!")
else:
    agent = active_runs[run_id]["agent"]
    print(f"Total test results: {len(agent.test_results)}")
    for r in agent.test_results:
        print(f"  {r['scenario'].test_id}: {r['verification'].status.value}")
