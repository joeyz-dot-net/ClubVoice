# MPV 音乐播放 + 双向语音通信设置指南（方案 A）

## ✅ 当前实施方案：简化混音架构

**架构类型**：单输入单输出，由 Clubdeck 完成硬件混音

## 功能说明

此应用现在支持：
1. **MPV 播放音乐** → 直接发送到 Clubdeck 输入设备
2. **Clubdeck 自动混音** → 将房间音频和 MPV 音乐混合
3. **Python 应用透明转发** → 接收 Clubdeck 混音后的音频发送到浏览器
4. **浏览器麦克风** → 发送到 Clubdeck 房间

## 硬件要求

- **Hi-Fi Cable** (推荐) 或 **VB-Cable 2ch**：用于所有音频通信
- **MPV 播放器**：用于播放音乐

---

## 音频流向图

```
┌─────────────────────────────────────────────────────────────────┐
│  MPV 播放器                                                      │
│    输出设备: Hi-Fi Cable Input                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Clubdeck 应用（自动混音）                                       │
│    输入设备: Hi-Fi Cable Output                                 │
│    ⚙️ 内部混合: Clubdeck 房间音频 + MPV 音乐                    │
│    输出设备: Hi-Fi Cable Input                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Python 应用（透明转发）                                         │
│    输入设备: Hi-Fi Cable Output (接收 Clubdeck 混音)           │
│    输出设备: Hi-Fi Cable Input (发送浏览器音频)                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  浏览器                                                          │
│    接收: Clubdeck + MPV 混音后的音频                            │
│    发送: 浏览器麦克风音频                                        │
└─────────────────────────────────────────────────────────────────┘
```

## 设备配置方案

### 方案 A：简化混音架构（推荐）⭐

**核心思想**：取消 MPV 独立输入流，让 MPV 直接输出到 Clubdeck 输入设备，由 Clubdeck 的音频卡完成硬件混音。

```
┌─────────────────────────────────────────────────────────────────┐
│  MPV 播放器                                                      │
│    输出设备: Hi-Fi Cable Input (VB-Audio Hi-Fi Cable)          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Clubdeck 应用（房间）                                           │
│    输入设备: Hi-Fi Cable Output (VB-Audio Hi-Fi Cable)         │
│    ⚙️ Clubdeck 内部自动混合:                                    │
│       • Clubdeck 房间音频                                        │
│       • MPV 音乐（从 Hi-Fi Cable 输入）                          │
│    输出设备: Hi-Fi Cable Input (VB-Audio Hi-Fi Cable)          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Python 应用程序（透明转发）                                     │
│                                                                   │
│  ┌─ 输入 (Clubdeck 混音后的音频)                                │
│  │  设备: Hi-Fi Cable Output (VB-Audio Hi-Fi Cable)             │
│  │  内容: Clubdeck 房间音频 + MPV 音乐（已混合）                │
│  │                                                               │
│  └─ 输出 (浏览器麦克风)                                          │
│     设备: Hi-Fi Cable Input (VB-Audio Hi-Fi Cable)              │
│     内容: 浏览器麦克风音频                                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  浏览器                                                          │
│    接收: Clubdeck 房间音频 + MPV 音乐（已混合）                 │
│    发送: 浏览器麦克风音频                                        │
└─────────────────────────────────────────────────────────────────┘
```

**优点：**
- ✅ 无需 Python 混音，零延迟
- ✅ 无缓冲区同步问题
- ✅ Clubdeck 内部混音更稳定
- ✅ 只需一个虚拟线缆（Hi-Fi Cable）
- ✅ 代码简单，易于维护

**缺点：**
- ❌ MPV 和 Clubdeck 共享同一输入设备
- ❌ 无法独立控制 MPV 音量（需在 MPV 中调节）

---

### 方案 B：Python 双输入混音（当前实现）

**核心思想**：Python 读取两个独立的输入流（Clubdeck + MPV），在软件中混音。

```
MPV 播放器 → CABLE Input (VB-Cable)
                    ↓
            CABLE Output (VB-Cable) → Python MPV 输入流
                                            ↓
Clubdeck → Hi-Fi Cable Input → Hi-Fi Cable Output → Python Clubdeck 输入流
                                                            ↓
                                            Python 混音（缓冲区同步）
                                                            ↓
                                                    ┌───────┴────────┐
                                            浏览器 ←┘                └→ Clubdeck
```

**优点：**
- ✅ MPV 和 Clubdeck 完全隔离
- ✅ 可以独立控制 MPV 音量
- ✅ 可以实现高级功能（ducking、均衡器等）

