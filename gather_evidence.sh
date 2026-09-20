#!/bin/bash
source .venv/bin/activate
export PYTHONPATH=src

echo -e "\n=== 1. cat docs/audit/parser_reality.md ==="
cat docs/audit/parser_reality.md
echo -e "\n=== 1. cat docs/audit/layout_migration.md ==="
cat docs/audit/layout_migration.md

echo -e "\n=== 2. git log for docs ==="
git log --oneline -- docs/audit/parser_reality.md docs/audit/layout_migration.md

echo -e "\n=== 3. current capabilities() in labwired.py ==="
sed -n '/def capabilities/,/return SimulatorCapabilities/p' src/firmware_agent/simulator/labwired.py | sed -n '1,/return SimulatorCapabilities/p' | head -n 80

echo -e "\n=== 4 & 5. Real Python call for stm32f103, nrf54l15, madeup_chip_xyz ==="
python3 -c "
from firmware_agent.simulator.labwired import LabWiredAdapter
a = LabWiredAdapter()
print('stm32f103:')
c1 = a.capabilities('stm32f103')
print(f'  available={c1.available}, error={c1.error!r}, pins={c1.supported_pins[:10]}...')
print('nrf54l15:')
c2 = a.capabilities('nrf54l15')
print(f'  available={c2.available}, error={c2.error!r}, pins={c2.supported_pins[:10]}...')
print('madeup_chip_xyz:')
c3 = a.capabilities('madeup_chip_xyz')
print(f'  available={c3.available}, error={c3.error!r}, pins={c3.supported_pins}')
"

echo -e "\n=== 6. git diff of chip='stm32f103' removal in cli.py ==="
git log -p -1 HEAD -- src/firmware_agent/cli.py | grep -C 3 "chip="
echo -e "\n=== 6b. Real firmware-agent test run against fan_controller.c ==="
firmware-agent test firmware/demos/fan_controller.c --chip stm32f103

echo -e "\n=== 7. grep -c srcdoc artifacts/report.html ==="
grep -c "srcdoc" artifacts/report.html || echo "NOT FOUND"

echo -e "\n=== 8. Server startup output ==="
uvicorn firmware_agent.server:app --port 8888 > server.log 2>&1 &
SERVER_PID=$!
sleep 2
cat server.log

echo -e "\n=== 9. curl GET / ==="
curl -s http://127.0.0.1:8888/ | head -n 15
echo "..."

echo -e "\n=== 9. curl GET /api/runs/run_correct/trace.json ==="
curl -s http://127.0.0.1:8888/api/runs/run_correct/trace.json | head -c 200
echo "..."

echo -e "\n=== 9. curl GET /view/run_correct ==="
curl -s http://127.0.0.1:8888/view/run_correct | head -n 15
echo "..."

echo -e "\n=== 9. curl GET /api/boards ==="
curl -s http://127.0.0.1:8888/api/boards | head -c 300
echo "..."

echo -e "\n=== 10. curl POST /api/boards (VALID) ==="
curl -s -X POST http://127.0.0.1:8888/api/boards \
  -H "Content-Type: application/json" \
  -d '{"chip": "stm32f103", "peripherals": [{"id": "LED", "pins": ["PC13"]}]}'

echo -e "\n=== 10. curl POST /api/boards (INVALID) ==="
curl -s -X POST http://127.0.0.1:8888/api/boards \
  -H "Content-Type: application/json" \
  -d '{"chip": "stm32f103", "peripherals": [{"id": "LED", "pins": ["INVALID_PIN"]}]}'

kill $SERVER_PID

echo -e "\n\n=== 11. Viewer API load logic snippet ==="
sed -n '/\/\/ Real data wiring boot logic/,/\} else if (inlineCompareEl)/p' src/firmware_agent/reporting/viewer/rig_view.html
