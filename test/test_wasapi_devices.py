"""
Windows WASAPI 音频设备测试程序
测试哪些设备可以成功打开和使用 + 实时音量监控
"""
import sounddevice as sd
import numpy as np
import time
import threading
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout


console = Console()

# 全局音量数据存储
volume_data = {}
volume_lock = threading.Lock()


def test_output_device(device_id: int, device_info: dict, sample_rate: int = 48000, channels: int = 2) -> dict:
    """
    测试输出设备是否可用
    
    Returns:
        dict: 测试结果 {'success': bool, 'error': str, 'latency': float}
    """
    result = {
        'success': False,
        'error': None,
        'latency': 0.0,
        'tested_sample_rate': sample_rate,
        'tested_channels': channels
    }
    
    try:
        # 生成测试音频（静音）
        test_audio = np.zeros((1024, channels), dtype='int16')
        
        # 尝试打开输出流
        stream = sd.OutputStream(
            device=device_id,
            samplerate=sample_rate,
            channels=channels,
            dtype='int16',
            blocksize=512
        )
        
        start_time = time.time()
        stream.start()
        
        # 写入测试数据
        stream.write(test_audio)
        
        end_time = time.time()
        result['latency'] = (end_time - start_time) * 1000  # 转换为毫秒
        
        stream.stop()
        stream.close()
        
        result['success'] = True
        
    except sd.PortAudioError as e:
        result['error'] = f"PortAudio错误: {str(e)}"
    except Exception as e:
        result['error'] = f"其他错误: {str(e)}"
    
    return result


def test_input_device(device_id: int, device_info: dict, sample_rate: int = 48000, channels: int = 2) -> dict:
    """
    测试输入设备是否可用
    
    Returns:
        dict: 测试结果 {'success': bool, 'error': str, 'latency': float}
    """
    result = {
        'success': False,
        'error': None,
        'latency': 0.0,
        'tested_sample_rate': sample_rate,
        'tested_channels': channels
    }
    
    try:
        # 尝试打开输入流
        stream = sd.InputStream(
            device=device_id,
            samplerate=sample_rate,
            channels=channels,
            dtype='int16',
            blocksize=512
        )
        
        start_time = time.time()
        stream.start()
        
        # 读取测试数据
        data, overflowed = stream.read(512)
        
        end_time = time.time()
        result['latency'] = (end_time - start_time) * 1000  # 转换为毫秒
        
        stream.stop()
        stream.close()
        
        result['success'] = True
        
    except sd.PortAudioError as e:
        result['error'] = f"PortAudio错误: {str(e)}"
    except Exception as e:
        result['error'] = f"其他错误: {str(e)}"
    
    return result


def calculate_volume(audio_data: np.ndarray) -> float:
    """计算音量 (RMS)"""
    if audio_data.dtype == np.int16:
        float_data = audio_data.astype(np.float32) / 32768.0
    else:
        float_data = audio_data
    
    rms = np.sqrt(np.mean(float_data ** 2))
    return min(100.0, rms * 100.0 * 10.0)


def create_volume_bar(volume: float, width: int = 15) -> str:
    """创建音量条"""
    filled = int(volume / 100.0 * width)
    empty = width - filled
    
    if volume < 20:
        color = "green"
    elif volume < 50:
        color = "yellow"
    elif volume < 80:
        color = "orange1"
    else:
        color = "red"
    
    bar = "█" * filled + "░" * empty
    return f"[{color}]{bar}[/{color}]"


def monitor_input_device(device_id: int, device_info: dict, stop_event: threading.Event):
    """后台监控输入设备音量"""
    try:
        sample_rate = int(device_info['default_samplerate'])
        channels = min(device_info['max_input_channels'], 2)
        
        def callback(indata, frames, time_info, status):
            if stop_event.is_set():
                raise sd.CallbackAbort
            
            volume = calculate_volume(indata)
            with volume_lock:
                volume_data[device_id] = volume
        
        with sd.InputStream(
            device=device_id,
            samplerate=sample_rate,
            channels=channels,
            dtype='int16',
            blocksize=512,
            callback=callback
        ):
            while not stop_event.is_set():
                time.sleep(0.1)
    except:
        pass  # 静默失败


