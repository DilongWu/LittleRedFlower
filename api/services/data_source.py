"""
Data source configuration module.
Supports switching between Eastmoney (东方财富) and Sina (新浪) data sources.
"""
import os
import json
import logging

# Default data source
DEFAULT_DATA_SOURCE = "sina"  # "eastmoney" or "sina"

# Config file path
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_source_config.json")

def get_data_source() -> str:
    """Get the current data source setting."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("data_source", DEFAULT_DATA_SOURCE)
    except Exception as e:
        logging.error(f"Error reading data source config: {e}")
    return DEFAULT_DATA_SOURCE


def set_data_source(source: str) -> bool:
    """Set the data source. Returns True if successful."""
    if source not in ["eastmoney", "sina"]:
        return False

    try:
        config = {"data_source": source}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logging.info(f"Data source changed to: {source}")
        return True
    except Exception as e:
        logging.error(f"Error saving data source config: {e}")
        return False


def test_data_source(source: str) -> dict:
    """Test if a data source is available. Returns status dict."""
    import akshare as ak

    result = {
        "source": source,
        "available": False,
        "error": None,
        "sample_data": None
    }

    try:
        if source == "eastmoney":
            # Test Eastmoney API
            df = ak.stock_board_industry_name_em()
            if not df.empty:
                result["available"] = True
                result["sample_data"] = f"Got {len(df)} industry sectors"
        elif source == "sina":
            # Test Sina API
            df = ak.stock_zh_a_spot()
            if not df.empty:
                result["available"] = True
                result["sample_data"] = f"Got {len(df)} stocks"
    except Exception as e:
        result["error"] = str(e)[:100]

    return result
