"""
US Tech Stocks Data Service
使用Yahoo Finance获取美股科技巨头数据
性能优化：
1. 并发获取数据（ThreadPoolExecutor）
2. 数据缓存机制（1小时过期）
3. 异常隔离（单股票失败不影响整体）
4. 超时控制和降级策略
"""

import yfinance as yf
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import logging
import time

logger = logging.getLogger(__name__)

# 追踪的9只科技巨头（FAAMG + 其他龙头）
US_TECH_STOCKS = {
    "AAPL": {"name": "苹果", "name_en": "Apple", "emoji": "🍎"},
    "MSFT": {"name": "微软", "name_en": "Microsoft", "emoji": "Ⓜ️"},
    "GOOGL": {"name": "谷歌", "name_en": "Alphabet", "emoji": "🔍"},
    "AMZN": {"name": "亚马逊", "name_en": "Amazon", "emoji": "🛒"},
    "META": {"name": "Meta", "name_en": "Meta Platforms", "emoji": "📘"},
    "NVDA": {"name": "英伟达", "name_en": "NVIDIA", "emoji": "💻"},
    "TSLA": {"name": "特斯拉", "name_en": "Tesla", "emoji": "⚡"},
    "NFLX": {"name": "奈飞", "name_en": "Netflix", "emoji": "🎬"},
    "AMD": {"name": "AMD", "name_en": "AMD", "emoji": "🔧"}
}

# 缓存配置
CACHE_DURATION = 3600  # 1小时缓存
_memory_cache = {}  # 内存缓存

# 市值独立缓存（24小时有效，市值变化不大）
_market_cap_cache = {}  # {symbol: (market_cap_value, timestamp)}
_MARKET_CAP_CACHE_DURATION = 86400  # 24 hours


