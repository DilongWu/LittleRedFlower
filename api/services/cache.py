"""
Unified caching system for market data.
"""
import datetime
import logging
from typing import Any, Optional, Dict

# In-memory cache storage
_CACHE: Dict[str, Dict[str, Any]] = {}

# Lazy eviction counter and size limit
_set_count = 0
MAX_CACHE_SIZE = 100  # Defensive limit (~6 keys in practice)

# Default cache durations (in seconds) - Optimized for stability
CACHE_DURATIONS = {
    "index_overview": 900,      # 15 minutes
    "market_radar": 900,        # 15 minutes
    "fund_flow": 1800,          # 30 minutes (increased from 10 - data doesn't need real-time)
    "hot_concepts": 1800,       # 30 minutes (increased from 10 - data doesn't need real-time)
    "stock_diagnosis": 60,      # 1 minute (user-specific)
    "stock_list": 3600,         # 1 hour (rarely changes)
    "dashboard_all": 300,       # 5 minutes (aggregation cache)
}

# Keys eligible for extended cache during non-trading hours
_EXTENDED_CACHE_KEYS = {"index_overview", "market_radar", "dashboard_all"}
_NON_TRADING_DURATION = 3600  # 1 hour during non-trading hours


# ------------------------------------------------------------------
# 中国法定假日（需要每年更新！）
# 假日期间 A 股休市，缓存自动延长
# ------------------------------------------------------------------
_CN_HOLIDAYS_2026 = {
    # 元旦
    datetime.date(2026, 1, 1),
    datetime.date(2026, 1, 2),
    datetime.date(2026, 1, 3),
    # 春节 (农历正月初一 2026-02-17)
    datetime.date(2026, 2, 15),
    datetime.date(2026, 2, 16),
    datetime.date(2026, 2, 17),
    datetime.date(2026, 2, 18),
    datetime.date(2026, 2, 19),
    datetime.date(2026, 2, 20),
    datetime.date(2026, 2, 21),
    # 清明节
    datetime.date(2026, 4, 4),
    datetime.date(2026, 4, 5),
    datetime.date(2026, 4, 6),
    # 劳动节
    datetime.date(2026, 5, 1),
    datetime.date(2026, 5, 2),
    datetime.date(2026, 5, 3),
    datetime.date(2026, 5, 4),
    datetime.date(2026, 5, 5),
    # 端午节
    datetime.date(2026, 5, 31),
    datetime.date(2026, 6, 1),
    datetime.date(2026, 6, 2),
    # 中秋节 + 国庆节
    datetime.date(2026, 10, 1),
    datetime.date(2026, 10, 2),
    datetime.date(2026, 10, 3),
    datetime.date(2026, 10, 4),
    datetime.date(2026, 10, 5),
    datetime.date(2026, 10, 6),
    datetime.date(2026, 10, 7),
    datetime.date(2026, 10, 8),
}


def _is_cn_holiday(d: datetime.date) -> bool:
    """Check if a date is a Chinese public holiday (based on hardcoded list)."""
    return d in _CN_HOLIDAYS_2026


def _is_a_share_trading_hours() -> bool:
    """
    Check if current time is within A-share trading hours.
    A-share trading: Mon-Fri 9:30-11:30, 13:00-15:00 (Beijing time, UTC+8).
    Also returns False on Chinese public holidays.
    """
    import pytz
    try:
        beijing_tz = pytz.timezone("Asia/Shanghai")
    except Exception:
        # Fallback: manual UTC+8 offset
        beijing_tz = pytz.FixedOffset(480)
    now = datetime.datetime.now(beijing_tz)

    # Weekend check
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False

    # Holiday check
    if _is_cn_holiday(now.date()):
        return False

    t = now.time()
    morning_open = datetime.time(9, 25)  # Include pre-open auction
    morning_close = datetime.time(11, 30)
    afternoon_open = datetime.time(13, 0)
    afternoon_close = datetime.time(15, 0)

    if morning_open <= t <= morning_close:
        return True
    if afternoon_open <= t <= afternoon_close:
        return True

    return False


def _get_effective_duration(key: str, duration_seconds: int) -> int:
    """
    Return effective cache duration, extending it during non-trading hours
    for eligible keys.
    """
    # Only extend for specific market-data keys
    for prefix in _EXTENDED_CACHE_KEYS:
        if key.startswith(prefix):
            if not _is_a_share_trading_hours():
                extended = max(duration_seconds, _NON_TRADING_DURATION)
                logging.debug(f"Non-trading hours: extending cache for {key} to {extended}s")
                return extended
            break
    return duration_seconds


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
    global _set_count

    if duration_seconds is None:
        # Try to get default duration based on key prefix
        for prefix, default_duration in CACHE_DURATIONS.items():
            if key.startswith(prefix):
                duration_seconds = default_duration
                break
        else:
            duration_seconds = 300  # Default 5 minutes

    # Apply non-trading hours extension for eligible keys
    duration_seconds = _get_effective_duration(key, duration_seconds)

    # Lazy eviction: every 10 calls, sweep expired entries
    _set_count += 1
    if _set_count % 10 == 0:
        now = datetime.datetime.now()
        expired_keys = [k for k, v in _CACHE.items() if now > v.get("expires_at", now)]
        for k in expired_keys:
            del _CACHE[k]
        if expired_keys:
            logging.debug(f"Lazy eviction: removed {len(expired_keys)} expired entries")

    # Defensive size limit
    if len(_CACHE) >= MAX_CACHE_SIZE:
        # Remove oldest entry by created_at
        oldest_key = min(_CACHE, key=lambda k: _CACHE[k].get("created_at", datetime.datetime.min))
        del _CACHE[oldest_key]
        logging.debug(f"Cache at max size, evicted oldest entry: {oldest_key}")

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
