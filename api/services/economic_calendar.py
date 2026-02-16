"""
Economic Calendar Service
Primary: ForexFactory (free, no API key)
Backup: Finnhub (requires FINNHUB_API_KEY env var)
"""
import os
import datetime
import logging
import requests

from api.services.cache import get_cache, set_cache

logger = logging.getLogger(__name__)

# Cache duration: 6 hours
CACHE_DURATION = 6 * 3600

# ForexFactory calendar URL (free, no API key needed)
FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

# Currency code → country code mapping
CURRENCY_TO_COUNTRY = {
    "USD": "US",
    "EUR": "EU",
    "GBP": "GB",
    "JPY": "JP",
    "CNY": "CN",
    "AUD": "AU",
    "CAD": "CA",
    "NZD": "NZ",
    "CHF": "CH",
    "ALL": "ALL",
}

# Impact normalization (ForexFactory)
IMPACT_NORMALIZE = {
    "High": "high",
    "Medium": "medium",
    "Low": "low",
    "Holiday": "low",
    "Non-Economic": "low",
}

# Impact mapping (Finnhub)
FINNHUB_IMPACT_MAP = {
    3: "high",
    2: "medium",
    1: "low",
}

# Category detection from event name
CATEGORY_KEYWORDS = {
    "inflation": ["CPI", "PPI", "Inflation", "PCE", "Price Index"],
    "employment": ["Employment", "Unemployment", "Payroll", "NFP", "Jobless", "Jobs", "Claimant"],
    "gdp": ["GDP", "Growth"],
    "interest_rate": ["Interest Rate", "Fed", "FOMC", "Rate Decision", "BOE", "ECB", "BOJ", "RBA", "RBNZ"],
    "trade": ["Trade Balance", "Export", "Import", "Current Account"],
    "manufacturing": ["PMI", "Manufacturing", "ISM", "Industrial Production"],
    "consumer": ["Retail Sales", "Consumer", "Confidence", "Sentiment"],
    "housing": ["Housing", "Home Sales", "Building Permits", "Existing Home"],
    "speech": ["Speaks", "Speech", "Press Conference", "Testimony", "Statement"],
}


