with open("ps3_agent/api/server.py", "r") as f:
    code = f.read()

target = """            "simulator": r["execution"].simulator if r.get("execution") else "Unknown",
        })"""

replacement = """            "simulator": r["execution"].simulator if r.get("execution") else "Unknown",
            "minimized": {
                "original": r["minimized"].original_steps,
                "reduced": r["minimized"].minimized_steps
            } if r.get("minimized") else None
        })"""

code = code.replace(target, replacement)

with open("ps3_agent/api/server.py", "w") as f:
    f.write(code)
