"""
使用 Python 播放 music.mp3 到 CABLE-B Input (设备 30)
"""
import sounddevice as sd
import numpy as np
from pathlib import Path
import time

try:
    import soundfile as sf
    has_soundfile = True
except ImportError:
    has_soundfile = False
    print("⚠️  未安装 soundfile 库，无法播放 MP3")
    print("请运行: pip install soundfile")
    print()

# 设备配置
CABLE_B_INPUT = 30  # CABLE-B Input (VB-Audio Virtual Cable B) WASAPI 48kHz
TARGET_SAMPLE_RATE = 48000

def play_mp3(file_path):
    """播放 MP3 文件到 CABLE-B Input"""
    if not has_soundfile:
        return False
    
    print(f"🎵 播放: {file_path}")
    print(f"📤 输出设备: {CABLE_B_INPUT} (CABLE-B Input)")
    print()
    
    try:
        # 读取音频文件
        print("读取音频文件...")
        data, sample_rate = sf.read(str(file_path))
        
        # 显示音频信息
        duration = len(data) / sample_rate
        channels = 1 if data.ndim == 1 else data.shape[1]
        print(f"✓ 采样率: {sample_rate}Hz")
        print(f"✓ 声道数: {channels}")
        print(f"✓ 时长: {duration:.1f}秒")
        print()
        
        # 转换为立体声（如果是单声道）
        if data.ndim == 1:
            data = np.column_stack([data, data])
        
        # 重采样到 48kHz（如果需要）
        if sample_rate != TARGET_SAMPLE_RATE:
            print(f"重采样: {sample_rate}Hz → {TARGET_SAMPLE_RATE}Hz")
            ratio = TARGET_SAMPLE_RATE / sample_rate
            new_length = int(len(data) * ratio)
            indices = np.linspace(0, len(data) - 1, new_length)
            data = np.array([np.interp(indices, np.arange(len(data)), data[:, i]) 
                           for i in range(data.shape[1])]).T
            sample_rate = TARGET_SAMPLE_RATE
        
        print(f"开始播放...")
        print(f"[提示] 请在另一个终端运行: echo \"35\" | python tools/simple_volume_monitor.py")
        print()
        
        # 播放
        sd.play(data, samplerate=sample_rate, device=CABLE_B_INPUT)
        
        # 显示进度
        start_time = time.time()
        while sd.get_stream().active:
            elapsed = time.time() - start_time
            progress = min(100, (elapsed / duration) * 100)
            bar_length = 40
            filled = int(bar_length * progress / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            print(f'\r播放进度: [{bar}] {progress:5.1f}% ({elapsed:.1f}s / {duration:.1f}s)', end='')
            time.sleep(0.1)
        
        print()
        print()
        print("✓ 播放完成！")
        return True
        
    except FileNotFoundError:
        print(f"❌ 文件不存在: {file_path}")
        return False
    except Exception as e:
        print(f"❌ 播放失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    # 查找 music.mp3
    music_file = Path("music.mp3")
    
    if not music_file.exists():
        # 在当前目录和上级目录查找
        for path in [Path.cwd(), Path.cwd().parent]:
            test_file = path / "music.mp3"
            if test_file.exists():
                music_file = test_file
                break
    
    if not music_file.exists():
        print("❌ 未找到 music.mp3")
        print("请将 music.mp3 放到当前目录")
        return
    
    play_mp3(music_file)

if __name__ == "__main__":
    main()
