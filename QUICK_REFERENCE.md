# ClubVoice 快速参考指南

> 本指南提供 ClubVoice 项目的快速查询和常见任务的解决方案。详细信息请参考 `.github/copilot-instructions.md`。

---

## 🚀 快速开始

### 启动应用

```bash
# 开发模式（交互式设备选择）
python run.py

# 遵循提示：
# 1. 选择输入设备 (推荐: 10 - CABLE Output)
# 2. 选择输出设备 (推荐: 10 - CABLE Input)  
# 3. 确认配置 [y/n]
# 4. 访问 http://localhost:5000
```

### 构建 EXE

```powershell
# VS Code 中
Ctrl+Shift+B  # 显示构建任务菜单

# 或使用 PowerShell
cd D:\Code\ClubVoice
pyinstaller ClubVoice.spec -y
```

---

## 📋 常见任务

### 选择正确的设备

**问题**: 应用选择了 16ch CABLE 设备

**解决方案**: 应用已优化以自动选择 2ch 设备。如需手动选择：
- 在设备列表中查找 **`CABLE Output (VB-Audio Virtual Cable) - 2ch`**
- 避免名称中包含 `16ch` 的设备
- 推荐的设备会用 ★ 标记

**代码位置**: [src/audio/device_manager.py#L283-L310](src/audio/device_manager.py#L283-L310)

---

### 修复 WebSocket 连接错误

**问题**: "HTTP 500" 或 "write() before start_response"

**诊断步骤**:
1. 检查应用启动是否完成（应显示 "Running on http://...")
2. 查看浏览器控制台是否有 JavaScript 错误
3. 检查防火墙是否阻止了 5000 端口

