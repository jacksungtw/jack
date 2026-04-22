#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雲端 Oath Gateway
部署在 Railway 上的固定服務
"""

import os
import json
import time
import logging
import socket
from datetime import datetime
from typing import Dict, List, Optional, Any

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import requests

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允許跨域

# ============================================================================
# 代理配置 (用於 Tailscale 用戶態網絡)
# ============================================================================

# 全局代理配置 (透過 Tailscale 用戶態網絡導航)
TAILSCALE_PROXY = {
    "http": "socks5h://localhost:1055",
    "https": "socks5h://localhost:1055"
}

# ============================================================================
# 環境變數配置
# ============================================================================

class Config:
    """配置管理"""
    
    # 服務配置
    SERVICE_NAME = os.environ.get("SERVICE_NAME", "oath-gateway")
    SERVICE_VERSION = os.environ.get("SERVICE_VERSION", "1.0.0")
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
    
    # 路徑配置
    PHOTOS_DIR = os.environ.get("PHOTOS_DIR", "/home/jetson/data/photos")
    RESULTS_DIR = os.environ.get("RESULTS_DIR", "/home/jetson/data/results")
    
    # 外部服務配置
    SITE_BRIDGE_URL = os.environ.get("SITE_BRIDGE_URL", "")
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    RAG_URL = os.environ.get("RAG_URL", "")
    
    # 公開 URL 配置
    OATH_PUBLIC_BASE = os.environ.get("OATH_PUBLIC_BASE", "")
    
    # 模型配置
    DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "oath-gateway")
    FALLBACK_MODEL = os.environ.get("FALLBACK_MODEL", "gpt-3.5-turbo")
    
    # 超時配置
    SITE_BRIDGE_TIMEOUT = int(os.environ.get("SITE_BRIDGE_TIMEOUT", "30"))
    DEEPSEEK_TIMEOUT = int(os.environ.get("DEEPSEEK_TIMEOUT", "60"))
    OPENAI_TIMEOUT = int(os.environ.get("OPENAI_TIMEOUT", "60"))
    
    @classmethod
    def validate(cls) -> List[str]:
        """驗證配置，返回錯誤列表"""
        errors = []
        
        # 必須配置
        if not cls.SITE_BRIDGE_URL:
            errors.append("SITE_BRIDGE_URL 未配置")
        
        if not cls.DEEPSEEK_API_KEY:
            errors.append("DEEPSEEK_API_KEY 未配置")
        
        # 創建目錄（可選）
        try:
            os.makedirs(cls.PHOTOS_DIR, exist_ok=True)
            os.makedirs(cls.RESULTS_DIR, exist_ok=True)
        except Exception as e:
            logger.warning(f"無法創建目錄: {e}")
        
        return errors

# ============================================================================
# 服務客戶端
# ============================================================================

class SiteBridgeClient:
    """Site Bridge 客戶端"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.timeout = Config.SITE_BRIDGE_TIMEOUT
    
    def health(self) -> Dict[str, Any]:
        """檢查 Site Bridge 健康狀態"""
        try:
            # 強制使用 Tailscale 代理
            response = requests.get(
                f"{self.base_url}/bridge/health",
                timeout=5,
                proxies=TAILSCALE_PROXY
            )
            return {
                "ok": response.status_code == 200,
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            logger.error(f"Site Bridge 健康檢查失敗: {e}")
            return {"ok": False, "error": str(e)}
    
    def take_photo(self) -> Dict[str, Any]:
        """通過 Site Bridge 拍照"""
        try:
            # 強制使用 Tailscale 代理
            response = requests.post(
                f"{self.base_url}/bridge/take_photo",
                json={},
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
                proxies=TAILSCALE_PROXY
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"拍照成功: {data}")
                photo_data = data.get('data', {})
                return {
                    "ok": True,
                    "data": data,
                    "filename": photo_data.get('filename'),
                    "url": photo_data.get('url'),
                    "timestamp": photo_data.get('ts')
                }
            else:
                logger.error(f"拍照失敗: {response.status_code}")
                return {
                    "ok": False,
                    "error": f"HTTP {response.status_code}",
                    "status_code": response.status_code
                }
                
        except Exception as e:
            logger.error(f"拍照請求失敗: {e}")
            return {"ok": False, "error": str(e)}
    
    def get_latest_photo(self) -> Optional[Dict[str, Any]]:
        """獲取最新照片"""
        try:
            response = requests.get(
                f"{self.base_url}/bridge/photo/latest",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"獲取最新照片失敗: {e}")
        return None

class DeepSeekClient:
    """DeepSeek API 客戶端"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com"
        self.timeout = Config.DEEPSEEK_TIMEOUT
    
    def chat_completion(self, messages: List[Dict], model: str = "deepseek-chat", 
                       stream: bool = False, **kwargs) -> Dict[str, Any]:
        """DeepSeek 聊天完成"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        
        try:
            if stream:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=self.timeout
                )
                return {"ok": True, "stream": True, "response": response}
            else:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return {"ok": True, "data": response.json()}
                
        except Exception as e:
            logger.error(f"DeepSeek API 錯誤: {e}")
            return {"ok": False, "error": str(e)}

