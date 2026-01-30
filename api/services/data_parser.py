"""
Data parsing utilities for converting raw text to structured JSON
Mirrors the frontend parseRawData.js logic
"""
import re
from typing import Dict, List, Optional, Any


def parse_index_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse index data like '上证指数: 4139.90 (0.18%)'"""
    match = re.match(r'^(.+?):\s*([\d.]+)\s*\(([-+]?[\d.]+)%\)', line)
    if match:
        return {
            'name': match.group(1).strip(),
            'value': float(match.group(2)),
            'change': float(match.group(3))
        }
    return None


def parse_turnover_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse turnover line like '沪深两市总成交额: 1.52万亿元'"""
    match = re.search(r'([\d.]+)(万亿|亿)元', line)
    if match:
        value = float(match.group(1))
        unit = match.group(2)
        return {
            'value': value,
            'unit': unit,
            'display': f'{value}{unit}元'
        }
    return None


def parse_sector_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse sector line like '- 化工: 5.20% (领涨股: 某某某)'"""
    trimmed = re.sub(r'^[-•]\s*', '', line).strip()

    # Pattern with leading stock
    match = re.match(r'^(.+?):\s*([-+]?[\d.]+)%\s*(?:\(领涨股:\s*(.+?)\))?', trimmed)
    if match:
        return {
            'name': match.group(1).strip(),
            'change': float(match.group(2)),
            'leadingStock': match.group(3).strip() if match.group(3) else None
        }

    # Simpler pattern
    simple_match = re.match(r'^(.+?):\s*([-+]?[\d.]+)%', trimmed)
    if simple_match:
        return {
            'name': simple_match.group(1).strip(),
            'change': float(simple_match.group(2)),
            'leadingStock': None
        }

    return None


def parse_limit_up_stock_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse limit-up stock line"""
    trimmed = re.sub(r'^[-•]\s*', '', line).strip()

    match = re.match(
        r'^(.+?)\s*\((\d+)连板\):\s*行业-(.+?),\s*首次封板-(\d+),\s*最后封板-(\d+),\s*炸板-(\d+)次',
        trimmed
    )
    if match:
        def format_time(t):
            s = str(t).zfill(6)
            return f'{s[0:2]}:{s[2:4]}:{s[4:6]}'

        return {
            'name': match.group(1).strip(),
            'boards': int(match.group(2)),
            'industry': match.group(3).strip(),
            'firstLockTime': format_time(match.group(4)),
            'lastLockTime': format_time(match.group(5)),
            'breakCount': int(match.group(6)),
            'analysis': None,
            'news': []
        }

    return None


def parse_raw_data(raw_data: str, sentiment: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Main parsing function - converts raw text to structured JSON

    Args:
        raw_data: Raw text data from report
        sentiment: Optional sentiment data to merge

    Returns:
        Structured data dictionary
    """
    if not raw_data:
        return {
            'marketOverview': [],
            'turnover': None,
            'turnoverChange': None,
            'sectors': {'gainers': [], 'losers': [], 'concepts': []},
            'news': [],
            'ladder': [],
            'sentiment': sentiment
        }

    lines = raw_data.split('\n')
    result = {
        'marketOverview': [],
        'turnover': None,
        'turnoverChange': None,
        'sectors': {'gainers': [], 'losers': [], 'concepts': []},
        'news': [],
        'ladder': [],
        'sentiment': sentiment
    }

    current_section = None
    current_sub_section = None
    current_stock = None

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue

        # Check for section headers like 【市场行情】
        section_match = re.match(r'^【(.*)】$', trimmed)
        if section_match:
            current_section = section_match.group(1)
            current_sub_section = None
            continue

        # Parse based on current section
        if current_section and ('市场行情' in current_section or '指数表现' in current_section):
            index_data = parse_index_line(trimmed)
            if index_data:
                result['marketOverview'].append(index_data)

        elif current_section and '成交额' in current_section:
            # Total turnover
            if '总成交额' in trimmed or '日均成交额' in trimmed:
                turnover = parse_turnover_line(trimmed)
                if turnover:
                    result['turnover'] = turnover

            # Turnover change
            elif '放量' in trimmed or '缩量' in trimmed:
                change_match = re.search(r'(放量|缩量)[:：]?\s*([\d.]+)(万亿|亿)元', trimmed)
                if change_match:
                    result['turnoverChange'] = {
                        'direction': change_match.group(1),
                        'value': float(change_match.group(2)),
                        'unit': change_match.group(3),
                        'display': f'{change_match.group(1)} {change_match.group(2)}{change_match.group(3)}元'
                    }

        elif current_section and '板块表现' in current_section:
            # Check for sub-sections
            if '领涨行业' in trimmed:
                current_sub_section = 'gainers'
                continue
            if '领跌行业' in trimmed:
                current_sub_section = 'losers'
                continue
            if '领涨概念' in trimmed:
                current_sub_section = 'concepts'
                continue

            # Parse sector line
            if trimmed.startswith('-') or trimmed.startswith('•'):
                sector = parse_sector_line(trimmed)
                if sector and current_sub_section:
                    result['sectors'][current_sub_section].append(sector)
                elif sector:
                    result['sectors']['gainers'].append(sector)

        elif current_section and '资讯' in current_section:
            # News items
            if trimmed.startswith('-') or trimmed.startswith('•'):
                news_title = re.sub(r'^[-•]\s*', '', trimmed).strip()
                if news_title:
                    result['news'].append({'title': news_title})

        elif current_section and ('涨停' in current_section or '强势股' in current_section):
            # Check if this is a stock header line
            if trimmed.startswith('-') or trimmed.startswith('•'):
                stock = parse_limit_up_stock_line(trimmed)
                if stock:
                    # Save previous stock
                    if current_stock:
                        result['ladder'].append(current_stock)
                    current_stock = stock

            # Check for AI analysis (indented line)
            elif line.startswith('    ') or line.startswith('\t'):
                if 'AI分析' in trimmed and current_stock:
                    analysis_text = re.sub(r'^\*\s*AI分析:\s*', '', trimmed)
                    # Remove metadata tags
                    analysis_text = re.sub(r'\[.+?:.+?\]', '', analysis_text).strip()
                    current_stock['analysis'] = {'text': analysis_text}

                elif '资讯' in trimmed and current_stock:
                    news_text = re.sub(r'^\*\s*资讯:\s*', '', trimmed)
                    current_stock['news'].append({'title': news_text})

    # Don't forget the last stock
    if current_stock:
        result['ladder'].append(current_stock)

    # Sort ladder by board count (descending)
    result['ladder'].sort(key=lambda x: x['boards'], reverse=True)

    return result
