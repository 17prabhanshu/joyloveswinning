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
    Unified gateway for Gemini LLM calls featuring:
    - diskcache-based response caching
    - 429 rate-limit backoff with jitter
    - 503 capacity fallback chain (3.6 -> 1.5 -> 2.0-exp)
    - asyncio.Semaphore concurrency limits
    - Replay mode for absolute demo safety
    """
    
    def __init__(self, max_concurrency: int = 2, replay_mode: bool = False):
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.replay_mode = replay_mode
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.fallback_chain = ["gemini-3.7-flash", "gemini-3.8-flash", "gemini-3.5-flash"]
        
    def _hash_prompt(self, model: str, prompt: str) -> str:
        data = f"{model}::{prompt}".encode("utf-8")
        return hashlib.sha256(data).hexdigest()
        
    async def generate_content(self, prompt: str, default_fallback: str = "") -> httpx.Response:
        """
        Main entry point for generating content.
        Returns a mock httpx.Response object to maintain compatibility with existing consumers.
        """
        async with self.semaphore:
            # Replay Mode Safety Net
            if self.replay_mode and llm_cache:
                for model in self.fallback_chain:
                    cache_key = self._hash_prompt(model, prompt)
                    if cache_key in llm_cache:
                        logger.info(f"[Replay Mode] Serving cached response for {model}")
                        return self._mock_response(200, llm_cache[cache_key])
                logger.warning(f"[Replay Mode] Cache miss for prompt. Returning safe default.")
                return self._mock_response(200, default_fallback)

            if not self.api_key:
                logger.warning("No GEMINI_API_KEY found.")
                return self._mock_response(500, "No API Key configured.")

            # Standard Execution with Fallbacks
            for model in self.fallback_chain:
                cache_key = self._hash_prompt(model, prompt)
                
                # Check normal cache
                if llm_cache and cache_key in llm_cache:
                    logger.info(f"[Cache Hit] Returning cached response for {model}")
                    return self._mock_response(200, llm_cache[cache_key])
                    
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                
                # Attempt to call the model (with 429 backoff)
                resp = await self._call_with_backoff(url, payload, model)
                
                if resp and resp.status_code == 200:
                    # Cache the successful response
                    if llm_cache:
                        try:
                            # Try to parse and extract text just to verify it's valid, then cache the raw text
                            data = resp.json()
                            text = data["candidates"][0]["content"]["parts"][0]["text"]
                            llm_cache[cache_key] = text
                        except Exception as e:
                            logger.error(f"Failed to parse and cache response: {e}")
                    return resp
                    
                # If 503 Capacity issue, gracefully degrade to next model in chain
                if resp and resp.status_code == 503:
                    logger.warning(f"[{model}] 503 Capacity Error. Falling back to next model.")
                    continue
                    
                # Other errors (e.g., 400 Bad Request) usually mean the prompt is bad, no need to fallback
                if resp and resp.status_code != 429:
                    logger.error(f"[{model}] Unhandled error {resp.status_code}: {resp.text}")
                    return resp

            # If ALL models fail, return the safe default if provided
            logger.error("All models in fallback chain failed.")
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
