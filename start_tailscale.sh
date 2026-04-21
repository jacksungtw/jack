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
    echo    # 啟動 tailscaled (使用 /tmp 避免權限問題)
    echo "啟動 tailscaled 服務 (加強代理模式)..."
    tailscaled --tun=userspace-networking \
               --statedir=/tmp/tailscale \
               --socket=/tmp/tailscaled.sock \
               --outbound-http-proxy-listen=localhost:1055 \
               --socks5-server=localhost:1055 &
    TAILSCALED_PID=$!
    
    # 等待 daemon 啟動並建立 Socket
    sleep 5
    
    # 登入 Tailscale
    echo "🔐 正在登入 Tailscale..."
    tailscale --socket=/tmp/tailscaled.sock up \
              --authkey="$TAILSCALE_AUTHKEY" \
              --hostname="railway-oath-gateway" \
              --accept-routes \
              --accept-dns
    
    echo "✅ Tailscale 已連線"
    
    # 關鍵：配置代理環境變數 (雙重大小寫確保兼容性)
    export ALL_PROXY="socks5://localhost:1055"
    export all_proxy="socks5://localhost:1055"
    export HTTP_PROXY="http://localhost:1055"
    export http_proxy="http://localhost:1055"
    export HTTPS_PROXY="http://localhost:1055"
    export https_proxy="http://localhost:1055"
    
    # 設定排除名單
    export NO_PROXY="localhost,127.0.0.1"
    export no_proxy="localhost,127.0.0.1"
    
    echo "🌐 代理已配置: ALL_PROXY=$ALL_PROXY"
    
    # 等待網絡穩定並確保代理已工作
    sleep 3
else
    echo "⚠️ 警告: TAILSCALE_AUTHKEY 未設置，跳過雲地連線"
fi

# 3. 设置 Site Bridge URL
if [ -z "$SITE_BRIDGE_URL" ]; then
    export SITE_BRIDGE_URL="http://100.88.112.41:9001"
    echo "🌐 自動設置 SITE_BRIDGE_URL: $SITE_BRIDGE_URL"
fi

# 4. 设置默认端口
if [ -z "$PORT" ]; then
    export PORT=8000
fi

# 5. 強化連通性測試 (最多重試 3 次)
echo "🔗 正在測試地端連線 ($SITE_BRIDGE_URL)..."
MAX_RETRIES=3
RETRY_COUNT=0
SUCCESS=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s --max-time 5 "$SITE_BRIDGE_URL/bridge/health" > /dev/null; then
        echo "✅ 地端連線測試成功！"
        SUCCESS=true
        break
    else
        RETRY_COUNT=$((RETRY_COUNT+1))
        echo "⚠️  連線測試失敗 (第 $RETRY_COUNT 次)，稍後重試..."
        sleep 5
    fi
done

if [ "$SUCCESS" = false ]; then
    echo "❌ 警告: 地端連線測試最終失敗，但程序將嘗試啟動..."
fi

# 6. 啟動 Gunicorn
echo "🚀 啟動 Gunicorn 伺服器..."
exec gunicorn --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    oath_gateway:app
