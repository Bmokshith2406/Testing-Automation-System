import time
from typing import Any, Dict, Tuple

from app.core.config import get_settings

settings = get_settings()

# Simple in-memory cache; can later swap with Redis
SEARCH_CACHE: Dict[str, Tuple[float, Any]] = {}


def cache_get(key: str):
    try:
        entry = SEARCH_CACHE.get(key)
    except Exception:
        return None

    if not entry:
        return None

    try:
        ts, value = entry
    except Exception:
        # Corrupt entry — remove safely
        try:
            del SEARCH_CACHE[key]
        except Exception:
            pass
        return None

    try:
        if time.time() - ts > settings.CACHE_TTL_SECONDS:
            try:
                del SEARCH_CACHE[key]
            except Exception:
                pass
            return None
    except Exception:
        # If time or TTL computation fails, treat as expired
        try:
            del SEARCH_CACHE[key]
        except Exception:
            pass
        return None

    return value


def cache_set(key: str, value: Any):
    try:
        SEARCH_CACHE[key] = (time.time(), value)
    except Exception:
        # Never allow cache write failure to break app flow
        pass
