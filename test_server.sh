#!/bin/bash
source .venv/bin/activate
export PYTHONPATH=src

echo "=== Starting uvicorn ==="
uvicorn firmware_agent.server:app --host 127.0.0.1 --port 8765 &
PID=$!
sleep 2

echo -e "\n=== GET /api/runs ==="
curl -s http://127.0.0.1:8765/api/runs

echo -e "\n\n=== GET /api/boards ==="
curl -s http://127.0.0.1:8765/api/boards | head -c 500
echo "..."

echo -e "\n\n=== GET /view/run_correct (HTML Check) ==="
curl -s http://127.0.0.1:8765/view/run_correct | head -n 25

echo -e "\n\n=== POST /api/boards (Success) ==="
curl -s -X POST http://127.0.0.1:8765/api/boards \
  -H "Content-Type: application/json" \
  -d '{"chip": "stm32f103", "peripherals": [{"id": "LED", "pins": ["PC13"]}]}'

echo -e "\n\n=== POST /api/boards (Failure - Invalid Pin) ==="
curl -s -X POST http://127.0.0.1:8765/api/boards \
  -H "Content-Type: application/json" \
  -d '{"chip": "stm32f103", "peripherals": [{"id": "LED", "pins": ["INVALID_PIN"]}]}'

kill $PID
