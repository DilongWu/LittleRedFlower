#!/usr/bin/env python
"""直接测试美股 API 端点"""

import sys
sys.path.insert(0, '/c/WorkDir/LittleRedFlower')

from api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

print("Testing US Tech API endpoints...")
print("=" * 60)

# Test 1: Get latest data
print("\n[1] GET /api/us-tech/latest")
response = client.get("/api/us-tech/latest")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Success: {data.get('summary', {}).get('total', 0)} stocks")
    print(f"Avg change: {data.get('summary', {}).get('avg_change', 0)}%")
else:
    print(f"Error: {response.text[:200]}")

# Test 2: Trigger generation
print("\n[2] POST /api/trigger/us-tech")
response = client.post("/api/trigger/us-tech")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Message: {data.get('message', 'Unknown')}")
else:
    print(f"Error: {response.text[:200]}")

print("\n" + "=" * 60)
print("API test completed!")
