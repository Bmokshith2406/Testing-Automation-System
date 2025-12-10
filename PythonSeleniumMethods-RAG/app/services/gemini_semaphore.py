import asyncio
import inspect

from app.core.config import get_settings

settings = get_settings()

# ----------------------------------------
# Global Gemini concurrency throttle
# ----------------------------------------

# Default safe concurrency
GEMINI_MAX_CONCURRENCY = 4

GEMINI_SEMAPHORE = asyncio.Semaphore(GEMINI_MAX_CONCURRENCY)


# ----------------------------------------
# Async-safe wrapper helper
# ----------------------------------------

async def run_gemini_call(func):
    """
    Wrap ANY Gemini call safely with concurrency throttle.

    Supports:
      - sync callables   -> run inside asyncio.to_thread(...)
      - async callables  -> properly awaited

    Usage:
        response = await run_gemini_call(
            lambda: model.generate_content(prompt)
        )
    """
    async with GEMINI_SEMAPHORE:
        try:
            result = func()

            # Async callable (coroutine)
            if inspect.isawaitable(result):
                return await result

            # Sync callable → run in executor
            return await asyncio.to_thread(lambda: result)

        except Exception:
            # Let caller log/retry
            raise
