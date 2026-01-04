"""
检查Python输出流状态
"""
import sounddevice as sd

print("=" * 70)
print("检查设备28 (CABLE-A Input) 状态")
print("=" * 70)

try:
    device_info = sd.query_devices(28)
    print(f"\n设备名称: {device_info['name']}")
    print(f"输出声道: {device_info['max_output_channels']}")
    print(f"默认采样率: {int(device_info['default_samplerate'])}Hz")
    
    if device_info['max_output_channels'] == 0:
        print("\n❌ 错误：此设备不支持输出（无法写入）")
        print("   CABLE-A Input应该有输出声道")
    else:
        print(f"\n✅ 设备支持输出: {device_info['max_output_channels']}声道")
        
        print("\n现在测试写入音频到设备28...")
        print("如果Clubdeck麦克风设置正确，房间应该听到测试音")
        
        import numpy as np
        import time
        
        # 生成测试音（440Hz A4音符，3秒）
        duration = 3
        sample_rate = 48000
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = np.sin(2 * np.pi * 440 * t) * 0.3  # 30%音量
        
        # 转换为立体声int16
        stereo_tone = np.column_stack([tone, tone])
        int16_tone = (stereo_tone * 32767).astype(np.int16)
        
        print(f"\n播放 {duration}秒 440Hz测试音到设备28...")
        print("Clubdeck房间应该能听到 '嘟~' 声")
        
        sd.play(int16_tone, sample_rate, device=28, blocking=True)
        
        print("\n✅ 测试音播放完成")
        print("\n如果Clubdeck听到了测试音：")
        print("  → Python→Clubdeck通路正常")
        print("  → 检查浏览器是否真的在发送音频")
        print("  → 检查 debug.html '发送包数' 是否增加")
        print("\n如果Clubdeck没听到测试音：")
        print("  → Clubdeck麦克风输入设置错误")
        print("  → 应设置为: CABLE-A Output (设备36)")

except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
