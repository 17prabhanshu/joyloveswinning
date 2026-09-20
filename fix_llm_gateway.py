import re

with open("ps3_agent/api/llm_gateway.py", "r") as f:
    code = f.read()

# Remove the early exit for no API key
early_exit = """        if not self.api_key:
            logger.warning("No GEMINI_API_KEY found.")
            return self._mock_response(500, "No API Key configured.")"""

new_early_exit = """        # Replay Mode Safety Net
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
            return self._mock_response(500, "No API Key configured.")"""

code = code.replace(early_exit, "")
# Now replace the original replay mode block
old_replay = """            # Replay Mode Safety Net
            if self.replay_mode and llm_cache:
                for model in self.fallback_chain:
                    cache_key = self._hash_prompt(model, prompt)
                    if cache_key in llm_cache:
                        logger.info(f"[Replay Mode] Serving cached response for {model}")
                        return self._mock_response(200, llm_cache[cache_key])
                logger.warning(f"[Replay Mode] Cache miss for prompt. Returning safe default.")
                return self._mock_response(200, default_fallback)"""

code = code.replace(old_replay, new_early_exit)

with open("ps3_agent/api/llm_gateway.py", "w") as f:
    f.write(code)

print("Fixed llm_gateway.py API key check order")
