# 测试步骤

## 当前问题
- 浏览器只能收到 Clubdeck 音频，没有 MPV 音乐
- Clubdeck 房间也没有 MPV 音乐
- Clubdeck 收不到浏览器麦克风

## 调试日志已添加

现在代码中添加了调试日志：
- 🔵 **MPV 音频检测**：当 MPV 有声音时显示蓝色日志
- 🟢 **混音信息**（Clubdeck → 浏览器）：显示 Clubdeck + MPV 混音
- 🟡 **发送到 Clubdeck**（浏览器 → Clubdeck）：显示浏览器麦克风 + MPV 混音

## 测试步骤

### 1. 确保 MPV 输出正确
在 MPV 中设置音频输出设备为：
```
CABLE Input (VB-Audio Virtual Cable)
```

### 2. 运行 Python 应用
```bash
python run.py
```

#### 设备选择建议：
- **Clubdeck 输入**（接收 Clubdeck 音频）：`CABLE Output (VB-Audio Virtual Cable)`
- **Clubdeck 输出**（发送到 Clubdeck）：`CABLE Input (VB-Audio Virtual Cable)`
- **MPV 输入**（接收 MPV 音乐）：`CABLE Output (VB-Audio Virtual Cable)`

### 3. 启动 MPV 播放音乐
```bash
mpv your-music.mp3
```

### 4. 观察日志

#### 预期看到的日志：

**当 MPV 播放音乐时：**
```
[cyan]MPV 音频: 15234 幅度, 1024 samples[/cyan]
```

**当 Clubdeck 有声音且 MPV 正在播放：**
```
[green]混音: Clubdeck(3421) + MPV(15234) = 18234[/green]
```

**当浏览器麦克风说话且 MPV 正在播放：**
```
[yellow]发送到 Clubdeck: Browser(5678) + MPV(15234) = 19876[/yellow]
```

### 5. 检查点

#### ✅ MPV 音频是否被捕获？
- 看到蓝色的 "MPV 音频" 日志吗？
- 如果没有：
  1. 检查 MPV 输出设备是否设置为 `CABLE Input`
  2. 检查 Python 应用是否选择了 `CABLE Output` 作为 MPV 输入
  3. 在 Windows 声音设置中确认 VB-Cable 设备正常

#### ✅ 浏览器能收到混音？
- 看到绿色的"混音"日志吗？
- 浏览器中能听到 Clubdeck + MPV 吗？
- 如果只听到 Clubdeck：检查 MPV 是否正在播放

#### ✅ Clubdeck 能收到混音？
- 看到黄色的"发送到 Clubdeck"日志吗？
- Clubdeck 房间中能听到浏览器麦克风 + MPV 吗？
- 如果收不到浏览器麦克风：
  1. 确认 config.json 中 `duplex_mode` 是 `full`
  2. 检查浏览器是否授予麦克风权限

## 故障排查

### 问题 1: 看不到 MPV 音频日志
**原因**：MPV 音频流没有被捕获

**解决方法**：
1. 在 Windows 声音设置中打开"声音控制面板"
2. 播放 MPV 音乐
3. 查看"录制"标签，确认 `CABLE Output` 有绿色音量条
4. 如果没有：
   - 右键 → 显示已禁用的设备
   - 启用 `CABLE Output`

### 问题 2: 看到 MPV 日志但浏览器听不到
**原因**：混音逻辑问题或 WebSocket 未连接

**解决方法**：
1. 打开浏览器控制台（F12）
2. 查看是否有 WebSocket 连接成功消息
3. 刷新浏览器页面

### 问题 3: Clubdeck 收不到浏览器麦克风
**原因**：半双工模式或输出队列问题

**解决方法**：
1. 检查 `config.json`：
   ```json
   {
     "audio": {
       "duplex_mode": "full"
     }
   }
   ```
2. 在浏览器中对着麦克风说话
3. 查看是否有黄色"发送到 Clubdeck"日志

### 问题 4: 音频有回声或延迟
**原因**：音频回环或缓冲区设置

**解决方法**：
1. 确保 Clubdeck 输入/输出使用不同的虚拟设备
2. 减小 `chunk_size`（在 config.json 中）
3. 使用耳机而非扬声器

## 测试完成后

如果一切正常，请移除调试日志以减少终端输出。
在 `src/audio/vb_cable_bridge.py` 中删除：
- MPV 音频检测日志
- 混音信息日志
- 发送到 Clubdeck 日志
