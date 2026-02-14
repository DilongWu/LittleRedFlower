"""
自选股看板 — 数据接口
/api/watchlist/quotes?symbols=600519,000001,MSFT

根据 symbol 格式自动判断 A股/美股：
  - 纯数字 → A股，用 AkShare 获取实时行情
  - 字母   → 美股，优先从 us_stocks 内存缓存取，兜底 yfinance
"""

import re
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime

from fastapi import APIRouter, Query, HTTPException

from api.services.cache import get_cache, set_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

# ── helpers ────────────────────────────────────────────────────────

_SYMBOL_IS_A_SHARE = re.compile(r"^\d{6}$")
_SYMBOL_VALID = re.compile(r"^[A-Z0-9]{1,10}$")
_MAX_SYMBOLS = 50


def _is_a_share(symbol: str) -> bool:
    return bool(_SYMBOL_IS_A_SHARE.match(symbol))


# ── A‑share batch DataFrame cache ─────────────────────────────────
# stock_zh_a_spot_em() returns ALL A-shares (~5000 rows) and takes
# ~2 minutes.  We cache the whole DataFrame in memory for 5 minutes
# so that multiple requests / symbols share a single fetch.

_a_share_spot_cache: Dict[str, object] = {}  # {"df": DataFrame, "ts": float}
_A_SHARE_SPOT_TTL = 300  # 5 minutes


def _get_a_share_spot_df():
    """Return cached or freshly-fetched A-share spot DataFrame."""
    now = time.time()
    if (
        _a_share_spot_cache.get("df") is not None
        and now - _a_share_spot_cache.get("ts", 0) < _A_SHARE_SPOT_TTL
    ):
        return _a_share_spot_cache["df"]

    import akshare as ak
    df = ak.stock_zh_a_spot_em()
    if df is not None and not df.empty:
        _a_share_spot_cache["df"] = df
        _a_share_spot_cache["ts"] = now
    return df


# ── A‑share real‑time quotes via AkShare ───────────────────────────

def _fetch_a_share_quotes(symbols: List[str]) -> Dict[str, dict]:
    """Fetch A‑share real‑time quotes via akshare.
    Returns {symbol: data_dict} for each requested symbol.
    Uses stock_zh_a_spot_em (东方财富实时行情) which returns all A-shares at once.
    """
    results: Dict[str, dict] = {}

    try:
        df = _get_a_share_spot_df()

        if df is None or df.empty:
            logger.warning("AkShare stock_zh_a_spot_em returned empty")
            return results

        # Build a lookup by symbol code (代码)
        df_indexed = df.set_index("代码")

        for symbol in symbols:
            try:
                if symbol not in df_indexed.index:
                    logger.warning(f"A‑share {symbol} not found in spot data")
                    continue

                row = df_indexed.loc[symbol]

                price = float(row.get("最新价", 0) or 0)
                change = float(row.get("涨跌额", 0) or 0)
                change_pct = float(row.get("涨跌幅", 0) or 0)
                volume = float(row.get("成交量", 0) or 0)
                open_p = float(row.get("今开", 0) or 0)
                high = float(row.get("最高", 0) or 0)
                low = float(row.get("最低", 0) or 0)
                name = str(row.get("名称", symbol))
                turnover = float(row.get("成交额", 0) or 0)

                # Volume string
                if volume >= 1e8:
                    vol_str = f"{volume / 1e8:.2f}亿手"
                elif volume >= 1e4:
                    vol_str = f"{volume / 1e4:.1f}万手"
                else:
                    vol_str = f"{int(volume)}手"

                # Turnover string (成交额 in yuan)
                if turnover >= 1e8:
                    turnover_str = f"{turnover / 1e8:.2f}亿"
                elif turnover >= 1e4:
                    turnover_str = f"{turnover / 1e4:.1f}万"
                else:
                    turnover_str = f"{int(turnover)}"

                results[symbol] = {
                    "symbol": symbol,
                    "name": name,
                    "name_en": name,
                    "emoji": "🇨🇳",
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_pct, 2),
                    "open": round(open_p, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(price, 2),
                    "volume": int(volume),
                    "volume_str": vol_str,
                    "turnover_str": turnover_str,
                    "trend": [],  # Will try to fill from history
                    "market_cap": 0,
                    "market_cap_str": "N/A",
                    "market": "A",
                    "currency": "CNY",
                    "updated_at": datetime.now().isoformat(),
                    "from_cache": False,
                    "data_source": "akshare",
                }

            except Exception as e:
                logger.error(f"Error parsing A‑share {symbol}: {e}")

    except Exception as e:
        logger.error(f"AkShare batch fetch failed: {e}")

    return results


