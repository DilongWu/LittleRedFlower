import pandas as pd
import datetime
import math
import time

from api.services.data_source import get_data_source, fetch_with_fallback
from api.services.cache import get_cache, set_cache
from api.services.http_client import fetch_with_retry


def _clean_float(val):
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return f
    except:
        return 0.0


def _get_sectors_tushare():
    """Get sector data from Tushare."""
    from api.services import tushare_client
    return tushare_client.get_industry_board()


def _get_sectors_eastmoney(ak):
    """Get sector data from Eastmoney via AkShare."""
    df = fetch_with_retry(ak.stock_board_industry_name_em, max_retries=2)

    if df is not None and not df.empty:
        sectors = []
        for _, row in df.iterrows():
            change_pct = _clean_float(row.get('涨跌幅', 0))
            sectors.append({
                "name": row.get('板块名称', ''),
                "change": change_pct,
                "top_stock": row.get('领涨股票', '')
            })
        return sectors
    return None


def _get_sectors_sina(ak):
    """Get sector data from Sina via AkShare (fallback to concept board)."""
    df = fetch_with_retry(ak.stock_board_concept_name_em, max_retries=2)

    if df is not None and not df.empty:
        sectors = []
        for _, row in df.head(30).iterrows():
            change_pct = _clean_float(row.get('涨跌幅', 0))
            sectors.append({
                "name": row.get('板块名称', ''),
                "change": change_pct,
                "top_stock": row.get('领涨股票', '')
            })
        return sectors
    return None


def _get_limit_up_tushare(now):
    """Get limit-up ladder data from Tushare."""
    from api.services import tushare_client

    today_str = now.strftime("%Y%m%d")
    dates_to_try = [today_str]
    for i in range(1, 4):
        dates_to_try.append((now - datetime.timedelta(days=i)).strftime("%Y%m%d"))

    for date_str in dates_to_try:
        ladder = tushare_client.get_limit_up_pool(date_str)
        if ladder:
            return ladder, date_str

    return None, today_str


def _get_limit_up_eastmoney(ak, now):
    """Get limit-up ladder data from Eastmoney via AkShare."""
    today_str = now.strftime("%Y%m%d")
    ladder = {}

    dates_to_try = [today_str]
    for i in range(1, 4):
        dates_to_try.append((now - datetime.timedelta(days=i)).strftime("%Y%m%d"))

    for date_str in dates_to_try:
        zt_df = fetch_with_retry(ak.stock_zt_pool_em, date=date_str, max_retries=1)

        if zt_df is not None and not zt_df.empty and '连板数' in zt_df.columns:
            zt_df['连板数'] = pd.to_numeric(zt_df['连板数'], errors='coerce').fillna(1).astype(int)
            zt_df = zt_df.sort_values(by='连板数', ascending=False)

            for _, row in zt_df.iterrows():
                lb = str(row['连板数'])
                if lb not in ladder:
                    ladder[lb] = []

                ladder[lb].append({
                    "name": row['名称'],
                    "code": row['代码'],
                    "reason": row.get('涨停原因类别', ''),
                    "industry": row.get('所属行业', ''),
                    "time": str(row.get('首次封板时间', ''))
                })

            return ladder, date_str

    return None, today_str


def get_market_radar_data():
    """Get market radar data with caching and automatic fallback between data sources."""
    import akshare as ak

    current_source = get_data_source()
    cache_key = f"market_radar_{current_source}"

    # Check cache first
    cached_data = get_cache(cache_key)
    if cached_data is not None:
        return cached_data

    now = datetime.datetime.now()
    sectors = None
    ladder = None
    date_str = now.strftime("%Y%m%d")
    actual_source = None

    # Build fetch functions for sectors
    sectors_fetch_funcs = {
        "tushare": _get_sectors_tushare,
        "eastmoney": lambda: _get_sectors_eastmoney(ak),
        "sina": lambda: _get_sectors_sina(ak),
    }

    # Try to fetch sectors with automatic fallback
    sectors, source_used = fetch_with_fallback(sectors_fetch_funcs, "sectors")
    if source_used:
        actual_source = source_used

    # Reduced delay between requests from 1.0s to 0.3s for better performance
    time.sleep(0.3)

    # Build fetch functions for limit-up ladder
    ladder_fetch_funcs = {
        "tushare": lambda: _get_limit_up_tushare(now),
        "eastmoney": lambda: _get_limit_up_eastmoney(ak, now),
        "sina": lambda: _get_limit_up_eastmoney(ak, now),  # Use same as eastmoney
    }

    # Try to fetch ladder with automatic fallback
    ladder_result, ladder_source = fetch_with_fallback(ladder_fetch_funcs, "limit-up ladder")
    if ladder_result:
        if isinstance(ladder_result, tuple):
            ladder, date_str = ladder_result
        else:
            ladder = ladder_result
        if ladder_source and not actual_source:
            actual_source = ladder_source

    data = {
        "data_source": actual_source or current_source,
        "date": date_str,
        "sectors": sectors or [],
        "ladder": ladder or {}
    }

    # Cache results with longer duration
    if sectors or ladder:
        set_cache(cache_key, data, 600)  # 10 minutes (increased from 5)
    else:
        set_cache(cache_key, data, 120)  # 2 minutes for empty (increased from 1)

    return data