def get_stock_data(symbol: str, use_cache: bool = True) -> Optional[Dict]:
    """
    获取单只股票数据（带缓存和容错）
    Args:
        symbol: 股票代码
        use_cache: 是否使用缓存（默认True）
    """
    # 检查内存缓存
    if use_cache and symbol in _memory_cache:
        cache_data, cache_time = _memory_cache[symbol]
        if datetime.now() - cache_time < timedelta(seconds=CACHE_DURATION):
            logger.info(f"{symbol} 使用缓存数据")
            cache_data['from_cache'] = True
            return cache_data

    try:
        logger.info(f"开始获取 {symbol} 数据...")
        start_time = time.time()

        ticker = yf.Ticker(symbol)

        # 获取历史数据（最近30天），设置超时
        hist = ticker.history(period="30d", timeout=10)

        if hist.empty:
            logger.warning(f"{symbol} 历史数据为空")
            return _get_cached_or_error(symbol)

        # 最新和前一交易日数据
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest

        # 计算涨跌
        current_price = latest['Close']
        prev_close = prev['Close']
        change = current_price - prev_close
        change_percent = (change / prev_close) * 100

        # 趋势数据（最近30天收盘价）
        trend_data = hist['Close'].tolist()

        stock_info = US_TECH_STOCKS.get(symbol, {"name": symbol, "name_en": symbol, "emoji": "📊"})

        # 获取额外信息（使用快速方法，避免慢速API调用）
        try:
            info = ticker.fast_info  # 使用fast_info代替info（更快）
            market_cap = info.last_price * info.shares if hasattr(info, 'shares') else 0
        except:
            # 降级到普通info
            try:
                info_dict = ticker.info
                market_cap = info_dict.get('marketCap', 0)
            except:
                market_cap = 0

        elapsed = time.time() - start_time
        logger.info(f"{symbol} 数据获取完成，耗时 {elapsed:.2f}秒")

        result = {
            "symbol": symbol,
            "name": stock_info["name"],
            "name_en": stock_info["name_en"],
            "emoji": stock_info.get("emoji", "📊"),
            "price": round(current_price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "open": round(latest['Open'], 2),
            "high": round(latest['High'], 2),
            "low": round(latest['Low'], 2),
            "close": round(latest['Close'], 2),
            "volume": int(latest['Volume']),
            "volume_str": f"{int(latest['Volume']/1000000)}M" if latest['Volume'] > 1000000 else f"{int(latest['Volume']/1000)}K",
            "trend": [round(p, 2) for p in trend_data[-30:]],
            "market_cap": market_cap,
            "market_cap_str": _format_market_cap(market_cap),
            "updated_at": datetime.now().isoformat(),
            "from_cache": False,
            "data_source": "yahoo_finance"
        }

        # 存入缓存
        _memory_cache[symbol] = (result, datetime.now())

        return result

    except Exception as e:
        logger.error(f"{symbol} 获取数据失败: {e}")
        return _get_cached_or_error(symbol)


def _get_cached_or_error(symbol: str) -> Optional[Dict]:
    """获取缓存数据或返回错误占位符"""
    # 尝试从缓存获取（即使过期）
    if symbol in _memory_cache:
        cache_data, _ = _memory_cache[symbol]
        cache_data['from_cache'] = True
        cache_data['is_stale'] = True
        logger.warning(f"{symbol} 使用过期缓存数据")
        return cache_data

    # 返回错误占位符
    stock_info = US_TECH_STOCKS.get(symbol, {"name": symbol, "name_en": symbol, "emoji": "❌"})
    return {
        "symbol": symbol,
        "name": stock_info["name"],
        "name_en": stock_info["name_en"],
        "emoji": stock_info.get("emoji", "❌"),
        "error": "数据获取失败",
        "data_source": "error"
    }


def _format_market_cap(market_cap: float) -> str:
    """格式化市值显示"""
    if market_cap >= 1e12:
        return f"${round(market_cap/1e12, 2)}T"
    elif market_cap >= 1e9:
        return f"${round(market_cap/1e9, 2)}B"
    elif market_cap >= 1e6:
        return f"${round(market_cap/1e6, 2)}M"
    else:
        return "N/A"


def get_us_tech_overview(use_cache: bool = True, max_workers: int = 5) -> Dict:
    """
    获取所有科技股的概览数据（批量下载优化）
    Args:
        use_cache: 是否使用缓存
        max_workers: 最大并发线程数（用于获取 market_cap 等补充数据）
    """
    logger.info(f"开始获取美股科技股数据...")
    start_time = time.time()

    stocks_data = []
    symbols = list(US_TECH_STOCKS.keys())

    # Check if all symbols are cached
    if use_cache:
        all_cached = True
        for symbol in symbols:
            if symbol not in _memory_cache:
                all_cached = False
                break
            cache_data, cache_time = _memory_cache[symbol]
            if datetime.now() - cache_time >= timedelta(seconds=CACHE_DURATION):
                all_cached = False
                break

        if all_cached:
            logger.info("所有股票均命中缓存")
            for symbol in symbols:
                cache_data, _ = _memory_cache[symbol]
                cache_data_copy = dict(cache_data)
                cache_data_copy['from_cache'] = True
                stocks_data.append(cache_data_copy)
            return _build_overview_result(stocks_data, start_time)

    # Batch download all tickers at once (single request to yfinance)
    try:
        logger.info(f"批量下载 {len(symbols)} 只股票数据...")
        tickers_str = " ".join(symbols)
        hist_data = yf.download(tickers_str, period="30d", group_by="ticker", threads=True, timeout=20)

        if hist_data is not None and not hist_data.empty:
            for symbol in symbols:
                try:
                    # Extract per-symbol data from the batch result
                    if len(symbols) > 1:
                        sym_hist = hist_data[symbol].dropna(how='all')
                    else:
                        sym_hist = hist_data.dropna(how='all')

                    if sym_hist.empty or len(sym_hist) < 2:
                        logger.warning(f"{symbol} 批量下载数据不足")
                        stocks_data.append(_get_cached_or_error(symbol))
                        continue

                    latest = sym_hist.iloc[-1]
                    prev = sym_hist.iloc[-2]

                    current_price = float(latest['Close'])
                    prev_close = float(prev['Close'])
                    change = current_price - prev_close
                    change_percent = (change / prev_close) * 100

                    trend_data = sym_hist['Close'].tolist()

                    stock_info = US_TECH_STOCKS.get(symbol, {"name": symbol, "name_en": symbol, "emoji": "📊"})

                    result = {
                        "symbol": symbol,
                        "name": stock_info["name"],
                        "name_en": stock_info["name_en"],
                        "emoji": stock_info.get("emoji", "📊"),
                        "price": round(current_price, 2),
                        "change": round(change, 2),
                        "change_percent": round(change_percent, 2),
                        "open": round(float(latest['Open']), 2),
                        "high": round(float(latest['High']), 2),
                        "low": round(float(latest['Low']), 2),
                        "close": round(float(latest['Close']), 2),
                        "volume": int(latest['Volume']),
                        "volume_str": f"{int(latest['Volume']/1000000)}M" if latest['Volume'] > 1000000 else f"{int(latest['Volume']/1000)}K",
                        "trend": [round(float(p), 2) for p in trend_data[-30:]],
                        "market_cap": 0,
                        "market_cap_str": "N/A",
                        "updated_at": datetime.now().isoformat(),
                        "from_cache": False,
                        "data_source": "yahoo_finance"
                    }

                    # Cache the result
                    _memory_cache[symbol] = (result, datetime.now())
                    stocks_data.append(result)

                except Exception as e:
                    logger.error(f"{symbol} 解析批量数据失败: {e}")
                    stocks_data.append(_get_cached_or_error(symbol))
        else:
            logger.warning("批量下载返回空数据，回退到逐个获取")
            raise Exception("Batch download returned empty data")

    except Exception as e:
        logger.warning(f"批量下载失败: {e}，回退到逐个获取")
        # Fallback: fetch individually with ThreadPoolExecutor
        stocks_data = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(get_stock_data, symbol, use_cache): symbol
                for symbol in symbols
            }
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    data = future.result(timeout=15)
                    if data:
                        stocks_data.append(data)
                except Exception as ex:
                    logger.error(f"{symbol} 获取异常: {ex}")
                    stocks_data.append(_get_cached_or_error(symbol))

    # Try to enrich market_cap in background (non-critical)
    try:
        _enrich_market_caps(stocks_data, max_workers)
    except Exception as e:
        logger.warning(f"市值数据补充失败（不影响主数据）: {e}")

    return _build_overview_result(stocks_data, start_time)


