# 混音模式使用指南

## 功能概述

ClubVoice 现在支持**双输入混音模式**，可以同时接收两个音频设备（ID 26 和 27）的音频流，将它们混合后转发到浏览器客户端。

## 音频流向

```
┌─────────────────┐     ┌─────────────────┐
│  设备 26        │     │  设备 27        │
│  CABLE-B Output │     │  CABLE-A Output │
│  48kHz 2ch      │     │  48kHz 2ch      │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │   输入流1              │   输入流2
         │                       │
         └───────┬───────────────┘
                 │
                 ▼
         ┌───────────────┐
         │  混音线程      │
         │  平均混合算法  │
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │  混音队列      │
         │  48kHz 2ch    │
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │  WebSocket    │
         │  转发到浏览器  │
         └───────────────┘
```

## 配置文件

### config.ini

```ini
[audio]
duplex_mode = half
input_device_id = 27        # 第一个输入设备
input_device_id_2 = 26      # 第二个输入设备
mix_mode = true             # 启用混音模式
```

### 参数说明

- `input_device_id`: 主输入设备ID（CABLE-A Output）
- `input_device_id_2`: 第二输入设备ID（CABLE-B Output）
- `mix_mode`: 是否启用混音模式
  - `true`: 双输入混音
  - `false`: 单输入模式

## 混音算法

```python
# 平均混合算法（避免削波）
mixed = ((audio1.astype(np.int32) + audio2.astype(np.int32)) // 2).astype(np.int16)
```

**优点**：
- 防止音频溢出（削波）
- 两路音频音量平衡
- 计算简单，实时性能好

**示例**：
```
Audio 1: [1000, 2000]  (设备26的样本)
Audio 2: [3000, 4000]  (设备27的样本)
Mixed:   [2000, 3000]  (混合后的输出)
```

## 关键实现

### 1. VBCableBridge 类

```python
# 初始化时配置混音参数
bridge = VBCableBridge(
    input_device_id=27,
    input_device_id_2=26,
    mix_mode=True,
    ...
)
```

### 2. 双输入回调

- `_input_callback()`: 处理设备1的音频
- `_input_callback_2()`: 处理设备2的音频

两个回调分别将音频数据放入 `input_queue` 和 `input_queue_2`。

### 3. 混音线程

```python
def _mixer_worker(self):
    while self.running:
        # 从两个队列获取音频
        audio1 = self.input_queue.get(timeout=0.05)
        audio2 = self.input_queue_2.get(timeout=0.05)
        
        # 确保形状一致
        if audio1.shape != audio2.shape:
            min_len = min(len(audio1.flatten()), len(audio2.flatten()))
            audio1 = audio1.flatten()[:min_len].reshape(-1, 2)
            audio2 = audio2.flatten()[:min_len].reshape(-1, 2)
        
        # 平均混合
        mixed = ((audio1.astype(np.int32) + audio2.astype(np.int32)) // 2).astype(np.int16)
        
        # 放入混音队列
        self.mixed_queue.put_nowait(mixed)
```

### 4. WebSocket转发

WebSocket处理器从 `mixed_queue` 读取混音后的数据并转发到浏览器客户端。

## 线程架构

```
主线程 (Flask-SocketIO)
├── 输入线程1 (sounddevice) → input_queue
├── 输入线程2 (sounddevice) → input_queue_2
├── 混音线程 (Python)       → mixed_queue
└── 转发线程 (WebSocket)    → 浏览器客户端
```

## 使用场景

1. **双路Clubdeck音频**：同时接收两个Clubdeck房间的音频
2. **音乐+语音分离**：一路接收语音，一路接收音乐，混合播放
3. **多源监听**：监听多个音频源并合并到单一输出

## 测试

### 测试配置加载

```bash
python test_mixer.py
```

### 测试混音算法

```bash
python -c "import numpy as np; a1 = np.array([1000, 2000], dtype=np.int16); a2 = np.array([3000, 4000], dtype=np.int16); mixed = ((a1.astype(np.int32) + a2.astype(np.int32)) // 2).astype(np.int16); print(f'Mixed: {mixed}')"
```

## 注意事项

1. **设备同步**：两个输入设备必须有相同的采样率（48kHz）
2. **队列管理**：三个队列（input_queue, input_queue_2, mixed_queue）都有200帧的最大容量
3. **性能考虑**：混音线程使用50ms超时，避免阻塞
4. **错误处理**：如果一个队列空，继续等待，不会中断混音线程

## 禁用混音模式

在 `config.ini` 中设置：

```ini
[audio]
mix_mode = false
```

系统将回退到单输入模式，只使用 `input_device_id` 指定的设备。

## 调试

启动时会显示混音配置：

```
音频桥接器配置:
  输入1: 2ch @ 48000Hz (设备 27)
  输入2: 2ch @ 48000Hz (设备 26)
  浏览器: 2ch @ 48000Hz
  Chunk Size: 512 frames
✓ 模式: 双输入混音
```

控制台日志：
```
✓ 输入流1已启动: 设备 27, 48000Hz, 2ch
✓ 输入流2已启动: 设备 26, 48000Hz, 2ch
✓ 混音线程已启动
```
