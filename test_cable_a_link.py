"""测试 CABLE-A 链路：Device 28 (写入) → Device 36 (读取)"""
import sounddevice as sd
import numpy as np
import time
import threading

print("\n" + "="*80)
print("测试 CABLE-A 虚拟音频线缆")
print("="*80)

# 发送端：Device 28 (CABLE-A Input)
print("\n发送端: Device 28 - CABLE-A Input (Python 写入)")
print("接收端: Device 36 - CABLE-A Output (Clubdeck 应读取)")

# 测试音频：440Hz 正弦波
duration = 2.0  # 秒
sample_rate = 48000
t = np.arange(0, duration, 1/sample_rate)
test_tone = (np.sin(2*np.pi*440*t) * 10000).astype(np.int16)
stereo_tone = np.column_stack([test_tone, test_tone])

received_volume = []

def input_callback(indata, frames, time_info, status):
    """从 Device 36 读取数据"""
    if status:
        print(f"[录音状态] {status}")
    
    # 计算音量
    float_data = indata.astype(np.float32) / 32768.0
    rms = np.sqrt(np.mean(float_data ** 2))
    volume = min(100.0, rms * 100.0 * 10.0)
    received_volume.append(volume)

print("\n[1/3] 启动接收端 (Device 36)...")
input_stream = sd.InputStream(
    device=36,
    samplerate=48000,
    channels=2,
    dtype='int16',
    callback=input_callback
)
input_stream.start()
time.sleep(0.5)

print("[2/3] 发送测试音到 Device 28...")
with sd.OutputStream(device=28, samplerate=48000, channels=2, dtype='int16') as output_stream:
    output_stream.write(stereo_tone)

print("[3/3] 等待接收完成...")
time.sleep(0.5)

input_stream.stop()
input_stream.close()

print("\n" + "="*80)
print("测试结果")
print("="*80)

if len(received_volume) > 0:
    avg_volume = sum(received_volume) / len(received_volume)
    max_volume = max(received_volume)
    
    print(f"接收到的数据包: {len(received_volume)}")
    print(f"平均音量: {avg_volume:.1f}%")
    print(f"峰值音量: {max_volume:.1f}%")
    
    if max_volume > 50:
        print("\n✅ CABLE-A 链路正常工作！")
        print("   Device 28 → Device 36 音频传输成功")
        print("\n🎯 Clubdeck 麦克风应该选择:")
        print("   → CABLE-A Output (VB-Audio Virtual Cable A)")
        print("   → 对应设备 ID: 36")
    elif max_volume > 5:
        print("\n⚠️ 检测到微弱信号")
        print("   链路可能工作但音量太低")
    else:
        print("\n❌ 未检测到信号")
        print("   CABLE-A 可能未正确安装或配置")
else:
    print("❌ 未接收到任何数据")

print("="*80)
