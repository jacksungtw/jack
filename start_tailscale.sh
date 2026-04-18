#!/bin/bash
# Oath Gateway 启动脚本 (Tailscale 版本)

set -e  # 出错时退出

echo "🚀 开始启动 Oath Gateway (Tailscale 版本)..."
echo "环境变量:"
echo "PORT: $PORT"
echo "DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:0:10}..."
echo "TAILSCALE_AUTHKEY: ${TAILSCALE_AUTHKEY:0:10}..."
echo "SITE_BRIDGE_URL: $SITE_BRIDGE_URL"
echo "SERVICE_NAME: $SERVICE_NAME"

# 检查必须的环境变量
echo "🔍 检查配置..."
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "❌ 错误: DEEPSEEK_API_KEY 未设置"
    exit 1
fi

if [ -z "$TAILSCALE_AUTHKEY" ]; then
    echo "⚠️  警告: TAILSCALE_AUTHKEY 未设置，无法连接 Tailscale"
else
    echo "🔧 配置 Tailscale..."
    
    # 启动 tailscaled
    echo "启动 tailscaled 服务..."
    tailscaled --tun=userspace-networking --socket=/var/run/tailscale/tailscaled.sock &
    TAILSCALED_PID=$!
    sleep 3
    
    # 连接 Tailscale
    echo "连接 Tailscale 网络..."
    tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname="oath-gateway-railway" --accept-routes --accept-dns
    
    echo "✅ Tailscale 连接成功"
    echo "📡 Tailscale 状态:"
    tailscale status
    
    # 等待网络稳定
    sleep 2
fi

# 如果 SITE_BRIDGE_URL 未设置，使用 Tailscale 地址
if [ -z "$SITE_BRIDGE_URL" ]; then
    export SITE_BRIDGE_URL="http://yahboom:9002"
    echo "🌐 自动设置 SITE_BRIDGE_URL: $SITE_BRIDGE_URL"
fi

# 设置默认端口
if [ -z "$PORT" ]; then
    export PORT=8000
    echo "🌐 设置默认端口: $PORT"
fi

# 测试 Site Bridge 连接
echo "🔗 测试 Site Bridge 连接..."
if curl -s --max-time 5 "$SITE_BRIDGE_URL/bridge/health" > /dev/null; then
    echo "✅ Site Bridge 连接正常"
else
    echo "⚠️  Site Bridge 连接失败，拍照功能可能不可用"
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
