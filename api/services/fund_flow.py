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


def _find_col(columns, keywords):
    for col in columns:
        if all(k in col for k in keywords):
            return col
    return None


def _get_fund_flow_eastmoney(ak, limit):
    """Get fund flow data from Eastmoney."""
    df = ak.stock_individual_fund_flow_rank()
    if df is None or df.empty:
        return None

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


def _get_fund_flow_sina(ak, limit):
    """Get fund flow data from Sina (approximated from stock data)."""
    try:
        # Sina doesn't have direct fund flow API
        # We'll use stock data and sort by volume/turnover as a proxy
        df = ak.stock_zh_a_spot()
        if df is None or df.empty:
            return None

        # Find relevant columns
        cols = df.columns
        code_col = None
        name_col = None
        price_col = None
        change_col = None
        volume_col = None

        for col in cols:
            if '代码' in col:
                code_col = col
            if '名称' in col:
                name_col = col
            if '最新' in col or '现价' in col:
                price_col = col
            if '涨跌幅' in col:
                change_col = col
            if '成交量' in col or '成交额' in col:
                volume_col = col

        if not all([code_col, name_col]):
            return None

        # Sort by volume (descending) as proxy for fund activity
        if volume_col:
            import pandas as pd
            df[volume_col] = pd.to_numeric(df[volume_col], errors='coerce')
            df = df.sort_values(by=volume_col, ascending=False)

        result = []
        for _, row in df.head(limit).iterrows():
            result.append({
                "code": row.get(code_col, ""),
                "name": row.get(name_col, ""),
                "price": _clean_float(row.get(price_col, None)) if price_col else None,
                "change_pct": _clean_float(row.get(change_col, None)) if change_col else None,
                "net_inflow": _clean_float(row.get(volume_col, None)) if volume_col else None,  # Using volume as proxy
                "net_ratio": None,
            })

        return result

    except Exception as e:
        logging.error(f"Error in _get_fund_flow_sina: {e}")
        return None


def get_fund_flow_rank(limit: int = 30):
    import akshare as ak  # Lazy import

    current_source = get_data_source()

    try:
        if current_source == "eastmoney":
            result = _get_fund_flow_eastmoney(ak, limit)
        else:
            result = _get_fund_flow_sina(ak, limit)

        if result:
            return {
                "date": datetime.datetime.now().strftime("%Y%m%d"),
                "data_source": current_source,
                "data": result
            }
    except Exception as e:
        logging.error(f"Error fetching fund flow ({current_source}): {e}")

    # Return Mock Data
    return {
        "date": datetime.datetime.now().strftime("%Y%m%d"),
        "data_source": "demo",
        "data": [
            {"code": "600000", "name": "浦发银行", "price": 7.20, "change_pct": 1.25, "net_inflow": 12000.5, "net_ratio": 5.2},
            {"code": "601127", "name": "赛力斯", "price": 88.50, "change_pct": 3.45, "net_inflow": 8500.2, "net_ratio": 3.1},
            {"code": "000001", "name": "平安银行", "price": 10.30, "change_pct": 0.50, "net_inflow": 4500.0, "net_ratio": 2.2},
            {"code": "300059", "name": "东方财富", "price": 13.80, "change_pct": -0.80, "net_inflow": -2000.0, "net_ratio": -1.5},
            {"code": "600519", "name": "贵州茅台", "price": 1650.00, "change_pct": -0.20, "net_inflow": -3500.0, "net_ratio": -0.8},
            {"code": "002594", "name": "比亚迪", "price": 280.00, "change_pct": 1.10, "net_inflow": 3200.0, "net_ratio": 1.8},
        ]
    }
