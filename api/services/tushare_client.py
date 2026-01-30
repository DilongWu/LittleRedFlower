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
    Get index daily data using Tushare index_daily API.

    Args:
        symbol: Index code like 'sh000001', 'sz399001'
        days: Number of days of data

    Returns:
        DataFrame with columns matching AkShare format for compatibility
    """
    try:
        pro = get_pro_api()

        # Convert AkShare style symbol to Tushare style
        # sh000001 -> 000001.SH, sz399001 -> 399001.SZ
        if symbol.startswith('sh'):
            ts_code = symbol[2:] + '.SH'
        elif symbol.startswith('sz'):
            ts_code = symbol[2:] + '.SZ'
        else:
            ts_code = symbol

        # Calculate date range
        end_date = datetime.datetime.now().strftime('%Y%m%d')
        start_date = (datetime.datetime.now() - datetime.timedelta(days=days + 30)).strftime('%Y%m%d')

        df = pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

        if df is not None and not df.empty:
            # Sort by date ascending (Tushare returns descending)
            df = df.sort_values('trade_date', ascending=True).tail(days).copy()

            # Rename columns to match AkShare format for compatibility
            col_map = {
                'trade_date': '日期',
                'open': '开盘',
                'high': '最高',
                'low': '最低',
                'close': '收盘',
                'vol': '成交量',
                'amount': '成交额',
                'pct_chg': '涨跌幅'
            }
            df = df.rename(columns=col_map)
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


# ============ Sector/Industry Board ============

def get_industry_board() -> Optional[List[Dict[str, Any]]]:
    """
    Get industry board data with change percentage.
    Returns format compatible with AkShare's stock_board_industry_name_em.
    """
    try:
        pro = get_pro_api()
        # Get THS industry index
        df = pro.ths_index(exchange='A', type='I')  # I = Industry
        if df is None or df.empty:
            return None

        # Get latest daily data for these indices
        today = datetime.datetime.now().strftime('%Y%m%d')
        results = []

        for _, row in df.head(50).iterrows():
            ts_code = row.get('ts_code', '')
            name = row.get('name', '')
            try:
                # Get daily data
                daily = pro.ths_daily(ts_code=ts_code, start_date=today, end_date=today)
                if daily is not None and not daily.empty:
                    change_pct = daily.iloc[0].get('pct_change', 0)
                    results.append({
                        "name": name,
                        "change": float(change_pct) if change_pct else 0.0,
                        "top_stock": ""
                    })
            except Exception:
                continue

        return results if results else None

    except Exception as e:
        logging.error(f"Tushare get_industry_board error: {e}")
    return None


def get_concept_board() -> Optional[List[Dict[str, Any]]]:
    """
    Get concept board data with change percentage.
    Returns format compatible with AkShare's stock_board_concept_name_em.
    """
    try:
        pro = get_pro_api()
        # Get THS concept index
        df = pro.ths_index(exchange='A', type='N')  # N = Concept
        if df is None or df.empty:
            return None

        today = datetime.datetime.now().strftime('%Y%m%d')
        results = []

        for _, row in df.head(50).iterrows():
            ts_code = row.get('ts_code', '')
            name = row.get('name', '')
            try:
                daily = pro.ths_daily(ts_code=ts_code, start_date=today, end_date=today)
                if daily is not None and not daily.empty:
                    change_pct = daily.iloc[0].get('pct_change', 0)
                    results.append({
                        "name": name,
                        "change": float(change_pct) if change_pct else 0.0,
                        "lead": ""
                    })
            except Exception:
                continue

        return results if results else None

    except Exception as e:
        logging.error(f"Tushare get_concept_board error: {e}")
    return None


# ============ Fund Flow (资金流向) ============

# Cache for stock quotes (reduces API calls)
_STOCK_QUOTES_CACHE: Dict[str, Any] = {
    "data": {},
    "expires_at": None
}


def _get_stock_quotes_batch(ts_codes: List[str], trade_date: str = None) -> Dict[str, Dict[str, Any]]:
    """
    Batch fetch stock quotes with caching.
    Returns a dict mapping ts_code to {price, change_pct}.
    Uses cache to avoid repeated API calls.
    """
    global _STOCK_QUOTES_CACHE

    now = datetime.datetime.now()

    # Cache duration: Tushare daily_basic only updates after market close
    # So there's no point refreshing frequently during trading hours
    # Use 1 hour cache during trading, 2 hours otherwise
    is_trading_hours = 9 <= now.hour < 15 or (now.hour == 15 and now.minute == 0)
    cache_duration = 3600 if is_trading_hours else 7200  # 1 hour or 2 hours

    if (_STOCK_QUOTES_CACHE["expires_at"] is not None and
        now < _STOCK_QUOTES_CACHE["expires_at"] and
        _STOCK_QUOTES_CACHE["data"]):
        logging.debug("Using cached stock quotes")
        return _STOCK_QUOTES_CACHE["data"]

    # Cache expired or empty, fetch new data
    try:
        pro = get_pro_api()
        if trade_date is None:
            trade_date = now.strftime('%Y%m%d')

        # Use daily_basic API to get price and change_pct for all stocks
        # This is a single API call for all stocks
        df = pro.daily_basic(trade_date=trade_date, fields='ts_code,close,pct_chg')

        if df is None or df.empty:
            # Try yesterday if today's data not available yet
            yesterday = (now - datetime.timedelta(days=1)).strftime('%Y%m%d')
            df = pro.daily_basic(trade_date=yesterday, fields='ts_code,close,pct_chg')

        if df is None or df.empty:
            logging.warning("Failed to fetch stock quotes batch")
            return {}

        # Build quotes dict
        quotes = {}
        for _, row in df.iterrows():
            ts_code = row.get('ts_code', '')
            quotes[ts_code] = {
                "price": float(row['close']) if pd.notna(row.get('close')) else None,
                "change_pct": float(row['pct_chg']) if pd.notna(row.get('pct_chg')) else None
            }

        # Update cache
        _STOCK_QUOTES_CACHE["data"] = quotes
        _STOCK_QUOTES_CACHE["expires_at"] = now + datetime.timedelta(seconds=cache_duration)

        logging.info(f"Refreshed stock quotes cache with {len(quotes)} stocks, expires in {cache_duration}s")
        return quotes

    except Exception as e:
        logging.error(f"Error fetching stock quotes batch: {e}")
        return _STOCK_QUOTES_CACHE.get("data", {})  # Return stale cache if available


def get_fund_flow_rank(limit: int = 30) -> Optional[List[Dict[str, Any]]]:
    """
    Get fund flow rank data with real-time quotes.
    Returns format compatible with AkShare's stock_individual_fund_flow_rank.

    Optimized: Uses batch quote fetching with caching to avoid rate limits.
    """
    try:
        pro = get_pro_api()
        today = datetime.datetime.now().strftime('%Y%m%d')

        # Get money flow data
        df = pro.moneyflow(trade_date=today)
        if df is None or df.empty:
            # Try yesterday
            yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y%m%d')
            df = pro.moneyflow(trade_date=yesterday)

        if df is None or df.empty:
            return None

        # Get stock names
        stock_basic = pro.stock_basic(fields='ts_code,name')
        if stock_basic is not None:
            name_map = dict(zip(stock_basic['ts_code'], stock_basic['name']))
        else:
            name_map = {}

        # Sort by net main inflow
        df = df.sort_values(by='net_mf_amount', ascending=False)

        # Get top stocks' ts_codes
        top_stocks = df.head(limit)
        ts_codes = top_stocks['ts_code'].tolist()

        # Batch fetch quotes (uses cache)
        quotes = _get_stock_quotes_batch(ts_codes, today)

        results = []
        for _, row in top_stocks.iterrows():
            ts_code = row.get('ts_code', '')
            code = ts_code.split('.')[0] if '.' in ts_code else ts_code

            # Get quote data from cache
            quote = quotes.get(ts_code, {})

            results.append({
                "code": code,
                "name": name_map.get(ts_code, ''),
                "price": quote.get("price"),
                "change_pct": quote.get("change_pct"),
                "net_inflow": float(row.get('net_mf_amount', 0)) if row.get('net_mf_amount') else None,
                "net_ratio": float(row.get('net_mf_vol', 0)) if row.get('net_mf_vol') else None,
            })

        return results if results else None

    except Exception as e:
        logging.error(f"Tushare get_fund_flow_rank error: {e}")
    return None


# ============ Limit Up Pool (涨停池) ============

def get_limit_up_pool(trade_date: str = None) -> Optional[Dict[str, List[Dict[str, Any]]]]:
    """
    Get limit up pool with ladder data.
    Returns format compatible with AkShare's stock_zt_pool_em.

    Note: Requires Tushare permission level 5000+.
    """
    try:
        pro = get_pro_api()
        if trade_date is None:
            trade_date = datetime.datetime.now().strftime('%Y%m%d')

        # Try limit_list_d API
        df = pro.limit_list_d(trade_date=trade_date, limit_type='U')
        if df is None or df.empty:
            return None

        ladder = {}
        for _, row in df.iterrows():
            # Tushare uses 'up_stat' for consecutive limit up days
            lb = str(row.get('up_stat', 1))
            if lb not in ladder:
                ladder[lb] = []

            ts_code = row.get('ts_code', '')
            code = ts_code.split('.')[0] if '.' in ts_code else ts_code

            ladder[lb].append({
                "name": row.get('name', ''),
                "code": code,
                "reason": row.get('lu_desc', ''),  # Limit up description
                "industry": row.get('industry', ''),
                "time": str(row.get('first_time', ''))
            })

        return ladder if ladder else None

    except Exception as e:
        logging.error(f"Tushare get_limit_up_pool error: {e}")
    return None
