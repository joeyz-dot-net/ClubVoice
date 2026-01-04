"""
检查 Python 是否正在读取设备 36
"""
import sounddevice as sd
import numpy as np
import time

print("=" * 70)
print("检查设备 36 是否有音频数据")
print("=" * 70)

device_id = 36

print(f"\n正在从设备 {device_id} 读取 5 秒音频...")
print("请确保 Clubdeck 房间有人说话或播放音乐\n")

try:
    # 读取 5 秒音频
    duration = 5
    sample_rate = 48000
    
    recording = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=2,
        device=device_id,
        dtype='int16'
    )
    
    print("录音中...")
    for i in range(duration, 0, -1):
        print(f"\r剩余 {i} 秒...", end='', flush=True)
        time.sleep(1)
    
    sd.wait()
    print("\r录音完成！    \n")
    
    # 分析音频
    float_data = recording.astype(np.float32) / 32768.0
    rms = np.sqrt(np.mean(float_data ** 2))
    volume = min(100.0, rms * 100.0 * 10.0)
    
    print("=" * 70)
    print("结果分析:")
    print("=" * 70)
    print(f"平均音量: {volume:.1f}%")
    print(f"最大振幅: {np.max(np.abs(float_data)) * 100:.1f}%")
    print(f"样本数: {len(recording)}")
    
    if volume > 10:
        print("\n✅ 设备 36 有音频数据！")
        print("   问题不在设备读取，可能是 Python 程序配置问题")
    elif volume > 1:
        print("\n⚠️  设备 36 有轻微音频，但音量太小")
        print("   需要调高 Clubdeck 输出音量")
    else:
        print("\n❌ 设备 36 没有音频数据！")
        print("   Clubdeck 没有输出到 CABLE-A Input")
    
    print("\n" + "=" * 70)
    print("解决方案:")
    print("=" * 70)
    
    if volume < 1:
        print("""
检查 Clubdeck 配置：
  1. 打开 Clubdeck 音频设置
  2. 扬声器输出设备 = CABLE-A Input (VB-Audio Virtual Cable A)
  3. 主音量调到 80-100%
  
验证方法：
  Win + R → mmsys.cpl → 播放标签
  查看 "CABLE-A Input" 是否有绿色音量条跳动
""")
    else:
        print("""
设备有音频，但 Python 程序可能有问题：
  1. 检查 Python 终端是否有错误信息
  2. 确认看到 "CABLE-A (Clubdeck→浏览器) 设备 36"
  3. 重启程序: Ctrl+C 然后 python run.py
  
可能的问题：
  - 设备被其他程序独占
  - 采样率不匹配
  - 程序启动时设备不可用
""")

except Exception as e:
    print(f"\n❌ 错误: {e}")
    print("\n设备可能被占用或不可用")
    print("解决方法:")
    print("  1. 关闭占用设备的程序")
    print("  2. 重启 VB-Cable 音频引擎")
    print("  3. 重启 Python 程序")

print("=" * 70)
