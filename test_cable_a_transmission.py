"""
测试 CABLE-A 虚拟线缆传输
device 28 (CABLE-A Input) 写入 → device 36 (CABLE-A Output) 读取
"""
import sounddevice as sd
import numpy as np
import threading
import time

print("=" * 70)
print("测试 CABLE-A 虚拟线缆传输")
print("=" * 70)
print("device 28 (CABLE-A Input) → device 36 (CABLE-A Output)")
print("=" * 70)

# 生成测试音
sample_rate = 48000
duration = 5
t = np.linspace(0, duration, int(sample_rate * duration), False)
tone = np.sin(2 * np.pi * 440 * t) * 0.5  # 50%音量

# 转换为立体声int16
stereo_tone = np.column_stack([tone, tone])
int16_tone = (stereo_tone * 32767).astype(np.int16)

print(f"\n正在播放 {duration}秒 440Hz测试音到设备28...")

received_volume = []
monitoring = True

def monitor_device_36():
    """监控设备36的音量"""
    global monitoring
    try:
        stream = sd.InputStream(
            device=36,
            samplerate=48000,
            channels=2,
            dtype='int16',
            blocksize=512
        )
        stream.start()
        
        while monitoring:
            indata, _ = stream.read(512)
            if indata is not None:
                float_data = indata.astype(np.float32) / 32768.0
                rms = np.sqrt(np.mean(float_data ** 2))
                volume = min(100.0, rms * 100.0 * 10.0)
                received_volume.append(volume)
        
        stream.stop()
        stream.close()
    except Exception as e:
        print(f"监控错误: {e}")

# 启动监控线程
monitor_thread = threading.Thread(target=monitor_device_36, daemon=True)
monitor_thread.start()

time.sleep(0.5)  # 等待监控线程启动

# 播放测试音到device 28
try:
    sd.play(int16_tone, sample_rate, device=28, blocking=True)
    print("✅ 播放完成")
except Exception as e:
    print(f"❌ 播放错误: {e}")

time.sleep(0.5)
monitoring = False
time.sleep(0.2)

# 分析结果
print("\n" + "=" * 70)
print("传输测试结果:")
print("=" * 70)

if len(received_volume) > 0:
    avg_volume = sum(received_volume) / len(received_volume)
    max_volume = max(received_volume)
    
    print(f"设备36接收到的音量:")
    print(f"  平均: {avg_volume:.1f}%")
    print(f"  峰值: {max_volume:.1f}%")
    
    if max_volume > 30:
        print(f"\n✅ CABLE-A 虚拟线缆工作正常！")
        print(f"   device 28 → device 36 传输成功")
        print(f"\n问题在于：")
        print(f"  ❌ Clubdeck 麦克风输入设置错误")
        print(f"  ✅ 正确设置: CABLE-A Output (设备36)")
        print(f"\n请检查 Clubdeck 音频设置：")
        print(f"  1. 打开 Clubdeck 设置")
        print(f"  2. 麦克风输入 → 选择 'CABLE-A Output'")
        print(f"  3. 确认不是 'CABLE-B' 或其他设备")
    elif max_volume > 5:
        print(f"\n⚠️  CABLE-A 有信号但音量太小")
        print(f"   可能需要调高音量")
    else:
        print(f"\n❌ CABLE-A 虚拟线缆没有传输音频！")
        print(f"   device 28 写入但 device 36 没有收到")
        print(f"\n可能原因：")
        print(f"  1. VB-Cable 驱动问题")
        print(f"  2. 设备被其他程序独占")
        print(f"  3. Windows 音频服务异常")
        print(f"\n解决方法：")
        print(f"  1. 重启 VB-Cable Audio Driver")
        print(f"  2. 关闭其他使用 CABLE-A 的程序")
        print(f"  3. 重启音频服务")
else:
    print("❌ 未能监控设备36")

print("=" * 70)
