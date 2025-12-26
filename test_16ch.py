"""
测试从 VB-Cable 16ch 读取数据
"""
import sounddevice as sd
import numpy as np
import time

def list_devices():
    """列出所有音频设备"""
    print("\n可用音频设备:")
    print("-" * 60)
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        ch_in = dev['max_input_channels']
        ch_out = dev['max_output_channels']
        rate = int(dev['default_samplerate'])
        name = dev['name']
        if ch_in > 0 or ch_out > 0:
            print(f"[{i:2d}] {name}")
            print(f"     输入: {ch_in}ch, 输出: {ch_out}ch, 采样率: {rate}Hz")

def test_read_16ch(device_id: int, duration: float = 3.0):
    """测试读取 16ch 设备"""
    device_info = sd.query_devices(device_id)
    channels = device_info['max_input_channels']
    sample_rate = int(device_info['default_samplerate'])
    
    print(f"\n测试设备: {device_info['name']}")
    print(f"声道数: {channels}")
    print(f"采样率: {sample_rate} Hz")
    print(f"录制时长: {duration} 秒")
    print("-" * 60)
    
    # 录制音频
    print("开始录制...")
    recording = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=channels,
        device=device_id,
        dtype='int16'
    )
    sd.wait()
    print("录制完成!")
    
    # 分析数据
    print(f"\n数据形状: {recording.shape}")
    print(f"数据类型: {recording.dtype}")
    print(f"数据范围: [{recording.min()}, {recording.max()}]")
    
    # 分析每个声道
    print("\n各声道分析:")
    for ch in range(min(channels, 16)):
        ch_data = recording[:, ch]
        rms = np.sqrt(np.mean(ch_data.astype(np.float32) ** 2))
        max_val = np.max(np.abs(ch_data))
        has_audio = max_val > 100  # 简单判断是否有音频
        status = "✓ 有音频" if has_audio else "✗ 静音"
        print(f"  声道 {ch+1:2d}: RMS={rms:8.1f}, 峰值={max_val:6d}  {status}")
    
    # 转换为立体声测试
    print("\n转换为立体声:")
    if channels >= 2:
        stereo = recording[:, :2].copy()
        print(f"  立体声形状: {stereo.shape}")
        print(f"  左声道 RMS: {np.sqrt(np.mean(stereo[:, 0].astype(np.float32) ** 2)):.1f}")
        print(f"  右声道 RMS: {np.sqrt(np.mean(stereo[:, 1].astype(np.float32) ** 2)):.1f}")
    
    return recording

def main():
    list_devices()
    
    print("\n" + "=" * 60)
    device_id = input("请输入要测试的设备 ID (留空退出): ").strip()
    
    if not device_id:
        return
    
    try:
        device_id = int(device_id)
        test_read_16ch(device_id, duration=3.0)
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    main()