# Common event name translations (English → Chinese)
EVENT_TRANSLATIONS = {
    # --- Inflation ---
    "CPI m/m": "CPI 月率",
    "CPI y/y": "CPI 年率",
    "Core CPI m/m": "核心CPI 月率",
    "Core CPI y/y": "核心CPI 年率",
    "PPI m/m": "PPI 月率",
    "PPI y/y": "PPI 年率",
    "Core PCE Price Index m/m": "核心PCE物价指数 月率",
    "PCE Price Index m/m": "PCE物价指数 月率",
    "PCE Price Index y/y": "PCE物价指数 年率",
    "PPI Input m/m": "PPI投入 月率",
    "PPI Input q/q": "PPI投入 季率",
    "PPI Output m/m": "PPI产出 月率",
    "PPI Output q/q": "PPI产出 季率",
    "German PPI m/m": "德国PPI 月率",
    "German Final CPI m/m": "德国CPI终值 月率",
    "French Final CPI m/m": "法国CPI终值 月率",
    "RPI y/y": "零售物价指数 年率",
    "FPI m/m": "食品物价指数 月率",
    "Cleveland Fed Inflation Expectations": "克利夫兰联储通胀预期",
    "Revised UoM Inflation Expectations": "密歇根大学通胀预期(修正)",
    "Common CPI y/y": "通用CPI 年率",
    "Median CPI y/y": "中位CPI 年率",
    "Trimmed CPI y/y": "修剪均值CPI 年率",
    "National Core CPI y/y": "全国核心CPI 年率",
    # --- Employment ---
    "Unemployment Claims": "初请失业金人数",
    "Unemployment Rate": "失业率",
    "Employment Change": "就业人数变化",
    "Claimant Count Change": "失业金申请人数变化",
    "ADP Weekly Employment Change": "ADP每周就业变化",
    "Average Earnings Index 3m/y": "平均薪资指数(3个月/年率)",
    "Wage Price Index q/q": "工资物价指数 季率",
    # --- GDP ---
    "Advance GDP q/q": "GDP初值 季率",
    "Advance GDP Price Index q/q": "GDP物价指数初值 季率",
    "Prelim GDP q/q": "GDP初值 季率",
    "Prelim GDP Price Index y/y": "GDP物价指数初值 年率",
    # --- Interest Rate / Central Bank ---
    "FOMC Meeting Minutes": "美联储会议纪要",
    "FOMC Member Barr Speaks": "美联储Barr讲话",
    "FOMC Member Bostic Speaks": "美联储Bostic讲话",
    "FOMC Member Bowman Speaks": "美联储Bowman讲话",
    "FOMC Member Daly Speaks": "美联储Daly讲话",
    "FOMC Member Goolsbee Speaks": "美联储Goolsbee讲话",
    "FOMC Member Kashkari Speaks": "美联储Kashkari讲话",
    "FOMC Member Logan Speaks": "美联储Logan讲话",
    "ECB President Lagarde Speaks": "欧央行行长拉加德讲话",
    "ECB Economic Bulletin": "欧央行经济公报",
    "Official Cash Rate": "官方现金利率",
    "RBNZ Monetary Policy Statement": "新西兰联储货币政策声明",
    "RBNZ Rate Statement": "新西兰联储利率声明",
    "RBNZ Press Conference": "新西兰联储新闻发布会",
    "RBNZ Gov Breman Speaks": "新西兰联储主席讲话",
    "Monetary Policy Meeting Minutes": "货币政策会议纪要",
    "German Buba Monthly Report": "德国央行月报",
    "German Buba President Nagel Speaks": "德国央行行长Nagel讲话",
    # --- Trade ---
    "Trade Balance": "贸易帐",
    "Current Account": "经常帐",
    "Goods Trade Balance": "商品贸易帐",
    "Italian Trade Balance": "意大利贸易帐",
    "Foreign Securities Purchases": "海外证券购买",
    "TIC Long-Term Purchases": "TIC长期资本净流入",
    # --- Manufacturing ---
    "Flash Manufacturing PMI": "制造业PMI初值",
    "Flash Services PMI": "服务业PMI初值",
    "Empire State Manufacturing Index": "纽约联储制造业指数",
    "Philly Fed Manufacturing Index": "费城联储制造业指数",
    "Industrial Production m/m": "工业产出 月率",
    "Revised Industrial Production m/m": "工业产出(修正) 月率",
    "German Flash Manufacturing PMI": "德国制造业PMI初值",
    "German Flash Services PMI": "德国服务业PMI初值",
    "French Flash Manufacturing PMI": "法国制造业PMI初值",
    "French Flash Services PMI": "法国服务业PMI初值",
    "Capacity Utilization Rate": "产能利用率",
    "Manufacturing Sales m/m": "制造业销售 月率",
    "Tertiary Industry Activity m/m": "第三产业活动指数 月率",
    "Core Machinery Orders m/m": "核心机械订单 月率",
    # --- Consumer ---
    "Retail Sales m/m": "零售销售 月率",
    "Core Retail Sales m/m": "核心零售销售 月率",
    "Consumer Confidence": "消费者信心指数",
    "Revised UoM Consumer Sentiment": "密歇根大学消费者信心(修正)",
    "Personal Income m/m": "个人收入 月率",
    "Personal Spending m/m": "个人支出 月率",
    "CB Leading Index m/m": "谘商会领先指标 月率",
    "GDT Price Index": "全球乳制品价格指数",
    "BusinessNZ Services Index": "新西兰商业服务指数",
    "MI Leading Index m/m": "墨尔本先行指标 月率",
    "CBI Industrial Order Expectations": "英国工业订单预期",
    "NAB Quarterly Business Confidence": "澳洲NAB季度商业信心",
    "Wholesale Sales m/m": "批发销售 月率",
    # --- Housing ---
    "Building Permits": "营建许可",
    "Housing Starts": "新屋开工",
    "New Home Sales": "新屋销售",
    "Pending Home Sales m/m": "成屋签约销售 月率",
    "NAHB Housing Market Index": "NAHB房产市场指数",
    "HPI y/y": "房价指数 年率",
    "NHPI m/m": "新屋价格指数 月率",
    "Rightmove HPI m/m": "Rightmove房价指数 月率",
    # --- Durable Goods ---
    "Durable Goods Orders m/m": "耐用品订单 月率",
    "Core Durable Goods Orders m/m": "核心耐用品订单 月率",
    "Prelim Wholesale Inventories m/m": "批发库存初值 月率",
    # --- Energy ---
    "Crude Oil Inventories": "EIA原油库存",
    "Natural Gas Storage": "天然气库存",
    # --- Bond Auction ---
    "German 10-y Bond Auction": "德国10年期国债拍卖",
    "Spanish 10-y Bond Auction": "西班牙10年期国债拍卖",
    # --- Other ---
    "Bank Holiday": "银行假日",
    "ECOFIN Meetings": "欧盟财长会议",
    "Eurogroup Meetings": "欧元集团会议",
    "German ZEW Economic Sentiment": "德国ZEW经济景气指数",
    "ZEW Economic Sentiment": "ZEW经济景气指数",
    "Public Sector Net Borrowing": "公共部门净借款",
    "API Weekly Statistical Bulletin": "API每周统计公报",
    "IPPI m/m": "工业品价格指数 月率",
    "RMPI m/m": "原材料价格指数 月率",
}

