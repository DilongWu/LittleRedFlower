import pandas as pd
import datetime
import json
import os
import logging
import math

from api.services.data_source import get_data_source


def _clean_float(val):
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return 0.0 # Return 0 for sectors likely better than None
        return f
    except:
        return 0.0

# Simple in-memory cache
_MARKET_CACHE = {
    "data": None,
    "timestamp": None,
    "source": None
}

CACHE_DURATION_SECONDS = 300  # 5 minutes


def _get_sectors_eastmoney(ak):
    """Get sector data from Eastmoney (东方财富)."""
    sectors_df = ak.stock_board_industry_name_em()
    if sectors_df.empty:
        return []

    sectors = []
    for _, row in sectors_df.iterrows():
        change_pct = _clean_float(row.get('涨跌幅', 0))

        sectors.append({
            "name": row['板块名称'],
            "change": change_pct,
            "top_stock": row.get('领涨股票', '')
        })

    return sectors


def _get_sectors_sina(ak):
    """Get sector data from Sina (新浪) - aggregated from individual stocks."""
    # Sina doesn't have a direct sector API like Eastmoney
    # We'll try multiple approaches
    try:
        # First try: Use concept board from Eastmoney as fallback (might work intermittently)
        try:
            concept_df = ak.stock_board_concept_name_em()
            if concept_df is not None and not concept_df.empty:
                sectors = []
                for _, row in concept_df.head(30).iterrows():
                    change_pct = _clean_float(row.get('涨跌幅', 0))

                    sectors.append({
                        "name": row.get('板块名称', ''),
                        "change": change_pct,
                        "top_stock": row.get('领涨股票', '')
                    })
                return sectors
        except Exception as e:
            logging.warning(f"Concept board failed: {e}")

        # Second try: Get stock list and create summary
        try:
            stock_list = ak.stock_info_a_code_name()
            if stock_list is not None and not stock_list.empty:
                # Return a simplified sector view based on available data
                # Since we can't get real-time sector data, return empty to trigger mock
                pass
        except:
            pass

        return []

    except Exception as e:
        logging.error(f"Error in _get_sectors_sina: {e}")
        return []


def _get_limit_up_eastmoney(ak, now):
    """Get limit-up ladder data from Eastmoney."""
    today_str = now.strftime("%Y%m%d")
    zt_df = pd.DataFrame()

    try:
        zt_df = ak.stock_zt_pool_em(date=today_str)
    except:
        pass

    if zt_df.empty:
        # Fallback to previous trading days
        for i in range(1, 4):
            prev = (now - datetime.timedelta(days=i)).strftime("%Y%m%d")
            try:
                zt_df = ak.stock_zt_pool_em(date=prev)
                if not zt_df.empty:
                    today_str = prev
                    break
            except:
                pass

    ladder = {}
    if not zt_df.empty and '连板数' in zt_df.columns:
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

    return ladder, today_str


def _get_limit_up_sina(ak, now):
    """Get limit-up stocks from Sina data."""
    today_str = now.strftime("%Y%m%d")
    ladder = {}

    try:
        # Try to get limit-up pool (uses Eastmoney internally but might work)
        try:
            zt_df = ak.stock_zt_pool_em(date=today_str)
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
                return ladder, today_str
        except Exception as e:
            logging.warning(f"Limit-up pool failed: {e}")

        # Fallback: Try previous trading days
        for i in range(1, 4):
            prev = (now - datetime.timedelta(days=i)).strftime("%Y%m%d")
            try:
                zt_df = ak.stock_zt_pool_em(date=prev)
                if zt_df is not None and not zt_df.empty:
                    today_str = prev
                    if '连板数' in zt_df.columns:
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
                    return ladder, today_str
            except:
                pass

    except Exception as e:
        logging.error(f"Error in _get_limit_up_sina: {e}")

    return ladder, today_str


def get_market_radar_data():
    global _MARKET_CACHE
    import akshare as ak  # Lazy import to prevent startup errors

    now = datetime.datetime.now()
    current_source = get_data_source()

    # Check cache (invalidate if source changed)
    if (_MARKET_CACHE["data"] and _MARKET_CACHE["timestamp"]
            and _MARKET_CACHE["source"] == current_source):
        if (now - _MARKET_CACHE["timestamp"]).total_seconds() < CACHE_DURATION_SECONDS:
            return _MARKET_CACHE["data"]

    try:
        data = {"data_source": current_source}

        if current_source == "eastmoney":
            # Try Eastmoney first
            sectors = _get_sectors_eastmoney(ak)
            ladder, date_str = _get_limit_up_eastmoney(ak, now)
        else:
            # Use Sina
            sectors = _get_sectors_sina(ak)
            ladder, date_str = _get_limit_up_sina(ak, now)

        data['sectors'] = sectors
        data['ladder'] = ladder
        data['date'] = date_str

        # Validate we got real data
        if not sectors and not ladder:
            raise Exception("No data returned from API")

        # Update Cache
        _MARKET_CACHE["data"] = data
        _MARKET_CACHE["timestamp"] = now
        _MARKET_CACHE["source"] = current_source

        return data

    except Exception as e:
        logging.error(f"Error fetching market radar data ({current_source}): {e}")
        logging.info("Returning Mock Data due to API failure.")
        return {
            "date": now.strftime("%Y%m%d"),
            "data_source": "demo",
            "sectors": [
                {"name": "通信设备", "change": 5.2, "top_stock": "中际旭创"},
                {"name": "半导体", "change": 4.1, "top_stock": "北方华创"},
                {"name": "证券", "change": 2.5, "top_stock": "东方财富"},
                {"name": "银行", "change": -0.5, "top_stock": "招商银行"},
                {"name": "房地产", "change": -1.2, "top_stock": "万科A"},
                {"name": "医疗器械", "change": -2.1, "top_stock": "迈瑞医疗"},
                {"name": "酿酒行业", "change": -0.8, "top_stock": "贵州茅台"},
                {"name": "光伏设备", "change": 1.5, "top_stock": "隆基绿能"},
                {"name": "汽车整车", "change": 3.0, "top_stock": "赛力斯"},
                {"name": "消费电子", "change": 2.2, "top_stock": "立讯精密"},
                {"name": "煤炭行业", "change": -1.5, "top_stock": "中国神华"},
                {"name": "电力行业", "change": 0.2, "top_stock": "长江电力"},
            ],
            "ladder": {
                "5": [{"name": "龙头股份", "code": "600630", "reason": "电商+龙字辈", "industry": "纺织服装"}],
                "4": [{"name": "中视传媒", "code": "600088", "reason": "央企传媒", "industry": "文化传媒"}],
                "3": [
                    {"name": "长江投资", "code": "600119", "reason": "上海国资", "industry": "物流行业"},
                    {"name": "中华企业", "code": "600675", "reason": "房地产", "industry": "房地产"}
                ],
                "2": [
                    {"name": "浦东金桥", "code": "600639", "reason": "上海自贸", "industry": "房地产"},
                    {"name": "畅联股份", "code": "603648", "reason": "物流", "industry": "物流行业"},
                    {"name": "开开实业", "code": "600272", "reason": "医药", "industry": "医药商业"}
                ]
            }
        }