def _enrich_market_caps(stocks_data: List[Dict], max_workers: int = 3):
    """Enrich stocks with market cap data (best effort, won't fail the main flow).
    Uses a dedicated 24-hour cache to avoid redundant API calls."""
    now_ts = time.time()
    symbols_needing_cap = []

    for s in stocks_data:
        if 'error' in s:
            continue
        sym = s['symbol']
        # Check dedicated market_cap cache first
        if sym in _market_cap_cache:
            cached_cap, cached_ts = _market_cap_cache[sym]
            if now_ts - cached_ts < _MARKET_CAP_CACHE_DURATION:
                s['market_cap'] = cached_cap
                s['market_cap_str'] = _format_market_cap(cached_cap)
                # Also update main cache
                if sym in _memory_cache:
                    cached, ts = _memory_cache[sym]
                    cached['market_cap'] = cached_cap
                    cached['market_cap_str'] = s['market_cap_str']
                continue
        if s.get('market_cap', 0) == 0:
            symbols_needing_cap.append(s)

    if not symbols_needing_cap:
        return

    def fetch_cap(stock):
        try:
            ticker = yf.Ticker(stock['symbol'])
            info = ticker.fast_info
            market_cap = info.last_price * info.shares if hasattr(info, 'shares') else 0
            stock['market_cap'] = market_cap
            stock['market_cap_str'] = _format_market_cap(market_cap)
            # Store in dedicated market_cap cache
            _market_cap_cache[stock['symbol']] = (market_cap, time.time())
            # Update main cache
            if stock['symbol'] in _memory_cache:
                cached, ts = _memory_cache[stock['symbol']]
                cached['market_cap'] = market_cap
                cached['market_cap_str'] = stock['market_cap_str']
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(fetch_cap, symbols_needing_cap))


