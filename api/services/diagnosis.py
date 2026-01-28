import datetime
import pandas as pd


def _safe_float(value, default=None):
    try:
        return float(value)
    except Exception:
        return default


def get_stock_diagnosis(symbol: str, days: int = 60):
    import akshare as ak  # Lazy import to avoid startup failures

    if not symbol:
        return {"error": "Missing symbol"}

    symbol = symbol.strip()

    # 1) Basic info
    basic_info = {}
    try:
        info_df = ak.stock_individual_info_em(symbol=symbol)
        if not info_df.empty and "item" in info_df.columns and "value" in info_df.columns:
            for _, row in info_df.iterrows():
                basic_info[row["item"]] = row["value"]
    except Exception:
        pass

    # 2) Historical daily data
    hist_df = None
    try:
        hist_df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
    except Exception:
        pass

    if hist_df is None or hist_df.empty:
        # Return empty data instead of mock data
        return {
            "symbol": symbol,
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "error": "无法获取股票数据，请检查股票代码是否正确",
            "data_source": "error"
        }

    # Ensure proper columns
    # Columns usually: 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
    hist_df = hist_df.tail(days).copy()

    hist_df["收盘"] = pd.to_numeric(hist_df.get("收盘"), errors="coerce")
    hist_df["成交量"] = pd.to_numeric(hist_df.get("成交量"), errors="coerce")

    latest = hist_df.iloc[-1]
    prev = hist_df.iloc[-2] if len(hist_df) >= 2 else latest

    latest_close = _safe_float(latest.get("收盘"), 0.0) or 0.0
    prev_close = _safe_float(prev.get("收盘"), latest_close) or latest_close
    change_pct = ((latest_close - prev_close) / prev_close * 100) if prev_close else 0.0

    # Moving averages
    ma5 = hist_df["收盘"].rolling(5).mean().iloc[-1]
    ma10 = hist_df["收盘"].rolling(10).mean().iloc[-1]
    ma20 = hist_df["收盘"].rolling(20).mean().iloc[-1]

    # Volume trend
    vol5 = hist_df["成交量"].rolling(5).mean().iloc[-1]
    vol20 = hist_df["成交量"].rolling(20).mean().iloc[-1]
    vol_ratio = (vol5 / vol20) if (vol5 and vol20) else None

    # Simple technical state
    trend = "中性"
    if latest_close > ma5 > ma10 > ma20:
        trend = "多头"
    elif latest_close < ma5 < ma10 < ma20:
        trend = "空头"

    diagnosis = {
        "symbol": symbol,
        "date": str(latest.get("日期", datetime.datetime.now().date())),
        "price": round(latest_close, 2),
        "change_pct": round(change_pct, 2),
        "ma5": round(float(ma5), 2) if pd.notna(ma5) else None,
        "ma10": round(float(ma10), 2) if pd.notna(ma10) else None,
        "ma20": round(float(ma20), 2) if pd.notna(ma20) else None,
        "vol_ratio": round(float(vol_ratio), 2) if (vol_ratio is not None and pd.notna(vol_ratio)) else None,
        "trend": trend,
        "basic": basic_info,
    }

    return diagnosis
