#!/bin/bash
# 本地构建前端脚本

echo "========================================"
echo "构建Little Red Flower前端"
echo "========================================"
echo ""

cd web

echo "📦 安装依赖..."
npm install

echo ""
echo "🔨 构建生产版本..."
npm run build

echo ""
if [ -d "dist" ]; then
    echo "✅ 构建成功！"
    echo ""
    echo "📁 构建文件位置: web/dist/"
    echo "📊 文件大小:"
    du -sh dist/
    echo ""
    echo "📝 文件列表:"
    ls -lh dist/ | head -10
    echo ""
    echo "🚀 可以部署到Azure了！"
else
    echo "❌ 构建失败！dist文件夹未生成"
    exit 1
fi

echo ""
echo "========================================"
echo "测试构建结果（可选）"
echo "========================================"
echo "运行: python -m uvicorn api.main:app --port 8000"
echo "访问: http://localhost:8000"
echo ""
