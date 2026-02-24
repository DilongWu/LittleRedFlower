"""
Direct Eastmoney API client (bypassing AkShare).
Uses push2delay.eastmoney.com which works from overseas servers.
"""
import logging
import requests
import datetime
from typing import Optional, List, Dict, Any

_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://data.eastmoney.com/',
    'Accept': 'application/json, text/plain, */*',
}

BASE_URL = 'https://push2delay.eastmoney.com/api/qt/clist/get'


def get_concept_board_direct(limit: int = 20) -> Optional[List[Dict[str, Any]]]:
    """
    Get hot concept boards from Eastmoney directly.
    Sorted by change% descending.
    """
    try:
        params = {
            'pn': 1,
            'pz': limit,
            'po': 1,  # descending
            'np': 1,
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': 2,
            'invt': 2,
            'fid': 'f3',  # sort by change%
            'fs': 'm:90+t:3+f:!50',  # concept boards
            'fields': 'f2,f3,f4,f12,f14,f128,f140',
            '_': '1'
        }
        r = requests.get(BASE_URL, params=params, headers=_HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()

        if not data.get('data') or not data['data'].get('diff'):
            return None

        results = []
        for item in data['data']['diff']:
            name = item.get('f14', '')
            change = item.get('f3')
            lead_code = item.get('f140', '')
            lead_name = item.get('f128', '')
            lead = f"{lead_name}" if lead_name else lead_code

            results.append({
                'name': name,
                'change': float(change) if change is not None else 0.0,
                'lead': lead,
            })

        return results

    except Exception as e:
        logging.error(f"Direct eastmoney concept board failed: {e}")
        return None


def get_industry_board_direct(limit: int = 20) -> Optional[List[Dict[str, Any]]]:
    """
    Get industry boards from Eastmoney directly.
    Sorted by change% descending.
    """
    try:
        params = {
            'pn': 1,
            'pz': limit,
            'po': 1,
            'np': 1,
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': 2,
            'invt': 2,
            'fid': 'f3',
            'fs': 'm:90+t:2+f:!50',  # industry boards
            'fields': 'f2,f3,f4,f12,f14,f128,f140',
            '_': '1'
        }
        r = requests.get(BASE_URL, params=params, headers=_HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()

        if not data.get('data') or not data['data'].get('diff'):
            return None

        results = []
        for item in data['data']['diff']:
            results.append({
                'name': item.get('f14', ''),
                'change': float(item.get('f3', 0)) if item.get('f3') is not None else 0.0,
                'lead': item.get('f128', '') or item.get('f140', ''),
            })

        return results

    except Exception as e:
        logging.error(f"Direct eastmoney industry board failed: {e}")
        return None


def get_index_quotes_direct() -> Optional[List[Dict[str, Any]]]:
    """
    Get major index quotes (上证/深证/创业板 etc.) directly.
    """
    try:
        params = {
            'pn': 1,
            'pz': 10,
            'po': 1,
            'np': 1,
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': 2,
            'invt': 2,
            'fid': 'f3',
            'fs': 'm:1+s:2,m:0+t:5',  # major indices
            'fields': 'f2,f3,f4,f12,f14',
            '_': '1'
        }
        r = requests.get(BASE_URL, params=params, headers=_HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()

        if not data.get('data') or not data['data'].get('diff'):
            return None

        results = []
        for item in data['data']['diff']:
            results.append({
                'name': item.get('f14', ''),
                'code': item.get('f12', ''),
                'price': item.get('f2'),
                'change': item.get('f3'),
                'change_amount': item.get('f4'),
            })

        return results

    except Exception as e:
        logging.error(f"Direct eastmoney index quotes failed: {e}")
        return None