def _fetch_a_share_trend(symbol: str) -> List[float]:
    """Fetch recent 30‑day close prices for an A‑share (for mini trend line)."""
    cache_key = f"watchlist_trend_{symbol}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    try:
        import akshare as ak
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
        if df is not None and not df.empty:
            closes = df["收盘"].tail(30).tolist()
            trend = [round(float(c), 2) for c in closes]
            set_cache(cache_key, trend, 3600)  # cache 1 hour
            return trend
    except Exception as e:
        logger.warning(f"Failed to fetch A‑share trend for {symbol}: {e}")
    return []


# ── US‑stock quotes ────────────────────────────────────────────────

def _fetch_us_stock_quotes(symbols: List[str]) -> Dict[str, dict]:
    """Fetch US stock quotes. Prefer in‑memory cache from us_stocks service,
    fall back to yfinance single‑ticker fetch."""
    results: Dict[str, dict] = {}

    # 1. Try existing us_stocks memory cache first
    try:
        from api.services.us_stocks import _memory_cache as us_cache, US_TECH_STOCKS
        for symbol in symbols:
            if symbol in us_cache:
                cached_data, cache_time = us_cache[symbol]
                # Accept if <2h old
                from datetime import timedelta
                if datetime.now() - cache_time < timedelta(seconds=7200):
                    data = dict(cached_data)
                    data["from_cache"] = True
                    data["market"] = "US"
                    data["currency"] = "USD"
                    results[symbol] = data
    except Exception as e:
        logger.warning(f"Failed to read us_stocks cache: {e}")

    # 2. Remaining symbols: fetch via yfinance
    remaining = [s for s in symbols if s not in results]
    if not remaining:
        return results

    try:
        import yfinance as yf
        for symbol in remaining:
            cache_key = f"watchlist_quote_{symbol}"
            cached = get_cache(cache_key)
            if cached is not None:
                results[symbol] = cached
                continue

            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="30d", timeout=10)
                if hist.empty or len(hist) < 2:
                    continue

                latest = hist.iloc[-1]
                prev = hist.iloc[-2]
                current_price = float(latest["Close"])
                prev_close = float(prev["Close"])
                change = current_price - prev_close
                change_pct = (change / prev_close) * 100
                trend = [round(float(p), 2) for p in hist["Close"].tolist()[-30:]]

                vol = int(latest["Volume"])
                if vol >= 1e6:
                    vol_str = f"{vol / 1e6:.1f}M"
                elif vol >= 1e3:
                    vol_str = f"{vol / 1e3:.0f}K"
                else:
                    vol_str = str(vol)

                data = {
                    "symbol": symbol,
                    "name": symbol,
                    "name_en": symbol,
                    "emoji": "🇺🇸",
                    "price": round(current_price, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_pct, 2),
                    "open": round(float(latest["Open"]), 2),
                    "high": round(float(latest["High"]), 2),
                    "low": round(float(latest["Low"]), 2),
                    "close": round(current_price, 2),
                    "volume": vol,
                    "volume_str": vol_str,
                    "trend": trend,
                    "market_cap": 0,
                    "market_cap_str": "N/A",
                    "market": "US",
                    "currency": "USD",
                    "updated_at": datetime.now().isoformat(),
                    "from_cache": False,
                    "data_source": "yfinance",
                }

                # Try to get name from US_TECH_STOCKS registry
                try:
                    from api.services.us_stocks import US_TECH_STOCKS
                    if symbol in US_TECH_STOCKS:
                        info = US_TECH_STOCKS[symbol]
                        data["name"] = info["name"]
                        data["name_en"] = info["name_en"]
                        data["emoji"] = info.get("emoji", "🇺🇸")
                except Exception:
                    pass

                set_cache(cache_key, data, 600)  # cache 10 min
                results[symbol] = data

            except Exception as e:
                logger.error(f"yfinance fetch failed for {symbol}: {e}")

    except ImportError:
        logger.error("yfinance not installed")

    return results


