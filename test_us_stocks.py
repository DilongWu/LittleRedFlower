#!/usr/bin/env python
"""测试美股科技股数据获取功能"""

import sys
sys.path.insert(0, '/c/WorkDir/LittleRedFlower')

from api.services.us_stocks import get_stock_data, get_us_tech_overview
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

print("=" * 60)
print("美股科技股数据获取测试")
print("=" * 60)

# 测试1: 单只股票
print("\n【测试1】获取 AAPL 单只股票数据...")
data = get_stock_data('AAPL', use_cache=False)
if data and 'error' not in data:
    print(f"✅ 成功！")
    print(f"   股票: {data['symbol']} - {data['name']} {data.get('emoji', '')}")
    print(f"   价格: ${data['price']}")
    print(f"   涨跌: {data['change']} ({data['change_percent']}%)")
    print(f"   成交量: {data.get('volume_str', 'N/A')}")
    print(f"   市值: {data.get('market_cap_str', 'N/A')}")
    print(f"   数据源: {data['data_source']}")
else:
    print(f"❌ 失败: {data}")

# 测试2: 获取所有科技股（限制3个并发以避免速率限制）
print("\n【测试2】获取所有科技股数据（并发模式）...")
overview = get_us_tech_overview(use_cache=False, max_workers=3)

if overview:
    summary = overview['summary']
    print(f"✅ 数据获取完成！")
    print(f"   总计: {summary['total']} 只")
    print(f"   成功: {summary['success']} 只")
    print(f"   上涨: {summary['up']} 只")
    print(f"   下跌: {summary['down']} 只")
    print(f"   平均涨幅: {summary['avg_change']}%")
    print(f"   耗时: {overview.get('elapsed_time', 'N/A')} 秒")

    if summary.get('top_gainer'):
        tg = summary['top_gainer']
        print(f"   领涨股: {tg['name']} (+{tg['change_percent']}%)")

    if summary.get('top_loser'):
        tl = summary['top_loser']
        print(f"   领跌股: {tl['name']} ({tl['change_percent']}%)")

    print(f"\n【详细数据】")
    for symbol, stock in overview['stocks'].items():
        if 'error' not in stock:
            status = "📈" if stock['change_percent'] >= 0 else "📉"
            print(f"   {status} {stock['emoji']} {stock['name']:8} ${stock['price']:8.2f}  {stock['change_percent']:+6.2f}%")
        else:
            print(f"   ❌ {stock.get('emoji', '?')} {stock.get('name', symbol):8} - 数据获取失败")
else:
    print(f"❌ 获取失败")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
