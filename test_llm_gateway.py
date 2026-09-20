import asyncio
import os
import sys
import time

from dotenv import load_dotenv
load_dotenv()

from ps3_agent.api.llm_gateway import gateway

async def test_worker(i):
    print(f"[{time.time():.2f}] Worker {i} starting request...")
    resp = await gateway.generate_content(f"Respond exactly with the number {i}")
    status = resp.status_code if hasattr(resp, 'status_code') else "Unknown"
    print(f"[{time.time():.2f}] Worker {i} finished with status {status}")

async def main():
    print("Testing LLMGateway Concurrency Cap (Max 2) and Caching...")
    
    import shutil
    from pathlib import Path
    cache_dir = Path(__file__).parent / ".llm_cache"
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        
    from ps3_agent.api.llm_gateway import llm_cache
    llm_cache.clear()

    tasks = [test_worker(i) for i in range(4)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
