#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云端 Oath Gateway 集成测试
测试云端 Gateway -> Site Bridge -> Jetson1 的完整链路
"""

import os
import sys
import requests
import json
import time
import urllib3
from typing import Dict, List, Optional, Tuple

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CloudIntegrationTest:
    def __init__(self):
        # 从环境变量读取配置
        self.cloud_gateway_url = os.environ.get(
            "CLOUD_GATEWAY_URL", 
            "http://localhost:8000"  # 本地测试默认
        )
        self.site_bridge_url = os.environ.get(
            "SITE_BRIDGE_URL",
            "http://localhost:9001"  # 本地测试默认
        )
        self.jetson1_camera_url = os.environ.get(
            "JETSON1_CAMERA_URL",
            "http://192.168.213.72:8800"
        )
        
        # 测试配置
        self.photo_keywords = ["拍照", "拍一張", "take photo", "capture", "照相", "攝影"]
        
    def print_header(self, text: str):
        """打印测试标题"""
        print("\n" + "="*60)
        print(f"🧪 {text}")
        print("="*60)
    
    def print_result(self, test_name: str, success: bool, message: str = None):
        """打印测试结果"""
        if success:
            print(f"✅ {test_name}: 通过")
        else:
            print(f"❌ {test_name}: 失败")
            if message:
                print(f"   错误: {message}")
    
    def test_jetson1_camera(self) -> Tuple[bool, Optional[Dict]]:
        """测试 Jetson1 相机 API"""
        self.print_header("测试 Jetson1 相机 API")
        try:
            response = requests.get(f"{self.jetson1_camera_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    self.print_result("Jetson1 相机健康检查", True)
                    print(f"   信息: {data}")
                    return True, data
                else:
                    self.print_result("Jetson1 相机健康检查", False, "响应 ok 字段为 false")
                    return False, None
            else:
                self.print_result("Jetson1 相机健康检查", False, f"状态码: {response.status_code}")
                return False, None
        except Exception as e:
            self.print_result("Jetson1 相机健康检查", False, str(e))
            return False, None
    
    def test_site_bridge_health(self) -> Tuple[bool, Optional[Dict]]:
        """测试 Site Bridge 健康状态"""
        self.print_header("测试 Site Bridge 健康状态")
        try:
            response = requests.get(f"{self.site_bridge_url}/bridge/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    self.print_result("Site Bridge 健康检查", True)
                    print(f"   信息: {data}")
                    return True, data
                else:
                    self.print_result("Site Bridge 健康检查", False, "响应 ok 字段为 false")
                    return False, None
            else:
                self.print_result("Site Bridge 健康检查", False, f"状态码: {response.status_code}")
                return False, None
        except Exception as e:
            self.print_result("Site Bridge 健康检查", False, str(e))
            return False, None
    
    def test_site_bridge_take_photo(self) -> Tuple[bool, Optional[Dict]]:
        """测试 Site Bridge 拍照功能"""
        self.print_header("测试 Site Bridge 拍照功能")
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.site_bridge_url}/bridge/take_photo",
                json={"retry": True, "timeout": 30},
                timeout=40
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    self.print_result("Site Bridge 拍照", True)
                    print(f"   文件名: {data.get('data', {}).get('filename')}")
                    print(f"   下载URL: {data.get('data', {}).get('url')}")
                    print(f"   响应时间: {elapsed:.2f}秒")
                    return True, data
                else:
                    self.print_result("Site Bridge 拍照", False, f"错误: {data.get('error')}")
                    return False, None
            else:
                self.print_result("Site Bridge 拍照", False, f"状态码: {response.status_code}")
                return False, None
        except Exception as e:
            self.print_result("Site Bridge 拍照", False, str(e))
            return False, None
    
    def test_cloud_gateway_health(self) -> Tuple[bool, Optional[Dict]]:
        """测试云端 Gateway 健康状态"""
        self.print_header("测试云端 Gateway 健康状态")
        try:
            response = requests.get(f"{self.cloud_gateway_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    self.print_result("云端 Gateway 健康检查", True)
                    print(f"   信息: {data}")
                    return True, data
                else:
                    self.print_result("云端 Gateway 健康检查", False, "响应 ok 字段为 false")
                    return False, None
            else:
                self.print_result("云端 Gateway 健康检查", False, f"状态码: {response.status_code}")
                return False, None
        except Exception as e:
            self.print_result("云端 Gateway 健康检查", False, str(e))
            return False, None
    
    def test_cloud_gateway_chat(self, message: Dict) -> Tuple[bool, Optional[Dict], float]:
        """测试云端 Gateway 聊天功能"""
        try:
            payload = {
                "model": "oath-gateway",
                "messages": [message],
                "max_tokens": 100,
                "temperature": 0.7
            }
            
            start_time = time.time()
            response = requests.post(
                f"{self.cloud_gateway_url}/v1/chat/completions",
                json=payload,
                timeout=60
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return True, data, elapsed
                else:
                    return False, None, elapsed
            else:
                return False, None, elapsed
        except Exception as e:
            return False, None, 0
    
    def test_cloud_gateway_photo_command(self) -> Tuple[bool, Optional[Dict]]:
        """测试云端 Gateway 拍照指令处理"""
        self.print_header("测试云端 Gateway 拍照指令处理")
        
        # 构建拍照指令消息
        photo_message = {
            "role": "user",
            "content": "請拍一張照片並分析亮度"
        }
        
        success, data, elapsed = self.test_cloud_gateway_chat(photo_message)
        
        if success:
            content = data["choices"][0]["message"]["content"]
            if any(keyword in content.lower() for keyword in ["拍照", "照片", "分析"]):
                self.print_result("云端 Gateway 拍照指令处理", True)
                print(f"   响应时间: {elapsed:.2f}秒")
                print(f"   响应摘要: {content[:150]}...")
                return True, data
            else:
                self.print_result("云端 Gateway 拍照指令处理", False, "响应内容不符合拍照指令预期")
                return False, None
        else:
            self.print_result("云端 Gateway 拍照指令处理", False, "聊天请求失败")
            return False, None
    
    def test_full_photo_workflow(self) -> bool:
        """测试完整拍照工作流"""
        self.print_header("测试完整拍照工作流 (云端 Gateway -> Site Bridge -> Jetson1)")
        
        print("步骤 1: 检查 Jetson1 相机连接")
        jetson_ok, _ = self.test_jetson1_camera()
        if not jetson_ok:
            self.print_result("完整工作流", False, "Jetson1 相机不可用")
            return False
        
        print("\n步骤 2: 检查 Site Bridge 连接")
        bridge_ok, _ = self.test_site_bridge_health()
        if not bridge_ok:
            self.print_result("完整工作流", False, "Site Bridge 不可用")
            return False
        
        print("\n步骤 3: 检查云端 Gateway 连接")
        cloud_ok, _ = self.test_cloud_gateway_health()
        if not cloud_ok:
            self.print_result("完整工作流", False, "云端 Gateway 不可用")
            return False
        
        print("\n步骤 4: 发送拍照指令到云端 Gateway")
        photo_ok, _ = self.test_cloud_gateway_photo_command()
        if not photo_ok:
            self.print_result("完整工作流", False, "云端 Gateway 拍照指令处理失败")
            return False
        
        print("\n步骤 5: 验证 Site Bridge 拍照功能")
        photo_data_ok, photo_data = self.test_site_bridge_take_photo()
        if not photo_data_ok:
            self.print_result("完整工作流", False, "Site Bridge 拍照失败")
            return False
        
        self.print_result("完整拍照工作流", True)
        print("🎉 所有组件正常工作！")
        return True
    
    def run_all_tests(self) -> Dict[str, bool]:
        """运行所有测试"""
        print("🚀 开始云端集成测试")
        print(f"📅 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"☁️  云端 Gateway URL: {self.cloud_gateway_url}")
        print(f"🌉 Site Bridge URL: {self.site_bridge_url}")
        print(f"🤖 Jetson1 Camera URL: {self.jetson1_camera_url}")
        
        test_results = {}
        
        # 运行测试
        test_results["Jetson1 相机健康"] = self.test_jetson1_camera()[0]
        test_results["Site Bridge 健康"] = self.test_site_bridge_health()[0]
        test_results["Site Bridge 拍照"] = self.test_site_bridge_take_photo()[0]
        test_results["云端 Gateway 健康"] = self.test_cloud_gateway_health()[0]
        test_results["云端 Gateway 拍照指令"] = self.test_cloud_gateway_photo_command()[0]
        test_results["完整工作流"] = self.test_full_photo_workflow()
        
        # 打印汇总
        self.print_header("测试结果汇总")
        
        passed = sum(test_results.values())
        total = len(test_results)
        
        print(f"📊 测试通过率: {passed}/{total} ({passed/total*100:.1f}%)")
        print()
        
        for test_name, result in test_results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{status} {test_name}")
        
        print()
        
        if passed == total:
            print("🎉 所有测试通过！云端集成架构工作正常。")
            print("下一步: 部署到生产环境并配置 Chatbot UI。")
        else:
            print("⚠️  部分测试失败，请检查:")
            for test_name, result in test_results.items():
                if not result:
                    print(f"   - {test_name}")
            
            print("\n🔧 故障排除建议:")
            print("   1. 检查环境变量配置 (CLOUD_GATEWAY_URL, SITE_BRIDGE_URL, JETSON1_CAMERA_URL)")
            print("   2. 确保所有服务正在运行")
            print("   3. 检查网络连通性和防火墙设置")
            print("   4. 查看各服务日志以获取详细信息")
        
        return test_results

def main():
    """主函数"""
    tester = CloudIntegrationTest()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "jetson":
            tester.test_jetson1_camera()
        elif sys.argv[1] == "bridge":
            tester.test_site_bridge_health()
            tester.test_site_bridge_take_photo()
        elif sys.argv[1] == "cloud":
            tester.test_cloud_gateway_health()
            tester.test_cloud_gateway_photo_command()
        elif sys.argv[1] == "workflow":
            tester.test_full_photo_workflow()
        elif sys.argv[1] == "all":
            tester.run_all_tests()
        else:
            print("用法: python test_integration.py [jetson|bridge|cloud|workflow|all]")
            print("默认运行所有测试")
            tester.run_all_tests()
    else:
        tester.run_all_tests()

if __name__ == "__main__":
    main()