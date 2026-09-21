import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
res = requests.get(url)
if res.status_code == 200:
    for model in res.json().get("models", []):
        print(model["name"])
else:
    print("Error:", res.text)