# Country name translations
COUNTRY_NAMES = {
    "US": "🇺🇸 美国",
    "EU": "🇪🇺 欧元区",
    "GB": "🇬🇧 英国",
    "JP": "🇯🇵 日本",
    "CN": "🇨🇳 中国",
    "AU": "🇦🇺 澳大利亚",
    "CA": "🇨🇦 加拿大",
    "NZ": "🇳🇿 新西兰",
    "CH": "🇨🇭 瑞士",
    "DE": "🇩🇪 德国",
    "FR": "🇫🇷 法国",
    "IT": "🇮🇹 意大利",
    "ES": "🇪🇸 西班牙",
}


def _translate_event(event_name: str) -> str:
    """Translate event name to Chinese. Falls back to original if not found."""
    return EVENT_TRANSLATIONS.get(event_name, event_name)


def _detect_category(event_name: str) -> str:
    """Detect category from event name."""
    if not event_name:
        return "other"
    upper = event_name.upper()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.upper() in upper:
                return category
    return "other"


def _get_week_range(week_offset: int = 0):
    """Get Monday-Sunday range for current/next/last week."""
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(weeks=week_offset)
    sunday = monday + datetime.timedelta(days=6)
    return monday, sunday


def _parse_ff_events(raw_events: list) -> list:
    """Parse ForexFactory JSON events into our format."""
    result = []
    for ev in raw_events:
        raw_date = ev.get("date", "")
        event_date = ""
        event_time = ""

        if raw_date:
            try:
                dt = datetime.datetime.fromisoformat(raw_date)
                # Convert from US Eastern to UTC+8 (China time)
                dt_cn = dt + datetime.timedelta(hours=13)
                event_date = dt_cn.strftime("%Y-%m-%d")
                event_time = dt_cn.strftime("%H:%M")
            except (ValueError, TypeError):
                event_date = raw_date[:10] if len(raw_date) >= 10 else raw_date

        country_code = ev.get("country", "")
        country = CURRENCY_TO_COUNTRY.get(country_code, country_code)

        impact_raw = ev.get("impact", "Low")
        impact = IMPACT_NORMALIZE.get(impact_raw, "low")

        event_name = ev.get("title", "")
        category = _detect_category(event_name)
        event_name_cn = _translate_event(event_name)

        forecast = ev.get("forecast", "").strip() or None
        previous = ev.get("previous", "").strip() or None

        result.append({
            "date": event_date,
            "time": event_time,
            "country": country,
            "event": event_name_cn,
            "impact": impact,
            "actual": None,
            "forecast": forecast,
            "previous": previous,
            "category": category,
        })

    return result


def _fetch_from_forexfactory() -> list:
    """
    Fetch from ForexFactory (primary). Free, no API key.
    Only current week available.
    """
    try:
        resp = requests.get(FF_URL, timeout=15, headers={
            "User-Agent": "LittleRedFlower/1.0"
        })
        resp.raise_for_status()
        raw = resp.json()

        if not isinstance(raw, list):
            logger.error(f"Unexpected FF response format: {type(raw)}")
            return []

        events = _parse_ff_events(raw)
        logger.info(f"Fetched {len(events)} events from ForexFactory (primary)")
        return events

    except requests.exceptions.RequestException as e:
        logger.error(f"ForexFactory failed: {e}")
        return []
    except Exception as e:
        logger.error(f"ForexFactory parse error: {e}")
        return []


