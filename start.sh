#!/bin/bash
# Oath Gateway 啟動入口 (重定向至增強版啟動腳本)

set -e  # 出錯時退出

echo "🚀 開始啟動 Oath Gateway (透過統一啟動器)..."

# 1. 檢查必須的 API Key
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "❌ 錯誤: DEEPSEEK_API_KEY 未設置"
    exit 1
fi

# 2. 授權並執行增強版 Tailscale 與 Gunicorn 啟動腳本
# 這會確保所有代理設置、SOCKS5 插件與連線測試都被正確執行
chmod +x ./start_tailscale.sh
exec ./start_tailscale.sh
