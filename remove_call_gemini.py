import re

with open("ps3_agent/api/server.py", "r") as f:
    code = f.read()

# Remove the old call_gemini implementation
start_idx = code.find("async def call_gemini(prompt: str) -> httpx.Response:")
if start_idx != -1:
    end_idx = code.find("app = FastAPI", start_idx)
    if end_idx != -1:
        code = code[:start_idx] + "from ps3_agent.api.llm_gateway import gateway as llm_gateway\n\n" + code[end_idx:]

# Replace `resp = await call_gemini(prompt)` with `resp = await llm_gateway.generate_content(prompt)`
code = code.replace("resp = await call_gemini(prompt)", "resp = await llm_gateway.generate_content(prompt)")

with open("ps3_agent/api/server.py", "w") as f:
    f.write(code)

print("Updated server.py to use LLMGateway")
