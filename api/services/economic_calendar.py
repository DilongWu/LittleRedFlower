"""
Economic Calendar Service
Fetches economic calendar data from ForexFactory (via faireconomy.media).
Free, no API key required.
"""
import datetime
import logging
import requests

from api.services.cache import get_cache, set_cache

logger = logging.getLogger(__name__)

# Cache duration: 6 hours
CACHE_DURATION = 6 * 3600

# ForexFactory calendar URL (free, no API key needed)
# Only "thisweek" is available from the free feed
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

# Impact normalization
IMPACT_NORMALIZE = {
    "High": "high",
    "Medium": "medium",
    "Low": "low",
    "Holiday": "low",
    "Non-Economic": "low",
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
                # Parse ISO format: "2026-02-16T21:30:00-05:00"
                dt = datetime.datetime.fromisoformat(raw_date)
                # Convert from US Eastern to UTC+8 (China time) for display
                # ForexFactory uses ET (UTC-5), we add 13 hours for UTC+8
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

        # Clean up values (remove extra whitespace)
        forecast = ev.get("forecast", "").strip() or None
        previous = ev.get("previous", "").strip() or None

        result.append({
            "date": event_date,
            "time": event_time,
            "country": country,
            "event": event_name,
            "impact": impact,
            "actual": None,  # FF free data doesn't include actuals in advance
            "forecast": forecast,
            "previous": previous,
            "category": category,
        })

    return result


def _fetch_from_forexfactory() -> list:
    """
    Fetch economic calendar from ForexFactory via faireconomy.media.
    Free, no API key required. Only current week is available.
    """
    try:
        resp = requests.get(FF_URL, timeout=15, headers={
            "User-Agent": "LittleRedFlower/1.0"
        })
        resp.raise_for_status()
        raw = resp.json()

        if not isinstance(raw, list):
            logger.error(f"Unexpected response format from ForexFactory: {type(raw)}")
            return []

        events = _parse_ff_events(raw)
        logger.info(f"Fetched {len(events)} events from ForexFactory")
        return events

    except requests.exceptions.RequestException as e:
        logger.error(f"ForexFactory API request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Error parsing ForexFactory data: {e}")
        return []


def get_economic_calendar(week_offset: int = 0) -> dict:
    """
    Get economic calendar data with caching.

    Args:
        week_offset: 0 for this week, 1 for next week, -1 for last week

    Returns:
        Dict with 'data' list and 'last_updated' timestamp
    """
    cache_key = f"economic_calendar_week_{week_offset}"

    # Check cache
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    # Calculate date range for display
    monday, sunday = _get_week_range(week_offset)
    from_date = monday.strftime("%Y-%m-%d")
    to_date = sunday.strftime("%Y-%m-%d")

    # Only current week is supported by the free data source
    if week_offset != 0:
        result = {
            "data": [],
            "from_date": from_date,
            "to_date": to_date,
            "last_updated": datetime.datetime.now().isoformat(timespec="seconds"),
            "note": "免费数据源仅支持本周数据",
        }
        return result

    # Fetch from ForexFactory
    events = _fetch_from_forexfactory()

    if not events:
        result = {
            "data": [],
            "from_date": from_date,
            "to_date": to_date,
            "last_updated": datetime.datetime.now().isoformat(timespec="seconds"),
            "note": "暂无数据，请稍后重试",
        }
        # Cache empty result for 10 minutes
        set_cache(cache_key, result, 600)
        return result

    # Sort by date and time
    events.sort(key=lambda x: (x.get("date", ""), x.get("time", "")))

    # Filter: only keep events with medium/high impact by default
    # (but return all, let frontend filter)

    result = {
        "data": events,
        "from_date": from_date,
        "to_date": to_date,
        "last_updated": datetime.datetime.now().isoformat(timespec="seconds"),
    }

    # Cache for 6 hours
    set_cache(cache_key, result, CACHE_DURATION)
    return result
