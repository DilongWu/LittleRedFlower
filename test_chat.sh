#!/bin/bash
# AI聊天助手测试脚本

echo "========================================="
echo "AI聊天助手功能测试"
echo "========================================="
echo ""

echo "1. 检查文件创建..."
echo "  - 后端服务: api/services/chat.py"
if [ -f "api/services/chat.py" ]; then
    echo "    [OK] 文件存在"
else
    echo "    [FAIL] 文件不存在"
fi

echo "  - 前端组件: web/src/components/ChatAssistant.jsx"
if [ -f "web/src/components/ChatAssistant.jsx" ]; then
    echo "    [OK] 文件存在"
else
    echo "    [FAIL] 文件不存在"
fi

echo "  - 样式文件: web/src/components/ChatAssistant.css"
if [ -f "web/src/components/ChatAssistant.css" ]; then
    echo "    [OK] 文件存在"
else
    echo "    [FAIL] 文件不存在"
fi

echo ""
echo "2. 测试Python导入..."
python -c "from api.services.chat import chat_service; print('    [OK] Chat service loaded')" 2>&1 | head -1

echo ""
echo "3. 检查API端点..."
grep -q "/api/chat" api/main.py && echo "    [OK] /api/chat endpoint added" || echo "    [FAIL] Endpoint not found"

echo ""
echo "4. 检查App.jsx集成..."
grep -q "ChatAssistant" web/src/App.jsx && echo "    [OK] ChatAssistant imported" || echo "    [FAIL] Import not found"

echo ""
echo "========================================="
echo "测试完成！"
echo "========================================="
echo ""
echo "下一步："
echo "1. 启动后端: python -m uvicorn api.main:app --reload --port 8000"
echo "2. 启动前端: cd web && npm run dev"
echo "3. 访问: http://localhost:5173"
echo "4. 登录后点击右下角聊天按钮测试"
echo ""
