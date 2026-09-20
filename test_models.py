import os
from dotenv import load_dotenv
load_dotenv()
import httpx
import asyncio

async def test():
    key = os.environ.get("GEMINI_API_KEY", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        models = resp.json().get('models', [])
        for m in models:
            print(m['name'])

asyncio.run(test())
