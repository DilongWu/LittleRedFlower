"""
自选股看板 — 数据接口
/api/watchlist/quotes?symbols=600519,000001,MSFT

根据 symbol 格式自动判断 A股/美股：
  - 纯数字 → A股/ETF，用东方财富 pushquot API 获取单股实时行情
  - 字母   → 美股，优先从 us_stocks 内存缓存取，兜底 yfinance
"""

import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
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


# ── 东方财富 pushquot API — 单股实时行情 ──────────────────────────────
# 替代 stock_zh_a_spot_em() 全量拉取（5000+ 只股票，2分钟，易OOM）
# 单股查询 <1 秒，支持 A 股 + ETF/基金

_EASTMONEY_PUSH_URL = "https://push2delay.eastmoney.com/api/qt/stock/get"
_EASTMONEY_UT = "fa5fd1943c7b386f172d6893dbfba10b"
_EASTMONEY_FIELDS = "f43,f44,f45,f46,f47,f48,f57,f58,f59,f116,f169,f170"


def _get_secid(symbol: str) -> str:
    """根据代码判断市场前缀：
    6 开头 → 1.（上海主板）
    0/3 开头 → 0.（深圳主板/创业板）
    5 开头 → 1.（上海 ETF）
    1 开头 → 0.（深圳 ETF）
    """
    if symbol.startswith(("6", "5")):
        return f"1.{symbol}"
    else:
        return f"0.{symbol}"


def _is_etf_symbol(symbol: str) -> bool:
    """判断是否为 ETF/基金代码（用于选择趋势数据接口）"""
    return symbol.startswith("5") or symbol.startswith("1")


