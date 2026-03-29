# 🔐 Tailscale VPN 配置指南

## 📋 概述

本指南指导您配置 Tailscale VPN，使 Railway 上的 Oath Gateway 能够安全访问本地网络的 Site Bridge。

## 🎯 架构

```
Railway Oath Gateway (Tailscale 客户端)
        ↓
Tailscale VPN 网络
        ↓
Jetson Site Bridge (Tailscale 节点: yahboom)
        ↓
Jetson1 Camera API (:8800)
```

## 🚀 配置步骤

### 步骤 1: 生成 Tailscale 认证密钥

1. **登录 Tailscale 管理面板**
   - 访问: https://login.tailscale.com/admin/authkeys
   - 使用您的 Tailscale 账户登录

2. **生成可重用认证密钥**
   - 点击 "Generate auth key"
   - 设置选项:
     - **Description**: `Railway Oath Gateway`
     - **Expiry**: 选择 "No expiration" (永久有效)
     - **Reusable**: ✅ 勾选 (重要!)
     - **Ephemeral**: ❌ 不要勾选
     - **Tags**: 可选，如 `tag:railway`
   - 点击 "Generate key"
   - **立即复制并保存密钥** (只显示一次)
   - 密钥格式: `tskey-auth-xxxxxxxxxxxxxxxxxxxxxxxx`

### 步骤 2: 配置 Railway 环境变量

在 Railway Dashboard → Variables 中添加:

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `TAILSCALE_AUTHKEY` | `tskey-auth-xxxxxxxxxxxxxxxxxxxxxxxx` | 步骤1生成的密钥 |
| `SITE_BRIDGE_HOSTNAME` | `yahboom` | Jetson的Tailscale主机名 |
| `SITE_BRIDGE_URL` | `http://yahboom:9002` | 通过Tailscale访问Site Bridge |
| `DEEPSEEK_API_KEY` | `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` | DeepSeek API密钥 |
| `SERVICE_NAME` | `oath-gateway` | 服务名称 |
| `DEFAULT_MODEL` | `oath-gateway` | 默认模型名称 |

### 步骤 3: 部署到 Railway

1. **推送更新后的代码**
   ```bash
   cd /home/jetson/jetson1/cloud_oath_gateway
   git add .
   git commit -m "feat: add tailscale integration"
   git push origin main
   ```

2. **Railway 自动部署**
   - Railway 检测到代码更新
   - 自动构建并部署
   - 查看部署日志确认 Tailscale 安装

### 步骤 4: 验证部署

#### 4.1 检查 Railway 日志
在 Railway Dashboard → Deployments → 点击最新部署 → 查看日志，确认:
- ✅ Tailscale 安装成功
- ✅ Tailscale 连接成功
- ✅ Gunicorn 启动成功

#### 4.2 测试健康检查
```bash
curl https://你的-oath-gateway.railway.app/health
```

预期响应包含:
```json
{
  "ok": true,
  "service": "oath-gateway",
  "site_bridge": {"ok": true}
}
```

#### 4.3 测试 Tailscale 连接
从 Railway 日志中查找 Tailscale 状态:
```
🔧 安装并配置 Tailscale...
🔑 使用认证密钥连接 Tailscale...
✅ Tailscale 连接成功
📡 Tailscale 状态:
100.xx.xx.xx oath-gateway-railway  admin@  linux   -
100.88.112.41 yahboom              admin@  linux   -
```

### 步骤 5: 配置 Site Bridge (Jetson)

确保 Jetson 上的 Site Bridge 正常运行:

```bash
# 检查 Site Bridge 状态
curl http://localhost:9002/bridge/health

# 检查 Tailscale 状态
tailscale status
```

## 🔧 故障排除

### Tailscale 连接失败

#### 问题 1: 认证密钥无效
**症状**: Railway 日志显示认证失败
**解决**:
1. 重新生成认证密钥
2. 确保密钥设置为 "Reusable"
3. 更新 Railway 环境变量

