"""
查找从 Clubdeck 读取声音的设备
"""
import sounddevice as sd

print("=" * 70)
print("查找从 Clubdeck 读取声音的设备")
print("=" * 70)

devices = sd.query_devices()

# 根据 3-cable 架构，应该使用 CABLE-C Output 读取 Clubdeck 房间声音
# 但实际可能配置成 CABLE-A Output

print("\n可能用于读取 Clubdeck 的设备 (Output 设备，有输入声道):\n")

candidates = []
for i, dev in enumerate(devices):
    name = dev['name']
    # 查找 CABLE-A 或 CABLE-C 的 Output 设备
    if ('CABLE-A Output' in name or 'CABLE-C Output' in name or 'CABLE Output' in name) and dev['max_input_channels'] > 0:
        api = sd.query_hostapis(dev['hostapi'])['name']
        candidates.append({
            'id': i,
            'name': name,
            'channels': dev['max_input_channels'],
            'sample_rate': int(dev['default_samplerate']),
            'api': api
        })

# 按 API 和采样率排序 (WASAPI 48kHz 优先)
candidates.sort(key=lambda x: (
    0 if x['api'] == 'Windows WASAPI' else 1,
    -x['sample_rate'],  # 48000Hz 优先
    x['channels']  # 2ch 优先
))

for idx, dev in enumerate(candidates, 1):
    priority = "⭐ 推荐" if dev['api'] == 'Windows WASAPI' and dev['sample_rate'] == 48000 and dev['channels'] == 2 else ""
    print(f"  [{dev['id']:2d}] {dev['name']:50s} - {dev['api']:20s} - {dev['channels']:2d}ch {dev['sample_rate']:5d}Hz {priority}")

print("\n" + "=" * 70)
print("3-Cable 架构建议:")
print("=" * 70)
print("""
Clubdeck 配置:
  麦克风输入 = CABLE-A Output  (接收浏览器语音)
  扬声器输出 = CABLE-C Input   (发送房间声音)

Python 读取:
  clubdeck_input_device_id = CABLE-C Output (WASAPI 48kHz 2ch)
  
如果没有 CABLE-C，可以临时使用 CABLE-A Output，
但这样 CABLE-A 会同时用于双向通信，可能产生回声。
""")

# 检查当前配置
print("=" * 70)
print("当前 config.ini 配置:")
print("=" * 70)
try:
    with open('config.ini', 'r', encoding='utf-8') as f:
        for line in f:
            if 'clubdeck_input_device_id' in line:
                print(f"  {line.strip()}")
except:
    pass

print()
