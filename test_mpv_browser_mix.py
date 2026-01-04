"""
测试方案1：MPV + 浏览器麦克风都输出到 CABLE-A Input，验证自动混音
"""
import sounddevice as sd
import numpy as np
import time
import threading

print("\n" + "="*80)
print("方案1测试：CABLE-A Input 自动混音")
print("="*80)
print("\n架构：")
print("  浏览器麦克风 → Device 28 (CABLE-A Input)")
print("  MPV 音乐     → Device 28 (CABLE-A Input)")
print("  ↓ (VB-Cable 内部自动混音)")
print("  Clubdeck 麦克风 ← Device 36 (CABLE-A Output)")
print("="*80)

# 生成两个不同的测试音
sample_rate = 48000
duration = 2.0
t = np.arange(0, duration, 1/sample_rate)

# 440Hz 代表浏览器麦克风
browser_tone = (np.sin(2*np.pi*440*t) * 8000).astype(np.int16)
# 880Hz 代表 MPV 音乐
mpv_tone = (np.sin(2*np.pi*880*t) * 8000).astype(np.int16)

browser_stereo = np.column_stack([browser_tone, browser_tone])
mpv_stereo = np.column_stack([mpv_tone, mpv_tone])

# 接收数据
received_data = []
detected_440 = False
detected_880 = False

def input_callback(indata, frames, time_info, status):
    """从 Device 36 (CABLE-A Output) 录音"""
    global detected_440, detected_880
    if status:
        print(f"[录音状态] {status}")
    
    received_data.append(indata.copy())
    
    # 简单频率检测
    float_data = indata[:, 0].astype(np.float32)
    rms = np.sqrt(np.mean(float_data ** 2))
    volume = rms * 32768
    
    if volume > 3000:
        # 计算主频率（简化版）
        fft = np.fft.rfft(float_data)
        freqs = np.fft.rfftfreq(len(float_data), 1/sample_rate)
        peak_freq = freqs[np.argmax(np.abs(fft))]
        
        if 400 < peak_freq < 500:
            detected_440 = True
        if 800 < peak_freq < 1000:
            detected_880 = True

print("\n[1/4] 启动监听端 (Device 36 - CABLE-A Output)...")
input_stream = sd.InputStream(
    device=36,
    samplerate=48000,
    channels=2,
    dtype='float32',
    callback=input_callback
)
input_stream.start()
time.sleep(0.5)

print("[2/4] 发送浏览器测试音 (440Hz) 到 Device 28...")
output_stream1 = sd.OutputStream(device=28, samplerate=48000, channels=2, dtype='int16')
output_stream1.start()

def play_browser():
    output_stream1.write(browser_stereo)
    output_stream1.stop()
    output_stream1.close()

browser_thread = threading.Thread(target=play_browser)
browser_thread.start()

time.sleep(0.5)

print("[3/4] 同时发送 MPV 测试音 (880Hz) 到 Device 28...")
with sd.OutputStream(device=28, samplerate=48000, channels=2, dtype='int16') as output_stream2:
    output_stream2.write(mpv_stereo)

print("[4/4] 等待接收完成...")
time.sleep(2.0)

input_stream.stop()
input_stream.close()
browser_thread.join()

print("\n" + "="*80)
print("测试结果")
print("="*80)

success = detected_440 and detected_880

if success:
    print("✅ 成功！VB-Cable 自动混音工作正常")
    print(f"   检测到 440Hz (浏览器音): {'是' if detected_440 else '否'}")
    print(f"   检测到 880Hz (MPV音乐): {'是' if detected_880 else '否'}")
    print("\n🎉 方案1可行！")
    print("\n📋 操作步骤：")
    print("   1. 打开 MPV 播放器设置")
    print("   2. 音频输出设备选择：CABLE-A Input (VB-Audio Virtual Cable A)")
    print("   3. 或者在 MPV 配置文件中添加：")
    print("      audio-device=wasapi/{设备ID}")
    print("\n✨ 配置后效果：")
    print("   - Clubdeck 可以听到：浏览器麦克风 + MPV 音乐（自动混音）")
    print("   - 浏览器可以听到：Clubdeck 房间 + MPV 音乐")
    
elif detected_440 or detected_880:
    print("⚠️ 部分成功")
    print(f"   检测到 440Hz (浏览器音): {'是' if detected_440 else '否'}")
    print(f"   检测到 880Hz (MPV音乐): {'是' if detected_880 else '否'}")
    print("\n可能原因：")
    print("   - 两个音源同时写入可能有竞争")
    print("   - 需要确保 VB-Cable 支持多个写入者")
    
else:
    print("❌ 未检测到混音信号")
    print("\n可能原因：")
    print("   1. VB-Cable 可能不支持多个程序同时写入同一设备")
    print("   2. 需要使用 VoiceMeeter 等专业混音软件")
    print("\n💡 建议：")
    print("   - 尝试方案2（VoiceMeeter）")
    print("   - 或者让我实现方案3（Python端混音）")

print("="*80)
