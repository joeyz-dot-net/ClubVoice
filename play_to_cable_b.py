"""
生成 MPV 播放到 CABLE-B Input 的命令
"""
import sounddevice as sd
import sys

# 查找 CABLE-B Input WASAPI 设备
devices = sd.query_devices()
cable_b_input = None

for i, dev in enumerate(devices):
    if 'CABLE-B Input' in dev['name'] and dev['max_output_channels'] == 2:
        api = sd.query_hostapis(dev['hostapi'])['name']
        if api == 'Windows WASAPI' and int(dev['default_samplerate']) == 48000:
            cable_b_input = (i, dev)
            break

if not cable_b_input:
    print("❌ 未找到 CABLE-B Input (WASAPI 48kHz) 设备")
    sys.exit(1)

device_id, device_info = cable_b_input

print(f"✓ 找到 CABLE-B Input 设备:")
print(f"  设备 ID: {device_id}")
print(f"  设备名称: {device_info['name']}")
print(f"  采样率: {int(device_info['default_samplerate'])}Hz")
print()

# 生成 sounddevice 播放命令（如果没有 MPV）
print("=" * 70)
print("方法 1: 使用 Python sounddevice 播放")
print("=" * 70)
print(f"""
python -c "import sounddevice as sd; import numpy as np; print('播放测试音到 CABLE-B...'); audio = (np.sin(2*np.pi*440*np.linspace(0,10,480000)) * 0.3 * 32767).astype('int16'); stereo = np.column_stack([audio, audio]); sd.play(stereo, 48000, device={device_id}); sd.wait(); print('完成')"
""")

print()
print("=" * 70)
print("方法 2: 使用 sounddevice 播放 MP3 文件")
print("=" * 70)
print(f"""
# 先安装 soundfile: pip install soundfile
python -c "import sounddevice as sd; import soundfile as sf; data, sr = sf.read('music.mp3'); sd.play(data, sr, device={device_id}); sd.wait()"
""")

print()
print("=" * 70)
print("监控命令 (在另一个终端运行)")
print("=" * 70)
print(f"""
echo "35" | python tools/simple_volume_monitor.py
""")
print("=" * 70)
