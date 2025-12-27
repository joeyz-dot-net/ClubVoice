# ClubVoice

浏览器 ↔ Clubdeck 实时语音通信应用

让网页用户可以与 Clubdeck 房间中的用户进行实时语音通话。

## 系统架构

```
┌──────────────┐         WebSocket          ┌──────────────────┐
│              │ ←─────────────────────────→│                  │
│   浏览器      │      Socket.IO             │   Python 服务器   │
│  (Web Client)│      二进制音频流            │   (Flask)        │
│              │                            │                  │
└──────────────┘                            └──────────────────┘
      ↑                                            ↑     ↓
      │                                            │     │
 Web Audio API                              ┌──────┴─────┴──────┐
 - 麦克风采集                                │   VB-Cable 桥接    │
 - 音频播放                                  │   (sounddevice)   │
                                            └──────┬─────┬──────┘
                                                   │     │
                                        ┌──────────┘     └──────────┐
                                        ↓                          ↓
                                 ┌─────────────┐            ┌─────────────┐
                                 │ VB-Cable A  │            │ VB-Cable B  │
                                 │ (发送到CD)   │            │ (从CD接收)   │
                                 └──────┬──────┘            └──────┬──────┘
                                        │                          │
                                        └──────────┬───────────────┘
                                                   ↓
                                        ┌──────────────────┐
                                        │    Clubdeck      │
                                        │   (房间用户)      │
                                        └──────────────────┘
```

## 功能特性

- 🎧 **只收听模式** - 仅接收 Clubdeck 房间音频
- 🎤 **完整模式** - 双向语音通话（收听 + 说话）
- 🔇 **双 VB-Cable 隔离** - 消除音频回路，无回声
- 🎚️ **自适应音频参数** - 自动匹配设备采样率和声道数
- 🔊 **平滑音频播放** - 无卡顿的连续播放
- 🎛️ **噪声门限 + 高通滤波** - 清晰的音频质量

## 技术栈

### 后端 (Python 3.10+)

| 组件 | 技术 | 用途 |
|------|------|------|
| Web 框架 | Flask | HTTP 服务器，静态文件托管 |
| 实时通信 | Flask-SocketIO | WebSocket 双向音频传输 |
| 音频 I/O | sounddevice | 读写 VB-Cable 虚拟声卡 |
| 音频处理 | NumPy | 重采样、声道转换、降噪 |
| 终端 UI | Rich | 美化设备选择界面 |

### 前端 (JavaScript)

| 组件 | 技术 | 用途 |
|------|------|------|
| 实时通信 | Socket.IO Client | 与服务器 WebSocket 通信 |
| 音频采集 | Web Audio API | 麦克风采集 |
| 音频播放 | AudioBufferSourceNode | 播放 Clubdeck 声音 |

## 前置要求

1. **VB-Cable 虚拟声卡**（至少 2 个）
   - [VB-Cable](https://vb-audio.com/Cable/) - 免费版
   - [VB-Cable A+B](https://vb-audio.com/Cable/) - 付费版（推荐）

2. **Clubdeck 音频设置**
   - 麦克风输入：VB-Cable A Input
   - 音频输出：VB-Cable B Output

## 安装

```bash
# 克隆仓库
git clone <repository-url>
cd voice-communication-app

# 安装依赖
pip install -r requirements.txt
```

## 使用方法

### 开发运行

```bash
python run.py
```

启动后会显示设备选择界面：
1. 选择 **输入设备**（VB-Cable 的输出端，用于接收 Clubdeck 音频）
2. 选择 **输出设备**（VB-Cable 的输入端，用于发送音频到 Clubdeck）

### 访问页面

| 页面 | URL | 说明 |
|------|-----|------|
| 只收听模式 | `http://localhost:5000/` | 默认主页，仅接收音频 |
| 完整模式 | `http://localhost:5000/static/full.html` | 双向通话（含麦克风）|
| 调试页面 | `http://localhost:5000/static/debug.html` | 完整调试控制 |

### 打包 EXE

```bash
# 使用 PyInstaller 打包
pyinstaller VoiceCommunicationApp.spec -y

# 输出目录
dist/VoiceCommunicationApp.exe
```

VS Code 用户可使用 `Ctrl+Shift+B` 运行构建任务。

### 清理临时文件

程序退出时会自动清理 PyInstaller 解压的临时目录（系统 `%TEMP%` 下的 `_MEI*` 目录）。

如需手动清理残留的旧临时目录，可以运行：

```bash
# 开发模式
python cleanup.py

# 或直接运行 EXE（从 dist/ 目录）
ClubVoice.exe  # 退出时自动清理
```

**说明**：PyInstaller 打包的程序运行时会解压到系统临时目录（通常是 `C:\Users\<用户>\AppData\Local\Temp\_MEI*`）。程序正常退出时会自动清理，异常退出可能留下残留文件。

## 项目结构

```
voice-communication-app/
├── src/
│   ├── main.py                    # 主入口
│   ├── bootstrap.py               # 启动引导（设备选择）
│   ├── config/
│   │   └── settings.py            # 配置管理
│   ├── server/
│   │   ├── app.py                 # Flask 应用
│   │   └── websocket_handler.py   # Socket.IO 处理
│   └── audio/
│       ├── device_manager.py      # 设备管理
│       ├── vb_cable_bridge.py     # VB-Cable 桥接
│       └── processor.py           # 音频处理
├── static/
│   ├── index.html                 # 只收听模式（默认）
│   ├── full.html                  # 完整模式
│   ├── debug.html                 # 调试页面
│   └── js/
│       └── client.js              # 前端音频客户端
├── config.json                    # 服务器配置
├── requirements.txt               # Python 依赖
├── VoiceCommunicationApp.spec     # PyInstaller 配置
└── run.py                         # 运行入口
```

## 音频参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 采样率 | 48000 Hz | 浏览器端采样率 |
| 声道数 | 2 (立体声) | 浏览器端声道数 |
| 位深度 | 16-bit | PCM 格式 |
| 缓冲区 | 512 samples | 服务端缓冲区大小 |

## 配置文件

`config.json`:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": false
  }
}
```

## 常见问题

### Q: 听到回声/啸叫？
A: 确保使用两个不同的 VB-Cable 设备，一个用于发送，一个用于接收。

### Q: 音频卡顿？
A: 检查网络延迟，或尝试增大 `playbackLatency` 参数。

### Q: 听不到声音？
A: 确保点击了「开始收听」按钮（浏览器安全策略要求用户交互后才能播放音频）。

### Q: 找不到 VB-Cable 设备？
A: 确保已安装 VB-Cable 并重启电脑。

## License

MIT License