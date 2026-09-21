with open("frontend/src/components/SetupScreen.tsx", "r") as f:
    code = f.read()

code = code.replace("const [fastMode, setFastMode] = useState(false);", "const [fastMode, setFastMode] = useState(true);")
code = code.replace("Toggle Deterministic Mock Mode", "Toggle Real Hardware Simulation (Slow)")

with open("frontend/src/components/SetupScreen.tsx", "w") as f:
    f.write(code)
