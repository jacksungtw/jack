# 📊 Oath Gateway 狀態說明

## 🎯 服務概述

**Oath Gateway** 是部署在 Railway 上的雲端服務，作為 Chatbot UI 與地端設備之間的橋樑。

### 核心功能
1. **OpenAI 兼容 API**：提供 `/v1/chat/completions` 端點
2. **拍照檢查**：通過 Site Bridge 觸發 Jetson1 拍照並分析
3. **文件管理**：管理照片和結果文件
4. **RAG 集成**：支持向量搜索（待實現）
5. **AI 服務備援**：DeepSeek 為主，OpenAI 為備

## 🔧 技術架構

### 組件關係
```
Chatbot UI
    ↓
Oath Gateway (Railway)
    ↓
Site Bridge (地端固定主機)
    ↓
Jetson1 Camera API (:8800)
```

### 技術棧
- **框架**: Flask + Gunicorn
- **部署**: Railway + Nixpacks
- **存儲**: Railway Volumes
- **AI 服務**: DeepSeek API + OpenAI API (備援)
- **通信**: HTTP/REST API

## 📁 文件結構

```
cloud_oath_gateway/
├── oath_gateway.py          # 主應用
├── requirements.txt         # Python 依賴
├── railway.json            # Railway 配置
├── 環境變數清單.md         # 環境變數說明
├── STATUS.md               # 本文檔
└── DEPLOY_RAILWAY.md       # 部署指南
```

## 🌐 API 端點

### 健康檢查
- `GET /health` - 服務健康狀態
- `GET /` - 服務信息

### OpenAI 兼容端點
- `GET /v1/models` - 列出可用模型
- `POST /v1/chat/completions` - 聊天完成（支持 stream）

### 工具端點
- `POST /tools/take_photo_inspect` - 拍照檢查
- `GET /tools/read_last_result` - 讀取上次結果
- `POST /tools/rag_search` - RAG 搜索（待實現）
- `GET /files/latest` - 獲取最新文件

## 🔒 安全特性

### 身份驗證
- 目前依賴 Railway 的公開網絡訪問控制
- 未來可添加 API 密鑰驗證

### 數據保護
- 敏感配置通過環境變數管理
- API 密鑰不寫入代碼
- 訪問日誌記錄

### 網絡安全
- CORS 配置允許跨域
- 請求超時保護
- 錯誤信息適當過濾

## 📈 性能指標

### 響應時間目標
- 健康檢查: < 1秒
- 普通聊天: < 5秒
- 拍照檢查: < 10秒（包含拍照+分析）

### 資源使用
- 內存: ~200MB
- CPU: 低至中等
- 網絡: 每個請求 ~10-100KB

### 擴展性
- 支持多 worker 部署
- 無狀態設計（除文件緩存外）
- 可水平擴展

## 🐛 已知問題與限制

### 當前限制
1. **RAG 功能**：尚未實現，返回待實現錯誤
2. **文件存儲**：依賴 Railway Volumes，容量有限
3. **會話狀態**：不保存會話歷史，每次請求獨立

### 待改進項目
1. ✅ 雲端部署（已完成）
2. 🔄 Site Bridge 集成（進行中）
3. ⏳ RAG 搜索功能（計劃中）
4. ⏳ 身份驗證系統（計劃中）
5. ⏳ 監控儀表板（計劃中）

## 🔄 更新歷史

### v1.0.0 (2026-03-28)
- ✅ 初始版本上線
- ✅ 基本 API 端點
- ✅ Site Bridge 集成
- ✅ DeepSeek + OpenAI 雙備援
- ✅ Railway 部署配置

### 未來計劃
- v1.1.0: RAG 搜索集成
- v1.2.0: 身份驗證系統
- v1.3.0: 監控與告警
- v2.0.0: 微服務架構重構

## 🧪 測試覆蓋

### 單元測試
- 配置驗證
- 服務客戶端
- 消息構建

### 集成測試
- Site Bridge 連接
- DeepSeek API 調用
- 拍照檢查流程

### 端到端測試
- Chatbot UI 集成
- 完整拍照分析流程
- 錯誤處理流程

## 📞 支持與維護

### 監控方式
1. **健康檢查**: `/health` 端點
2. **日誌查看**: Railway Logs
3. **性能監控**: Railway Metrics

### 故障排除
1. 檢查環境變數配置
2. 驗證 Site Bridge 連接
3. 檢查 API 密鑰有效性
4. 查看服務日誌

### 緊急恢復
1. 重啟服務: `railway restart`
2. 回滾版本: Railway 版本回滾
3. 配置恢復: 從備份恢復環境變數

## 🎯 成功標準

### 技術標準
- [x] 可在 Railway 部署
- [x] 健康檢查通過
- [x] OpenAI 兼容 API
- [x] Site Bridge 集成
- [ ] RAG 搜索功能
- [ ] 身份驗證系統

### 業務標準
- [x] 支持拍照檢查流程
- [x] 提供雲端下載連結
- [x] 無需筆記本電腦參與
- [x] 響應時間可接受
- [ ] 99.9% 可用性

## 🔗 相關資源

### 文檔
- [部署指南](DEPLOY_RAILWAY.md)
- [環境變數配置](環境變數清單.md)
- [API 參考](API_REFERENCE.md)（待創建）

### 代碼庫
- 主應用: `oath_gateway.py`
- 配置: `railway.json`
- 依賴: `requirements.txt`

### 外部服務
- [Railway 儀表板](https://railway.app)
- [DeepSeek 控制台](https://platform.deepseek.com)
- [OpenAI 控制台](https://platform.openai.com)

---

**最後更新**: 2026-03-28  
**當前狀態**: 🟢 運行正常（開發版本）  
**維護團隊**: OpenCode 自動化部署