#### 问题 2: 网络连接问题
**症状**: Tailscale 无法建立连接
**解决**:
1. 检查 Jetson 的 Tailscale 状态: `tailscale status`
2. 确保 Jetson 在线: `tailscale ping yahboom`
3. 检查防火墙设置

#### 问题 3: MagicDNS 不工作
**症状**: Railway 无法解析 `yahboom` 主机名
**解决**:
1. 在 Railway 启动脚本中添加 `--accept-dns` 参数
2. 使用 IP 地址代替主机名:
   ```bash
   # 获取 yahboom 的 Tailscale IP
   tailscale status --json | jq -r '.Peer[] | select(.HostName=="yahboom") | .TailscaleIPs[0]'
   ```
3. 更新 `SITE_BRIDGE_URL` 使用 IP 地址

### Site Bridge 连接失败

#### 问题 1: 端口不可达
**症状**: `site_bridge: {"ok": false}`
**解决**:
1. 检查 Site Bridge 是否运行: `curl http://localhost:9002/bridge/health`
2. 检查防火墙: `sudo ufw status` (如果需要)
3. 确保 Site Bridge 监听 `0.0.0.0`:9002

#### 问题 2: 权限问题
**症状**: 连接被拒绝
**解决**:
1. 检查 Site Bridge 日志
2. 确保没有 API 密钥验证阻止连接

### Railway 构建失败

#### 问题 1: Tailscale 安装失败
**解决**:
1. 检查 `start.sh` 脚本权限: `chmod +x start.sh`
2. 查看 Nixpacks 日志
3. 尝试简化安装命令

#### 问题 2: 内存不足
**症状**: 容器崩溃
**解决**:
1. Railway Dashboard → Settings → Resources
2. 增加内存限制
3. 减少 Gunicorn workers (修改 `start.sh`)

## 🛠️ 高级配置

### 使用子网路由器 (可选)
如果需要在 Tailscale 网络中访问其他本地设备:

1. **在 Jetson 上启用子网路由器**:
   ```bash
   sudo tailscale up --advertise-routes=192.168.213.0/24 --accept-routes
   ```

2. **在 Tailscale 管理面板批准路由**
3. **Railway 容器将能访问整个子网**

### 多环境配置
- **开发环境**: 使用 ephemeral 密钥
- **生产环境**: 使用永久密钥 + 严格访问控制
- **测试环境**: 使用单独的 Tailscale network

### 监控与日志
- **Tailscale 日志**: Railway 启动日志
- **连接监控**: `tailscale ping yahboom`
- **网络诊断**: `tailscale netcheck`

## 🔒 安全最佳实践

1. **密钥管理**
   - 定期轮换认证密钥
   - 使用不同的密钥用于不同环境
   - 不要在代码中硬编码密钥

2. **访问控制**
   - 使用 Tailscale ACLs 限制访问
   - 为 Railway 容器分配特定标签
   - 定期审查访问日志

3. **网络隔离**
   - 考虑使用单独的 Tailscale network
   - 限制子网路由范围
   - 启用退出节点控制

## 📞 支持

### Tailscale 资源
- **官方文档**: https://tailscale.com/kb/
- **故障排除**: https://tailscale.com/kb/1017/troubleshooting
- **社区支持**: https://github.com/tailscale/tailscale/discussions

### Railway 支持
- **文档**: https://docs.railway.app
- **Discord**: https://discord.gg/railway

### 本地调试命令
```bash
# 检查 Tailscale 状态
tailscale status
tailscale ping yahboom
tailscale netcheck

# 检查 Site Bridge
curl http://localhost:9002/bridge/health
curl http://100.88.112.41:9002/bridge/health

# 检查 Railway 连接
curl https://你的-oath-gateway.railway.app/health
```

## 🎯 成功标准

- [ ] Tailscale 认证密钥生成并配置
- [ ] Railway 环境变量正确设置
- [ ] Railway 部署成功，Tailscale 连接正常
- [ ] Oath Gateway 健康检查通过
- [ ] Site Bridge 连接测试成功
- [ ] 拍照分析功能正常工作
- [ ] 无需公网 IP 或端口转发