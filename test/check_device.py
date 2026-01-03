"""
音频设备检查和实时音量监控工具
"""
import sounddevice as sd
import numpy as np
import sys
import time
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel


console = Console()


def list_devices():
    """列出所有可用设备"""
    devices = sd.query_devices()
    
    console.print("\n[bold cyan]📤 输出设备列表[/bold cyan]\n")
    output_table = Table(show_header=True, header_style="bold cyan")
    output_table.add_column("ID", style="yellow", width=4)
    output_table.add_column("设备名称", style="white", width=50)
    output_table.add_column("声道", style="magenta", width=6)
    output_table.add_column("采样率", style="blue", width=10)
    
    for i, dev in enumerate(devices):
        if dev['max_output_channels'] > 0:
            device_name = dev['name']
            if 'CABLE' in device_name.upper() or 'VB-AUDIO' in device_name.upper():
                device_name = f"[cyan]{device_name}[/cyan] ★"
            
            output_table.add_row(
                str(i),
                device_name[:48],
                f"{dev['max_output_channels']}ch",
                f"{int(dev['default_samplerate'])}Hz"
            )
    
    console.print(output_table)
    
    console.print("\n[bold cyan]📥 输入设备列表[/bold cyan]\n")
    input_table = Table(show_header=True, header_style="bold cyan")
    input_table.add_column("ID", style="yellow", width=4)
    input_table.add_column("设备名称", style="white", width=50)
    input_table.add_column("声道", style="magenta", width=6)
    input_table.add_column("采样率", style="blue", width=10)
    
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            device_name = dev['name']
            if 'CABLE' in device_name.upper() or 'VB-AUDIO' in device_name.upper():
                device_name = f"[cyan]{device_name}[/cyan] ★"
            
            input_table.add_row(
                str(i),
                device_name[:48],
                f"{dev['max_input_channels']}ch",
                f"{int(dev['default_samplerate'])}Hz"
            )
    
    console.print(input_table)


def create_volume_bar(volume: float, width: int = 40) -> str:
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


def calculate_volume(audio_data: np.ndarray) -> float:
    """计算音量 (RMS)"""
    if audio_data.dtype == np.int16:
        float_data = audio_data.astype(np.float32) / 32768.0
    else:
        float_data = audio_data
    
    rms = np.sqrt(np.mean(float_data ** 2))
    return min(100.0, rms * 100.0 * 10.0)


def monitor_device(device_id: int, is_input: bool = True):
    """实时监控设备音量"""
    devices = sd.query_devices()
    
    if device_id < 0 or device_id >= len(devices):
        console.print(f"[red]设备 ID {device_id} 无效![/red]")
        return
    
    device_info = devices[device_id]
    
    if is_input and device_info['max_input_channels'] == 0:
        console.print(f"[red]设备 {device_id} 不支持输入![/red]")
        return
    
    if not is_input and device_info['max_output_channels'] == 0:
        console.print(f"[red]设备 {device_id} 不支持输出![/red]")
        return
    
    console.clear()
    console.print(Panel.fit(
        f"[bold cyan]实时音量监控[/bold cyan]\n\n"
        f"设备 ID: [yellow]{device_id}[/yellow]\n"
        f"设备名称: {device_info['name']}\n"
        f"采样率: {int(device_info['default_samplerate'])}Hz\n"
        f"声道数: {device_info['max_input_channels' if is_input else 'max_output_channels']}ch\n\n"
        f"[dim]按 Ctrl+C 停止监控[/dim]",
        border_style="cyan"
    ))
    
    sample_rate = int(device_info['default_samplerate'])
    channels = min(device_info['max_input_channels' if is_input else 'max_output_channels'], 2)
    frame_count = 0
    peak_volume = 0.0
    
    def callback(indata, frames, time_info, status):
        nonlocal frame_count, peak_volume
        
        if status:
            console.print(f"[yellow]状态: {status}[/yellow]")
        
        volume = calculate_volume(indata)
        frame_count += 1
        peak_volume = max(peak_volume, volume)
        
        # 显示音量条
        bar = create_volume_bar(volume, width=50)
        sys.stdout.write(f"\r音量: [{bar}] {volume:5.1f}% | 峰值: {peak_volume:5.1f}% | 帧: {frame_count}     ")
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
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]监控已停止[/yellow]")
    except Exception as e:
        console.print(f"\n\n[red]错误: {e}[/red]")


def main():
    """主函数"""
    console.clear()
    console.print(Panel.fit(
        "[bold cyan]音频设备检查工具[/bold cyan]\n"
        "设备列表 + 实时音量监控",
        border_style="cyan"
    ))
    
    # 列出所有设备
    list_devices()
    
    # 询问是否监控
    console.print("\n[bold yellow]选项:[/bold yellow]")
    console.print("1. 监控输入设备")
    console.print("2. 退出")
    
    choice = Prompt.ask("\n请选择", choices=["1", "2"], default="2")
    
    if choice == "1":
        device_input = Prompt.ask("\n请输入要监控的输入设备 ID")
        try:
            device_id = int(device_input)
            monitor_device(device_id, is_input=True)
        except ValueError:
            console.print("[red]无效的设备 ID[/red]")
    else:
        console.print("[dim]已退出[/dim]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        import traceback
        traceback.print_exc()
