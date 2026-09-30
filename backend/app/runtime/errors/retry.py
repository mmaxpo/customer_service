import asyncio


async def with_retry(fn, retries=1, delay=0.5):
    for attempt in range(retries):
        try:
            return await fn()
        except Exception:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(delay)
