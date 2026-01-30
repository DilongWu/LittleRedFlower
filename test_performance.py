#!/usr/bin/env python3
"""
性能测试脚本 - 验证优化效果
"""
import time
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# API 基础 URL
BASE_URL = "http://localhost:8000"

# 测试的 API 端点
ENDPOINTS = {
    "指数K线": "/api/index/overview",
    "全景雷达": "/api/market/radar",
    "资金流向": "/api/fund/flow",
    "热点题材": "/api/concept/hot",
}

def test_single_endpoint(name, endpoint):
    """测试单个端点的响应时间"""
    url = f"{BASE_URL}{endpoint}"

    try:
        start = time.time()
        response = requests.get(url, timeout=30)
        elapsed = time.time() - start

        if response.status_code == 200:
            data_size = len(response.content)
            return {
                "name": name,
                "status": "✅ 成功",
                "time": f"{elapsed:.2f}秒",
                "size": f"{data_size / 1024:.1f} KB",
                "elapsed_ms": elapsed * 1000
            }
        else:
            return {
                "name": name,
                "status": f"❌ 失败 (HTTP {response.status_code})",
                "time": f"{elapsed:.2f}秒",
                "size": "-",
                "elapsed_ms": elapsed * 1000
            }
    except Exception as e:
        return {
            "name": name,
            "status": f"❌ 错误: {str(e)}",
            "time": "-",
            "size": "-",
            "elapsed_ms": 0
        }

def test_concurrent_load():
    """测试并发加载性能"""
    print("=" * 70)
    print("🚀 开始性能测试 - 并发加载所有端点")
    print("=" * 70)

    start_total = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=len(ENDPOINTS)) as executor:
        future_to_endpoint = {
            executor.submit(test_single_endpoint, name, endpoint): name
            for name, endpoint in ENDPOINTS.items()
        }

        for future in as_completed(future_to_endpoint):
            result = future.result()
            results.append(result)

    total_time = time.time() - start_total

    # 打印结果表格
    print("\n📊 测试结果:")
    print("-" * 70)
    print(f"{'端点':<12} {'状态':<20} {'响应时间':<12} {'数据大小':<12}")
    print("-" * 70)

    success_count = 0
    total_response_time = 0

    for r in sorted(results, key=lambda x: x["elapsed_ms"], reverse=True):
        print(f"{r['name']:<12} {r['status']:<20} {r['time']:<12} {r['size']:<12}")
        if "成功" in r['status']:
            success_count += 1
            total_response_time += r['elapsed_ms']

    print("-" * 70)
    print(f"\n📈 统计信息:")
    print(f"  • 总耗时: {total_time:.2f} 秒")
    print(f"  • 成功率: {success_count}/{len(ENDPOINTS)} ({success_count/len(ENDPOINTS)*100:.0f}%)")
    if success_count > 0:
        avg_time = total_response_time / success_count / 1000
        print(f"  • 平均响应时间: {avg_time:.2f} 秒")
    print()

def test_sequential_load():
    """测试顺序加载性能（对比用）"""
    print("=" * 70)
    print("🐌 对比测试 - 顺序加载所有端点")
    print("=" * 70)

    start_total = time.time()
    results = []

    for name, endpoint in ENDPOINTS.items():
        result = test_single_endpoint(name, endpoint)
        results.append(result)

    total_time = time.time() - start_total

    # 打印结果表格
    print("\n📊 测试结果:")
    print("-" * 70)
    print(f"{'端点':<12} {'状态':<20} {'响应时间':<12} {'数据大小':<12}")
    print("-" * 70)

    success_count = 0

    for r in results:
        print(f"{r['name']:<12} {r['status']:<20} {r['time']:<12} {r['size']:<12}")
        if "成功" in r['status']:
            success_count += 1

    print("-" * 70)
    print(f"\n📈 统计信息:")
    print(f"  • 总耗时: {total_time:.2f} 秒")
    print(f"  • 成功率: {success_count}/{len(ENDPOINTS)} ({success_count/len(ENDPOINTS)*100:.0f}%)")
    print()

def test_cache_performance():
    """测试缓存性能"""
    print("=" * 70)
    print("💾 缓存测试 - 重复请求同一端点")
    print("=" * 70)

    endpoint = "/api/index/overview"
    url = f"{BASE_URL}{endpoint}"

    # 第一次请求（缓存未命中）
    print("\n1️⃣  第一次请求（应该较慢）...")
    start = time.time()
    try:
        response1 = requests.get(url, timeout=30)
        time1 = time.time() - start
        print(f"   响应时间: {time1:.2f} 秒")
        print(f"   状态码: {response1.status_code}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return

    # 第二次请求（缓存应命中）
    print("\n2️⃣  第二次请求（应该很快）...")
    start = time.time()
    try:
        response2 = requests.get(url, timeout=30)
        time2 = time.time() - start
        print(f"   响应时间: {time2:.2f} 秒")
        print(f"   状态码: {response2.status_code}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return

    # 计算性能提升
    if time1 > 0 and time2 > 0:
        speedup = (time1 - time2) / time1 * 100
        print(f"\n🎯 缓存效果:")
        print(f"   • 第一次: {time1:.2f} 秒")
        print(f"   • 第二次: {time2:.2f} 秒")
        if speedup > 0:
            print(f"   • 性能提升: {speedup:.1f}%")
        else:
            print(f"   • 注意: 第二次请求反而更慢，可能缓存未生效")
    print()

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  📡 小红花系统性能测试工具")
    print("=" * 70)
    print("\n⚠️  请确保后端服务已启动 (http://localhost:8000)")
    input("按 Enter 键开始测试...")

    # 运行测试
    test_concurrent_load()
    print("\n" + "⏸️  " * 20 + "\n")

    test_sequential_load()
    print("\n" + "⏸️  " * 20 + "\n")

    test_cache_performance()

    print("=" * 70)
    print("✅ 测试完成！")
    print("=" * 70)
    print("\n💡 优化建议:")
    print("  1. 并发加载应该比顺序加载快 50-70%")
    print("  2. 缓存命中的第二次请求应该快 80-95%")
    print("  3. 成功率应该达到 95% 以上")
    print("  4. 单个端点响应时间应该在 1-3 秒以内")
    print()
