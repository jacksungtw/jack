#!/bin/bash
# Oath Gateway 启动脚本 (简化版)

set -e  # 出错时退出

echo "🚀 开始启动 Oath Gateway..."

# 检查必须的环境变量
echo "🔍 检查配置..."
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "❌ 错误: DEEPSEEK_API_KEY 未设置"
    exit 1
fi

if [ -z "$SITE_BRIDGE_URL" ]; then
    echo "⚠️  警告: SITE_BRIDGE_URL 未设置，拍照功能可能不可用"
fi

# 设置默认端口
if [ -z "$PORT" ]; then
    export PORT=8000
    echo "🌐 设置默认端口: $PORT"
fi

# 启动 Gunicorn
echo "🚀 启动 Gunicorn 服务器..."
exec gunicorn --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    oath_gateway:app