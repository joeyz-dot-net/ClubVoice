"""测试输出设备 28 (CABLE-A Input)"""
import sounddevice as sd
import numpy as np

print("\n=== Device 28 (CABLE-A Input) ===")
devices = sd.query_devices()
d = devices[28]
print(f"Name: {d['name']}")
print(f"Input channels: {d['max_input_channels']}")
print(f"Output channels: {d['max_output_channels']}")
print(f"Sample rate: {d['default_samplerate']}Hz")

print("\n=== Testing output to device 28 ===")
# 生成 0.5 秒 440Hz 测试音
test_tone = (np.sin(2*np.pi*440*np.arange(0, 0.5, 1/48000)) * 10000).astype(np.int16)

try:
    with sd.OutputStream(device=28, samplerate=48000, channels=2, dtype='int16') as stream:
        # 立体声输出
        stereo_tone = np.column_stack([test_tone, test_tone])
        stream.write(stereo_tone)
    print("✓ Test tone sent to device 28 successfully")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n提示: 如果 Clubdeck 配置正确（麦克风=CABLE-A Output），应该能听到测试音")
