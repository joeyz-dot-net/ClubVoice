"""
测试浏览器麦克风到 Clubdeck 的音频路径
"""
import sounddevice as sd
import numpy as np
import time

# 根据 config.ini: browser_output_device_id = 28
BROWSER_MIC_OUTPUT = 28  # CABLE-A Input (浏览器麦克风写入这里)

print("=" * 70)
print("浏览器麦克风设备测试")
print("=" * 70)

# 获取设备信息
dev = sd.query_devices(BROWSER_MIC_OUTPUT)
print(f"\n设备 {BROWSER_MIC_OUTPUT}: {dev['name']}")
print(f"  输入声道: {dev['max_input_channels']}")
print(f"  输出声道: {dev['max_output_channels']}")
print(f"  采样率: {int(dev['default_samplerate'])}Hz")
print(f"  类型: {'可写入(播放)' if dev['max_output_channels'] > 0 else '不可写入'}")

print("\n" + "=" * 70)
print("测试方案:")
print("=" * 70)
print("""
1. 关闭 Clubdeck 音乐输出（你已准备好）
2. 在 Clubdeck 中确认:
   - 麦克风输入设备 = CABLE-A Output
3. 运行下面的测试命令，会播放 5 秒测试音到 CABLE-A Input
4. 在 Clubdeck 房间中应该能听到 440Hz 蜂鸣声

测试命令:
  python -c "import sounddevice as sd; import numpy as np; print('播放测试音到 CABLE-A Input (模拟浏览器麦克风)...'); audio = (np.sin(2*np.pi*440*np.linspace(0,5,240000)) * 0.3 * 32767).astype('int16'); stereo = np.column_stack([audio, audio]); sd.play(stereo, 48000, device=28); sd.wait(); print('完成')"

或直接运行:
""")

# 询问是否立即测试
try:
    response = input("\n是否立即播放测试音? (y/n): ").strip().lower()
    
    if response == 'y':
        print("\n播放 5 秒 440Hz 测试音到 CABLE-A Input...")
        print("如果 Clubdeck 麦克风正确设置为 CABLE-A Output，房间内应该听到声音")
        print()
        
        # 生成 5 秒 440Hz 正弦波
        duration = 5
        sample_rate = 48000
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.sin(2 * np.pi * 440 * t) * 0.3
        stereo = np.column_stack([audio, audio])
        audio_int16 = (stereo * 32767).astype(np.int16)
        
        # 播放
        sd.play(audio_int16, samplerate=sample_rate, device=BROWSER_MIC_OUTPUT)
        
        # 显示倒计时
        for i in range(duration, 0, -1):
            print(f"\r播放中... {i} 秒", end='', flush=True)
            time.sleep(1)
        
        sd.wait()
        print("\r✓ 播放完成！           ")
        print("\n如果 Clubdeck 房间听到了声音，说明麦克风路径正常！")
    else:
        print("\n已取消测试")
        
except KeyboardInterrupt:
    print("\n\n已取消")
except Exception as e:
    print(f"\n错误: {e}")

print("\n" + "=" * 70)
print("Clubdeck 配置检查清单:")
print("=" * 70)
print("""
✓ 麦克风输入设备 = CABLE-A Output (接收 Python/浏览器的音频)
✓ 扬声器输出设备 = CABLE-A Input (发送房间音频到 Python)
""")
