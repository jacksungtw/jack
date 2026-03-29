#!/bin/bash
# Oath Gateway 启动脚本 (Tailscale + Gunicorn)

set -e  # 出错时退出

echo "🚀 开始启动 Oath Gateway..."

# 检查必要环境变量
if [ -z "$TAILSCALE_AUTHKEY" ]; then
    echo "⚠️  警告: TAILSCALE_AUTHKEY 未设置，跳过 Tailscale 连接"
else
    echo "🔧 安装并配置 Tailscale..."
    
    # 安装 Tailscale
    if ! command -v tailscale &> /dev/null; then
        echo "📦 安装 Tailscale..."
        # 根据系统选择安装方式
        if [ -f /etc/debian_version ]; then
            # Debian/Ubuntu
            curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.noarmor.gpg | tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
            curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.tailscale-keyring.list | tee /etc/apt/sources.list.d/tailscale.list
            apt-get update
            apt-get install -y tailscale
        elif [ -f /etc/alpine-release ]; then
            # Alpine
            apk add tailscale
        else
            # 通用 Linux (下载二进制)
            ARCH=$(uname -m)
            case $ARCH in
                x86_64) ARCH="amd64" ;;
                aarch64|arm64) ARCH="arm64" ;;
                armv7l|armhf) ARCH="arm" ;;
                *) ARCH="amd64" ;;
            esac
            
            TAILSCALE_URL="https://pkgs.tailscale.com/stable/tailscale_1.96.4_${ARCH}.tgz"
            curl -fsSL "$TAILSCALE_URL" | tar -xz -C /tmp
            mv /tmp/tailscale_*/* /usr/local/bin/
        fi
    fi
    
    echo "🔑 使用认证密钥连接 Tailscale..."
    
    # 启动 tailscaled 服务
    if [ ! -S /var/run/tailscale/tailscaled.sock ]; then
        echo "启动 tailscaled 后台服务..."
        tailscaled --tun=userspace-networking --socket=/var/run/tailscale/tailscaled.sock &
        TAILSCALED_PID=$!
        sleep 3
    fi
    
    # 连接 Tailscale
    tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname="oath-gateway-railway" --accept-routes --accept-dns
    
    echo "✅ Tailscale 连接成功"
    echo "📡 Tailscale 状态:"
    tailscale status
    
    # 获取 Site Bridge 的 Tailscale IP (使用 MagicDNS)
    if [ -n "$SITE_BRIDGE_HOSTNAME" ]; then
        echo "🔍 解析 Site Bridge 主机名: $SITE_BRIDGE_HOSTNAME"
        # 等待 DNS 解析
        sleep 2
    fi
fi

# 如果 SITE_BRIDGE_URL 未设置，尝试使用默认 Tailscale 地址
if [ -z "$SITE_BRIDGE_URL" ] && [ -n "$SITE_BRIDGE_HOSTNAME" ]; then
    export SITE_BRIDGE_URL="http://${SITE_BRIDGE_HOSTNAME}:9002"
    echo "🌐 自动设置 SITE_BRIDGE_URL: $SITE_BRIDGE_URL"
fi

# 检查必须的环境变量
echo "🔍 检查配置..."
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "❌ 错误: DEEPSEEK_API_KEY 未设置"
    exit 1
fi

if [ -z "$SITE_BRIDGE_URL" ]; then
    echo "⚠️  警告: SITE_BRIDGE_URL 未设置，拍照功能可能不可用"
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