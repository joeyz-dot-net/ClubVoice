# 🎚️ VB-Cable A/B 双线缆配置指南

## 📋 方案概述

使用 **VB-Cable A + VB-Cable B** 虚拟音频线缆实现浏览器与 Clubdeck 的完整双向语音通信，同时支持背景音乐混音。

```
┌─────────────────────────────────────────────────────────┐
│          浏览器用户                                       │
│    (麦克风 + 扬声器)                                      │
│         │         ▲                                     │
│         │         │ Socket.IO                          │
│         ▼         │                                     │
├─────────────────────────────────────────────────────────┤
│          Python 服务器                                   │
│                                                         │
│  输入设备 27 (CABLE-A Output)  ← Clubdeck 房间声音       │
│  输入设备 26 (CABLE-B Output)  ← MPV 背景音乐           │
│           │            │                                │
│           └────┬───────┘                                │
│                ▼                                        │
│          混音处理 (Mix + Ducking)                       │
│                │                                        │
│                ▼                                        │
│  输出设备 (CABLE-A Input) → Clubdeck 麦克风            │
├─────────────────────────────────────────────────────────┤
│          Clubdeck 房间                                   │
│    (房间用户 + 音乐)                                     │
└─────────────────────────────────────────────────────────┘
```

### 🎯 架构特点

✅ **完全隔离**：CABLE-A 负责房间通话，CABLE-B 单独负责音乐  
✅ **全双工**：浏览器可同时听和说，无回环  
✅ **音乐混音**：房间声音 + MPV 音乐混合播放给浏览器  
✅ **动态闪避**：浏览器用户说话时，背景音乐自动降音量到 15%  
✅ **成本低**：仅需两条免费的 VB-Cable 虚拟线缆  

---

## 🛠️ 安装步骤

### 1. 安装虚拟音频设备

