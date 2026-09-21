from ps3_agent.api.server import active_runs
from ps3_agent.api.llm_gateway import gateway
import os
print("Gemini Key:", gateway.api_key)
print("Wokwi Token:", os.environ.get("WOKWI_CLI_TOKEN"))
