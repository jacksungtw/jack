#!/bin/bash
# Oath Gateway 启动脚本 (增强版 with Tailscale)

set -e  # 出错时退出

echo "🚀 开始启动 Oath Gateway..."

# 1. 检查必须的环境变量
echo "🔍 检查配置..."
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "❌ 错误: DEEPSEEK_API_KEY 未设置"
    exit 1
fi

# 2. 初始化 Tailscale (云地连线)
if [ -n "$TAILSCALE_AUTHKEY" ]; then
    echo "🛡️ 正在初始化 Tailscale..."
    
    # 确保 tailscaled 目录存在
    mkdir -p /tmp/tailscale
    
    # 启动 tailscaled (用户態網路模式)
    # 使用 --state=mem: 避免在唯讀檔案系統上寫入狀態
    tailscaled --tun=userspace-networking --statedir=/tmp/tailscale &
    
    # 等待 daemon 啟動
    sleep 3
    
    # 登入 Tailscale
    echo "🔐 正在登入 Tailscale..."
    tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname="railway-oath-gateway" --accept-routes
    
    echo "✅ Tailscale 已連線"
else
    echo "⚠️ 警告: TAILSCALE_AUTHKEY 未設置，跳過雲地連線，僅提供公網 API 功能"
fi

# 3. 设置默认端口
if [ -z "$PORT" ]; then
    export PORT=8000
    echo "🌐 设置默认端口: $PORT"
fi

# 4. 启动 Gunicorn
echo "🚀 启动 Gunicorn 服务器..."
exec gunicorn --bind 0.0.0.0:$PORT     --workers 2     --threads 4     --timeout 120     --access-logfile -     --error-logfile -     oath_gateway:app
