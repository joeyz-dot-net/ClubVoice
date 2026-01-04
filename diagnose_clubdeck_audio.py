"""
诊断 Clubdeck 音频输出问题
"""
import sounddevice as sd

print("=" * 70)
print("Clubdeck 音频输出诊断")
print("=" * 70)

print("\n当前配置:")
print("  clubdeck_input_device_id = 36 (CABLE-A Output) - Python 读取")
print("  browser_output_device_id = 28 (CABLE-A Input) - Python 写入")

print("\n" + "=" * 70)
print("CABLE-A 设备详情:")
print("=" * 70)

# CABLE-A Input - Clubdeck 应该输出到这里
dev_input = sd.query_devices(28)
print(f"\n设备 28 (CABLE-A Input):")
print(f"  名称: {dev_input['name']}")
print(f"  输入声道: {dev_input['max_input_channels']}")
print(f"  输出声道: {dev_input['max_output_channels']}")
print(f"  作用: Clubdeck 扬声器应该输出到这个设备")

# CABLE-A Output - Python 从这里读取
dev_output = sd.query_devices(36)
print(f"\n设备 36 (CABLE-A Output):")
print(f"  名称: {dev_output['name']}")
print(f"  输入声道: {dev_output['max_input_channels']}")
print(f"  输出声道: {dev_output['max_output_channels']}")
print(f"  作用: Python 从这个设备读取 Clubdeck 声音")

print("\n" + "=" * 70)
print("问题诊断:")
print("=" * 70)

print("""
如果设备 36 没有读取到 Clubdeck 声音，请检查:

1️⃣ Clubdeck 扬声器输出设备配置
   ❌ 错误设置: 系统默认扬声器 / 其他设备
   ✅ 正确设置: CABLE-A Input (VB-Audio Virtual Cable A)
   
   在 Clubdeck 中:
   - 打开音频设置
   - 扬声器/输出设备 = CABLE-A Input

2️⃣ Clubdeck 是否有声音输出
   - 房间内有人说话吗？
   - Clubdeck 本身有音量输出吗？
   - 可以在 Windows 声音设置中查看 CABLE-A Input 是否有音量活动

3️⃣ 测试 CABLE-A 虚拟线缆
   运行下面的命令来测试虚拟线缆是否工作:
   
   终端 1 (监控 CABLE-A Output):
     echo "36" | python tools/simple_volume_monitor.py
   
   终端 2 (播放测试音到 CABLE-A Input):
     python -c "import sounddevice as sd; import numpy as np; audio = (np.sin(2*np.pi*440*np.linspace(0,5,240000)) * 0.3 * 32767).astype('int16'); stereo = np.column_stack([audio, audio]); sd.play(stereo, 48000, device=28); sd.wait()"
   
   如果终端 1 看到音量波动，说明虚拟线缆工作正常。
   如果没有波动，可能需要重启 VB-Cable 驱动或重启系统。
""")

print("=" * 70)
print("Windows 声音设置检查:")
print("=" * 70)
print("""
快速检查方法:
1. Win + R 打开运行
2. 输入: mmsys.cpl
3. 点击"播放"标签
4. 查看 "CABLE-A Input" 是否有绿色音量条跳动
   - 有跳动 = Clubdeck 正在输出到这里 ✅
   - 无跳动 = Clubdeck 没有输出到这里 ❌
""")

print("=" * 70)
response = input("\n是否运行 CABLE-A 虚拟线缆测试? (y/n): ").strip().lower()

if response == 'y':
    print("\n正在启动测试...")
    print("请同时运行: echo \"36\" | python tools/simple_volume_monitor.py")
    print("\n按回车开始播放测试音到 CABLE-A Input...")
    input()
    
    import numpy as np
    import time
    
    print("播放 5 秒测试音到设备 28 (CABLE-A Input)...")
    duration = 5
    sample_rate = 48000
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * 440 * t) * 0.3
    stereo = np.column_stack([audio, audio])
    audio_int16 = (stereo * 32767).astype(np.int16)
    
    sd.play(audio_int16, samplerate=sample_rate, device=28)
    
    for i in range(duration, 0, -1):
        print(f"\r播放中... {i} 秒", end='', flush=True)
        time.sleep(1)
    
    sd.wait()
    print("\r✓ 播放完成！           ")
    print("\n如果设备 36 的监控显示音量波动，说明虚拟线缆正常工作")
else:
    print("\n已取消测试")