def main():
    """主函数"""
    console.clear()
    
    console.print(Panel.fit(
        "[bold cyan]Windows WASAPI 音频设备测试 + 实时监控[/bold cyan]\n"
        "检测所有音频设备的可用性并监控实时音量",
        border_style="cyan"
    ))
    
    # 获取所有设备
    devices = sd.query_devices()
    console.print(f"\n[dim]找到 {len(devices)} 个音频设备，正在测试并启动监控...[/dim]\n")
    
    # 测试所有输入设备并记录可用的
    input_devices = [(i, dev) for i, dev in enumerate(devices) if dev['max_input_channels'] > 0]
    available_input_devices = []
    
    for device_id, device_info in input_devices:
        test_channels = min(device_info['max_input_channels'], 2)
        test_sample_rate = int(device_info['default_samplerate'])
        result = test_input_device(device_id, device_info, sample_rate=test_sample_rate, channels=test_channels)
        if result['success']:
            available_input_devices.append((device_id, device_info))
    
    # 启动所有可用输入设备的监控线程
    stop_event = threading.Event()
    monitor_threads = []
    
    for device_id, device_info in available_input_devices:
        thread = threading.Thread(
            target=monitor_input_device,
            args=(device_id, device_info, stop_event),
            daemon=True
        )
        thread.start()
        monitor_threads.append(thread)
        with volume_lock:
            volume_data[device_id] = 0.0
    
    # 等待监控启动
    time.sleep(0.5)
    
    def generate_table():
        """生成实时更新的表格"""
        input_table = Table(show_header=True, header_style="bold cyan", title="📥 输入设备实时监控")
        input_table.add_column("ID", style="yellow", width=4)
        input_table.add_column("设备名称", style="white", width=45)
        input_table.add_column("声道", style="magenta", width=6)
        input_table.add_column("采样率", style="blue", width=10)
        input_table.add_column("实时音量", style="green", width=25)
        
        for device_id, device_info in input_devices:
            # 高亮 VB-Cable 设备
            device_name = device_info['name']
            if 'CABLE' in device_name.upper() or 'VB-AUDIO' in device_name.upper():
                device_name = f"[cyan]{device_name}[/cyan] ★"
            
            # 获取实时音量
            with volume_lock:
                volume = volume_data.get(device_id, 0.0)
            
            if device_id in [d[0] for d in available_input_devices]:
                volume_display = f"{create_volume_bar(volume, 15)} {volume:4.1f}%"
            else:
                volume_display = "[dim]不可用[/dim]"
            
            input_table.add_row(
                str(device_id),
                device_name[:43],
                f"{device_info['max_input_channels']}ch",
                f"{int(device_info['default_samplerate'])}Hz",
                volume_display
            )
        
        return input_table
    
    # 显示提示
    console.print("\n[bold yellow]实时监控已启动，按 Ctrl+C 停止[/bold yellow]\n")
    
    try:
        # 使用 Live 实时更新显示
        with Live(generate_table(), refresh_per_second=10, console=console) as live:
            while True:
                time.sleep(0.1)
                live.update(generate_table())
    except KeyboardInterrupt:
        console.print("\n\n[yellow]停止监控...[/yellow]")
        stop_event.set()
        time.sleep(0.3)
        
        # 显示 ClubVoice 配置建议
        console.print("\n")
        console.print(Panel(
            "[bold cyan]💡 ClubVoice 配置建议[/bold cyan]\n\n"
            "查找以下设备ID并更新到 config.ini：\n"
            "• [yellow]input_device_id[/yellow] = CABLE-B Output (MPV 音乐)\n"
            "• [yellow]input_device_id_2[/yellow] = CABLE-A Output (Clubdeck 房间)\n"
            "• [yellow]output_device_id[/yellow] = CABLE-A Input (发送到 Clubdeck)",
            border_style="green"
        ))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]测试已取消[/yellow]")
    except Exception as e:
        console.print(f"\n[red]错误: {e}[/red]")
        import traceback
        traceback.print_exc()
