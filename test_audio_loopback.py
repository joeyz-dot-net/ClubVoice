"""检测音频回环：测试浏览器麦克风是否会被发送回浏览器"""
import sounddevice as sd
import numpy as np
import time
import threading

print("\n" + "="*80)
print("音频回环检测")
print("="*80)
print("\n当前配置：")
print("  浏览器麦克风 → Device 28 (CABLE-A Input) → Clubdeck 麦克风")
print("  Clubdeck 扬声器 → Device 34 (CABLE Output) → 浏览器扬声器")
print("\n测试方法：")
print("  1. 发送440Hz测试音到 Device 28")
print("  2. 监听 Device 34 是否收到该测试音")
print("  3. 如果收到，说明有音频回环！")
print("="*80)

# 生成测试音：440Hz 正弦波，持续1秒
sample_rate = 48000
duration = 1.0
t = np.arange(0, duration, 1/sample_rate)
test_tone = (np.sin(2*np.pi*440*t) * 10000).astype(np.int16)
stereo_tone = np.column_stack([test_tone, test_tone])

received_data = []
detected_tone = False

def input_callback(indata, frames, time_info, status):
    """从 Device 34 录音"""
    global detected_tone
    if status:
        print(f"[录音状态] {status}")
    
    # 检测是否有440Hz信号
    float_data = indata[:, 0].astype(np.float32)
    
    # 简单频率检测：计算峰值
    rms = np.sqrt(np.mean(float_data ** 2))
    volume = rms * 32768
    
    if volume > 5000:  # 检测到强信号
        detected_tone = True
        received_data.append(volume)

print("\n[1/3] 启动监听端 (Device 34 - Clubdeck 房间输出)...")
input_stream = sd.InputStream(
    device=34,
    samplerate=48000,
    channels=2,
    dtype='float32',
    callback=input_callback
)
input_stream.start()
time.sleep(0.5)

print("[2/3] 发送测试音到 Device 28 (浏览器麦克风输出)...")
with sd.OutputStream(device=28, samplerate=48000, channels=2, dtype='int16') as output_stream:
    output_stream.write(stereo_tone)

print("[3/3] 等待接收完成...")
time.sleep(1.5)

input_stream.stop()
input_stream.close()

print("\n" + "="*80)
print("检测结果")
print("="*80)

if detected_tone:
    avg_volume = sum(received_data) / len(received_data) if received_data else 0
    print(f"❌ 检测到音频回环！")
    print(f"   接收到的测试音音量: {avg_volume:.0f}")
    print(f"\n⚠️ 问题原因：")
    print("   Clubdeck 的配置可能有误：")
    print("   - Clubdeck 扬声器输出可能设置为 CABLE-A Input")
    print("   - 或者 VB-Cable 驱动配置了环回模式")
    print(f"\n🔧 解决方案：")
    print("   1. 检查 Clubdeck 扬声器输出设备")
    print("      应该是：CABLE Input (VB-Audio Virtual Cable)")
    print("      不应该是：CABLE-A Input")
    print("   2. 确认 Clubdeck 麦克风输入设备")
    print("      应该是：CABLE-A Output (VB-Audio Virtual Cable A)")
else:
    print("✅ 未检测到音频回环")
    print("   Device 28 → Device 34 路径隔离正常")
    print("\n   回音可能来自其他原因：")
    print("   - 浏览器端的回声消除未生效")
    print("   - 网络延迟导致的回声")
    print("   - Clubdeck 房间内其他用户的麦克风开启")

print("="*80)
