import datetime
import logging
import math
import pandas as pd

from api.services.data_source import get_data_source
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


def _find_col(columns, keywords):
    for col in columns:
        if all(k in col for k in keywords):
            return col
    return None


def _get_fund_flow_data(ak, limit):
    """Get fund flow data with retry mechanism."""

    # Try fund flow rank first (best data source)
    df = fetch_with_retry(ak.stock_individual_fund_flow_rank, max_retries=2)

    if df is not None and not df.empty:
        cols = df.columns
        code_col = _find_col(cols, ["代码"]) or "代码"
        name_col = _find_col(cols, ["名称"]) or "名称"
        price_col = _find_col(cols, ["最新价"]) or _find_col(cols, ["现价"]) or "最新价"
        change_col = _find_col(cols, ["涨跌幅"]) or "涨跌幅"
        net_col = _find_col(cols, ["主力", "净流入", "净额"]) or _find_col(cols, ["主力", "净流入"]) or "主力净流入-净额"
        ratio_col = _find_col(cols, ["主力", "净流入", "净占比"]) or "主力净流入-净占比"

        result = []
        for _, row in df.head(limit).iterrows():
            result.append({
                "code": row.get(code_col, ""),
                "name": row.get(name_col, ""),
                "price": _clean_float(row.get(price_col, None)),
                "change_pct": _clean_float(row.get(change_col, None)),
                "net_inflow": _clean_float(row.get(net_col, None)),
                "net_ratio": _clean_float(row.get(ratio_col, None)),
            })
        return result

    # Fallback: Try stock list
    stock_list = fetch_with_retry(ak.stock_info_a_code_name, max_retries=2)

    if stock_list is not None and not stock_list.empty:
        result = []
        for _, row in stock_list.head(limit).iterrows():
            result.append({
                "code": row.get("code", ""),
                "name": row.get("name", ""),
                "price": None,
                "change_pct": None,
                "net_inflow": None,
                "net_ratio": None,
            })
        return result

    return None


def get_fund_flow_rank(limit: int = 30):
    """Get fund flow rank with caching."""
    import akshare as ak

    current_source = get_data_source()
    cache_key = f"fund_flow_{current_source}"

    # Check cache first
    cached_data = get_cache(cache_key)
    if cached_data is not None:
        return cached_data

    try:
        result = _get_fund_flow_data(ak, limit)

        if result:
            data = {
                "date": datetime.datetime.now().strftime("%Y%m%d"),
                "data_source": current_source,
                "data": result
            }
            set_cache(cache_key, data, 300)  # 5 minutes
            return data

    except Exception as e:
        logging.error(f"Error fetching fund flow: {e}")

    # Return empty data
    empty_data = {
        "date": datetime.datetime.now().strftime("%Y%m%d"),
        "data_source": "error",
        "data": []
    }
    set_cache(cache_key, empty_data, 60)  # 1 minute for errors
    return empty_data
