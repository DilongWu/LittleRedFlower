"""
Tushare Pro API client wrapper.
Provides data fetching functions similar to AkShare for seamless switching.

Note: Some Tushare APIs require certain point levels. This module uses
free/low-point APIs where possible, with fallbacks.
"""
import logging
import datetime
from typing import Optional, List, Dict, Any
import pandas as pd

from api.services.data_source import get_tushare_token
from api.services.http_client import fetch_with_retry

# Global Tushare pro api instance
_PRO_API = None
_TS_MODULE = None


def get_ts_module():
    """Get tushare module (lazy import)."""
    global _TS_MODULE
    if _TS_MODULE is None:
        import tushare as ts
        token = get_tushare_token()
        if token:
            ts.set_token(token)
        _TS_MODULE = ts
    return _TS_MODULE


def get_pro_api():
    """Get or create Tushare pro api instance."""
    global _PRO_API
    if _PRO_API is None:
        token = get_tushare_token()
        if not token:
            raise ValueError("Tushare token not configured")

        ts = get_ts_module()
        _PRO_API = ts.pro_api()

    return _PRO_API


def reset_pro_api():
    """Reset the pro api instance (call after token change)."""
    global _PRO_API, _TS_MODULE
    _PRO_API = None
    _TS_MODULE = None


# ============ Index Data ============

def get_index_daily(symbol: str, days: int = 60) -> Optional[pd.DataFrame]:
    """
    Get index daily data. Falls back to AkShare if Tushare fails.

    Args:
        symbol: Index code like 'sh000001', 'sz399001'
        days: Number of days of data

    Returns:
        DataFrame with columns matching AkShare format
    """
    try:
        # Use AkShare as the backend (more reliable)
        import akshare as ak

        df = ak.stock_zh_index_daily_em(symbol=symbol)
        if df is not None and not df.empty:
            df = df.tail(days).copy()
            # Rename columns to standard format if needed
            col_map = {
                'date': '日期',
                'open': '开盘',
                'high': '最高',
                'low': '最低',
                'close': '收盘',
                'volume': '成交量'
            }
            for old_col, new_col in col_map.items():
                if old_col in df.columns and new_col not in df.columns:
                    df = df.rename(columns={old_col: new_col})
            return df

    except Exception as e:
        logging.error(f"Tushare get_index_daily error: {e}")

    return None


# ============ Stock Data ============

def get_stock_basic() -> Optional[pd.DataFrame]:
    """Get basic stock list."""
    try:
        pro = get_pro_api()
        df = pro.stock_basic(
            exchange='',
            list_status='L',
            fields='ts_code,symbol,name,area,industry,list_date'
        )
        return df
    except Exception as e:
        logging.error(f"Tushare get_stock_basic error: {e}")
    return None


def get_daily_basic(trade_date: str = None) -> Optional[pd.DataFrame]:
    """Get daily basic data for all stocks."""
    try:
        pro = get_pro_api()
        if trade_date is None:
            trade_date = datetime.datetime.now().strftime('%Y%m%d')

        df = pro.daily_basic(
            trade_date=trade_date,
            fields='ts_code,close,turnover_rate,volume_ratio,pe,pb'
        )
        return df
    except Exception as e:
        logging.error(f"Tushare get_daily_basic error: {e}")
    return None


# ============ Fund Flow ============

def get_moneyflow_hsgt() -> Optional[pd.DataFrame]:
    """Get north-south fund flow (沪深港通资金流向)."""
    try:
        pro = get_pro_api()
        end_date = datetime.datetime.now().strftime('%Y%m%d')
        start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d')

        df = pro.moneyflow_hsgt(start_date=start_date, end_date=end_date)
        return df
    except Exception as e:
        logging.error(f"Tushare get_moneyflow_hsgt error: {e}")
    return None


def get_stock_moneyflow(ts_code: str = None, trade_date: str = None) -> Optional[pd.DataFrame]:
    """
    Get individual stock money flow.

    Note: This requires higher Tushare permission level.
    """
    try:
        pro = get_pro_api()
        if trade_date is None:
            trade_date = datetime.datetime.now().strftime('%Y%m%d')

        # Try to get money flow data
        df = pro.moneyflow(trade_date=trade_date)
        return df
    except Exception as e:
        logging.error(f"Tushare get_stock_moneyflow error: {e}")
    return None


# ============ Concept/Industry ============

def get_concept_list() -> Optional[pd.DataFrame]:
    """Get concept board list."""
    try:
        pro = get_pro_api()
        df = pro.concept()
        return df
    except Exception as e:
        logging.error(f"Tushare get_concept_list error: {e}")
    return None


def get_concept_detail(concept_id: str) -> Optional[pd.DataFrame]:
    """Get stocks in a concept board."""
    try:
        pro = get_pro_api()
        df = pro.concept_detail(id=concept_id)
        return df
    except Exception as e:
        logging.error(f"Tushare get_concept_detail error: {e}")
    return None


def get_ths_index() -> Optional[pd.DataFrame]:
    """Get THS (同花顺) industry/concept index list."""
    try:
        pro = get_pro_api()
        df = pro.ths_index()
        return df
    except Exception as e:
        logging.error(f"Tushare get_ths_index error: {e}")
    return None


# ============ Limit Up/Down (涨跌停) ============

def get_limit_list(trade_date: str = None, limit_type: str = 'U') -> Optional[pd.DataFrame]:
    """
    Get limit up/down stocks.

    Args:
        trade_date: Trade date in YYYYMMDD format
        limit_type: 'U' for limit up, 'D' for limit down

    Note: This requires higher Tushare permission level (5000+ points).
    """
    try:
        pro = get_pro_api()
        if trade_date is None:
            trade_date = datetime.datetime.now().strftime('%Y%m%d')

        df = pro.limit_list_d(trade_date=trade_date, limit_type=limit_type)
        return df
    except Exception as e:
        logging.error(f"Tushare get_limit_list error: {e}")
    return None


# ============ Market Overview ============

def get_index_global() -> Optional[pd.DataFrame]:
    """Get global market index data."""
    try:
        pro = get_pro_api()
        df = pro.index_global(ts_code='XIN9')  # A50
        return df
    except Exception as e:
        logging.error(f"Tushare get_index_global error: {e}")
    return None
