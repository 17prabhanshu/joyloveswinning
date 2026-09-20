import re

with open("ps3_agent/api/llm_gateway.py", "r") as f:
    code = f.read()

method_start = code.find("async def generate_content")
method_end = code.find("async def _call_with_backoff")

new_method = """async def generate_content(self, prompt: str, default_fallback: str = "") -> httpx.Response:
        \"\"\"
        Main entry point for generating content.
        Returns a mock httpx.Response object to maintain compatibility with existing consumers.
        \"\"\"
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

    """

code = code[:method_start] + new_method + code[method_end:]

with open("ps3_agent/api/llm_gateway.py", "w") as f:
    f.write(code)

print("Fixed generate_content method")
