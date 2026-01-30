import datetime
import logging
import math

from api.services.data_source import get_data_source, fetch_with_fallback
from api.services.cache import get_cache, set_cache
from api.services.http_client import fetch_with_retry


def _clean_float(val):
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _get_concepts_tushare(limit):
    """Get hot concepts from Tushare."""
    from api.services import tushare_client
    result = tushare_client.get_concept_board()
    if result:
        # Sort by change and limit
        sorted_result = sorted(result, key=lambda x: (x.get("change") or 0), reverse=True)
        return sorted_result[:limit]
    return None


def _get_concepts_eastmoney(ak, limit):
    """Get hot concepts from Eastmoney with retry and limit."""
    df = fetch_with_retry(ak.stock_board_concept_name_em, max_retries=3)
    if df is None or df.empty:
        return None

    data = []
    # Only process top N to reduce data size
    for _, row in df.head(limit * 2).iterrows():  # Get 2x to have buffer after sorting
        name = row.get("板块名称", "")
        change = _clean_float(row.get("涨跌幅", 0))
        lead = row.get("领涨股票", "")
        data.append({
            "name": name,
            "change": change,
            "lead": lead,
        })

    # Sort by change and return top N
    data_sorted = sorted(data, key=lambda x: (x.get("change") or 0), reverse=True)
    return data_sorted[:limit]


def _get_concepts_sina(ak, limit):
    """Get hot concepts from Sina (approximated) with retry."""
    try:
        # Try multiple data sources
        df = fetch_with_retry(ak.stock_zh_a_spot, max_retries=3)

        if df is None or df.empty:
            return None

        # Find columns
        cols = df.columns
        name_col = None
        change_col = None

        for col in cols:
            if '名称' in col:
                name_col = col
            if '涨跌幅' in col:
                change_col = col

        if not change_col:
            return None

        import pandas as pd
        df[change_col] = pd.to_numeric(df[change_col], errors='coerce')

        # Get top gainers as "hot stocks" (not concepts, but similar display)
        top_gainers = df.nlargest(limit, change_col)

        data = []
        for _, row in top_gainers.iterrows():
            data.append({
                "name": row.get(name_col, "") if name_col else "",
                "change": _clean_float(row.get(change_col, 0)),
                "lead": "热门股票",
            })

        return data

    except Exception as e:
        logging.error(f"Error in _get_concepts_sina: {e}")
        return None


def get_hot_concepts(limit: int = 15):
    """
    Get hot concepts with caching and automatic fallback between data sources.
    Optimized to only return top N concepts for better performance.
    """
    import akshare as ak

    current_source = get_data_source()
    cache_key = f"hot_concepts_{current_source}"

    # Check cache first
    cached_data = get_cache(cache_key)
    if cached_data is not None:
        return cached_data

    # Build fetch functions for each source
    fetch_funcs = {
        "tushare": lambda: _get_concepts_tushare(limit),
        "eastmoney": lambda: _get_concepts_eastmoney(ak, limit),
        "sina": lambda: _get_concepts_sina(ak, limit),
    }

    # Try to fetch with automatic fallback
    result, source_used = fetch_with_fallback(fetch_funcs, "hot concepts")

    if result:
        data = {
            "date": datetime.datetime.now().strftime("%Y%m%d"),
            "data_source": source_used or current_source,
            "data": result,
            "note": f"显示TOP {len(result)} 热门题材"
        }
        set_cache(cache_key, data, 1800)  # 30 minutes (increased from 10)
        return data

    # Return empty data and cache for short time
    empty_data = {
        "date": datetime.datetime.now().strftime("%Y%m%d"),
        "data_source": "error",
        "data": [],
        "note": "数据获取失败，请稍后重试"
    }
    set_cache(cache_key, empty_data, 120)  # 2 minutes for errors
    return empty_data
