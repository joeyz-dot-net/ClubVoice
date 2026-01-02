# ClubVoice 工具集

本目录包含用于调试和测试 ClubVoice 的辅助工具。

## 🎤 音量监控工具

### 1. 完整版音量监控器 (volume_monitor.py)

功能强大的实时音量监控工具，具有 Rich UI 界面。

**功能特性**：
- 🆔 设备 ID 显示（黄色高亮）
- 📊 彩色实时音量条
- 📈 音量波形图（最近50帧）
- 📉 RMS 音量 + 峰值显示
- 📈 运行统计（帧率、峰值、平均值）
- 🎨 美观的 Rich 终端界面

**使用方法**：
```bash
python tools/volume_monitor.py
```

**适用场景**：
- 详细调试音频设备
- 可视化音量变化
- 性能分析和优化

---

### 2. 简化版音量监控器 (simple_volume_monitor.py)

轻量级纯终端版本，无需 Rich 库。

**功能特性**：
- 🆔 设备 ID 显示（标题行）
- 🚀 快速启动
- 💻 单行实时音量条
- 📊 峰值和帧数统计
- ⚡ 低资源占用

**使用方法**：
```bash
python tools/simple_volume_monitor.py
```

**适用场景**：
- 快速测试设备
- 服务器环境（无 Rich 库）
- 低延迟监控

---

## 📝 使用示例

### 监控 VB-Cable A（Clubdeck 输出）

```bash
# 启动工具
python tools/volume_monitor.py

# 输入设备 ID（例如：27）
请输入要监控的设备 ID: 27

# 观察音量变化
# - 在 Clubdeck 房间中说话或播放音乐
# - 工具应显示音量波动
# - 按 Ctrl+C 停止监控
```

### 测试音频闪避阈值

```bash
# 1. 打开音量监控工具
python tools/volume_monitor.py

# 2. 选择 VB-Cable A
输入设备 ID: 27

# 3. 观察实际音量值
# 例如：说话时音量为 180-250
# 音乐播放时音量为 50-100

# 4. 调整 config.ini 中的阈值
# ducking_threshold = 150.0  (根据观察到的值调整)
```

### 验证设备配置

```bash
# 检查设备是否有输入信号
python tools/simple_volume_monitor.py

# 如果音量一直为 0%，可能原因：
# - 设备未连接到音频源
# - Clubdeck 输出设备配置错误
# - VB-Cable 驱动未正确安装
```

---

## 🔧 故障排除

### 问题 1: "设备不支持输入"

**原因**：选择的设备没有输入声道

**解决**：
- VB-Cable Output 是输入设备（接收 Clubdeck 输出）
- VB-Cable Input 是输出设备（发送到 Clubdeck 输入）
- 选择正确的 Output 设备

### 问题 2: 音量一直为 0%

**原因**：设备未接收到音频信号

**解决**：
1. 检查 Clubdeck 输出设备配置
2. 确认 VB-Cable 驱动已安装
3. 在 Windows 声音设置中测试设备
4. 重启 Clubdeck 或 VB-Cable Audio Driver

### 问题 3: 帧率过低

**原因**：系统资源不足或设备采样率不匹配

**解决**：
1. 关闭其他音频应用
2. 检查设备采样率是否为 48000 Hz
3. 减小缓冲区大小（修改 chunk_size 参数）

---

## 📊 性能参考

**正常指标**：
- 帧率：93-94 FPS (48000Hz / 512 = 93.75 FPS)
- 延迟：< 11ms (512 / 48000 = 10.67ms)
- CPU 占用：< 5%

**异常指标**：
- 帧率 < 80 FPS：系统资源不足或设备问题
- 音量持续 > 90%：增益过大，可能导致削波失真
- 音量持续 = 0%：设备未连接或配置错误

---

## 🎯 高级用法

### 自定义参数

修改 `volume_monitor.py` 中的参数：

```python
# 调整缓冲区大小（影响延迟）
monitor = VolumeMonitor(
    device_id=27,
    sample_rate=48000,
    channels=2,
    chunk_size=256  # 更小 = 更低延迟，更高 CPU
)
```

### 长时间监控

使用 `simple_volume_monitor.py` 并重定向输出：

```bash
python tools/simple_volume_monitor.py > volume_log.txt 2>&1
```

### 与音频闪避配合

1. 运行监控工具观察 Clubdeck 语音音量
2. 记录典型语音音量范围（例如 150-300）
3. 设置 `ducking_threshold` 略低于最小值（例如 140）
4. 测试音频闪避效果

---

## 📚 相关文档

- [Audio Ducking 功能文档](../AUDIO_DUCKING.md)
- [配置文件说明](../config.ini)
- [项目主文档](../README.md)

---

## 🐛 报告问题

如果遇到工具相关问题，请提供：
1. 设备信息（名称、ID、采样率）
2. 错误信息或异常行为描述
3. 系统信息（Windows 版本、Python 版本）
4. 运行日志（如有）
