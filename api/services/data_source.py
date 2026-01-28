"""
Data source configuration module.
Supports switching between Eastmoney (东方财富), Sina (新浪), and Tushare Pro data sources.
"""
import os
import json
import logging

# Default data source
DEFAULT_DATA_SOURCE = "eastmoney"  # "eastmoney", "sina", or "tushare"

# Valid data sources
VALID_DATA_SOURCES = ["eastmoney", "sina", "tushare"]

# Config file paths
# Data source selection config (runtime)
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_source_config.json")
# Main config file with API keys (src/config.json)
MAIN_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src", "config.json")

# Tushare token (set via environment variable or config)
_TUSHARE_TOKEN = None


def get_data_source() -> str:
    """Get the current data source setting."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                source = config.get("data_source", DEFAULT_DATA_SOURCE)
                if source in VALID_DATA_SOURCES:
                    return source
    except Exception as e:
        logging.error(f"Error reading data source config: {e}")
    return DEFAULT_DATA_SOURCE


def set_data_source(source: str) -> bool:
    """Set the data source. Returns True if successful."""
    if source not in VALID_DATA_SOURCES:
        return False

    try:
        # Read existing config
        config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)

        config["data_source"] = source
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logging.info(f"Data source changed to: {source}")
        return True
    except Exception as e:
        logging.error(f"Error saving data source config: {e}")
        return False


def get_tushare_token() -> str:
    """Get Tushare token from environment, main config (src/config.json), or data source config."""
    global _TUSHARE_TOKEN
    if _TUSHARE_TOKEN:
        return _TUSHARE_TOKEN

    # 1. Try environment variable first (highest priority)
    token = os.getenv("TUSHARE_TOKEN")
    if token:
        _TUSHARE_TOKEN = token
        return token

    # 2. Try main config file (src/config.json) - where other API keys are stored
    try:
        if os.path.exists(MAIN_CONFIG_FILE):
            with open(MAIN_CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                token = config.get("tushareToken")  # camelCase to match existing style
                if token:
                    _TUSHARE_TOKEN = token
                    return token
    except Exception as e:
        logging.error(f"Error reading main config file: {e}")

    # 3. Try data source config file (legacy/API-set location)
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                token = config.get("tushare_token")
                if token:
                    _TUSHARE_TOKEN = token
                    return token
    except Exception as e:
        logging.error(f"Error reading tushare token from data source config: {e}")

    return ""


def set_tushare_token(token: str) -> bool:
    """Save Tushare token to main config file (src/config.json)."""
    global _TUSHARE_TOKEN
    try:
        # Save to main config file
        config = {}
        if os.path.exists(MAIN_CONFIG_FILE):
            with open(MAIN_CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)

        config["tushareToken"] = token
        with open(MAIN_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        _TUSHARE_TOKEN = token
        logging.info("Tushare token saved to config.json")
        return True
    except Exception as e:
        logging.error(f"Error saving tushare token: {e}")
        return False


def test_data_source(source: str) -> dict:
    """Test if a data source is available. Returns status dict."""
    result = {
        "source": source,
        "available": False,
        "error": None,
        "sample_data": None
    }

    try:
        if source == "tushare":
            # Test Tushare API
            token = get_tushare_token()
            if not token:
                result["error"] = "Tushare token not configured. Set TUSHARE_TOKEN env var or use /api/datasource/tushare-token"
                return result

            import tushare as ts
            ts.set_token(token)
            pro = ts.pro_api()
            df = pro.index_daily(ts_code='000001.SH', limit=1)
            if df is not None and not df.empty:
                result["available"] = True
                result["sample_data"] = f"Got index data, latest: {df.iloc[0]['close']}"

        elif source == "eastmoney":
            import akshare as ak
            df = ak.stock_board_industry_name_em()
            if not df.empty:
                result["available"] = True
                result["sample_data"] = f"Got {len(df)} industry sectors"

        elif source == "sina":
            import akshare as ak
            df = ak.stock_zh_a_spot()
            if not df.empty:
                result["available"] = True
                result["sample_data"] = f"Got {len(df)} stocks"

    except Exception as e:
        result["error"] = str(e)[:200]

    return result


def fetch_with_fallback(fetch_funcs: dict, description: str = "data"):
    """
    Try to fetch data from multiple sources with automatic fallback.

    Args:
        fetch_funcs: Dict mapping source name to fetch function, e.g.:
            {
                "tushare": lambda: tushare_client.get_index_daily(...),
                "eastmoney": lambda: ak.stock_zh_index_daily_em(...),
                "sina": lambda: ak.index_zh_a_hist(...)
            }
        description: Description of what we're fetching (for logging)

    Returns:
        Tuple of (data, actual_source) or (None, None) if all sources fail
    """
    current_source = get_data_source()

    # Build ordered list of sources to try (current source first, then others)
    sources_to_try = [current_source]
    for source in VALID_DATA_SOURCES:
        if source not in sources_to_try and source in fetch_funcs:
            sources_to_try.append(source)

    last_error = None

    for source in sources_to_try:
        if source not in fetch_funcs:
            continue

        try:
            logging.debug(f"Trying to fetch {description} from {source}")
            data = fetch_funcs[source]()

            # Check if data is valid
            if data is not None:
                if hasattr(data, 'empty'):
                    if not data.empty:
                        # Success! If source changed, update the config
                        if source != current_source:
                            logging.info(f"Fallback successful: {description} fetched from {source} (was {current_source})")
                            set_data_source(source)
                        return data, source
                else:
                    # Non-DataFrame data, just check if not None/empty
                    if data:
                        if source != current_source:
                            logging.info(f"Fallback successful: {description} fetched from {source} (was {current_source})")
                            set_data_source(source)
                        return data, source

        except Exception as e:
            last_error = str(e)
            logging.warning(f"Failed to fetch {description} from {source}: {e}")
            continue

    logging.error(f"All sources failed for {description}. Last error: {last_error}")
    return None, None
