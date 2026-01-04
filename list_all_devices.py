"""列出所有音频设备的详细信息"""
import sounddevice as sd

devices = sd.query_devices()

print("\n" + "="*80)
print("所有音频设备详情")
print("="*80)

for i, dev in enumerate(devices):
    print(f"\n[{i:2d}] {dev['name']}")
    print(f"    输入声道: {dev['max_input_channels']}")
    print(f"    输出声道: {dev['max_output_channels']}")
    print(f"    采样率: {int(dev['default_samplerate'])}Hz")
    
    # 标注设备类型
    if dev['max_input_channels'] > 0 and dev['max_output_channels'] > 0:
        print(f"    类型: 双向设备（录音+播放）")
    elif dev['max_input_channels'] > 0:
        print(f"    类型: 录音设备（麦克风输入）⬅️ Clubdeck 应从这里读取")
    elif dev['max_output_channels'] > 0:
        print(f"    类型: 播放设备（扬声器输出）➡️ Python 可写入")

print("\n" + "="*80)
print("当前配置：")
print("="*80)
print("browser_output_device_id = 28 (Python 写入)")
print("  → CABLE-A Input (VB-Audio Virtual Cable A)")
print("\nClubdeck 麦克风应该选择：")
print("  → 找到 'CABLE-A' 且 max_input_channels > 0 的设备")
print("="*80)
