"""
调整 CABLE-A 音量
"""
import sounddevice as sd

print("=" * 70)
print("CABLE-A 音量诊断")
print("=" * 70)

print("""
✓ Clubdeck 正在输出到 CABLE-A Input（有跳动）
✗ 但音量太小

可能原因:
1. Clubdeck 输出音量太低
2. CABLE-A Input 设备音量太低
3. VB-Cable 系统音量太低

解决方案:
""")

print("=" * 70)
print("1️⃣ 调整 Clubdeck 输出音量")
print("=" * 70)
print("""
在 Clubdeck 中:
- 找到主音量/扬声器音量控制
- 将音量调高到 80-100%
- 确保没有静音
""")

print("=" * 70)
print("2️⃣ 调整 Windows 中 CABLE-A Input 的音量")
print("=" * 70)
print("""
方法 A: 图形界面
1. Win + R → mmsys.cpl
2. 播放标签 → 找到 "CABLE-A Input"
3. 右键 → 属性 → 级别
4. 将音量调到 100%

方法 B: 命令行（现在就可以运行）
""")

print("=" * 70)
response = input("是否自动将 CABLE-A Input 音量设置为 100%? (y/n): ").strip().lower()

if response == 'y':
    import subprocess
    
    print("\n尝试使用 nircmd 设置音量...")
    print("（如果没有安装 nircmd，此步骤会失败，需要手动调整）")
    
    # 尝试使用 nircmd（如果安装了）
    try:
        result = subprocess.run(
            ['nircmd', 'setsysvolume', '65535'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✓ 系统音量已设置")
        else:
            print("✗ nircmd 未安装")
    except FileNotFoundError:
        print("✗ nircmd 未安装")
    
    print("\n请手动调整:")
    print("1. Win + R → mmsys.cpl")
    print("2. 播放 → CABLE-A Input → 属性 → 级别 → 100%")

print("\n" + "=" * 70)
print("3️⃣ 实时监控音量")
print("=" * 70)
print("""
运行监控命令查看调整后的效果:
  echo "36" | python tools/simple_volume_monitor.py

调整后应该看到:
- 有人说话时: 40-80% 音量
- 音乐播放时: 30-60% 音量
- 安静时: 0-5% 音量
""")

print("=" * 70)
print("4️⃣ 测试完整音频链路")
print("=" * 70)
print("""
在另一个终端运行:
  echo "36" | python tools/simple_volume_monitor.py

然后在 Clubdeck 房间中:
- 大声说话
- 播放音乐
- 观察监控终端的音量变化

如果音量仍然很小 (<10%)，可能需要:
- 检查 Clubdeck 内部的音量设置
- 检查 VB-Cable 驱动是否正常
- 重启 VB-Cable Audio Engine
""")

print("\n" + "=" * 70)
print("5️⃣ 快速测试")
print("=" * 70)

response2 = input("\n是否播放大音量测试音到 CABLE-A Input? (y/n): ").strip().lower()

if response2 == 'y':
    import numpy as np
    import time
    
    print("\n播放大音量测试音到 CABLE-A Input (设备 28)...")
    print("同时监控设备 36 看音量是否足够大\n")
    
    duration = 5
    sample_rate = 48000
    t = np.linspace(0, duration, int(sample_rate * duration))
    # 增加音量到 0.6 (原来是 0.3)
    audio = np.sin(2 * np.pi * 440 * t) * 0.6
    stereo = np.column_stack([audio, audio])
    audio_int16 = (stereo * 32767).astype(np.int16)
    
    sd.play(audio_int16, samplerate=sample_rate, device=28)
    
    for i in range(duration, 0, -1):
        print(f"\r播放中... {i} 秒 (如果设备 36 监控显示 60-80% 说明正常)", end='', flush=True)
        time.sleep(1)
    
    sd.wait()
    print("\r✓ 播放完成！" + " " * 60)
    print("\n如果设备 36 显示的音量 > 50%，说明虚拟线缆工作正常")
    print("如果音量很小 (< 20%)，需要调整 Windows 音量设置")

print("\n" + "=" * 70)
