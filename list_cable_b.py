import sounddevice as sd

devices = sd.query_devices()
print("\n所有 CABLE-B 输入设备 (Output 设备):\n")
for i, dev in enumerate(devices):
    if 'CABLE-B' in dev['name'] and dev['max_input_channels'] > 0:
        api = sd.query_hostapis(dev['hostapi'])['name']
        print(f"  [{i:2d}] {dev['name']:50s} - {api:20s} - {dev['max_input_channels']:2d}in/{dev['max_output_channels']:2d}out - {int(dev['default_samplerate'])}Hz")

print("\n所有 CABLE-B 输出设备 (Input 设备):\n")
for i, dev in enumerate(devices):
    if 'CABLE-B' in dev['name'] and dev['max_output_channels'] > 0:
        api = sd.query_hostapis(dev['hostapi'])['name']
        print(f"  [{i:2d}] {dev['name']:50s} - {api:20s} - {dev['max_input_channels']:2d}in/{dev['max_output_channels']:2d}out - {int(dev['default_samplerate'])}Hz")