**VB-Cable A 和 VB-Cable B**
- 下载：[https://vb-audio.com/Cable/](https://vb-audio.com/Cable/)
- 需要购买或使用虚拟机免费版
- Windows 11/10 兼容

**安装后应该看到**：
```
设备 26: CABLE-B Output (VB-Audio Virtual Cable B)
设备 27: CABLE-A Output (VB-Audio Virtual Cable A)
```

---

## ⚙️ 配置步骤

### 2. Clubdeck 音频设置

在 Clubdeck 中配置麦克风和扬声器：

```
🎤 输入（麦克风输入设备）
   → CABLE-A Output  (接收 Python 服务器发送的音频)

🔊 输出（扬声器输出设备）
   → CABLE-A Input   (发送房间声音到 Python 服务器)
```

### 3. Python 程序配置

编辑 [config.ini](config.ini)：

```ini
[audio]
duplex_mode = full          # 全双工：可同时收听和发言
mix_mode = true             # 启用混音：合并房间+音乐

# 输入设备 1：CABLE-A Output - 从 Clubdeck 接收房间声音
input_device_id = 27
input_sample_rate = 48000
input_channels = 2

# 输入设备 2：CABLE-B Output - 读取 MPV 背景音乐
input_device_id_2 = 26
input_sample_rate_2 = 48000
input_channels_2 = 2

# 音频闪避配置（浏览器说话时降低音乐音量）
ducking_enabled = true
ducking_threshold = 150.0    # 说话检测阈值
ducking_gain = 0.15          # 说话时音乐降到 15%
ducking_transition_time = 0.1 # 平滑过渡
```

### 4. 启动程序

```powershell
python run.py
```

程序启动时会自动检测设备：
```
🎧 输入设备（从 Clubdeck 接收音频）
  ★ 1  27 CABLE-A Output (VB-Audio Virtual Cable A)  2ch  48000 Hz

🎧 输入设备 2（从 MPV 接收音乐）
  ★ 1  26 CABLE-B Output (VB-Audio Virtual Cable B)  2ch  48000 Hz

🔊 输出设备（发送音频到 Clubdeck）
  ★ 1  CABLE-A Input (VB-Audio Virtual Cable A)      2ch  48000 Hz
```

按 `Enter` 接受推荐配置。

---

## 🔄 音频流向详解

### 浏览器 → Clubdeck

```
用户在浏览器说话
    ↓
Web Audio API 捕获麦克风
    ↓
ScriptProcessorNode (2048 samples, 42.67ms)
    ↓
转换为 Int16 PCM + Base64 编码
    ↓
Socket.IO 发送到 Python 服务器
    ↓
解码 Base64 → numpy 数组
    ↓
检测说话幅值 > 150 ──→ 触发 MPV 闪避
    ↓
降噪 (noise gate) + 高通滤波 (100Hz)
    ↓
通过 sounddevice 写入 CABLE-A Input
    ↓
Clubdeck 麦克风接收 (CABLE-A Output)
    ↓
房间所有人都听到浏览器用户的声音
```

**延迟**：~60-100ms

### Clubdeck + MPV → 浏览器

```
Clubdeck 房间声音
    ↓
CABLE-A Input ──→ Python 服务器读取 (设备 27)

MPV 背景音乐
    ↓
CABLE-B Input ──→ Python 服务器读取 (设备 26)

混音处理 (Mixer Thread):
  房间音量 + MPV 音量 * ducking_factor
  (如果浏览器说话: 房间 100% + 音乐 15%)
  (如果浏览器静音: 房间 100% + 音乐 100%)
    ↓
处理管道：
  - 重采样 (如需要)
  - 声道转换
  - 平滑过渡
    ↓
Base64 编码
    ↓
Socket.IO 发送 (play_audio 事件)
    ↓
浏览器接收并播放
```

**延迟**：~50-70ms

---

## 🔄 音频流向示意图

```
┌─────────────┐         CABLE-A         ┌──────────────┐
│   浏览器     │◄──────────────────────►│ Python 服务器 │
│  (用户麦克风) │   Output ← Input       │              │
└─────────────┘                         └──────────────┘
                                              ▲
                                              │ CABLE-B
                                              │ Output ← Input
                                              ▼
                                      ┌──────────────┐
                                      │   Clubdeck   │
                                      │  (语音房间)   │
                                      └──────────────┘
```

### 数据流详解

1. **浏览器 → Clubdeck（通过 CABLE-A）**
   - 浏览器麦克风 → WebRTC 编码 → WebSocket → Python
   - Python 处理 → `CABLE-A Input` → Clubdeck 麦克风

2. **Clubdeck + MPV → 浏览器（通过 CABLE-A + CABLE-B）**
   - Clubdeck 房间声音 → `CABLE-A Output` → Python (设备27)
   - MPV 背景音乐 → `CABLE-B Output` → Python (设备26)
   - Python 混音 → Base64 编码 → WebSocket → 浏览器扬声器

3. **Clubdeck 配置**
   - 麦克风输入 = CABLE-A Output
   - 扬声器输出 = CABLE-A Input
   - 不需要配置 CABLE-B（MPV 单独管理）

---

## 🧪 测试验证

### 1. 验证设备识别

启动程序后，检查终端输出是否正确识别设备 26 和 27。

### 2. 测试 Clubdeck 房间声音

在 Clubdeck 房间中说话，浏览器应该能听到。

**验证方法**：
```bash
python tools/volume_monitor.py
# 选择设备 27
# 在 Clubdeck 说话，应看到音量波动
```

### 3. 测试 MPV 音乐

在 MPV 播放音乐，浏览器应该能听到。

**验证方法**：
```bash
python tools/volume_monitor.py
# 选择设备 26
# 如果 MPV 播放，应看到稳定的音量
```

### 4. 测试浏览器麦克风

打开 `http://localhost:5000`，开启麦克风：

- 浏览器说话 → Clubdeck 应该听到
- Clubdeck 有人说话 → 浏览器应该听到
- 同时进行上述两个 → 应该都能进行（全双工）

### 5. 测试音量闪避

在浏览器开启麦克风并说话：

- MPV 音乐应该自动降音量
- 停止说话后，音乐逐渐恢复正常音量
- 过渡应该平滑，不突兀

---

## 🔧 调试工具

### 实时音量监控

```powershell
# 完整版（需要 Rich 库）
python tools/volume_monitor.py

# 简化版（纯终端）
python tools/simple_volume_monitor.py
```

### WebSocket 诊断

```powershell
# 检查 Socket.IO 连接
python diagnose_websocket_v2.py
```

### 调试面板

访问 `http://localhost:5000/debug.html` 查看：
- 🎤 麦克风音量实时波形
- 📊 接收音量波形
- 📈 连接状态和统计信息
- ⚙️ 参数调整界面

---

## ❓ 常见问题

### Q1: 浏览器听不到 Clubdeck 房间声音

**检查项**：
1. Clubdeck 输出设备是否设置为 "CABLE-A Input"？
2. 运行 `python tools/volume_monitor.py` 选择设备 27，Clubdeck 房间有声音吗？
3. config.ini 中 `duplex_mode = full`？
4. `mix_mode = true`？

**解决方案**：
- 重启 Python 程序
- 检查虚拟线缆驱动是否正确安装
- 用 `python diagnose_websocket_v2.py` 诊断

### Q2: Clubdeck 听不到浏览器声音

**检查项**：
1. Clubdeck 麦克风输入是否设置为 "CABLE-A Output"？
2. 浏览器麦克风权限是否已授予？
3. 浏览器是否开启了麦克风？（应有 🎤 图标）
4. config.ini 中 `duplex_mode = full`？

**解决方案**：
- 在浏览器允许麦克风权限
- 检查 WebSocket 连接（访问 debug.html）
- 查看服务器日志是否有错误信息

### Q3: 音量闪避不工作

**症状**：浏览器说话时，MPV 音乐没有自动降音量

**检查项**：
1. config.ini 中 `ducking_enabled = true`？
2. `ducking_threshold = 150` 是否合理？（可尝试 100-200）
3. MPV 是否正在播放？
4. 浏览器的说话幅值是否超过阈值？

**调试**：
```bash
python tools/volume_monitor.py
# 选择设备 26 (MPV)
# 在浏览器说话，观察 MPV 音量是否下降到 15%
```

### Q4: 声音卡顿或延迟大

**原因**：
- 缓冲区太大
- CPU 占用过高
- 采样率不匹配

**解决方案**：
```ini
[audio]
chunk_size = 256      # 从 512 改小（降低延迟，增加 CPU）
input_sample_rate = 48000   # 确保都是 48000Hz
```

### Q5: 有明显回声或自己听到自己的声音

**原因**：
- Web Audio API 的 echoCancellation 不够完美
- Clubdeck 的 AEC 失效
- 房间中有多个音箱

**解决方案**：
1. 检查浏览器隐私设置，允许麦克风权限
2. 在 Clubdeck 中降低麦克风增益
3. 降低 `ducking_gain` 参数（从 0.15 改为 0.1）
4. 用 debug.html 观察麦克风和接收音量，验证是否真的有回声

---

## 📊 性能参考

| 指标 | 值 |
|------|-----|
| **采样率** | 48000 Hz |
| **声道数** | 2 (立体声) |
| **缓冲区** | 512 frames = 10.67ms |
| **发送周期** | 42.67ms (2048 samples) |
| **往返延迟** | ~100-150ms |
| **CPU 占用** | 3-8% |
| **网络带宽** | 3-4 Mbps |

---

## 🎉 快速开始检查清单

- [ ] 安装 VB-Cable A 和 VB-Cable B
- [ ] 在 Clubdeck 中配置输入为 CABLE-A Output，输出为 CABLE-A Input
- [ ] 编辑 config.ini（设置 device 26 和 27）
- [ ] 运行 `python run.py`
- [ ] 按 Enter 接受推荐配置
- [ ] 打开浏览器 `http://localhost:5000`
- [ ] 测试麦克风：允许权限
- [ ] 在 Clubdeck 房间说话 → 浏览器应听到
- [ ] 在浏览器说话 → Clubdeck 应听到
- [ ] 播放 MPV 音乐 → 浏览器应听到
- [ ] 在浏览器说话 → MPV 音乐应自动降音量

**一切正常？恭喜！开始享受全双工语音通信吧！🎉**

---

## 参考文档

- [快速参考](doc/QUICK_REFERENCE.md) - 常见任务和解决方案
- [AI 代理指南](.github/copilot-instructions.md) - 架构和技术细节
- [项目完成报告](doc/PROJECT_COMPLETION_REPORT.md) - 项目历史和改进记录
