import os
from dotenv import load_dotenv
load_dotenv()
import json
import time
import random
import hashlib
import asyncio
import logging
from typing import Optional, Dict, Any

try:
    import httpx
except ImportError:
    pass

try:
    from diskcache import Cache
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", ".llm_cache")
    llm_cache = Cache(cache_dir)
except ImportError:
    llm_cache = None

logger = logging.getLogger("llm_gateway")

class LLMGateway:
    """
    Unified gateway for LLM calls featuring:
    - diskcache-based response caching
    - Groq API as primary (lightning fast)
    - Ollama as fallback
    """
    
    def __init__(self, max_concurrency: int = 2, replay_mode: bool = False):
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.replay_mode = replay_mode
        self.groq_key = os.environ.get("GROQ_API_KEY", "")
        self.groq_model = "openai/gpt-oss-120b"
        
        self.ollama_model = "qwen2.5:1.5b"
        self.ollama_url = "http://localhost:11434/api/generate"
        
    def _hash_prompt(self, model: str, prompt: str) -> str:
        data = f"{model}::{prompt}".encode("utf-8")
        return hashlib.sha256(data).hexdigest()
        
    async def _call_ollama(self, prompt: str, model: str) -> Optional[str]:
        payload = {"model": model, "prompt": prompt, "stream": False}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.ollama_url, json=payload, timeout=180.0)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("response")
        except Exception as e:
            logger.warning(f"[Ollama] Failed to call Ollama: {e}")
        return None

    def _mock_gemini_response(self, status: int, text: str) -> Any:
        class MockResponse:
            def __init__(self, status_code, text_content):
                self.status_code = status_code
                self.text = text_content
            def json(self):
                return {"candidates": [{"content": {"parts": [{"text": self.text}]}}]}
        return MockResponse(status, text)

    async def generate_content(self, prompt: str, default_fallback: str = "") -> Any:
        async with self.semaphore:
            # 1. Cache
            cache_key = self._hash_prompt(self.groq_model, prompt)
            if llm_cache and cache_key in llm_cache:
                return self._mock_gemini_response(200, llm_cache[cache_key])
                
            # 2. Groq
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.groq_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2
            }
            
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, json=payload, headers=headers, timeout=30.0)
                    if resp.status_code == 200:
                        text = resp.json()["choices"][0]["message"]["content"]
                        if llm_cache is not None:
                            llm_cache[cache_key] = text
                        return self._mock_gemini_response(200, text)
                    else:
                        logger.warning(f"[Groq] API Error: {resp.status_code}")
            except Exception as e:
                logger.error(f"[Groq] Network exception: {e}")
                
            # 3. Ollama
            logger.info(f"[Ollama] Falling back to local offline model: {self.ollama_model}")
            ollama_text = await self._call_ollama(prompt, self.ollama_model)
            if ollama_text:
                return self._mock_gemini_response(200, ollama_text)
                
            # 4. Default
            logger.warning("[Gateway] All models failed. Returning safe default.")
            return self._mock_gemini_response(200, default_fallback)

is_replay = os.environ.get("DEMO_REPLAY_MODE", "0") == "1"
gateway = LLMGateway(max_concurrency=2, replay_mode=is_replay)
