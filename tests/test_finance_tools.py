"""
Test script for Yahoo Finance tools integration.
Validates:
1. Tool definitions are correct OpenAI format
2. All tools execute successfully with real data
3. Chat service correctly imports and exposes tools
"""

import json
import sys
sys.path.insert(0, '/home/azureuser/LittleRedFlower')

from api.services.finance_tools import FINANCE_TOOLS, execute_tool, TOOL_HANDLERS

def test_tool_definitions():
    """Verify tool definitions match OpenAI function calling format"""
    print("=" * 50)
    print("TEST 1: Tool Definitions Format")
    print("=" * 50)

    required_tools = ['get_stock_quote', 'get_stock_history', 'get_analyst_ratings', 'get_financials', 'get_company_info']

    for tool in FINANCE_TOOLS:
        assert tool["type"] == "function", f"Tool type should be 'function', got {tool['type']}"
        func = tool["function"]
        assert "name" in func, "Missing 'name'"
        assert "description" in func, "Missing 'description'"
        assert "parameters" in func, "Missing 'parameters'"
        assert func["parameters"]["type"] == "object", "Parameters should be object type"
        assert "properties" in func["parameters"], "Missing properties"
        assert "required" in func["parameters"], "Missing required"
        assert "symbol" in func["parameters"]["required"], f"symbol should be required for {func['name']}"
        print(f"  ✅ {func['name']} - valid")

    tool_names = [t["function"]["name"] for t in FINANCE_TOOLS]
    for name in required_tools:
        assert name in tool_names, f"Missing tool: {name}"

    assert len(FINANCE_TOOLS) == 5, f"Expected 5 tools, got {len(FINANCE_TOOLS)}"
    print(f"\n  All {len(FINANCE_TOOLS)} tools have valid OpenAI format ✅")


def test_tool_execution():
    """Test each tool executes and returns valid JSON"""
    print("\n" + "=" * 50)
    print("TEST 2: Tool Execution (Live Data)")
    print("=" * 50)

    tests = [
        ("get_stock_quote", {"symbol": "MSFT"}),
        ("get_stock_quote", {"symbol": "NVDA"}),
        ("get_stock_history", {"symbol": "AAPL", "period": "5d"}),
        ("get_analyst_ratings", {"symbol": "MSFT"}),
        ("get_financials", {"symbol": "NVDA", "statement": "income"}),
        ("get_company_info", {"symbol": "TSLA"}),
    ]

    for name, args in tests:
        result = execute_tool(name, args)
        data = json.loads(result)
        assert "error" not in data, f"{name}({args}) returned error: {data.get('error')}"
        print(f"  ✅ {name}({args.get('symbol')}) - OK")

    print("\n  All tools execute successfully with real data ✅")


def test_chat_service_integration():
    """Verify chat service imports tools correctly"""
    print("\n" + "=" * 50)
    print("TEST 3: Chat Service Integration")
    print("=" * 50)

    from api.services.chat import ChatService, AZURE_CONFIG
    # The import itself validates the integration
    print("  ✅ ChatService imports finance_tools successfully")
    print(f"  ✅ Config loaded: deployment={AZURE_CONFIG.get('deploymentName', 'N/A')}")

    # Verify the chat service class has the right methods
    svc = ChatService()
    assert hasattr(svc, 'get_response'), "Missing get_response method"
    assert hasattr(svc, 'build_system_prompt'), "Missing build_system_prompt method"
    print("  ✅ ChatService has all required methods")

    # Check system prompt mentions tools
    prompt = svc.build_system_prompt()
    assert "美股" in prompt or "工具" in prompt, "System prompt should mention US stocks or tools"
    print("  ✅ System prompt updated for US stocks")


def test_tool_handlers_complete():
    """Verify all defined tools have handlers"""
    print("\n" + "=" * 50)
    print("TEST 4: Handler Completeness")
    print("=" * 50)

    tool_names = [t["function"]["name"] for t in FINANCE_TOOLS]
    for name in tool_names:
        assert name in TOOL_HANDLERS, f"Missing handler for {name}"
        print(f"  ✅ {name} has handler")

    print("\n  All tools have corresponding handlers ✅")


if __name__ == "__main__":
    try:
        test_tool_definitions()
        test_tool_execution()
        test_chat_service_integration()
        test_tool_handlers_complete()
        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