# ── Route ──────────────────────────────────────────────────────────

@router.get("/quotes")
def get_watchlist_quotes(symbols: str = Query(..., description="Comma‑separated stock symbols, e.g. 600519,MSFT,AAPL")):
    """
    统一自选股报价接口。
    根据 symbol 格式自动判断 A股(纯数字)/美股(字母)，合并返回。

    NOTE: This is a sync def on purpose — FastAPI runs it in a thread pool,
    avoiding blocking the async event loop with slow AkShare / yfinance calls.
    """
    raw_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]

    # ── Input validation ──
    symbol_list = []
    invalid: List[str] = []
    for s in raw_list:
        if _SYMBOL_VALID.match(s):
            if s not in symbol_list:        # deduplicate
                symbol_list.append(s)
        else:
            invalid.append(s)

    if not symbol_list:
        return {"quotes": {}, "errors": invalid}

    if len(symbol_list) > _MAX_SYMBOLS:
        raise HTTPException(
            status_code=400,
            detail=f"Too many symbols (max {_MAX_SYMBOLS}). Got {len(symbol_list)}.",
        )

    a_shares = [s for s in symbol_list if _is_a_share(s)]
    us_shares = [s for s in symbol_list if not _is_a_share(s)]

    all_quotes: Dict[str, dict] = {}
    errors: List[str] = list(invalid)

    # ── A‑shares ──
    if a_shares:
        # Check per-symbol cache first
        uncached_a = []
        for s in a_shares:
            cache_key = f"watchlist_quote_{s}"
            cached = get_cache(cache_key)
            if cached is not None:
                all_quotes[s] = cached
            else:
                uncached_a.append(s)

        if uncached_a:
            a_data = _fetch_a_share_quotes(uncached_a)
            for s in uncached_a:
                if s in a_data:
                    set_cache(f"watchlist_quote_{s}", a_data[s], 300)  # 5 min
                    all_quotes[s] = a_data[s]
                else:
                    errors.append(s)

    # ── US shares ──
    if us_shares:
        us_data = _fetch_us_stock_quotes(us_shares)
        for s in us_shares:
            if s in us_data:
                all_quotes[s] = us_data[s]
            else:
                errors.append(s)

    return {
        "quotes": all_quotes,
        "errors": errors,
        "updated_at": datetime.now().isoformat(),
    }


@router.get("/trend")
def get_watchlist_trend(symbol: str = Query(..., description="Single stock symbol")):
    """获取单个 symbol 的趋势数据（30天收盘价），用于延迟加载迷你趋势图。"""
    symbol = symbol.strip().upper()
    if not _SYMBOL_VALID.match(symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol")

    if _is_a_share(symbol):
        trend = _fetch_a_share_trend(symbol)
    else:
        # 美股趋势已在 quotes 中包含，但也可单独获取
        cache_key = f"watchlist_trend_{symbol}"
        cached = get_cache(cache_key)
        if cached is not None:
            return {"symbol": symbol, "trend": cached}
        try:
            import yfinance as yf
            hist = yf.Ticker(symbol).history(period="30d", timeout=10)
            trend = [round(float(p), 2) for p in hist["Close"].tolist()[-30:]] if not hist.empty else []
            set_cache(cache_key, trend, 3600)
        except Exception:
            trend = []

    return {"symbol": symbol, "trend": trend}
