#!/bin/bash
# Fortune Fusion Engine - Quick Setup Script
echo "🔮 Fortune Fusion Engine v2.3 安装中..."

# Install minimal dependencies
echo "📦 安装核心依赖..."
pip install fastapi uvicorn numpy pydantic 2>/dev/null

# Optional: Install prometheus-client for monitoring
read -p "是否安装 Prometheus 监控支持？(y/N): " install_prometheus
if [[ "$install_prometheus" =~ ^[Yy]$ ]]; then
    echo "📦 安装 prometheus-client..."
    pip install prometheus-client>=0.19.0 2>/dev/null
    echo "✅ Prometheus 监控已启用"
else
    echo "⏭️  跳过 Prometheus 监控（可通过 /metrics 端点查看提示）"
fi

# Start service
echo "🚀 启动服务 (端口 8000)..."
cd "$(dirname "$0")"
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &

# Wait for startup
sleep 3

# Test
echo "🧪 测试服务..."
curl -s http://localhost:8000/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'✅ 状态: {d[\"status\"]} | 体系: {len(d[\"systems_available\"])}个')" 2>/dev/null || echo "❌ 启动失败"

echo ""
echo "✅ 安装完成！"
echo "📖 API文档: http://localhost:8000/docs"
echo "🔮 查询示例:"
echo '  curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d '"'"'{"birth_info":{"year":1990,"month":6,"day":15,"hour":14,"minute":30,"latitude":32.06,"longitude":118.78},"gender":"male","scene":"终身格局"}'"'"''
echo ""
echo "💡 提示: 如需 Prometheus 监控，运行: pip install prometheus-client"
