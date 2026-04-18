#!/bin/bash
# Oath Gateway 启动脚本 (调试版)

set -e  # 出错时退出

echo "🚀 开始启动 Oath Gateway (调试模式)..."
echo "环境变量:"
echo "PORT: $PORT"
echo "DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:0:10}..."
echo "SITE_BRIDGE_URL: $SITE_BRIDGE_URL"
echo "SERVICE_NAME: $SERVICE_NAME"
echo "当前目录: $(pwd)"
echo "文件列表:"
ls -la

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

# 测试 Python 环境
echo "🐍 测试 Python 环境..."
python3 --version
python3 -c "import flask; print(f'Flask版本: {flask.__version__}')" || echo "Flask 导入失败"
python3 -c "import requests; print(f'Requests版本: {requests.__version__}')" || echo "Requests 导入失败"

# 启动 Gunicorn
echo "🚀 启动 Gunicorn 服务器..."
echo "命令: gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 --access-logfile - --error-logfile - oath_gateway:app"

exec gunicorn --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    oath_gateway:app
