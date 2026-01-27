import datetime
import logging
import math

from api.services.data_source import get_data_source


def _clean_float(val):
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _get_concepts_eastmoney(ak, limit):
    """Get hot concepts from Eastmoney."""
    df = ak.stock_board_concept_name_em()
    if df is None or df.empty:
        return None

    data = []
    for _, row in df.iterrows():
        name = row.get("板块名称", "")
        change = _clean_float(row.get("涨跌幅", 0))
        lead = row.get("领涨股票", "")
        data.append({
            "name": name,
            "change": change,
            "lead": lead,
        })

    data_sorted = sorted(data, key=lambda x: (x.get("change") or 0), reverse=True)
    return data_sorted[:limit]


def _get_concepts_sina(ak, limit):
    """Get hot concepts from Sina (approximated)."""
    try:
        # Sina has limited concept data
        # Try to get stock data and extract trending stocks as "concepts"
        df = ak.stock_zh_a_spot()
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
                "change": row.get(change_col, 0),
                "lead": "热门股票",  # Placeholder
            })

        return data

    except Exception as e:
        logging.error(f"Error in _get_concepts_sina: {e}")
        return None


def get_hot_concepts(limit: int = 20):
    import akshare as ak  # Lazy import

    current_source = get_data_source()

    try:
        if current_source == "eastmoney":
            result = _get_concepts_eastmoney(ak, limit)
        else:
            result = _get_concepts_sina(ak, limit)

        if result:
            return {
                "date": datetime.datetime.now().strftime("%Y%m%d"),
                "data_source": current_source,
                "data": result
            }
    except Exception as e:
        logging.error(f"Error fetching concepts ({current_source}): {e}")

    # Mock Data
    return {
        "date": datetime.datetime.now().strftime("%Y%m%d"),
        "data_source": "demo",
        "data": [
            {"name": "Sora概念", "change": 5.4, "lead": "因赛集团"},
            {"name": "低空经济", "change": 4.1, "lead": "万丰奥威"},
            {"name": "算力租赁", "change": 3.2, "lead": "高新发展"},
            {"name": "华为升腾", "change": 2.8, "lead": "软通动力"},
            {"name": "汽车拆解", "change": 1.9, "lead": "华宏科技"},
            {"name": "冷链物流", "change": -0.5, "lead": "四方科技"},
            {"name": "煤炭行业", "change": -1.2, "lead": "中国神华"},
        ]
    }
