import re

with open("ps3_agent/api/server.py", "r") as f:
    code = f.read()

# Analyze Test Failure Fallback
fallback_analyze = '"{ \\"root_cause\\": \\"Cache Miss (Replay Mode)\\", \\"code_fix\\": \\"// No fix in replay mode\\" }"'
code = code.replace(
    'resp = await llm_gateway.generate_content(prompt)',
    f'resp = await llm_gateway.generate_content(prompt, default_fallback={fallback_analyze})',
    1 # Only replace the first occurrence (analyze_test_failure)
)

# Patch Firmware Fallback
fallback_patch = '"// Cached fallback patch\\nvoid control_fan(void) {\\n  // Safe mode\\n}"'
code = code.replace(
    'resp = await llm_gateway.generate_content(prompt)',
    f'resp = await llm_gateway.generate_content(prompt, default_fallback={fallback_patch})',
    1 # Second occurrence (patch_firmware)
)

# Chat with Agent Fallback
fallback_chat = '"This is a cached response from Replay Mode."'
code = code.replace(
    'resp = await llm_gateway.generate_content(prompt)',
    f'resp = await llm_gateway.generate_content(prompt, default_fallback={fallback_chat})',
    1 # Third occurrence (chat_with_agent)
)

# Also ensure dotenv is loaded at the top
if "from dotenv import load_dotenv" not in code:
    code = "import os\nfrom dotenv import load_dotenv\nload_dotenv()\n" + code

with open("ps3_agent/api/server.py", "w") as f:
    f.write(code)

print("Updated server.py with safe defaults and dotenv.")
