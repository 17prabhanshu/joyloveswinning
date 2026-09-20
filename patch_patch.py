with open("frontend/src/components/TestLab.tsx", "r") as f:
    code = f.read()

target = "body: JSON.stringify({ code })"
replacement = "body: JSON.stringify({ fix_snippet: code })"
code = code.replace(target, replacement)

with open("frontend/src/components/TestLab.tsx", "w") as f:
    f.write(code)
