#!/bin/bash
source .venv/bin/activate
export PYTHONPATH=src

echo "========================================="
echo "=== PREREQUISITES VERIFICATION ========="
echo "========================================="

echo -e "\n--- Prereq 1: capabilities() ---"
python3 -c "
from firmware_agent.simulator.labwired import LabWiredAdapter
a = LabWiredAdapter()
c1 = a.capabilities('stm32f103')
print(f'stm32f103: available={c1.available}, pins={len(c1.supported_pins)}, sample={c1.supported_pins[:3]}')
c2 = a.capabilities('nrf54l15')
print(f'nrf54l15: available={c2.available}, pins={len(c2.supported_pins)}, sample={c2.supported_pins[:3]}')
c3 = a.capabilities('bogus')
print(f'bogus: available={c3.available}, error={c3.error[:80]}')
"

echo -e "\n--- Prereq 2: Docs ---"
git show HEAD^:docs/audit/parser_reality.md | head -n 3
echo "[diff from previous commit]"
git diff HEAD^ HEAD -- docs/audit/parser_reality.md | head -n 10

echo -e "\n--- Prereq 3: No dummy ---"
grep -B 1 -A 1 "demo_chip" src/firmware_agent/cli.py

echo -e "\n--- Prereq 4: srcdoc ---"
grep -c "srcdoc" artifacts/report.html


echo -e "\n\n========================================="
echo "=== PART A VERIFICATION ================="
echo "========================================="
echo "Starting uvicorn on port 8765..."
uvicorn firmware_agent.server:app --host 127.0.0.1 --port 8765 > uvicorn.log 2>&1 &
PID=$!
sleep 2

echo -e "\n--- GET /api/runs ---"
curl -s http://127.0.0.1:8765/api/runs

echo -e "\n\n--- GET /api/boards ---"
curl -s http://127.0.0.1:8765/api/boards | head -c 300
echo "..."

echo -e "\n\n--- GET /view/run_correct (HTML Check) ---"
curl -s http://127.0.0.1:8765/view/run_correct | head -n 15

echo -e "\n\n--- POST /api/boards (Success) ---"
curl -s -X POST http://127.0.0.1:8765/api/boards \
  -H "Content-Type: application/json" \
  -d '{"chip": "stm32f103", "peripherals": [{"id": "LED", "pins": ["PC13"]}]}'

echo -e "\n\n--- POST /api/boards (Failure - Invalid Pin) ---"
curl -s -X POST http://127.0.0.1:8765/api/boards \
  -H "Content-Type: application/json" \
  -d '{"chip": "stm32f103", "peripherals": [{"id": "LED", "pins": ["INVALID_PIN"]}]}'

echo -e "\n\n--- CLI view command replacement ---"
firmware-agent view run_correct

kill $PID
