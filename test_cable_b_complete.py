"""
完整测试 CABLE-B 音频流
同时播放和监控
"""
import numpy as np
import sounddevice as sd
import threading
import time
from rich.console import Console
from rich.live import Live
from rich.panel import Panel

console = Console()

# 设备配置 - 使用 WASAPI 48kHz 2ch 设备
CABLE_B_INPUT = 30   # CABLE-B Input (VB-Audio Virtual Cable B) - WASAPI 48kHz 2ch
CABLE_B_OUTPUT = 35  # CABLE-B Output (VB-Audio Virtual Cable B) - WASAPI 48kHz 2ch
SAMPLE_RATE = 48000
CHANNELS = 2

# 音量数据
volume_data = []
stop_monitor = False

def monitor_cable_b_output():
    """监控 CABLE-B Output 的音量"""
    global volume_data, stop_monitor
    
    def callback(indata, frames, time_info, status):
        if status:
            console.print(f"[yellow]状态: {status}[/yellow]")
        
        # 计算音量 (RMS)
        rms = np.sqrt(np.mean(indata.astype(np.float32) ** 2 / (32768.0 ** 2)))
        volume_percent = min(100.0, rms * 100.0 * 10.0)
        volume_data.append(volume_percent)
        
        # 只保留最近50个数据点
        if len(volume_data) > 50:
            volume_data.pop(0)
    
    try:
        with sd.InputStream(
            device=CABLE_B_OUTPUT,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='int16',
            blocksize=512,
            callback=callback
        ):
            while not stop_monitor:
                time.sleep(0.1)
    except Exception as e:
        console.print(f"[red]监控错误: {e}[/red]")

def create_volume_bar(volume, width=40):
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

def main():
    global stop_monitor
    
    console.clear()
    console.print(Panel(
        "[bold cyan]🎵 CABLE-B 完整测试[/bold cyan]\n"
        "同时监控 CABLE-B Output 并播放测试音频到 CABLE-B Input",
        border_style="cyan"
    ))
    
    # 启动监控线程
    console.print("\n[dim]启动监控线程...[/dim]")
    monitor_thread = threading.Thread(target=monitor_cable_b_output, daemon=True)
    monitor_thread.start()
    time.sleep(0.5)
    
    console.print("[green]✓ 监控已启动[/green]\n")
    
    # 生成测试音频（440Hz 正弦波，持续 8 秒）
    console.print("[dim]生成测试音频 (440Hz, 8秒)...[/dim]")
    duration = 8
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    left = np.sin(2 * np.pi * 440 * t) * 0.3
    right = np.sin(2 * np.pi * 440 * t) * 0.3
    stereo = np.column_stack([left, right])
    audio_data = (stereo * 32767).astype(np.int16)
    
    console.print("[green]✓ 音频生成完成[/green]\n")
    console.print(f"[bold yellow]开始播放到设备 {CABLE_B_INPUT} (CABLE-B Input)...[/bold yellow]\n")
    
    # 播放音频（非阻塞）
    sd.play(audio_data, samplerate=SAMPLE_RATE, device=CABLE_B_INPUT)
    
    # 实时显示音量
    def generate_display():
        current_volume = volume_data[-1] if volume_data else 0.0
        avg_volume = sum(volume_data) / len(volume_data) if volume_data else 0.0
        max_volume = max(volume_data) if volume_data else 0.0
        
        return Panel(
            f"""[cyan]设备 {CABLE_B_OUTPUT}: CABLE-B Output[/cyan]

[bold]实时音量:[/bold]
{create_volume_bar(current_volume, 50)} [bold]{current_volume:5.1f}%[/bold]

[bold]统计信息:[/bold]
  平均音量: {avg_volume:5.1f}%
  峰值音量: {max_volume:5.1f}%
  采样帧数: {len(volume_data)}

[dim]如果看到音量波动，说明 CABLE-B 工作正常[/dim]
[dim]如果音量一直为 0%，说明音频没有通过虚拟线缆[/dim]""",
            title="📊 CABLE-B Output 实时监控",
            border_style="green"
        )
    
    try:
        with Live(generate_display(), refresh_per_second=10, console=console) as live:
            start_time = time.time()
            while time.time() - start_time < duration + 1:
                live.update(generate_display())
                time.sleep(0.1)
    except KeyboardInterrupt:
        console.print("\n[yellow]用户中断[/yellow]")
    
    # 停止
    sd.stop()
    stop_monitor = True
    time.sleep(0.3)
    
    # 最终结果
    console.print("\n" + "=" * 60)
    if volume_data and max(volume_data) > 5:
        console.print("[bold green]✓ 测试成功！CABLE-B 音频流正常工作[/bold green]")
        console.print(f"[green]  最大音量: {max(volume_data):.1f}%[/green]")
    else:
        console.print("[bold red]✗ 测试失败！CABLE-B Output 没有接收到音频[/bold red]")
        console.print("[yellow]可能原因:[/yellow]")
        console.print("  1. VB-Cable B 驱动未正确安装")
        console.print("  2. 设备 ID 不正确")
        console.print("  3. 音频设备被其他程序占用")
    console.print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
