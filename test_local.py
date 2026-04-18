#!/usr/bin/env python3
# 本地测试脚本

import os
import sys
import subprocess

print("🔧 测试 Oath Gateway 本地启动...")

# 设置环境变量
env = os.environ.copy()
env['DEEPSEEK_API_KEY'] = 'sk-9ba6e495d5db4d1b83720b14aafff6c1'
env['SITE_BRIDGE_URL'] = 'http://localhost:9002'
env['PORT'] = '8000'
env['SERVICE_NAME'] = 'oath-gateway'
env['DEFAULT_MODEL'] = 'oath-gateway'
env['DEBUG'] = 'false'

# 测试导入
print("🐍 测试 Python 导入...")
try:
    import flask
    import requests
    import gunicorn
    print(f"✅ Flask: {flask.__version__}")
    print(f"✅ Requests: {requests.__version__}")
    print(f"✅ Gunicorn: {gunicorn.__version__}")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)

# 测试应用导入
print("📦 测试应用导入...")
try:
    from oath_gateway import app
    print("✅ 应用导入成功")
except Exception as e:
    print(f"❌ 应用导入失败: {e}")
    sys.exit(1)

print("🎉 所有测试通过！")
print("运行命令: gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 4 oath_gateway:app")