class OpenAIClient:
    """OpenAI API 客戶端 (備援)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com"
        self.timeout = Config.OPENAI_TIMEOUT
    
    def chat_completion(self, messages: List[Dict], model: str = "gpt-3.5-turbo",
                       stream: bool = False, **kwargs) -> Dict[str, Any]:
        """OpenAI 聊天完成 (備援)"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return {"ok": True, "data": response.json()}
        except Exception as e:
            logger.error(f"OpenAI API 錯誤: {e}")
            return {"ok": False, "error": str(e)}

# ============================================================================
# 核心服務邏輯
# ============================================================================

class OathGatewayService:
    """Oath Gateway 核心服務"""
    
    def __init__(self):
        self.site_bridge = SiteBridgeClient(Config.SITE_BRIDGE_URL)
        self.deepseek = DeepSeekClient(Config.DEEPSEEK_API_KEY)
        self.openai = OpenAIClient(Config.OPENAI_API_KEY) if Config.OPENAI_API_KEY else None
        
        # 狀態追蹤
        self.last_photo_result = None
        self.last_analysis_result = None
        
    def process_photo_inspection(self, user_message: str) -> Dict[str, Any]:
        """
        處理拍照檢查請求
        返回: {"ok": bool, "photo_data": dict, "analysis": str, "download_url": str}
        """
        logger.info(f"處理拍照檢查: {user_message}")
        
        # 1. 拍照
        photo_result = self.site_bridge.take_photo()
        if not photo_result["ok"]:
            return {
                "ok": False,
                "error": f"拍照失敗: {photo_result.get('error')}",
                "step": "take_photo"
            }
        
        # 修正：正確提取 filename 和 url (從 photo_result 直接讀取，因為 SiteBridgeClient 已經幫我們提取過了)
        filename = photo_result.get("filename")
        photo_url = photo_result.get("url")
        photo_data = photo_result.get("data", {}) # 保留原始 JSON 給 AI 分析

        # 智能轉換：如果網址是私有 IP，轉換為 Tailscale 節點 IP 以確保外部可連
        if photo_url and ("192.168." in photo_url or "127.0.0.1" in photo_url or "localhost" in photo_url):
            import urllib.parse
            parsed = urllib.parse.urlparse(photo_url)
            # 獲取 Site Bridge 的 host (100.88.112.41)
            bridge_host = urllib.parse.urlparse(Config.SITE_BRIDGE_URL).hostname
            if bridge_host:
                photo_url = parsed._replace(netloc=f"{bridge_host}:{parsed.port or 8800}").geturl()
                logger.info(f"網址已轉換為 Tailscale IP: {photo_url}")
        
        # 保存照片信息
        self.last_photo_result = {
            "filename": filename,
            "url": photo_url,
            "timestamp": datetime.now().isoformat(),
            "data": photo_data
        }
        
        # 2. 準備分析消息
        messages = self._build_inspection_messages(user_message, photo_data)
        
        # 3. 調用 AI 分析
        ai_result = self._call_ai_for_analysis(messages)
        if not ai_result["ok"]:
            return {
                "ok": False,
                "error": f"AI 分析失敗: {ai_result.get('error')}",
                "step": "ai_analysis",
                "photo_data": photo_data
            }
        
        analysis_text = ai_result["analysis"]
        
        # 4. 構建響應
        response = self._build_oath_response(
            filename=filename,
            photo_url=photo_url,
            analysis=analysis_text,
            user_message=user_message
        )
        
        # 保存分析結果
        self.last_analysis_result = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "analysis": analysis_text,
            "photo_data": photo_data,
            "response": response
        }
        
        return {
            "ok": True,
            "photo_data": photo_data,
            "analysis": analysis_text,
            "response": response,
            "download_url": photo_url
        }
    
    def _build_inspection_messages(self, user_message: str, photo_data: Dict) -> List[Dict]:
        """構建拍照檢查消息"""
        system_prompt = """你是一個智能相機助手，專門分析照片的亮度、顏色和視覺特徵。
        
請根據用戶的指令和照片信息，提供專業的分析報告。

分析時請關注：
1. 亮度分類（過暗/正常/過亮）
2. 主色傾向（偏冷/偏暖/色彩平衡）
3. 平均亮度估算
4. 視覺質量評價
5. 改進建議

請以清晰、專業的方式回復。"""
        
        # 修正：正確從嵌套的 data 中獲取資訊
        real_photo_info = photo_data.get("data", {}) if "data" in photo_data else photo_data
        
        photo_info = json.dumps({
            "filename": real_photo_info.get("filename"),
            "timestamp": real_photo_info.get("ts"),
            "download_url": real_photo_info.get("url"),
            "note": "照片可通過提供的URL下載查看"
        }, ensure_ascii=False, indent=2)
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"用戶指令: {user_message}\n\n照片信息:\n{photo_info}\n\n請分析照片並提供詳細報告。"}
        ]
    
    def _call_ai_for_analysis(self, messages: List[Dict]) -> Dict[str, Any]:
        """調用 AI 進行分析，支持備援"""
        # 首先嘗試 DeepSeek
        result = self.deepseek.chat_completion(
            messages=messages,
            model="deepseek-chat",
            max_tokens=500,
            temperature=0.7
        )
        
        if result["ok"]:
            content = result["data"]["choices"][0]["message"]["content"]
            return {"ok": True, "analysis": content, "provider": "deepseek"}
        
        # DeepSeek 失敗，嘗試 OpenAI 備援
        if self.openai:
            logger.warning("DeepSeek 失敗，嘗試 OpenAI 備援")
            result = self.openai.chat_completion(
                messages=messages,
                model=Config.FALLBACK_MODEL,
                max_tokens=500,
                temperature=0.7
            )
            
            if result["ok"]:
                content = result["data"]["choices"][0]["message"]["content"]
                return {"ok": True, "analysis": content, "provider": "openai"}
        
        return {"ok": False, "error": "所有 AI 服務均失敗"}
    
    def _build_oath_response(self, filename: str, photo_url: str, 
                           analysis: str, user_message: str) -> str:
        """構建誓語格式的響應"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        response = f"願主師父在上，弟子回報：\n"
        response += f"時間：{timestamp}\n"
        response += f"（1）拍照完成：{filename if filename else '照片已拍攝'}\n"
        response += f"（2）照片連結：{photo_url if photo_url else '無有效連結'}\n"
        response += f"（3）分析結果：\n{analysis}\n"
        response += f"（4）用戶指令：{user_message}\n"
        
        return response
    
    def get_latest_files(self) -> Dict[str, Any]:
        """獲取最新文件信息"""
        result = {
            "photo": self.last_photo_result,
            "analysis": self.last_analysis_result,
            "timestamp": datetime.now().isoformat()
        }
        
        # 嘗試從 Site Bridge 獲取最新照片
        latest_photo = self.site_bridge.get_latest_photo()
        if latest_photo:
            result["latest_photo_from_bridge"] = latest_photo
        
        return result
    
    def rag_search(self, query: str) -> Dict[str, Any]:
        """RAG 搜索（待實現）"""
        if not Config.RAG_URL:
            return {"ok": False, "error": "RAG_URL 未配置"}
        
        # TODO: 實現 RAG 搜索
        return {"ok": False, "error": "RAG 功能待實現"}
    
    @staticmethod
    def _is_photo_command(text: str) -> bool:
        """判斷是否為拍照指令"""
        photo_keywords = ["拍照", "拍一張", "take photo", "capture", "照相", "攝影"]
        text_lower = text.lower()
        
        for keyword in photo_keywords:
            if keyword in text_lower:
                return True
        return False

# ============================================================================
# Flask 路由
# ============================================================================

# 初始化服務
service = OathGatewayService()

@app.route('/')
def index():
    """首頁"""
    return jsonify({
        "service": Config.SERVICE_NAME,
        "version": Config.SERVICE_VERSION,
        "status": "running",
        "endpoints": {
            "GET /health": "健康檢查",
            "GET /files/latest": "獲取最新文件",
            "POST /v1/chat/completions": "OpenAI 兼容聊天",
            "POST /tools/take_photo_inspect": "拍照檢查",
            "GET /tools/read_last_result": "讀取上次結果",
            "POST /tools/rag_search": "RAG 搜索"
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """健康檢查"""
    # 檢查配置
    config_errors = Config.validate()
    
    # 檢查 Site Bridge 連接
    bridge_health = service.site_bridge.health()
    
    status = {
        "ok": len(config_errors) == 0 and bridge_health["ok"],
        "service": Config.SERVICE_NAME,
        "version": Config.SERVICE_VERSION,
        "timestamp": datetime.now().isoformat(),
        "config_errors": config_errors,
        "site_bridge": bridge_health,
        "deepseek_configured": bool(Config.DEEPSEEK_API_KEY),
        "openai_configured": bool(Config.OPENAI_API_KEY),
        "rag_configured": bool(Config.RAG_URL)
    }
    
    return jsonify(status)

@app.route('/files/latest', methods=['GET'])
def get_latest_files():
    """獲取最新文件"""
    try:
        files = service.get_latest_files()
        return jsonify({
            "ok": True,
            "files": files,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"獲取最新文件失敗: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/v1/models', methods=['GET'])
def list_models():
    """列出可用模型 (OpenAI 兼容)"""
    return jsonify({
        "object": "list",
        "data": [
            {
                "id": Config.DEFAULT_MODEL,
                "object": "model",
                "owned_by": "oath-gateway",
                "created": 1704067200
            }
        ]
    })

@app.route('/chat/completions', methods=['POST'])
@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """聊天完成 (OpenAI 兼容)"""
    try:
        data = request.get_json(force=True)
        
        # 提取參數
        messages = data.get("messages", [])
        model = data.get("model", Config.DEFAULT_MODEL)
        stream = data.get("stream", False)
        max_tokens = data.get("max_tokens", 500)
        temperature = data.get("temperature", 0.7)
        
        if not messages:
            return jsonify({"error": "No messages provided"}), 400
        
        # 檢查是否為拍照指令
        user_message = messages[-1]["content"] if messages else ""
        if service._is_photo_command(user_message):
            # 這是拍照指令，調用拍照檢查
            result = service.process_photo_inspection(user_message)
            
            if result["ok"]:
                response_text = result["response"]
                
                if stream:
                    # 如果需要流式響應，模擬 OpenAI 格式的流
                    def generate_photo_stream():
                        chunk_id = f"chatcmpl-{int(time.time())}"
                        # 模擬一個字一個字傳出的效果 (或者直接傳一整塊但符合格式)
                        # 為求穩定，我們先傳一個包含完整內容的 chunk
                        chunk = {
                            "id": chunk_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": response_text},
                                "finish_reason": None
                            }]
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                        
                        # 發送結束標誌
                        end_chunk = {
                            "id": chunk_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {},
                                "finish_reason": "stop"
                            }]
                        }
                        yield f"data: {json.dumps(end_chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                    
                    return Response(
                        stream_with_context(generate_photo_stream()),
                        mimetype='text/event-stream'
                    )
                else:
                    # 非流式響應
                    return jsonify({
                        "id": f"chatcmpl-{int(time.time())}",
                        "object": "chat.completion",
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": response_text
                            },
                            "finish_reason": "stop"
                        }]
                    })
            else:
                return jsonify({
                    "error": {
                        "message": f"拍照檢查失敗: {result.get('error')}",
                        "type": "photo_capture_error"
                    }
                }), 500
        
        # 普通聊天，調用 DeepSeek
        result = service.deepseek.chat_completion(
            messages=messages,
            model="deepseek-chat",
            stream=stream,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        if not result["ok"]:
            # 嘗試 OpenAI 備援
            if service.openai:
                result = service.openai.chat_completion(
                    messages=messages,
                    model=Config.FALLBACK_MODEL,
                    stream=stream,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            
            if not result["ok"]:
                return jsonify({
                    "error": {
                        "message": f"AI 服務失敗: {result.get('error')}",
                        "type": "ai_service_error"
                    }
                }), 500
        
        if stream:
            # 流式響應
            def generate():
                try:
                    for chunk in result["response"].iter_content(chunk_size=None):
                        if chunk:
                            yield chunk
                except Exception as e:
                    logger.error(f"流式響應錯誤: {e}")
            
            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream'
            )
        else:
            # 普通響應
            return jsonify(result["data"])
            
    except Exception as e:
        logger.error(f"聊天完成錯誤: {e}")
        return jsonify({
            "error": {
                "message": str(e),
                "type": "internal_error"
            }
        }), 500

@app.route('/tools/take_photo_inspect', methods=['POST'])
def take_photo_inspect():
    """拍照檢查工具端點"""
    try:
        data = request.get_json(force=True) or {}
        user_message = data.get("message", "請拍照並分析亮度與偏色")
        
        result = service.process_photo_inspection(user_message)
        
        if result["ok"]:
            return jsonify({
                "ok": True,
                "message": "拍照檢查完成",
                "photo_data": result["photo_data"],
                "analysis": result["analysis"],
                "response": result["response"],
                "download_url": result["download_url"],
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "ok": False,
                "error": result.get("error"),
                "step": result.get("step"),
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"拍照檢查錯誤: {e}")
        return jsonify({
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/tools/read_last_result', methods=['GET'])
def read_last_result():
    """讀取上次結果"""
    try:
        return jsonify({
            "ok": True,
            "last_photo": service.last_photo_result,
            "last_analysis": service.last_analysis_result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"讀取上次結果錯誤: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/tools/rag_search', methods=['POST'])
def rag_search():
    """RAG 搜索"""
    try:
        data = request.get_json(force=True)
        query = data.get("query", "")
        
        if not query:
            return jsonify({"ok": False, "error": "未提供查詢內容"}), 400
        
        result = service.rag_search(query)
        
        if result["ok"]:
            return jsonify({
                "ok": True,
                "query": query,
                "results": result.get("results", []),
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "ok": False,
                "error": result.get("error"),
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"RAG 搜索錯誤: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/diagnostics', methods=['GET'])
def diagnostics():
    """診斷端點 - 測試連線與設定"""
    try:
        # 基本服務資訊
        diagnostics_info = {
            "service": Config.SERVICE_NAME,
            "version": Config.SERVICE_VERSION,
            "timestamp": datetime.now().isoformat(),
            "environment": {
                "SITE_BRIDGE_URL": Config.SITE_BRIDGE_URL,
                "TAILSCALE_AUTHKEY_set": bool(os.environ.get("TAILSCALE_AUTHKEY")),
                "DEBUG": Config.DEBUG,
                "HOST": os.environ.get("HOST", "0.0.0.0"),
                "PORT": os.environ.get("PORT", "8000")
            }
        }
        
        # 動態解析 SITE_BRIDGE_URL
        import urllib.parse
        parsed_bridge = urllib.parse.urlparse(Config.SITE_BRIDGE_URL)
        bridge_host = parsed_bridge.hostname or "100.88.112.41"
        bridge_port = parsed_bridge.port or 9001
        
        # 網路連線測試
        network_tests = []
        
        # 1. 測試 bridge 連線
        try:
            # TCP 連線測試
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            tcp_result = sock.connect_ex((bridge_host, bridge_port))
            sock.close()
            
            network_tests.append({
                "test": "tcp_connect",
                "target": f"{bridge_host}:{bridge_port}",
                "success": tcp_result == 0,
                "error_code": tcp_result if tcp_result != 0 else None,
                "error_message": os.strerror(tcp_result) if tcp_result != 0 else None
            })
            
            # HTTP 健康檢查測試
            try:
                response = requests.get(f"http://{bridge_host}:{bridge_port}/health", timeout=5)
                network_tests.append({
                    "test": "http_health_check",
                    "target": f"http://{bridge_host}:{bridge_port}/health",
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "response_time_ms": response.elapsed.total_seconds() * 1000 if hasattr(response, 'elapsed') else None
                })
            except Exception as e:
                network_tests.append({
                    "test": "http_health_check",
                    "target": f"http://{bridge_host}:{bridge_port}/health",
                    "success": False,
                    "error": str(e)
                })
                
        except Exception as e:
            network_tests.append({
                "test": "tcp_connect",
                "target": f"{bridge_host}:{bridge_port}",
                "success": False,
                "error": str(e)
            })
        
        # 2. 測試本地迴路
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            local_result = sock.connect_ex(("127.0.0.1", int(os.environ.get("PORT", 8000))))
            sock.close()
            network_tests.append({
                "test": "localhost_service",
                "target": f"127.0.0.1:{os.environ.get('PORT', 8000)}",
                "success": local_result == 0,
                "error_code": local_result if local_result != 0 else None
            })
        except Exception as e:
            network_tests.append({
                "test": "localhost_service",
                "target": f"127.0.0.1:{os.environ.get('PORT', 8000)}",
                "success": False,
                "error": str(e)
            })
        
        # 3. DNS 解析測試
        try:
            resolved_ip = socket.gethostbyname(bridge_host)
            network_tests.append({
                "test": "dns_resolution",
                "hostname": bridge_host,
                "resolved_ip": resolved_ip,
                "success": True
            })
        except Exception as e:
            network_tests.append({
                "test": "dns_resolution",
                "hostname": bridge_host,
                "success": False,
                "error": str(e)
            })
        
        diagnostics_info["network_tests"] = network_tests
        
        # Site Bridge 客戶端測試
        bridge_health = service.site_bridge.health()
        diagnostics_info["site_bridge"] = {
            "health_check": bridge_health,
            "client_base_url": service.site_bridge.base_url,
            "client_timeout": service.site_bridge.timeout
        }
        
        # 總結狀態
        all_network_tests_pass = all(test.get("success", False) for test in network_tests)
        diagnostics_info["summary"] = {
            "all_tests_pass": all_network_tests_pass and bridge_health["ok"],
            "network_tests_pass": all_network_tests_pass,
            "bridge_health_ok": bridge_health["ok"],
            "service_healthy": len(Config.validate()) == 0
        }
        
        return jsonify(diagnostics_info)
        
    except Exception as e:
        logger.error(f"診斷端點錯誤: {e}")
        return jsonify({
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

# ============================================================================
# 輔助函數
# ============================================================================



# ============================================================================
# 啟動應用
# ============================================================================

if __name__ == '__main__':
    # 驗證配置
    errors = Config.validate()
    if errors:
        logger.error("配置驗證失敗:")
        for error in errors:
            logger.error(f"  - {error}")
        logger.warning("繼續啟動，但部分功能可能不可用")
    
    # 啟動服務
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    
    logger.info(f"啟動 {Config.SERVICE_NAME} v{Config.SERVICE_VERSION}")
    logger.info(f"監聽: {host}:{port}")
    logger.info(f"Site Bridge URL: {Config.SITE_BRIDGE_URL}")
    logger.info(f"DeepSeek API 已配置: {bool(Config.DEEPSEEK_API_KEY)}")
    logger.info(f"OpenAI API 已配置: {bool(Config.OPENAI_API_KEY)}")
    
    app.run(host=host, port=port, debug=Config.DEBUG)