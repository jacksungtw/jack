# 🚀 Oath Gateway Railway 部署指南

## 📋 前置要求

### 1. Railway 賬戶
- 註冊 [Railway](https://railway.app) 賬戶
- 安裝 Railway CLI（可選）:
  ```bash
  npm i -g @railway/cli
  ```

### 2. API 密鑰準備
- [DeepSeek API 密鑰](https://platform.deepseek.com/api_keys)
- [OpenAI API 密鑰](https://platform.openai.com/api-keys)（可選，用於備援）

### 3. Site Bridge 準備
- 地端 Site Bridge 服務已部署並運行
- 確認 Site Bridge 可從公網訪問（或使用隧道）

**⚠️ 重要提示**: Site Bridge 運行在本地網絡 (`192.168.213.72:9002`)，Railway 無法直接訪問。必須建立公網訪問通道。

**推薦解決方案**:
1. **Cloudflare Tunnel** (推薦): 無需公網 IP，安全簡單
2. **路由器端口轉發**: 需要路由器配置權限
3. **Tailscale VPN**: 創建安全的點對點網絡

**詳細指南**: 請參考 [SITE_BRIDGE_PUBLIC_ACCESS.md](../SITE_BRIDGE_PUBLIC_ACCESS.md)

## 🛠️ 部署步驟

### 方法一：GitHub 部署（推薦）

#### 步驟1：創建 GitHub 倉庫
```bash
# 克隆代碼到本地
git clone <your-repo-url>
cd cloud_oath_gateway

# 初始化 Git
git init
git add .
git commit -m "feat: initial oath gateway deployment"

# 推送到 GitHub
git remote add origin https://github.com/<username>/oath-gateway.git
git branch -M main
git push -u origin main
```

#### 步驟2：Railway 新建項目
1. 訪問 [Railway Dashboard](https://railway.app)
2. 點擊 "New Project"
3. 選擇 "Deploy from GitHub repo"
4. 選擇你的倉庫
5. Railway 自動檢測並部署

#### 步驟3：配置環境變數
1. 在 Railway 項目中點擊 "Variables"
2. 添加以下必須變數：
   ```
    SITE_BRIDGE_URL=http://你的-site-bridge-地址  # 例如: https://site-bridge.your-domain.com 或 http://公网IP:端口
    DEEPSEEK_API_KEY=sk-你的-deepseek-api-密鑰
   ```
3. 添加其他可選變數（參考 `環境變數清單.md`）

#### 步驟4：啟動服務
1. Railway 自動部署
2. 查看部署日誌
3. 訪問生成的服务 URL

### 方法二：Railway CLI 部署

#### 步驟1：安裝並登錄 CLI
```bash
# 安裝 Railway CLI
npm i -g @railway/cli

# 登錄
railway login
```

#### 步驟2：初始化項目
```bash
# 進入項目目錄
cd cloud_oath_gateway

# 初始化 Railway 項目
railway init

# 選擇創建新項目或鏈接到現有項目
```

#### 步驟3：設置環境變數
```bash
# 設置必須變數
railway variables set SITE_BRIDGE_URL=http://你的-site-bridge-地址  # 例如: https://site-bridge.your-domain.com 或 http://公网IP:端口
railway variables set DEEPSEEK_API_KEY=sk-你的-deepseek-api-密鑰

# 設置可選變數
railway variables set SERVICE_NAME=oath-gateway
railway variables set DEFAULT_MODEL=oath-gateway
```

#### 步驟4：部署
```bash
# 部署到 Railway
railway up

# 查看日誌
railway logs

# 查看服務狀態
railway status
```

### 方法三：直接上傳部署

#### 步驟1：創建新項目
1. 在 Railway Dashboard 點擊 "New Project"
2. 選擇 "Empty Project"

#### 步驟2：上傳代碼
1. 點擊 "Upload Files"
2. 選擇 `cloud_oath_gateway` 目錄中的所有文件
3. Railway 自動檢測並構建

#### 步驟3：配置環境變數
同方法一步驟3

## ⚙️ 配置詳解

### Railway 配置 (railway.json)
```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 oath_gateway:app",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

### 啟動命令解析
```bash
gunicorn --bind 0.0.0.0:$PORT \
         --workers 2 \          # Worker 數量
         --threads 4 \          # 每個 Worker 的線程數
         --timeout 120 \        # 超時時間（秒）
         oath_gateway:app       # Flask 應用入口
```

### 環境變數配置示例
```bash
# 必須配置
SITE_BRIDGE_URL=https://site-bridge.your-domain.com  # 或 http://公网IP:端口，必须可从公网访问
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx

# 推薦配置
SERVICE_NAME=oath-gateway
DEFAULT_MODEL=oath-gateway
DEBUG=false

# 可選配置
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx  # OpenAI 備援
RAG_URL=http://rag-service:8000     # RAG 服務
PHOTOS_DIR=/data/photos             # 照片存儲目錄
```

## 🧪 部署驗證

### 1. 檢查部署狀態
```bash
# Railway CLI
railway status

# 或查看 Railway Dashboard
```

### 2. 健康檢查
```bash
# 獲取服務 URL
railway environment

# 測試健康檢查
curl https://your-service.railway.app/health
```

預期響應：
```json
{
  "ok": true,
  "service": "oath-gateway",
  "config_errors": [],
  "site_bridge": {"ok": true}
}
```

### 3. API 測試
```bash
# 測試模型列表
curl https://your-service.railway.app/v1/models

# 測試聊天
curl -X POST https://your-service.railway.app/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "oath-gateway",
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```

### 4. 拍照檢查測試
```bash
# 測試拍照檢查
curl -X POST https://your-service.railway.app/tools/take_photo_inspect \
  -H "Content-Type: application/json" \
  -d '{
    "message": "請拍照並分析亮度"
  }'
```

## 🔧 進階配置

### 使用 Railway Volumes
如果需要持久化存儲照片和結果：

1. 在 Railway 項目中創建 Volume
2. 配置環境變數：
   ```bash
   PHOTOS_DIR=/data/photos
   RESULTS_DIR=/data/results
   ```
3. Railway 自動掛載 Volume

### 自定義域名
1. 在 Railway 項目中點擊 "Settings"
2. 選擇 "Domains"
3. 添加自定義域名
4. 配置 DNS 記錄

### 環境變數組
為不同環境創建變數組：
```bash
# 開發環境
railway variables --environment development set DEBUG=true

# 生產環境  
railway variables --environment production set DEBUG=false
```

## 🐛 故障排除

### 常見問題1：部署失敗
**症狀**: 構建失敗或啟動失敗

**解決方案**:
```bash
# 查看日誌
railway logs

# 常見原因：
# 1. requirements.txt 依賴問題
# 2. 環境變數缺失
# 3. 端口綁定錯誤
```

### 常見問題2：健康檢查失敗
**症狀**: `/health` 返回 `{"ok": false}`

**解決方案**:
1. 檢查 Site Bridge 連接
2. 驗證 API 密鑰
3. 檢查環境變數配置

### 常見問題3：服務無響應
**症狀**: 請求超時或 502 錯誤

**解決方案**:
```bash
# 重啟服務
railway restart

# 檢查資源使用
railway metrics

# 增加資源配額
# 在 Railway Dashboard 中調整
```

## 📈 監控與維護

### 日誌查看
```bash
# 實時日誌
railway logs --follow

# 最近100行日誌
railway logs --tail 100

# 特定時間範圍
railway logs --since "2024-01-01" --until "2024-01-02"
```

### 性能監控
1. 訪問 Railway Dashboard 的 "Metrics" 標籤
2. 查看 CPU、內存、網絡使用情況
3. 設置告警閾值

### 備份與恢復
```bash
# 導出環境變數
railway variables --export > .env.backup

# 導入環境變數
railway variables --import .env.backup

# 數據庫/Volume 備份
# 通過 Railway Dashboard 操作
```

## 🔄 更新部署

### 代碼更新
```bash
# 更新代碼
git add .
git commit -m "feat: update something"
git push origin main

# Railway 自動重新部署
```

### 配置更新
```bash
# 更新環境變數
railway variables set NEW_VAR=value

# 重啟服務使配置生效
railway restart
```

### 版本回滾
1. 在 Railway Dashboard 中選擇 "Deployments"
2. 找到要回滾的版本
3. 點擊 "Redeploy"

## 🎯 生產環境建議

### 安全配置
1. **啟用身份驗證**：添加 API 密鑰驗證
2. **限制訪問**：配置 IP 白名單
3. **啟用 HTTPS**：Railway 自動提供

### 性能優化
1. **調整 Worker 數量**：根據 CPU 核心數調整
2. **啟用緩存**：添加 Redis 緩存層
3. **CDN 加速**：使用 Cloudflare CDN

### 高可用性
1. **多區域部署**：在不同區域部署實例
2. **健康檢查**：設置自動健康檢查
3. **備份策略**：定期備份數據和配置

## 📞 支持資源

### Railway 文檔
- [Railway 官方文檔](https://docs.railway.app)
- [Flask 部署指南](https://docs.railway.app/deploy/flask)
- [環境變數管理](https://docs.railway.app/guides/variables)

### 問題反饋
1. 查看 Railway 社區論壇
2. 提交 GitHub Issue
3. 聯繫 Railway 支持

### 緊急聯繫
- Railway 狀態頁: [status.railway.app](https://status.railway.app)
- 服務監控: Railway Dashboard → Metrics
- 日誌分析: Railway Dashboard → Logs

---

**部署完成後**，請更新 Chatbot UI 配置，將 Base URL 改為你的 Oath Gateway 地址。

**下一步**：部署 Site Bridge 服務並測試端到端流程。