def _fetch_single_quote_em(symbol: str) -> Optional[dict]:
    """东方财富单股实时行情查询。支持 A 股 + ETF/基金。"""
    secid = _get_secid(symbol)
    params = {
        "secid": secid,
        "ut": _EASTMONEY_UT,
        "fields": _EASTMONEY_FIELDS,
    }
    try:
        resp = requests.get(_EASTMONEY_PUSH_URL, params=params, timeout=5,
                            headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json().get("data")
        if not data or data.get("f43") == "-":
            return None

        # f59 = 小数位数，价格字段除以 10^f59
        # f59=2 → 股票（分→元，÷100）
        # f59=3 → ETF/基金（厘→元，÷1000）
        decimal_places = int(data.get("f59", 2))
        price_divisor = 10 ** decimal_places
        # f170（涨跌幅）始终 ÷100，单位为百分比

        raw_price = data.get("f43", 0)
        raw_high = data.get("f44", 0)
        raw_low = data.get("f45", 0)
        raw_open = data.get("f46", 0)
        raw_change = data.get("f169", 0)
        raw_change_pct = data.get("f170", 0)

        # 处理 "-" 或 None 值
        def safe_float(v, divisor=price_divisor):
            if v is None or v == "-":
                return 0.0
            return float(v) / divisor

        price = safe_float(raw_price)
        high = safe_float(raw_high)
        low = safe_float(raw_low)
        open_p = safe_float(raw_open)
        change = safe_float(raw_change)
        change_pct = float(raw_change_pct) / 100 if raw_change_pct not in (None, "-") else 0.0

        volume = int(data.get("f47", 0) or 0)  # 手
        turnover = float(data.get("f48", 0) or 0)  # 元
        name = data.get("f58", symbol)
        market_cap = float(data.get("f116", 0) or 0)

        # 格式化成交量
        if volume >= 1e8:
            vol_str = f"{volume / 1e8:.2f}亿手"
        elif volume >= 1e4:
            vol_str = f"{volume / 1e4:.1f}万手"
        else:
            vol_str = f"{volume}手"

        # 格式化成交额
        if turnover >= 1e8:
            turnover_str = f"{turnover / 1e8:.2f}亿"
        elif turnover >= 1e4:
            turnover_str = f"{turnover / 1e4:.1f}万"
        else:
            turnover_str = f"{int(turnover)}"

        # 格式化市值
        if market_cap >= 1e8:
            cap_str = f"{market_cap / 1e8:.0f}亿"
        else:
            cap_str = "N/A"

        return {
            "symbol": symbol,
            "name": name,
            "name_en": name,
            "emoji": "🇨🇳",
            "price": round(price, decimal_places),
            "change": round(change, decimal_places),
            "change_percent": round(change_pct, 2),
            "open": round(open_p, decimal_places),
            "high": round(high, decimal_places),
            "low": round(low, decimal_places),
            "close": round(price, decimal_places),
            "volume": volume,
            "volume_str": vol_str,
            "turnover_str": turnover_str,
            "market_cap": market_cap,
            "market_cap_str": cap_str,
            "trend": [],
            "market": "A",
            "currency": "CNY",
            "updated_at": datetime.now().isoformat(),
            "from_cache": False,
            "data_source": "eastmoney",
        }
    except Exception as e:
        logger.error(f"东方财富查询失败 {symbol}: {e}")
        return None


def _fetch_a_share_quotes(symbols: List[str]) -> Dict[str, dict]:
    """并发获取多只 A 股/ETF 的实时行情。
    Returns {symbol: data_dict} for each successfully fetched symbol.
    """
    results: Dict[str, dict] = {}
    if not symbols:
        return results

    # 并发查询（最多 10 线程）
    with ThreadPoolExecutor(max_workers=min(len(symbols), 10)) as executor:
        future_to_symbol = {
            executor.submit(_fetch_single_quote_em, s): s for s in symbols
        }
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                data = future.result()
                if data is not None:
                    results[symbol] = data
                else:
                    logger.warning(f"A‑share/ETF {symbol}: 东方财富返回空数据")
            except Exception as e:
                logger.error(f"A‑share/ETF {symbol} 查询异常: {e}")

    return results


# ── A‑share / ETF 趋势数据 ─────────────────────────────────────────

def _fetch_a_share_trend(symbol: str) -> List[float]:
    """Fetch recent 30‑day close prices for an A‑share or ETF (for mini trend line).

    股票用 stock_zh_a_hist()，ETF 用 fund_etf_hist_em()。
    如果第一种失败，自动 fallback 到另一种。
    """
    cache_key = f"watchlist_trend_{symbol}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    trend: List[float] = []

    try:
        import akshare as ak

        df = None
        # 根据代码前缀选择接口，失败后 fallback
        if _is_etf_symbol(symbol):
            # ETF: 先试 fund_etf_hist_em，失败再试 stock_zh_a_hist
            try:
                df = ak.fund_etf_hist_em(symbol=symbol, period="daily", adjust="qfq")
            except Exception:
                pass
            if df is None or df.empty:
                try:
                    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
                except Exception:
                    pass
        else:
            # 股票: 先试 stock_zh_a_hist，失败再试 fund_etf_hist_em
            try:
                df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
            except Exception:
                pass
            if df is None or df.empty:
                try:
                    df = ak.fund_etf_hist_em(symbol=symbol, period="daily", adjust="qfq")
                except Exception:
                    pass

        if df is not None and not df.empty:
            closes = df["收盘"].tail(30).tolist()
            trend = [round(float(c), 3) for c in closes]
            set_cache(cache_key, trend, 3600)  # cache 1 hour

    except Exception as e:
        logger.warning(f"Failed to fetch trend for {symbol}: {e}")

    return trend


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
    根据 symbol 格式自动判断 A股/ETF(纯数字)/美股(字母)，合并返回。

    A 股/ETF 用东方财富 pushquot API 单股查询（<1秒/只），不再全量拉取。

    NOTE: This is a sync def on purpose — FastAPI runs it in a thread pool,
    avoiding blocking the async event loop with slow network calls.
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

    # ── A‑shares / ETFs ──
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


# ── Stock Search (fuzzy) ─────────────────────────────────────────

_EASTMONEY_SEARCH_URL = "https://searchapi.eastmoney.com/api/suggest/get"
_EASTMONEY_SEARCH_TOKEN = "D43BF722C8E33BDC906FB84D85E326E8"

# Classify → market label mapping
_CLASSIFY_MAP = {
    "AStock": "A股",
    "Fund": "基金",
    "HK": "港股",
}


@router.get("/search")
def search_stocks(q: str = Query(..., min_length=1, max_length=20, description="搜索关键字（股票名/代码/拼音）"),
                  count: int = Query(8, ge=1, le=20)):
    """模糊搜索股票，支持中文名、拼音首字母、代码。
    使用东方财富 searchapi，返回 A 股 + 美股结果。
    """
    q = q.strip()
    if not q:
        return {"results": []}

    # Check cache first (60s TTL)
    cache_key = f"stock_search_{q}_{count}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    results = []

    try:
        resp = requests.get(
            _EASTMONEY_SEARCH_URL,
            params={
                "input": q,
                "type": "14",
                "token": _EASTMONEY_SEARCH_TOKEN,
                "count": str(count),
            },
            timeout=3,
        )
        data = resp.json()
        items = data.get("QuotationCodeTable", {}).get("Data") or []

        for item in items:
            code = item.get("Code", "")
            name = item.get("Name", "")
            classify = item.get("Classify", "")
            sec_type = item.get("SecurityTypeName", "")

            # Filter: only A-share (沪A/深A) and US stocks
            market = ""
            classify_lower = classify.lower()
            if classify == "AStock":
                market = "A股"
            elif classify_lower.startswith("usstock"):
                market = "美股"
            elif classify == "Fund":
                # Include ETFs (场内基金)
                market = "基金"
            else:
                # Skip HK, bonds, etc.
                continue

            results.append({
                "symbol": code,
                "name": name,
                "market": market,
                "type": sec_type,
            })

    except Exception as e:
        logger.error(f"Stock search failed for '{q}': {e}")

    response = {"results": results}
    set_cache(cache_key, response, 60)  # cache 60s
    return response
