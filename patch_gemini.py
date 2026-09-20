import re

with open("ps3_agent/api/server.py", "r") as f:
    code = f.read()

helper = """
async def call_gemini(prompt: str) -> httpx.Response:
    import httpx
    import os
    import asyncio
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    models = ["gemini-3.6-flash", "gemini-1.5-flash", "gemini-2.0-flash-exp"]
    
    async with httpx.AsyncClient() as client:
        resp = None
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            for attempt in range(2):
                try:
                    resp = await client.post(url, json=payload, timeout=180.0)
                    if resp.status_code == 200:
                        return resp
                    elif resp.status_code == 503:
                        await asyncio.sleep(1)
                        continue
                    else:
                        break  # try next model
                except Exception:
                    break  # try next model
        return resp

"""

if "async def call_gemini" not in code:
    code = code.replace("app = FastAPI", helper + "\napp = FastAPI")

# 1. Patch analyze_test_failure
analyze_old = """        import httpx
        import os
        import json
        GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url, 
                json={"contents": [{"parts": [{"text": prompt}]}]}, 
                timeout=180.0
            )"""
            
analyze_new = """        import json
        resp = await call_gemini(prompt)"""
code = code.replace(analyze_old, analyze_new)


# 2. Patch patch_firmware
patch_old = """        import httpx
        import os
        GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url, 
                json={"contents": [{"parts": [{"text": prompt}]}]}, 
                timeout=180.0
            )"""

patch_new = """        resp = await call_gemini(prompt)"""
code = code.replace(patch_old, patch_new)


# 3. Patch chat_with_agent
chat_old = """        import httpx
        import os
        GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=180.0)"""
            
chat_new = """        resp = await call_gemini(prompt)"""
code = code.replace(chat_old, chat_new)

with open("ps3_agent/api/server.py", "w") as f:
    f.write(code)

print("Successfully injected Gemini fallback logic!")
