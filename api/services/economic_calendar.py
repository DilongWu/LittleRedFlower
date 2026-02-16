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

        forecast = ev.get("forecast", "").strip() or None
        previous = ev.get("previous", "").strip() or None

        result.append({
            "date": event_date,
            "time": event_time,
            "country": country,
            "event": event_name,
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
                "event": event_name,
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
