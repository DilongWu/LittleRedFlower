import datetime
import math
import logging

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


def _find_col(columns, keywords):
    for col in columns:
        if all(k in col for k in keywords):
            return col
    return None


def _get_fund_flow_tushare(limit):
    """Get fund flow data from Tushare."""
    from api.services import tushare_client
    return tushare_client.get_fund_flow_rank(limit)


def _get_fund_flow_eastmoney_lite(ak, limit):
    """
    Get fund flow data using lightweight industry board interface.
    Uses stock_board_industry_name_em which only requires 1 request instead of 53.
    """
    try:
        # Get industry board data (1 request only!)
        df = fetch_with_retry(ak.stock_board_industry_name_em, max_retries=3)

        if df is None or df.empty:
            return None

        # Sort by net inflow and get top N
        if '涨跌幅' in df.columns:
            df = df.sort_values(by='涨跌幅', ascending=False)

        result = []
        for _, row in df.head(limit).iterrows():
            # Map board data to expected format
            result.append({
                "code": "",  # Boards don't have codes
                "name": row.get('板块名称', ''),
                "price": None,  # Boards don't have price
                "change_pct": _clean_float(row.get('涨跌幅', None)),
                "net_inflow": row.get('领涨股票', '-'),  # Use lead stock as placeholder
                "net_ratio": f"{_clean_float(row.get('涨跌幅', 0)):.2f}%" if row.get('涨跌幅') else '-',
            })

        logging.info(f"Successfully fetched {len(result)} industry boards")
        return result

    except Exception as e:
        logging.error(f"Error in _get_fund_flow_eastmoney_lite: {e}")
        return None


def _get_fund_flow_eastmoney_legacy(ak, limit):
    """
    Legacy method using stock_individual_fund_flow_rank (requires 53 requests).
    Keep as fallback but not recommended.
    """
    df = fetch_with_retry(ak.stock_individual_fund_flow_rank, max_retries=2, indicator='今日')

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

    return None


def _get_fund_flow_sina(ak, limit):
    """Get fund flow data from Sina via AkShare (fallback to stock list)."""
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


def get_fund_flow_rank(limit: int = 20):
    """
    Get fund flow rank with caching and automatic fallback between data sources.
    Optimized to use lightweight industry board data (1 request instead of 53).
    """
    import akshare as ak

    current_source = get_data_source()
    cache_key = f"fund_flow_{current_source}"

    # Check cache first
    cached_data = get_cache(cache_key)
    if cached_data is not None:
        return cached_data

    # Build fetch functions for each source
    # Priority: Use lite version for eastmoney to avoid 53 requests
    fetch_funcs = {
        "tushare": lambda: _get_fund_flow_tushare(limit),
        "eastmoney": lambda: _get_fund_flow_eastmoney_lite(ak, limit),  # Use lite version!
        "sina": lambda: _get_fund_flow_sina(ak, limit),
    }

    # Try to fetch with automatic fallback
    result, source_used = fetch_with_fallback(fetch_funcs, "fund flow")

    if result:
        data = {
            "date": datetime.datetime.now().strftime("%Y%m%d"),
            "data_source": source_used or current_source,
            "data": result,
            "note": "显示TOP行业板块（优化版，1次请求）"  # Add note
        }
        set_cache(cache_key, data, 1800)  # 30 minutes (increased from 10)
        return data

    # Fallback: Try legacy method as last resort
    logging.warning("Lite method failed, trying legacy method...")
    try:
        legacy_result = _get_fund_flow_eastmoney_legacy(ak, limit)
        if legacy_result:
            data = {
                "date": datetime.datetime.now().strftime("%Y%m%d"),
                "data_source": "eastmoney_legacy",
                "data": legacy_result,
                "note": "个股资金流向（降级方案）"
            }
            set_cache(cache_key, data, 1800)  # 30 minutes
            return data
    except Exception as e:
        logging.error(f"Legacy method also failed: {e}")

    # Return empty data
    empty_data = {
        "date": datetime.datetime.now().strftime("%Y%m%d"),
        "data_source": "error",
        "data": [],
        "note": "数据获取失败，请稍后重试"
    }
    set_cache(cache_key, empty_data, 120)  # 2 minutes for errors
    return empty_data