def _build_overview_result(stocks_data: List[Dict], start_time: float) -> Dict:
    """Build the final overview result dict from stocks data."""
    valid_stocks = [s for s in stocks_data if 'error' not in s]

    if valid_stocks:
        avg_change = sum(s['change_percent'] for s in valid_stocks) / len(valid_stocks)
        up_count = sum(1 for s in valid_stocks if s['change_percent'] > 0)
        down_count = sum(1 for s in valid_stocks if s['change_percent'] < 0)
        flat_count = len(valid_stocks) - up_count - down_count

        top_gainer = max(valid_stocks, key=lambda x: x['change_percent'])
        top_loser = min(valid_stocks, key=lambda x: x['change_percent'])
    else:
        avg_change = 0
        up_count = 0
        down_count = 0
        flat_count = 0
        top_gainer = None
        top_loser = None

    elapsed_time = time.time() - start_time
    logger.info(f"美股数据获取完成，成功 {len(valid_stocks)}/{len(US_TECH_STOCKS)}，耗时 {elapsed_time:.2f}秒")

    return {
        "stocks": stocks_data,
        "summary": {
            "total": len(stocks_data),
            "success": len(valid_stocks),
            "up": up_count,
            "down": down_count,
            "flat": flat_count,
            "avg_change": round(avg_change, 2),
            "top_gainer": {
                "symbol": top_gainer['symbol'],
                "name": top_gainer['name'],
                "change_percent": top_gainer['change_percent']
            } if top_gainer else None,
            "top_loser": {
                "symbol": top_loser['symbol'],
                "name": top_loser['name'],
                "change_percent": top_loser['change_percent']
            } if top_loser else None
        },
        "updated_at": datetime.now().isoformat(),
        "elapsed_time": round(elapsed_time, 2)
    }


def save_us_tech_data(data: Dict):
    """保存美股数据到文件"""
    try:
        # 获取storage目录
        storage_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage")
        os.makedirs(storage_dir, exist_ok=True)

        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"{today}_us_tech.json"
        filepath = os.path.join(storage_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"US tech data saved to {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error saving US tech data: {e}")
        return False


def load_us_tech_data(date: Optional[str] = None) -> Optional[Dict]:
    """从文件加载美股数据"""
    try:
        storage_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage")

        # 如果没有指定日期，使用今天
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        filename = f"{date}_us_tech.json"
        filepath = os.path.join(storage_dir, filename)

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)

        logger.warning(f"US tech data file not found: {filepath}")
        return None
    except Exception as e:
        logger.error(f"Error loading US tech data: {e}")
        return None


def clear_cache():
    """清空内存缓存"""
    global _memory_cache
    _memory_cache = {}
    logger.info("美股数据缓存已清空")


def get_cache_stats() -> Dict:
    """获取缓存统计信息"""
    now = datetime.now()
    stats = {
        "total_cached": len(_memory_cache),
        "cached_symbols": list(_memory_cache.keys()),
        "cache_ages": {}
    }

    for symbol, (_, cache_time) in _memory_cache.items():
        age_seconds = (now - cache_time).total_seconds()
        stats["cache_ages"][symbol] = {
            "age_seconds": int(age_seconds),
            "is_fresh": age_seconds < CACHE_DURATION
        }

    return stats


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    data = get_us_tech_overview(use_cache=False)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    save_us_tech_data(data)
