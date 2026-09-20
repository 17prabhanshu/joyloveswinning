import re

with open("ps3_agent/api/server.py", "r") as f:
    code = f.read()

# Replace Gemini API call in /analysis
old_analysis_call = """        GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url, 
                json={"contents": [{"parts": [{"text": prompt}]}]}, 
                timeout=15.0
            )
            
            if resp.status_code == 200:
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]"""

new_analysis_call = """        url = "http://localhost:11434/api/generate"
        payload = {"model": "qwen2.5:1.5b", "prompt": prompt, "stream": False}
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=30.0)
            if resp.status_code == 200:
                text = resp.json()["response"]"""

code = code.replace(old_analysis_call, new_analysis_call)


# Replace Gemini API call in /patch
old_patch_call = """        GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url, 
                json={"contents": [{"parts": [{"text": prompt}]}]}, 
                timeout=15.0
            )
            
            if resp.status_code == 200:
                data = resp.json()
                patched_code = data["candidates"][0]["content"]["parts"][0]["text"]"""

new_patch_call = """        url = "http://localhost:11434/api/generate"
        payload = {"model": "qwen2.5:1.5b", "prompt": prompt, "stream": False}
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=30.0)
            if resp.status_code == 200:
                patched_code = resp.json()["response"]"""

code = code.replace(old_patch_call, new_patch_call)

# Replace Gemini API call in /chat
old_chat_call = """        GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]"""

new_chat_call = """        url = "http://localhost:11434/api/generate"
        payload = {"model": "qwen2.5:1.5b", "prompt": prompt, "stream": False}
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=20.0)
            if resp.status_code == 200:
                text = resp.json()["response"]"""
                
code = code.replace(old_chat_call, new_chat_call)

with open("ps3_agent/api/server.py", "w") as f:
    f.write(code)

print("Patched successfully.")
