import datetime
import pandas as pd
import logging

from api.services.data_source import get_data_source


import math

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


def _get_index_eastmoney(ak, symbol, days, points):
    """Get index data from Eastmoney."""
    df = ak.stock_zh_index_daily_em(symbol=symbol)
    if df is None or df.empty:
        return None

    df = df.tail(days).copy()
    df["close"] = pd.to_numeric(df.get("收盘"), errors="coerce")

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest

    latest_close = float(latest.get("close", 0.0) or 0.0)
    prev_close = float(prev.get("close", latest_close) or latest_close)
    change_pct = ((latest_close - prev_close) / prev_close * 100) if prev_close else 0.0

    ma5 = df["close"].rolling(5).mean().iloc[-1]
    ma20 = df["close"].rolling(20).mean().iloc[-1]

    series = df["close"].tail(points).tolist()

    return {
        "date": str(latest.get("日期", datetime.datetime.now().date())),
        "close": _clean_json_float(latest_close),
        "change_pct": _clean_json_float(change_pct),
        "ma5": _clean_json_float(ma5),
        "ma20": _clean_json_float(ma20),
        "series": _series_to_sparkline(series),
    }


def _get_index_sina(ak, symbol, days, points):
    """Get index data from Sina."""
    try:
        # Convert symbol format for Sina (sh000001 -> 000001)
        code = symbol[2:] if symbol.startswith(('sh', 'sz')) else symbol

        # Try using index_zh_a_hist which should work with Sina
        end_date = datetime.datetime.now().strftime("%Y%m%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=days + 30)).strftime("%Y%m%d")

        df = ak.index_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date)
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
            close_col = '收盘'

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

    except Exception as e:
        logging.error(f"Error in _get_index_sina for {symbol}: {e}")
        return None


def get_index_overview(days: int = 60, points: int = 30):
    import akshare as ak  # Lazy import

    current_source = get_data_source()

    index_map = {
        "上证指数": "sh000001",
        "深证成指": "sz399001",
        "沪深300": "sh000300",
        "创业板指": "sz399006",
    }

    results = []

    for name, symbol in index_map.items():
        try:
            if current_source == "eastmoney":
                data = _get_index_eastmoney(ak, symbol, days, points)
            else:
                data = _get_index_sina(ak, symbol, days, points)

            if data:
                data["name"] = name
                data["symbol"] = symbol
                data["data_source"] = current_source
                results.append(data)

        except Exception as e:
            logging.error(f"Error fetching index {name} ({current_source}): {e}")
            continue

    if not results:
        return _get_mock_index_data()

    return results


def _get_mock_index_data():
    import random
    mock_indexes = [
        {"name": "上证指数", "symbol": "sh000001", "close": 2860.55, "prev": 2850.00},
        {"name": "深证成指", "symbol": "sz399001", "close": 8600.20, "prev": 8650.00},
        {"name": "沪深300", "symbol": "sh000300", "close": 3200.10, "prev": 3190.00},
        {"name": "创业板指", "symbol": "sz399006", "close": 1550.80, "prev": 1540.00},
    ]

    results = []
    for item in mock_indexes:
        change_pct = (item["close"] - item["prev"]) / item["prev"] * 100

        # Generate random sparkline
        series = []
        val = item["close"]
        for _ in range(30):
            val = val * (1 + (random.random() - 0.5) * 0.02)
            series.insert(0, val)

        ma5 = sum(series[-5:]) / 5
        ma20 = sum(series[-20:]) / 20

        results.append({
            "name": item["name"],
            "symbol": item["symbol"],
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "close": round(item["close"], 2),
            "change_pct": round(change_pct, 2),
            "ma5": round(ma5, 2),
            "ma20": round(ma20, 2),
            "series": [round(s, 2) for s in series],
            "data_source": "demo",
        })
    return results
