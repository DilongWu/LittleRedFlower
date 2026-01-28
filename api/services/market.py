import pandas as pd
import datetime
import logging
import math

from api.services.data_source import get_data_source
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


def _get_sectors_data(ak):
    """Get sector data with retry mechanism."""
    # Try industry board first
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

    # Fallback to concept board
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

    return []


def _get_limit_up_data(ak, now):
    """Get limit-up ladder data with retry mechanism."""
    today_str = now.strftime("%Y%m%d")
    ladder = {}

    # Try today first, then previous days
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

    return ladder, today_str


def get_market_radar_data():
    """Get market radar data with caching."""
    import akshare as ak

    current_source = get_data_source()
    cache_key = f"market_radar_{current_source}"

    # Check cache first
    cached_data = get_cache(cache_key)
    if cached_data is not None:
        return cached_data

    now = datetime.datetime.now()

    try:
        # Get sectors
        sectors = _get_sectors_data(ak)

        # Get limit-up ladder
        ladder, date_str = _get_limit_up_data(ak, now)

        data = {
            "data_source": current_source,
            "date": date_str,
            "sectors": sectors,
            "ladder": ladder
        }

        # Cache results
        if sectors or ladder:
            set_cache(cache_key, data, 300)  # 5 minutes
        else:
            set_cache(cache_key, data, 60)  # 1 minute for empty

        return data

    except Exception as e:
        logging.error(f"Error fetching market radar data: {e}")
        return {
            "date": now.strftime("%Y%m%d"),
            "data_source": "error",
            "error": str(e),
            "sectors": [],
            "ladder": {}
        }
