"""
简化版音量监控工具
无需 Rich 库，直接在终端显示音量条
"""
import sounddevice as sd
import numpy as np
import time
import sys


def clear_line():
    """清除当前行"""
    sys.stdout.write('\r')
    sys.stdout.flush()


def create_bar(value: float, width: int = 50, char: str = '█') -> str:
    """
    创建进度条
    
    Args:
        value: 值 (0-100)
        width: 宽度
        char: 填充字符
        
    Returns:
        进度条字符串
    """
    filled = int(value / 100.0 * width)
    empty = width - filled
    return char * filled + '░' * empty


def calculate_volume(audio_data: np.ndarray) -> float:
    """
    计算音量 (RMS)
    
    Args:
        audio_data: 音频数据
        
    Returns:
        音量 (0-100)
    """
    if audio_data.dtype == np.int16:
        float_data = audio_data.astype(np.float32) / 32768.0
    else:
        float_data = audio_data
    
    rms = np.sqrt(np.mean(float_data ** 2))
    return min(100.0, rms * 100.0 * 10.0)


def list_devices():
    """列出所有设备"""
    print("\n可用音频设备:")
    print("=" * 80)
    
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        input_ch = dev['max_input_channels']
        output_ch = dev['max_output_channels']
        
        if input_ch > 0 or output_ch > 0:
            print(f"[{i:2d}] {dev['name']}")
            print(f"     输入: {input_ch}ch, 输出: {output_ch}ch, "
                  f"采样率: {int(dev['default_samplerate'])}Hz")
    
    print("=" * 80)


def monitor_volume(device_id: int, duration: float = None):
    """
    监控设备音量
    
    Args:
        device_id: 设备ID
        duration: 监控时长(秒)，None = 无限
    """
    device_info = sd.query_devices(device_id)
    sample_rate = int(device_info['default_samplerate'])
    channels = min(device_info['max_input_channels'], 2)
    
    print(f"\n{'='*80}")
    print(f"监控设备 ID: {device_id}")
    print(f"设备名称: {device_info['name']}")
    print(f"采样率: {sample_rate}Hz, 声道数: {channels}")
    print(f"按 Ctrl+C 停止监控")
    print(f"{'='*80}\n")
    
    start_time = time.time()
    frame_count = 0
    peak_volume = 0.0
    
    def callback(indata, frames, time_info, status):
        nonlocal frame_count, peak_volume
        
        if status:
            print(f"\n警告: {status}")
        
        # 计算音量
        volume = calculate_volume(indata)
        frame_count += 1
        peak_volume = max(peak_volume, volume)
        
        # 显示音量条
        bar = create_bar(volume, width=50)
        clear_line()
        sys.stdout.write(f"音量: [{bar}] {volume:5.1f}% | 峰值: {peak_volume:5.1f}% | 帧: {frame_count}")
        sys.stdout.flush()
    
    try:
        with sd.InputStream(
            device=device_id,
            samplerate=sample_rate,
            channels=channels,
            dtype='int16',
            blocksize=512,
            callback=callback
        ):
            if duration:
                time.sleep(duration)
            else:
                # 无限循环直到用户中断
                while True:
                    time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n\n监控已停止")
    except Exception as e:
        print(f"\n\n错误: {e}")
    finally:
        runtime = time.time() - start_time
        fps = frame_count / runtime if runtime > 0 else 0
        print(f"\n运行时间: {runtime:.1f}s")
        print(f"平均帧率: {fps:.1f} FPS")
        print(f"总帧数: {frame_count}")


def main():
    """主函数"""
    print("=" * 80)
    print(" " * 25 + "🎤 音量监控工具 🎤")
    print("=" * 80)
    
    list_devices()
    
    try:
        device_input = input("\n请输入要监控的设备 ID (留空退出): ").strip()
        
        if not device_input:
            print("已取消")
            return
        
        device_id = int(device_input)
        
        # 验证设备
        device_info = sd.query_devices(device_id)
        if device_info['max_input_channels'] == 0:
            print(f"错误: 设备 {device_id} 不支持输入!")
            return
        
        # 开始监控
        monitor_volume(device_id)
    
    except ValueError:
        print("错误: 请输入有效的数字")
    except KeyboardInterrupt:
        print("\n已取消")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
