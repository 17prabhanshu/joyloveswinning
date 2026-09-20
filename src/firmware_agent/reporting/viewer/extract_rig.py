import sys
import json

with open("/Users/prabhanshushekhar/.gemini/antigravity/brain/f7705557-057c-49b9-b28f-03f190d76fdb/.system_generated/logs/transcript_full.jsonl", "r") as f:
    inputs = [json.loads(line) for line in f if json.loads(line).get("type") == "USER_INPUT"]
    
if inputs:
    last = inputs[-1]
    content = last.get("content", "")
    print(f"Length: {len(content)}")
    print(f"End snippet: {content[-100:]}")
