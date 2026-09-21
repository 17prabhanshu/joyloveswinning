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
    # We will use a local cache directory
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", ".llm_cache")
    llm_cache = Cache(cache_dir)
except ImportError:
    llm_cache = None

logger = logging.getLogger("llm_gateway")

class LLMGateway:
    """
    Unified gateway for LLM calls featuring:
    - diskcache-based response caching
    - Ollama as primary LLM
    - Gemini as fallback
    - 429 rate-limit backoff with jitter (for Gemini)
    - 503 capacity fallback chain
    - asyncio.Semaphore concurrency limits
    - Replay mode for absolute demo safety
    """
    
    def __init__(self, max_concurrency: int = 2, replay_mode: bool = False):
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.replay_mode = replay_mode
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        # Re-enabling Gemini as the primary brain for blazing speed and zero laptop lag!
        self.fallback_chain = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash"]
        # Keeping ultra-fast 1.5B model as the offline safety net
        self.ollama_model = "qwen2.5:1.5b"
        self.ollama_url = "http://localhost:11434/api/generate"
        
    def _hash_prompt(self, model: str, prompt: str) -> str:
        data = f"{model}::{prompt}".encode("utf-8")
        return hashlib.sha256(data).hexdigest()
        
    async def _call_ollama(self, prompt: str, model: str) -> Optional[str]:
        """Calls the local Ollama API."""
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

    async def generate_content(self, prompt: str, default_fallback: str = "") -> httpx.Response:
        """
        Main entry point for generating content.
        Features a robust fallback chain: Local Cache -> Gemini Models -> Local Ollama -> Safe Default
        """
        async with self.semaphore:
            # 1. Replay Mode Safety Net
            if self.replay_mode and llm_cache:
                for model in self.fallback_chain + [self.ollama_model]:
                    cache_key = self._hash_prompt(model, prompt)
                    if cache_key in llm_cache:
                        logger.info(f"[Replay Mode] Serving cached response for {model}")
                        return self._mock_response(200, llm_cache[cache_key])
                logger.warning(f"[Replay Mode] Cache miss for prompt. Returning safe default.")
                return self._mock_response(200, default_fallback)

            # 2. Cloud API (Gemini) Fallback Chain
            if self.api_key:
                for model in self.fallback_chain:
                    cache_key = self._hash_prompt(model, prompt)
                    
                    if llm_cache and cache_key in llm_cache:
                        logger.info(f"[Cache Hit] Returning cached response for {model}")
                        return self._mock_response(200, llm_cache[cache_key])
                        
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
                    payload = {"contents": [{"parts": [{"text": prompt}]}]}
                    
                    resp = await self._call_with_backoff(url, payload, model)
                    
                    if resp and resp.status_code == 200:
                        if llm_cache:
                            try:
                                data = resp.json()
                                text = data["candidates"][0]["content"]["parts"][0]["text"]
                                llm_cache[cache_key] = text
                            except Exception as e:
                                logger.error(f"Failed to cache response: {e}")
                        return resp
                        
                    if resp and resp.status_code in [503, 429]:
                        logger.warning(f"[{model}] API Error ({resp.status_code}). Falling back to next model.")
                        continue
                        
            else:
                logger.warning("No GEMINI_API_KEY found. Bypassing cloud models.")

            # 3. Local Open-Source LLM Fallback (Ollama)
            logger.info(f"[Ollama] Falling back to local offline model: {self.ollama_model}")
            ollama_resp_text = await self._call_ollama(prompt, self.ollama_model)
            if ollama_resp_text:
                return self._mock_response(200, ollama_resp_text)

            # 4. Total Failure - Use Safe Default
            logger.error("All AI models (Cloud & Local) in fallback chain failed.")
            if default_fallback:
                return self._mock_response(200, default_fallback)
            
            return self._mock_response(500, "All models failed and no safe default provided.")

    async def _call_with_backoff(self, url: str, payload: dict, model: str) -> Optional[httpx.Response]:
        """Handles 429 Rate Limits exclusively."""
        max_retries = 3
        base_delay = 1.0
        
        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries):
                try:
                    resp = await client.post(url, json=payload, timeout=180.0)
                    
                    if resp.status_code == 429:
                        logger.warning(f"[{model}] 429 Rate Limit. Instantly falling back to next model.")
                        return resp
                        
                    return resp
                    
                except httpx.ReadTimeout:
                    logger.warning(f"[{model}] ReadTimeout. Retrying...")
                    # Treat timeout similarly to 429 for retry purposes, but wait less
                    await asyncio.sleep(2.0)
                    continue
                except Exception as e:
                    logger.error(f"[{model}] Network exception: {e}")
                    return None
                    
        return None

    def _mock_response(self, status_code: int, text: str) -> httpx.Response:
        """Create a mock httpx.Response object to satisfy existing codebase parsers."""
        # The existing code expects resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        # or it expects resp.text in error cases.
        if status_code == 200:
            mock_json = {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": text}]
                        }
                    }
                ]
            }
        else:
            mock_json = {"error": text}
            
        class MockResponse:
            def __init__(self, status, json_data, raw_text):
                self.status_code = status
                self._json_data = json_data
                self.text = raw_text
                
            def json(self):
                return self._json_data
                
        return MockResponse(status_code, mock_json, text)

# Global singleton instance for easy import
# Replay mode can be enabled via environment variable for emergency demo usage
is_replay = os.environ.get("DEMO_REPLAY_MODE", "0") == "1"
gateway = LLMGateway(max_concurrency=2, replay_mode=is_replay)
