import json
import hashlib
from typing import Any
from firmware_agent.simulator.base import SimulationResult

def emit_trace_v1(result: SimulationResult, output_path: str, chip: str = "stm32f103"):
    """Convert LabWired results to schemas/trace.v1.json format."""
    
    # Load board descriptor
    import os
    board_descriptor = {
        "chip": chip,
        "package": "generic",
        "pin_count": 0,
        "peripherals": []
    }
    
    board_json_path = os.path.join("hardware", "boards", f"{chip}.json")
    if os.path.exists(board_json_path):
        with open(board_json_path, "r") as bf:
            board_descriptor = json.load(bf)
            
        # Validate pins against simulator capabilities
        from firmware_agent.simulator.labwired import LabWiredAdapter
        cap = LabWiredAdapter().capabilities(chip)
        if cap.available and cap.supported_pins:
            for p in board_descriptor.get("peripherals", []):
                for pin in p.get("pins", []):
                    if pin not in cap.supported_pins and pin not in ["TX", "RX"]:
                        raise ValueError(f"Descriptor references pin {pin} which simulator does not recognize for chip {chip}")
        elif not cap.available:
            import logging
            logging.getLogger(__name__).warning(f"Chip '{chip}' not available in simulator: {cap.error}. Skipping pin validation.")
                        
    trace = {
        "schema": "trace.v1",
        "run_id": result.raw_result.get("config", {}).get("script", "").split("/")[-2] if "config" in result.raw_result else "unknown",
        "test_id": "test_scenario",
        "firmware_hash": result.raw_result.get("firmware_hash", ""),
        "verdict": "PASS" if result.status == "pass" else "FAIL" if result.status == "fail" else "UNAVAILABLE",
        "duration_ns": result.cycles * 10, # Mock 100MHz clock for now
        "board": board_descriptor,
        "channels": {

            "gpio": [],
            "uart": [],
            "registers": [],
            "sensors": [],
            "faults": [],
            "execution": []
        },
        "assertions": []
    }
    

    # 2. Extract GPIO logic edges
    logic_edges = result.raw_result.get("logic_edges", {})
    
    # Get existing peripheral IDs
    existing_pids = {p.get("id") for p in trace["board"]["peripherals"]}
    
    for channel in logic_edges.get("channels", []):
        port = channel.get("peripheral", "").replace("gpio", "").upper()
        pin = channel.get("pin", "")
        key = f"P{port}{pin}"
        
        # Add to board peripherals only if not already present
        if key not in existing_pids and not any(key in p.get("pins", []) for p in trace["board"]["peripherals"]):
            trace["board"]["peripherals"].append({
                "id": key,
                "kind": "gpio",
                "label": f"GPIO {key}",
                "position": [0, 0, 0],
                "pins": [key]
            })

        
        # Add initial state
        trace["channels"]["gpio"].append({
            "t_ns": 0,
            "pin": key,
            "value": channel.get("initial", 0)
        })
        
        # Add transitions
        for trans in channel.get("transitions", []):
            cycle = trans.get("cycle", 0)
            trace["channels"]["gpio"].append({
                "t_ns": cycle * 10,
                "pin": key,
                "value": trans.get("value", 0)
            })
            
    # 3. Add UART
    if result.uart_output:
        import base64
        b64 = base64.b64encode(result.uart_output.encode()).decode()
        trace["channels"]["uart"].append({
            "t_ns": 0,
            "direction": "tx",
            "bytes": b64
        })
        
    with open(output_path, "w") as f:
        json.dump(trace, f, indent=2)