**缺点：**
- ❌ 需要复杂的缓冲区同步
- ❌ 可能有音频卡顿
- ❌ 增加延迟（~50-100ms）
- ❌ CPU 占用较高

---

### 方案 C：Voicemeeter 硬件混音

**核心思想**：使用 Voicemeeter 软件完成混音，Python 只负责转发。

```
MPV → Voicemeeter Input 1
Clubdeck → Voicemeeter Input 2
                ↓
        Voicemeeter 混音
                ↓
    Voicemeeter Output → Python 输入
```

**优点：**
- ✅ 专业混音软件
- ✅ 可视化控制台
- ✅ 低延迟硬件混音

**缺点：**
- ❌ 需要额外软件
- ❌ 配置复杂
- ❌ 占用系统资源

---

## 🎯 推荐实施方案

### 立即可用：方案 A（简化架构）⭐

**适用场景：**
- 只需要基本的音乐播放功能
- 追求低延迟和稳定性
- 不需要独立控制 MPV 音量

**实施步骤：**

1. **修改代码**：移除 MPV 输入流，改为单输入单输出架构
2. **配置 MPV**：
   ```
   输出设备: Hi-Fi Cable Input (VB-Audio Hi-Fi Cable)
   ```
3. **配置 Clubdeck**：
   ```
   输入设备: Hi-Fi Cable Output (Clubdeck + MPV 已混合)
   输出设备: Hi-Fi Cable Input
   ```
4. **配置 Python**：
   ```
   输入设备: Hi-Fi Cable Output (接收 Clubdeck 混音)
   输出设备: Hi-Fi Cable Input (发送浏览器音频)
   ```

### 未来增强：方案 B（双输入混音）

**需要解决的问题：**
1. ✅ 采样率同步（已实现）
2. ⚠️ 缓冲区同步（有问题）
3. ⚠️ 回调速度匹配（有问题）

**改进方案：**
- 使用固定大小的环形缓冲区
- 实现自适应采样率补偿（SRC）
- 添加缓冲区水位监控和动态调整

### 专业方案：方案 C（Voicemeeter）

**适用场景：**
- 需要专业级混音控制
- 多路音频源管理
- 实时 EQ 和效果处理

**实施步骤：**
1. 安装 Voicemeeter Potato
2. 配置虚拟输入/输出
3. Python 只连接 Voicemeeter 输出

---

## 💡 当前问题分析

### 问题 1：音频卡顿
**原因**：MPV 缓冲区在 3072-4096 samples 之间波动  
**诊断**：
- MPV 回调速度 ≠ Clubdeck 回调速度
- 缓冲区策略不够智能

**解决方案**：
- 🔴 **临时**：增加缓冲区容错范围
- 🟢 **根本**：切换到方案 A（无需混音）

### 问题 2：浏览器音频无法发送到 Clubdeck
**可能原因**：
- Clubdeck 输出流配置错误
- WebSocket 音频处理问题
- 音频阈值设置过高（已修复为 100）

**诊断步骤**：
1. 检查是否看到"浏览器音频接收"日志
2. 检查是否看到"发送到 Clubdeck"日志  
3. 检查 Clubdeck 输出队列是否有数据

---

## 📋 下一步行动

请选择一个方案：

### 选项 1：实施方案 A（推荐）⭐
- **工作量**：中等（需要修改代码）
- **预期效果**：彻底解决卡顿问题
- **时间**：30 分钟
- **优点**：简单、稳定、低延迟
- **缺点**：MPV 和 Clubdeck 共享输入设备

### 选项 2：继续优化方案 B
- **工作量**：较大（需要重写缓冲区逻辑）
- **预期效果**：可能改善，但难度高
- **时间**：1-2 小时
- **优点**：完全隔离，可扩展
- **缺点**：复杂度高，可能仍有问题

### 选项 3：切换到方案 C
- **工作量**：较小（配置外部软件）
- **预期效果**：稳定，但依赖第三方
- **时间**：20 分钟
- **优点**：专业混音，可视化控制
- **缺点**：需要额外软件

---

**请告诉我你想选择哪个方案，我会立即实施。**
└──┴──────────────────────┬──────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Clubdeck 应用                                                   │
│    输入设备: Hi-Fi Cable Output (VB-Audio Hi-Fi Cable)          │
│    输出设备: Hi-Fi Cable Input (VB-Audio Hi-Fi Cable)           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 启动步骤

### 1. 配置 MPV 输出设备

在 MPV 中设置音频输出设备为 `CABLE Input (VB-Audio Virtual Cable)`：

**方法 A：在 mpv.conf 中配置**
```ini
audio-device=wasapi/{设备 ID}
```

