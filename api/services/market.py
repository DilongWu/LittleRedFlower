import pandas as pd
import datetime
import math
import time
import os
import re
import json
import logging

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


def _resolve_storage_dir():
    """Get storage directory path."""
    env_dir = os.getenv("STORAGE_DIR")
    if env_dir:
        return env_dir
    azure_persist_dir = os.path.join("/home", "data", "storage")
    if os.path.isdir(os.path.join("/home", "site")):
        return azure_persist_dir
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "storage")


def _get_ladder_from_daily_report():
    """
    Parse limit-up ladder data from the daily report's raw_data.
    This avoids making API calls and uses pre-generated data from the morning report.
    Returns: (ladder_dict, date_str) or (None, None)
    """
    storage_dir = _resolve_storage_dir()
    if not os.path.exists(storage_dir):
        logging.warning(f"Storage directory not found: {storage_dir}")
        return None, None

    # Find the most recent daily report (check today and last 7 days)
    now = datetime.datetime.now()
    for i in range(8):
        check_date = (now - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        report_path = os.path.join(storage_dir, f"{check_date}_daily.json")
        if os.path.exists(report_path):
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    report = json.load(f)

                raw_data = report.get("raw_data", "")
                if not raw_data or "【昨日涨停梯队数据】" not in raw_data:
                    continue

                # Parse the ladder data from raw_data text
                ladder = _parse_ladder_from_raw_data(raw_data)
                if ladder:
                    logging.info(f"Loaded ladder data from daily report: {check_date}")
                    # Return the report date (which refers to yesterday's data)
                    return ladder, check_date.replace("-", "")

            except Exception as e:
                logging.error(f"Error reading daily report {check_date}: {e}")
                continue

    return None, None


def _parse_ladder_from_raw_data(raw_data: str) -> dict:
    """
    Parse ladder data from the raw_data text format.
    Example line: "- 白银有色 (7连板): 行业-有色金属, 首次封板-100220, ..."
    """
    ladder = {}

    # Find the section starting with 【昨日涨停梯队数据】
    start_marker = "【昨日涨停梯队数据】"
    start_idx = raw_data.find(start_marker)
    if start_idx == -1:
        return None

    # Extract just the ladder section
    ladder_section = raw_data[start_idx + len(start_marker):]

    # Pattern to match lines like: "- 白银有色 (7连板): 行业-有色金属, 首次封板-100220, 最后封板-100656, 炸板-2次"
    pattern = r'^- ([^\(]+) \((\d+)连板\): 行业-([^,]+), 首次封板-(\d+)'

    current_stock = None
    current_lb = None

    for line in ladder_section.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Check if this is a main stock line
        if line.startswith('- ') and '连板' in line:
            match = re.match(pattern, line)
            if match:
                name = match.group(1).strip()
                lb_count = match.group(2)  # "7", "4", "1" etc
                industry = match.group(3).strip()
                first_time = match.group(4)

                # Format first_time as HH:MM:SS for display
                if len(first_time) == 6:
                    first_time = f"{first_time[:2]}:{first_time[2:4]}:{first_time[4:]}"

                current_stock = name
                current_lb = lb_count

                if lb_count not in ladder:
                    ladder[lb_count] = []

                ladder[lb_count].append({
                    "name": name,
                    "code": "",  # Will be filled from news lines
                    "reason": industry,  # Default to industry, may be updated
                    "industry": industry,
                    "time": first_time
                })

        # Check if this is an AI analysis line (update reason)
        elif line.startswith('* AI分析:') and current_stock:
            # Extract the analysis text after the tags
            ai_match = re.search(r'\[首封:[^\]]+\] (.+)', line)
            if ai_match and current_lb in ladder:
                reason = ai_match.group(1)[:100]  # Truncate to 100 chars
                # Update the last stock in this level
                for stock in ladder[current_lb]:
                    if stock["name"] == current_stock:
                        stock["reason"] = reason
                        break

        # Check if this is a news line containing stock code
        elif line.startswith('* 资讯:') and current_stock:
            # Try to extract stock code from patterns like "白银有色601212龙虎榜" or "（003042）"
            code_match = re.search(r'[（(]?([0136]\d{5})[)）]?', line)
            if code_match and current_lb in ladder:
                code = code_match.group(1)
                # Update the last stock in this level if code is empty
                for stock in ladder[current_lb]:
                    if stock["name"] == current_stock and not stock["code"]:
                        stock["code"] = code
                        break

    return ladder if ladder else None


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
    """
    Get market radar data with caching and automatic fallback between data sources.

    Optimization: For ladder (limit-up) data, prioritize reading from the daily report
    to avoid API calls and rate limiting issues. The daily report is generated at 8:00 AM
    and contains comprehensive ladder data with AI analysis.
    """
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

    # === OPTIMIZATION: Try to get ladder data from daily report first ===
    # This avoids API calls which often fail due to rate limiting or permission issues
    ladder, ladder_date = _get_ladder_from_daily_report()
    if ladder:
        date_str = ladder_date or date_str
        actual_source = actual_source or "daily_report"
        logging.info(f"Using ladder data from daily report (date: {date_str})")
    else:
        # Fallback: Try API-based methods if daily report not available
        logging.info("Daily report ladder not available, trying API...")
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
