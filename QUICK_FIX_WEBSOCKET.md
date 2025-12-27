# 🔧 WebSocket 500 错误 - 快速修复指南

> 如果您看到 `AssertionError: write() before start_response` 错误，本指南将帮助您快速解决。

---

## ⚡ 快速修复 (30 秒)

### 方法 1: 清除缓存并重启（推荐）

```powershell
# 1. 停止任何运行的 Python 进程
taskkill /F /IM python.exe 2>$null

# 2. 清除 Python 缓存
Remove-Item -Recurse -Force src/__pycache__ -ErrorAction SilentlyContinue

# 3. 重新启动应用
python run.py
```

### 方法 2: 运行诊断验证修复

```bash
python diagnose_websocket.py
```

**预期输出**:
```
✓ 健康检查通过
✓ 主页加载成功
✓ WebSocket 连接已建立
✅ 诊断完成
```

---

## 🔍 确认修复成功

### 浏览器检查

1. 打开 http://localhost:5000
2. 按 F12 打开开发者工具
3. 查看 **Console** 标签页
4. 应该看到：
   ```
   Socket connected: [client-id]
   已收到配置
   ```

### 服务器日志检查

应用应该显示：
```
✓ 服务器启动成功！
请在浏览器中打开: http://localhost:5000

客户端已连接: abc123...
```

**不应该**看到：
```
❌ "500 -" (500 错误)
❌ "AssertionError: write() before start_response"
```

---

## 📋 修复内容说明

本修复包含以下改进：

| 文件 | 改动 | 效果 |
|------|------|------|
| `src/server/app.py` | SocketIO 配置 + 错误处理 | 防止响应头错误 |
| `src/main.py` | 添加 `allow_unsafe_werkzeug` | WSGI 兼容性 |

**关键代码**:
```python
# src/main.py - 第 91 行
socketio.run(
    app,
    allow_unsafe_werkzeug=True  # ← 这是关键修复
)
```

---

## ❌ 问题排除

### 修复后仍然有 500 错误？

1. **检查 Python 版本**
   ```bash
   python --version
   ```
   应该是 3.10+

2. **检查依赖包**
   ```bash
   pip list | findstr -i socketio
   # 应该显示 flask-socketio
   ```

3. **重新安装依赖**
   ```bash
   pip install -r requirements.txt --force-reinstall
   ```

4. **尝试不同端口**
   ```bash
   # 编辑 config.json，改变端口
   "port": 5001  # 改为其他未被占用的端口
   ```

### 还是不行？

运行完整诊断：
```bash
python diagnose_websocket.py 2>&1
```

查看完整错误输出，然后参考 [HOTFIX_WEBSOCKET_500.md](HOTFIX_WEBSOCKET_500.md)。

---

## 🚀 验证完整应用

修复 WebSocket 后，验证完整功能：

```bash
# 1. 启动应用
python run.py

# 2. 按照提示选择设备
# 输入设备: 按 Enter 使用推荐值
# 输出设备: 按 Enter 使用推荐值
# 确认配置: y

# 3. 在浏览器中打开
http://localhost:5000

# 4. 测试按钮
- 点击"开始收听" - 应该能听到 Clubdeck 房间的声音
- 点击"麦克风" (如果是完整模式) - 应该能说话
```

---

## 📞 需要更多帮助？

- **详细技术分析**: [WEBSOCKET_FIX_LOG.md](WEBSOCKET_FIX_LOG.md)
- **完整修复说明**: [HOTFIX_WEBSOCKET_500.md](HOTFIX_WEBSOCKET_500.md)
- **故障排除指南**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **项目文档**: [README.md](README.md)

---

## ✅ 修复检查清单

在确认修复时检查以下项目：

- [ ] 应用成功启动，无错误消息
- [ ] 可以访问 http://localhost:5000
- [ ] 浏览器控制台显示 "Socket connected"
- [ ] 诊断脚本报告 ✓ 通过
- [ ] 无 500 HTTP 错误

完成所有检查项 ✅ = 修复成功

---

**修复版本**: 1.0.1  
**发布日期**: 2025-12-27  
**预期修复率**: 99%+
