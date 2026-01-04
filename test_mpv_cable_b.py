"""
测试 MPV 播放到 CABLE-B
生成测试音频并通过 sounddevice 播放到 CABLE-B Input
"""
import numpy as np
import sounddevice as sd
import time
from rich.console import Console

console = Console()

# 设备 ID
CABLE_B_INPUT_DEVICE = 30  # CABLE-B Input (VB-Audio Virtual Cable B) 2ch 48000Hz

def generate_test_tone(frequency=440, duration=5, sample_rate=48000):
    """生成测试音频（正弦波）"""
    t = np.linspace(0, duration, int(sample_rate * duration))
    # 生成立体声
    left = np.sin(2 * np.pi * frequency * t) * 0.3
    right = np.sin(2 * np.pi * frequency * t) * 0.3
    stereo = np.column_stack([left, right])
    return (stereo * 32767).astype(np.int16)

def main():
    console.print("\n[bold cyan]🎵 测试 MPV 音频播放到 CABLE-B[/bold cyan]\n")
    
    # 列出 CABLE-B 设备
    devices = sd.query_devices()
    console.print(f"目标设备: [yellow]{devices[CABLE_B_INPUT_DEVICE]['name']}[/yellow]")
    console.print(f"设备 ID: [yellow]{CABLE_B_INPUT_DEVICE}[/yellow]")
    console.print(f"采样率: [yellow]48000Hz[/yellow]")
    console.print(f"声道数: [yellow]2[/yellow]\n")
    
    # 生成测试音频（440Hz，5秒）
    console.print("[dim]正在生成测试音频 (440Hz, 5秒)...[/dim]")
    audio_data = generate_test_tone(frequency=440, duration=5, sample_rate=48000)
    
    console.print("[green]✓ 音频生成完成[/green]\n")
    console.print("[bold yellow]开始播放到 CABLE-B Input...[/bold yellow]")
    console.print("[dim]请在另一个终端监控设备 35 (CABLE-B Output) 的音量[/dim]\n")
    
    try:
        # 播放音频到 CABLE-B Input
        sd.play(audio_data, samplerate=48000, device=CABLE_B_INPUT_DEVICE)
        sd.wait()
        
        console.print("\n[green]✓ 播放完成！[/green]")
        console.print("[dim]如果设备 35 有音量波动，说明 CABLE-B 工作正常[/dim]")
        
    except Exception as e:
        console.print(f"\n[red]✗ 播放失败: {e}[/red]")

if __name__ == "__main__":
    main()
