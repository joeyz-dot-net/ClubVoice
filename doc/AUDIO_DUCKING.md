# 🎵 音频闪避 (Audio Ducking) 功能文档

## 📖 功能说明

**音频闪避** 是一种自动音量控制技术：当 Clubdeck 房间中有人说话时，自动降低背景音乐的音量，让语音更清晰；当语音停止后，音乐音量平滑恢复。

## 🎯 工作原理

```
VB-Cable A (Clubdeck 房间语音) ──┐
                                 ├──> 语音检测器 ──> 控制闪避器 ──> 调整音乐音量
VB-Cable B (音乐播放) ──────────┘
```

### 音频流向

1. **VB-Cable A**: Clubdeck Output → Python 接收 → 发送给浏览器（100% 音量）
2. **VB-Cable B**: 音乐播放器 → Python 接收 → 检测语音 → 降低音量 → 混音
3. **混音输出**: Clubdeck 语音 + 闪避后的音乐 → 发送到浏览器

### 语音检测

- **RMS 阈值**: 150.0（可配置）- 超过此值认为有语音
- **最小持续时间**: 0.1 秒 - 避免误触发
- **释放时间**: 0.5 秒 - 语音停止后等待多久恢复音量

### 音量闪避

- **正常音量**: 100% - 无语音时的音乐音量
- **闪避音量**: 15% - 有语音时的音乐音量
- **过渡时间**: 0.1 秒 - 音量变化的平滑过渡时间

## ⚙️ 配置说明

编辑 [`config.ini`](config.ini):

```ini
[audio]
duplex_mode = half
mix_mode = true              # 必须启用混音模式
input_device_id = 27         # VB-Cable A Input (Clubdeck 房间)
input_device_id_2 = 26       # VB-Cable B Output (音乐播放)

# === 音频闪避配置 ===
ducking_enabled = true       # 是否启用音频闪避
ducking_threshold = 150.0    # 语音检测阈值（RMS，范围 0-32768）
ducking_gain = 0.15          # 闪避时的音乐音量（0.15 = 15%）
ducking_min_duration = 0.1   # 最小语音持续时间（秒）
ducking_release_time = 0.5   # 语音停止后多久恢复音量（秒）
ducking_transition_time = 0.1 # 音量变化过渡时间（秒）
```

## 🎛️ 参数调整

### 灵敏度调整

```ini
# 更敏感（更容易触发闪避）
ducking_threshold = 100.0

# 更不敏感（需要更大声才触发）
ducking_threshold = 200.0
```

### 音量调整

```ini
# 闪避时音乐更响（30%）
ducking_gain = 0.30

# 闪避时音乐更轻（10%）
ducking_gain = 0.10

# 完全静音
ducking_gain = 0.0
```

### 响应速度调整

```ini
# 更快响应（立即降低音量）
ducking_min_duration = 0.05   # 50ms 就触发
ducking_transition_time = 0.05 # 50ms 完成音量变化

# 更慢响应（更稳定，不会频繁切换）
ducking_min_duration = 0.2    # 200ms 才触发
ducking_release_time = 1.0    # 1秒后才恢复
ducking_transition_time = 0.2  # 200ms 完成音量变化
```

## 🚀 使用方法

### 1. 启动应用

```bash
python run.py
```

### 2. 查看状态

启动时会显示：

```
============================================================
🎵 音频闪避 (Audio Ducking) 已启用
============================================================
  检测源: VB-Cable A (Clubdeck 房间语音)
  控制源: VB-Cable B (音乐播放)
  语音阈值: 150.0
  正常音量: 100%
  闪避音量: 15%
============================================================
```

### 3. 实时日志

每 100 帧会显示当前状态：

```
[VAD] 🔊 检测到语音 (RMS: 2876.2)
[Ducker] 降低音量 → 15%
🔊 音乐音量: 15%
```

```
[VAD] 🔇 语音停止
[Ducker] 恢复音量 → 100%
🎵 音乐音量: 100%
```

## 🧪 测试

运行测试脚本验证功能：

```bash
python test/test_audio_ducking.py
```

测试包括：
- ✅ 语音活动检测
- ✅ 音频闪避控制
- ✅ 集成测试（模拟实际使用场景）

## 📊 预期效果

### 场景 1: 只播放音乐

```
Clubdeck: 静音
音乐: 100% ████████████████████
浏览器听到: Clubdeck (静音) + 音乐 (100%)
```

### 场景 2: 有人说话

```
Clubdeck: 🔊 有人说话
音乐: 15% ███ ⬅️ 自动降低
浏览器听到: Clubdeck (100%) + 音乐 (15%)
```

### 场景 3: 说话结束

```
Clubdeck: 静音
音乐: 100% ████████████████████ ⬅️ 平滑恢复
浏览器听到: Clubdeck (静音) + 音乐 (100%)
```

## ⚠️ 注意事项

### 前提条件

1. **必须启用混音模式**: `mix_mode = true`
2. **必须配置两个输入设备**:
   - `input_device_id` = VB-Cable A (Clubdeck 房间)
   - `input_device_id_2` = VB-Cable B (音乐播放)

### 禁用闪避

如果不需要音频闪避功能，设置：

```ini
[audio]
ducking_enabled = false
```

或者关闭混音模式：

```ini
[audio]
mix_mode = false
```

## 🔧 故障排除

### 问题 1: 音乐一直很小声

**原因**: 语音阈值太低，一直检测到"语音"

**解决**: 提高阈值

```ini
ducking_threshold = 200.0  # 或更高
```

### 问题 2: 说话时音乐不降低

**原因**: 语音阈值太高

**解决**: 降低阈值

```ini
ducking_threshold = 100.0  # 或更低
```

### 问题 3: 音乐音量频繁跳动

**原因**: 语音边界检测不稳定

**解决**: 增加最小持续时间和释放时间

```ini
ducking_min_duration = 0.2    # 200ms
ducking_release_time = 0.8    # 800ms
```

### 问题 4: 音量变化太突兀

**原因**: 过渡时间太短

**解决**: 增加过渡时间

```ini
ducking_transition_time = 0.2  # 200ms
```

## 📝 技术细节

### 语音检测算法

使用 **RMS（均方根）** 算法检测音频能量：

```python
rms = sqrt(mean(audio_data^2))
if rms > threshold:
    # 检测到语音
```

### 音量控制算法

使用 **线性增益插值** 实现平滑过渡：

```python
# 每帧调整增益
if current_gain < target_gain:
    current_gain += gain_step
else:
    current_gain -= gain_step

# 应用到音频
output = input * current_gain
```

### 性能优化

- **队列缓冲**: 200 帧最大队列，防止内存溢出
- **int16 处理**: 使用整数运算，避免浮点计算开销
- **溢出保护**: 混音后使用 `np.clip` 限制范围

## 🎉 总结

音频闪避功能让你可以：

✅ **自动管理音量** - 无需手动调整  
✅ **语音优先** - 说话时音乐自动降低  
✅ **平滑过渡** - 音量变化自然流畅  
✅ **高度可配置** - 根据需求调整参数  

现在你可以在 Clubdeck 房间听音乐，当有人说话时音乐会自动减小，再也不会错过任何对话！🎧
