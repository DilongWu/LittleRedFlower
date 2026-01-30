import datetime
import time
import pandas as pd
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

from api.services.data_source import get_data_source, fetch_with_fallback
from api.services.cache import get_cache, set_cache


def _clean_json_float(val):
    try:
        if val is None:
            return None
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 2)
    except (ValueError, TypeError):
        return None


def _series_to_sparkline(points):
    if not points:
        return []
    result = []
    for p in points:
        try:
            val = float(p)
            if math.isnan(val) or math.isinf(val):
                result.append(None)
            else:
                result.append(round(val, 2))
        except (ValueError, TypeError):
            result.append(None)
    return result


def _process_index_df(df, days, points):
    """Process index dataframe and extract data."""
    if df is None or df.empty:
        return None

    df = df.tail(days).copy()

    # Find close column
    close_col = None
    for col in df.columns:
        if '收盘' in col:
            close_col = col
            break
    if close_col is None:
        close_col = '收盘' if '收盘' in df.columns else df.columns[4] if len(df.columns) > 4 else None

    if close_col is None:
        return None

    df["close"] = pd.to_numeric(df[close_col], errors="coerce")

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest

    latest_close = float(latest.get("close", 0.0) or 0.0)
    prev_close = float(prev.get("close", latest_close) or latest_close)
    change_pct = ((latest_close - prev_close) / prev_close * 100) if prev_close else 0.0

    ma5 = df["close"].rolling(5).mean().iloc[-1]
    ma20 = df["close"].rolling(20).mean().iloc[-1]

    series = df["close"].tail(points).tolist()

    # Find date column
    date_col = None
    for col in df.columns:
        if '日期' in col:
            date_col = col
            break

    return {
        "date": str(latest.get(date_col, datetime.datetime.now().date())) if date_col else str(datetime.datetime.now().date()),
        "close": _clean_json_float(latest_close),
        "change_pct": _clean_json_float(change_pct),
        "ma5": _clean_json_float(ma5),
        "ma20": _clean_json_float(ma20),
        "series": _series_to_sparkline(series),
    }


def _fetch_index_tushare(symbol: str, days: int):
    """Fetch index data using Tushare."""
    from api.services import tushare_client
    return tushare_client.get_index_daily(symbol, days)


def _fetch_index_eastmoney(symbol: str):
    """Fetch index data using AkShare (Eastmoney source)."""
    import akshare as ak
    return ak.stock_zh_index_daily_em(symbol=symbol)


def _fetch_index_sina(symbol: str, days: int):
    """Fetch index data using AkShare (Sina/alternative source)."""
    import akshare as ak
    code = symbol[2:] if symbol.startswith(('sh', 'sz')) else symbol
    end_date = datetime.datetime.now().strftime("%Y%m%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=days + 30)).strftime("%Y%m%d")
    return ak.index_zh_a_hist(
        symbol=code,
        period="daily",
        start_date=start_date,
        end_date=end_date
    )


def _fetch_single_index(name, symbol, days, points):
    """Fetch a single index with fallback logic."""
    # Build fetch functions for each source
    fetch_funcs = {
        "tushare": lambda: _fetch_index_tushare(symbol, days),
        "eastmoney": lambda: _fetch_index_eastmoney(symbol),
        "sina": lambda: _fetch_index_sina(symbol, days),
    }

    # Try to fetch with automatic fallback
    df, source_used = fetch_with_fallback(fetch_funcs, f"index {name}")

    if df is not None:
        data = _process_index_df(df, days, points)
        if data:
            data["name"] = name
            data["symbol"] = symbol
            data["data_source"] = source_used
            return data, source_used

    return None, None


def get_index_overview(days: int = 60, points: int = 30):
    """Get index overview with caching, parallel fetching, and automatic fallback between data sources."""
    current_source = get_data_source()
    cache_key = f"index_overview_{current_source}"

    # Check cache first
    cached_data = get_cache(cache_key)
    if cached_data is not None:
        return cached_data

    index_map = {
        "上证指数": "sh000001",
        "深证成指": "sz399001",
        "沪深300": "sh000300",
        "创业板指": "sz399006",
    }

    results = []
    actual_source = None

    # Use ThreadPoolExecutor for parallel fetching
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all index fetching tasks
        future_to_index = {
            executor.submit(_fetch_single_index, name, symbol, days, points): name
            for name, symbol in index_map.items()
        }

        # Collect results as they complete
        for future in as_completed(future_to_index):
            try:
                data, source_used = future.result(timeout=10)  # 10 second timeout per index
                if data:
                    results.append(data)
                    # Track the actual source used
                    if actual_source is None:
                        actual_source = source_used
            except Exception as e:
                index_name = future_to_index[future]
                print(f"Error fetching {index_name}: {e}")
                continue

    # Sort results by original order
    ordered_results = []
    for name in index_map.keys():
        for result in results:
            if result["name"] == name:
                ordered_results.append(result)
                break

    # Cache results (even if empty, to avoid repeated failed requests)
    if ordered_results:
        # Use actual source in cache key for consistency
        if actual_source:
            cache_key = f"index_overview_{actual_source}"
        set_cache(cache_key, ordered_results, 600)  # 10 minutes (increased from 5)
    else:
        set_cache(cache_key, ordered_results, 120)  # 2 minutes for empty results

    return ordered_results
