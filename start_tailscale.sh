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
    echo "🔧 配置 Tailscale (Userspace 模式)..."
    
    mkdir -p /tmp/tailscale
    
    # 启动 tailscaled
    echo "启动 tailscaled 服务..."
    tailscaled --tun=userspace-networking \
               --statedir=/tmp/tailscale \
               --socket=/tmp/tailscaled.sock &
    TAILSCALED_PID=$!
    sleep 5
    
    # 连接 Tailscale
    echo "连接 Tailscale 网络..."
    tailscale --socket=/tmp/tailscaled.sock up --authkey="$TAILSCALE_AUTHKEY" --hostname="oath-gateway-railway" --accept-routes --accept-dns
    
    echo "✅ Tailscale 连接成功"
    
    # 配置代理环境变量 (Userspace 模式必需)
    export ALL_PROXY="socks5://localhost:1055"
    export HTTP_PROXY="http://localhost:1055"
    export HTTPS_PROXY="http://localhost:1055"
    export NO_PROXY="localhost,127.0.0.1"
    echo "🌐 代理已配置: ALL_PROXY=$ALL_PROXY"
    
    # 等待网络稳定
    sleep 2
fi

# 如果 SITE_BRIDGE_URL 未设置，使用 Tailscale 地址
if [ -z "$SITE_BRIDGE_URL" ]; then
    export SITE_BRIDGE_URL="http://100.88.112.41:9001"
    echo "🌐 自动设置 SITE_BRIDGE_URL: $SITE_BRIDGE_URL"
fi

# 设置默认端口
if [ -z "$PORT" ]; then
    export PORT=8000
    echo "🌐 设置默认端口: $PORT"
fi

# 测试 Site Bridge 连接
echo "🔗 测试 Site Bridge 连接 ($SITE_BRIDGE_URL)..."
if curl -s --max-time 5 "$SITE_BRIDGE_URL/bridge/health" > /dev/null; then
    echo "✅ Site Bridge 连接正常"
else
    echo "⚠️  Site Bridge 连接失败 (可能代理尚未就绪)，程序将继续启动"
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
