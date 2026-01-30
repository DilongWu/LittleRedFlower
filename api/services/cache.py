"""
Unified caching system for market data.
"""
import datetime
import logging
from typing import Any, Optional, Dict

# In-memory cache storage
_CACHE: Dict[str, Dict[str, Any]] = {}

# Default cache durations (in seconds) - Optimized for stability
CACHE_DURATIONS = {
    "index_overview": 900,      # 15 minutes
    "market_radar": 900,        # 15 minutes
    "fund_flow": 1800,          # 30 minutes (increased from 10 - data doesn't need real-time)
    "hot_concepts": 1800,       # 30 minutes (increased from 10 - data doesn't need real-time)
    "stock_diagnosis": 60,      # 1 minute (user-specific)
    "stock_list": 3600,         # 1 hour (rarely changes)
}


def get_cache(key: str) -> Optional[Any]:
    """
    Get data from cache if it exists and is not expired.

    Args:
        key: Cache key

    Returns:
        Cached data or None if not found/expired
    """
    if key not in _CACHE:
        return None

    entry = _CACHE[key]
    if "expires_at" not in entry or "data" not in entry:
        return None

    if datetime.datetime.now() > entry["expires_at"]:
        # Cache expired, remove it
        del _CACHE[key]
        return None

    logging.debug(f"Cache hit: {key}")
    return entry["data"]


def set_cache(key: str, data: Any, duration_seconds: Optional[int] = None) -> None:
    """
    Store data in cache.

    Args:
        key: Cache key
        data: Data to cache
        duration_seconds: Cache duration in seconds (uses default if not specified)
    """
    if duration_seconds is None:
        # Try to get default duration based on key prefix
        for prefix, default_duration in CACHE_DURATIONS.items():
            if key.startswith(prefix):
                duration_seconds = default_duration
                break
        else:
            duration_seconds = 300  # Default 5 minutes

    _CACHE[key] = {
        "data": data,
        "expires_at": datetime.datetime.now() + datetime.timedelta(seconds=duration_seconds),
        "created_at": datetime.datetime.now()
    }
    logging.debug(f"Cache set: {key} (expires in {duration_seconds}s)")


def clear_cache(prefix: Optional[str] = None) -> int:
    """
    Clear cache entries.

    Args:
        prefix: If provided, only clear entries starting with this prefix.
                If None, clear all cache.

    Returns:
        Number of entries cleared
    """
    global _CACHE

    if prefix is None:
        count = len(_CACHE)
        _CACHE = {}
        return count

    keys_to_delete = [k for k in _CACHE.keys() if k.startswith(prefix)]
    for key in keys_to_delete:
        del _CACHE[key]

    return len(keys_to_delete)


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    now = datetime.datetime.now()
    total = len(_CACHE)
    expired = sum(1 for entry in _CACHE.values() if now > entry.get("expires_at", now))

    return {
        "total_entries": total,
        "expired_entries": expired,
        "active_entries": total - expired,
        "keys": list(_CACHE.keys())
    }