def _fetch_from_finnhub(from_date: str, to_date: str) -> list:
    """
    Fetch from Finnhub (backup). Requires FINNHUB_API_KEY env var.
    """
    api_key = os.getenv("FINNHUB_API_KEY", "")
    if not api_key:
        logger.warning("FINNHUB_API_KEY not set, backup unavailable")
        return []

    try:
        resp = requests.get(
            "https://finnhub.io/api/v1/calendar/economic",
            params={"from": from_date, "to": to_date, "token": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        events = []
        for ev in data.get("economicCalendar", []):
            raw_time = ev.get("time", "")
            event_date = raw_time[:10] if raw_time and len(raw_time) >= 10 else ""
            event_time = ""
            if raw_time and "T" in raw_time:
                # Finnhub times are UTC, convert to UTC+8
                try:
                    dt = datetime.datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                    dt_cn = dt + datetime.timedelta(hours=8)
                    event_date = dt_cn.strftime("%Y-%m-%d")
                    event_time = dt_cn.strftime("%H:%M")
                except (ValueError, TypeError):
                    event_time = raw_time.split("T")[1][:5] if "T" in raw_time else ""

            actual = ev.get("actual")
            forecast = ev.get("estimate")
            previous = ev.get("prev")
            unit = ev.get("unit", "")

            def _fmt(val):
                if val is None:
                    return None
                return f"{val}%" if unit == "%" else str(val)

            impact = FINNHUB_IMPACT_MAP.get(ev.get("impact", 1), "low")
            country = ev.get("country", "")
            event_name = ev.get("event", "")

            events.append({
                "date": event_date,
                "time": event_time,
                "country": country,
                "event": _translate_event(event_name),
                "impact": impact,
                "actual": _fmt(actual),
                "forecast": _fmt(forecast),
                "previous": _fmt(previous),
                "category": _detect_category(event_name),
            })

        logger.info(f"Fetched {len(events)} events from Finnhub (backup)")
        return events

    except requests.exceptions.RequestException as e:
        logger.error(f"Finnhub failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Finnhub parse error: {e}")
        return []


def get_economic_calendar(week_offset: int = 0) -> dict:
    """
    Get economic calendar with caching.
    Primary: ForexFactory | Backup: Finnhub
    """
    cache_key = f"economic_calendar_week_{week_offset}"

    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    monday, sunday = _get_week_range(week_offset)
    from_date = monday.strftime("%Y-%m-%d")
    to_date = sunday.strftime("%Y-%m-%d")

    # Non-current week: only Finnhub supports it
    if week_offset != 0:
        events = _fetch_from_finnhub(from_date, to_date)
        if not events:
            result = {
                "data": [],
                "from_date": from_date,
                "to_date": to_date,
                "last_updated": datetime.datetime.now().isoformat(timespec="seconds"),
                "note": "仅支持本周数据" if not os.getenv("FINNHUB_API_KEY") else "暂无数据，请稍后重试",
            }
            return result
    else:
        # Try ForexFactory first, fallback to Finnhub
        events = _fetch_from_forexfactory()
        source = "ForexFactory"

        if not events:
            logger.warning("ForexFactory failed, falling back to Finnhub")
            events = _fetch_from_finnhub(from_date, to_date)
            source = "Finnhub"

        if not events:
            result = {
                "data": [],
                "from_date": from_date,
                "to_date": to_date,
                "last_updated": datetime.datetime.now().isoformat(timespec="seconds"),
                "note": "暂无数据，请稍后重试",
            }
            set_cache(cache_key, result, 600)
            return result

    events.sort(key=lambda x: (x.get("date", ""), x.get("time", "")))

    result = {
        "data": events,
        "from_date": from_date,
        "to_date": to_date,
        "last_updated": datetime.datetime.now().isoformat(timespec="seconds"),
    }

    set_cache(cache_key, result, CACHE_DURATION)
    return result