**已应用的修复** ([src/server/app.py#L26-L35](src/server/app.py#L26-L35)):
```python
ping_timeout=60        # 增加超时时间
ping_interval=25       # 配置心跳
max_http_buffer_size=1e6  # 支持更大的帧
```

---

### 处理音频初始化错误

**问题**: "Error opening OutputStream: Invalid number of channels"

**原因**: 设备声道数不匹配

**解决方案**:
1. 验证所选设备支持 2 声道输出（使用 sounddevice）
2. 尝试选择不同的设备
3. 检查设备是否被其他应用占用

```python
# 调试: 检查设备信息
import sounddevice as sd
devices = sd.query_devices()
for i, device in enumerate(devices):
    print(f"{i}: {device['name']} - "
          f"{device['max_output_channels']} out")
```

---

### 添加新的 WebSocket 事件

1. **在服务器端添加处理器** ([src/server/websocket_handler.py](src/server/websocket_handler.py#L51-L130)):
```python
@self.socketio.on('my_event')
def handle_my_event(data):
    console.print(f"[cyan]接收事件: {data}[/cyan]")
    emit('my_response', {'result': 'ok'})
```

2. **在客户端监听事件** ([static/js/client.js](static/js/client.js#L81-L115)):
```javascript
this.socket.on('my_response', (data) => {
    console.log('服务器响应:', data);
});

// 发送事件
this.socket.emit('my_event', { foo: 'bar' });
```

---

### 修改音频参数

**采样率/通道数配置**:
- 默认配置: [src/config/settings.py#L22-L33](src/config/settings.py#L22-L33)
- 运行时设置: 在 device selection 后动态应用

**修改步骤**:
```python
# src/config/settings.py
@dataclass
class AudioConfig:
    sample_rate: int = 48000        # ← 修改采样率
    channels: int = 2               # ← 修改通道数
    chunk_size: int = 512           # ← 修改缓冲区大小
```

---

### 部署到 B560 网络共享

```powershell
# 自动部署
Ctrl+Shift+B  # 选择 "Full Build"

# 或手动执行
pyinstaller ClubVoice.spec -y
Copy-Item -Path .\dist\* -Destination '\\b560\code\voice-communication-app' -Recurse -Force
```

**部署目标**: `\\b560\code\voice-communication-app`  
**备份位置**: `\\b560\code\bak\`  
**备份格式**: `voice-communication-app_20240115_143022`（带时间戳）

---

### 本地部署到 D:\Code

```powershell
# VS Code 任务
Ctrl+Shift+B  # 选择 "Deploy to Local"

# 部署位置
D:\Code\ClubVoice-Deploy
```

---

### 调试音频问题

**启用详细日志**:
```python
# src/server/websocket_handler.py
if random.randint(1, 10) == 1:  # 每 10 次打印 1 次
    console.print(f"[dim blue]音频接收: {max_amplitude}[/dim blue]")
```

**监控音频级别**:
- 访问 http://localhost:5000/debug.html
- 查看实时音频输入/输出级别图表

**测试音频流**:
```python
# test_16ch.py - 测试 16 通道设备
python test_16ch.py
```

---

## 🔍 故障排除

### 应用启动缓慢

**症状**: 设备选择后启动需要 > 10 秒

**原因**: sounddevice 初始化或 ALSA 配置

**解决**:
```bash
# 压制 ALSA 警告（Linux 系统）
export ALSA_CARD=default

# 或在代码中
import warnings
warnings.filterwarnings('ignore', message='.*ALSA.*')
```

---

### WebSocket 频繁断开

**症状**: 连接 5-10 秒后掉线

**检查**:
1. 防火墙或代理设置
2. 路由器或 WiFi 不稳定
3. 浏览器标签页被暂停

**配置调整** ([src/server/app.py#L26-L35](src/server/app.py#L26-L35)):
```python
socketio = SocketIO(
    app,
    ping_timeout=60,   # 从 60 增加到 90
    ping_interval=25,  # 从 25 增加到 15
)
```

---

### 音频延迟高

**症状**: 说话和听到回声之间有 > 200ms 延迟

**优化**:
```python
# 减小缓冲区
chunk_size=256  # 从 512 减小

# 减小播放缓冲
playback_latency=0.02  # 从 0.05 减小到 0.02
```

**权衡**: 过小的缓冲可能导致音频卡顿

---

## 📚 文档导航

| 文档 | 内容 | 适用于 |
|------|------|--------|
| [.github/copilot-instructions.md](.github/copilot-instructions.md) | 完整架构和工作流 | AI 代理、新开发者 |
| [TECHNICAL_SUMMARY.md](TECHNICAL_SUMMARY.md) | 问题、解决方案和改进 | 技术审查 |
| [ACCEPTANCE_REPORT.md](ACCEPTANCE_REPORT.md) | 验收测试结果 | 项目经理、QA |
| [COMPLETION_CHECKLIST.md](COMPLETION_CHECKLIST.md) | 完成项目清单 | 项目追踪 |
| [DUAL_CABLE_SETUP.md](DUAL_CABLE_SETUP.md) | VB-Cable 硬件配置 | 系统管理员 |
| [MPV_MUSIC_SETUP.md](MPV_MUSIC_SETUP.md) | MPV 音乐配置 | 音频工程师 |
| [README.md](README.md) | 项目概述和使用说明 | 所有人 |

---

## 🐛 报告问题

### 有效的问题报告包括

1. **症状描述**: 具体发生了什么
2. **复现步骤**: 如何重现问题
3. **日志输出**: 控制台错误信息
4. **系统信息**: Windows 版本、Python 版本、设备信息

### 常见问题和答案

**Q: 为什么应用每次启动都要选择设备？**  
A: 这是设计选择，允许灵活配置。未来版本将支持在 config.json 中保存设备选择。

**Q: 可以连接多个浏览器客户端吗？**  
A: 可以！应用支持多客户端连接，每个客户端都会接收 Clubdeck 音频。

**Q: 支持哪些音频格式？**  
A: 目前固定为 48kHz 立体声 int16 PCM。未来可扩展支持其他格式。

**Q: 如何在远程访问时使用？**  
A: 访问 `http://<server-ip>:5000`（替换为实际服务器 IP）。确保防火墙允许 TCP 5000 端口。

---

## 📞 获取帮助

- **架构问题**: 查阅 [.github/copilot-instructions.md](.github/copilot-instructions.md#架构--音频流)
- **设备问题**: 查阅 [DUAL_CABLE_SETUP.md](DUAL_CABLE_SETUP.md)
- **构建问题**: 查阅 [TECHNICAL_SUMMARY.md](TECHNICAL_SUMMARY.md#部署和验证)
- **代码问题**: 检查源文件中的内联注释和类型提示

---

**版本**: 1.0.0  
**最后更新**: 2024  
**维护者**: ClubVoice Team