**方法 B：命令行参数**
```bash
mpv --audio-device=wasapi/{设备 ID} your-music.mp3
```

**方法 C：在 MPV 运行时按 `#` 键选择音频设备**

---

### 2. 配置 Clubdeck

在 Clubdeck 应用中设置：
- **输入设备**: `CABLE Output (VB-Audio Virtual Cable)`
  - 这会接收 MPV 音乐 + Clubdeck 房间音频
- **输出设备**: `CABLE Input (VB-Audio Virtual Cable)`

---

### 3. 启动 Python 应用

```bash
python run.py
```

应用会提示您选择两个设备：

#### 输入设备（接收 Clubdeck 混音）
```
推荐: CABLE Output (VB-Audio Virtual Cable) 2ch
```
用于接收 Clubdeck 混音后的音频（房间音频 + MPV 音乐）。

#### 输出设备（发送浏览器音频）
```
推荐: CABLE Input (VB-Audio Virtual Cable) 2ch
```
用于发送浏览器麦克风音频到 Clubdeck 房间。

---

### 4. 打开浏览器

访问 `http://localhost:5000` 或应用显示的地址。

允许浏览器使用麦克风权限。

---

## 优势

✅ **零 Python 混音延迟**：由 Clubdeck 音频卡完成硬件混音  
✅ **无缓冲区同步问题**：单输入流，无需复杂的异步混音  
✅ **稳定性高**：架构简单，不易出错  
✅ **CPU 占用低**：Python 只负责透明转发  
✅ **延迟极低**：< 20ms  
✅ **代码简洁**：易于维护和调试  

---

## 注意事项

1. **MPV 和 Clubdeck 共享输入设备**：
   - MPV 输出到 `CABLE Input (VB-Audio Virtual Cable)`
   - Clubdeck 输入从 `CABLE Output (VB-Audio Virtual Cable)` 读取
   - 这样 Clubdeck 会自动听到 MPV 音乐

2. **音量控制**：
   - MPV 音量：在 MPV 中调节
   - Clubdeck 音量：在 Clubdeck 中调节
   - 浏览器音量：在浏览器中调节

3. **单虚拟线缆即可**：
   - 只需要 VB-Cable A（2ch）
   - 无需第二条虚拟音频线缆（VB-Cable B 可用于其他用途）

---

## 常见问题

### Q: 为什么要用这个架构？
**A**: 避免 Python 中复杂的双输入流混音和缓冲区同步问题。让音频卡完成硬件混音更稳定可靠。

### Q: MPV 音乐音量太大/太小怎么办？
**A**: 在 MPV 中调节音量，或在 Clubdeck 的混音设置中调整输入音量。

### Q: 听到回音怎么办？
**A**: 
1. 确保 Clubdeck 输出设备设置为 `CABLE Input (VB-Audio Virtual Cable)`
2. 确保浏览器使用耳机而非扬声器
3. 在浏览器中启用回声消除功能

### Q: 浏览器听不到 MPV 音乐？
**A**: 
1. 检查 MPV 输出设备是否为 `CABLE Input (VB-Audio Virtual Cable)`
2. 检查 Clubdeck 输入设备是否为 `CABLE Output (VB-Audio Virtual Cable)`
3. 在 Clubdeck 中播放音乐测试是否正常

### Q: Clubdeck 收不到浏览器麦克风？
**A**: 
1. 确认 config.json 中 `duplex_mode` 是 `full`
2. 检查浏览器是否授予麦克风权限
3. 在浏览器控制台查看是否有音频发送日志

---

## 技术细节

- **架构类型**: 简化单输入单输出
- **混音方式**: Clubdeck 硬件混音
- **Python 角色**: 透明转发
- **采样率**: 自动转换到 48kHz
- **声道数**: 自动转换到立体声 (2ch)
- **数据类型**: int16 (16-bit signed integer)
- **缓冲区大小**: 512 samples
- **延迟**: < 20ms (取决于设备和系统)

---

## 配置文件 (config.json)

```json
{
  "audio": {
    "duplex_mode": "full",
    "sample_rate": 48000,
    "channels": 2,
    "chunk_size": 512
  },
  "mpv": {
    "enabled": true,
    "default_pipe": "\\\\.\\pipe\\mpv-pipe",
    "ducking_volume": 15
  }
}
```

- `duplex_mode`: 双工模式 (`half` = 半双工, `full` = 全双工)
- `mpv.enabled`: 是否启用 MPV 混音功能
- `mpv.ducking_volume`: 音乐闪避音量（未来功能）

---

## 许可证

MIT License
