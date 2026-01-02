"""
实时音量监控工具
用于测试和调试音频设备的音量输入
"""
import sounddevice as sd
import numpy as np
import time
import sys
import os
from collections import deque
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text


console = Console()


class VolumeMonitor:
    """音量监控器"""
    
    def __init__(self, device_id: int, sample_rate: int = 48000, 
                 channels: int = 2, chunk_size: int = 512):
        """
        Args:
            device_id: 音频设备ID
            sample_rate: 采样率
            channels: 声道数
            chunk_size: 缓冲区大小
        """
        self.device_id = device_id
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        
        # 音量历史记录（用于显示波形）
        self.volume_history = deque(maxlen=50)
        self.peak_history = deque(maxlen=50)
        
        # 统计信息
        self.frame_count = 0
        self.start_time = time.time()
        self.peak_volume = 0.0
        self.avg_volume = 0.0
        
        # 获取设备信息
        self.device_info = sd.query_devices(device_id)
        
        # 音频流
        self.stream = None
        self.running = False
    
    def _calculate_volume(self, audio_data: np.ndarray) -> float:
        """
        计算音量 (RMS)
        
        Args:
            audio_data: 音频数据 (int16 或 float32)
            
        Returns:
            音量值 (0-100)
        """
        # 转换为 float32
        if audio_data.dtype == np.int16:
            float_data = audio_data.astype(np.float32) / 32768.0
        else:
            float_data = audio_data
        
        # 计算 RMS
        rms = np.sqrt(np.mean(float_data ** 2))
        
        # 转换为百分比 (0-100)
        return min(100.0, rms * 100.0 * 10.0)
    
    def _calculate_peak(self, audio_data: np.ndarray) -> float:
        """
        计算峰值音量
        
        Args:
            audio_data: 音频数据
            
        Returns:
            峰值 (0-100)
        """
        if audio_data.dtype == np.int16:
            peak = np.max(np.abs(audio_data)) / 32768.0
        else:
            peak = np.max(np.abs(audio_data))
        
        return min(100.0, peak * 100.0)
    
    def _audio_callback(self, indata, frames, time_info, status):
        """音频输入回调"""
        if status:
            console.print(f"[yellow]音频状态: {status}[/yellow]")
        
        try:
            # 计算音量
            volume = self._calculate_volume(indata)
            peak = self._calculate_peak(indata)
            
            # 更新历史记录
            self.volume_history.append(volume)
            self.peak_history.append(peak)
            
            # 更新统计
            self.frame_count += 1
            self.peak_volume = max(self.peak_volume, volume)
            
            # 计算平均音量
            if len(self.volume_history) > 0:
                self.avg_volume = sum(self.volume_history) / len(self.volume_history)
        
        except Exception as e:
            console.print(f"[red]回调错误: {e}[/red]")
    
    def _create_volume_bar(self, volume: float, width: int = 50) -> str:
        """
        创建音量条
        
        Args:
            volume: 音量值 (0-100)
            width: 条宽度
            
        Returns:
            音量条字符串
        """
        filled = int(volume / 100.0 * width)
        empty = width - filled
        
        # 根据音量选择颜色
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
    
    def _create_waveform(self, history: deque, width: int = 50, height: int = 10) -> str:
        """
        创建简易波形图
        
        Args:
            history: 音量历史记录
            width: 图宽度
            height: 图高度
            
        Returns:
            波形图字符串
        """
        if len(history) == 0:
            return "等待音频数据..."
        
        # 调整历史记录到指定宽度
        if len(history) > width:
            step = len(history) / width
            values = [history[int(i * step)] for i in range(width)]
        else:
            values = list(history) + [0] * (width - len(history))
        
        # 生成波形
        lines = []
        for row in range(height, 0, -1):
            threshold = (row / height) * 100
            line = ""
            for val in values:
                if val >= threshold:
                    # 根据音量选择字符
                    if val >= 80:
                        line += "█"
                    elif val >= 60:
                        line += "▓"
                    elif val >= 40:
                        line += "▒"
                    else:
                        line += "░"
                else:
                    line += " "
            lines.append(line)
        
        return "\n".join(lines)
    
    def _generate_display(self) -> Layout:
        """生成显示布局"""
        layout = Layout()
        
        # 顶部：设备信息
        device_panel = Panel(
            f"""[yellow bold]设备 ID: {self.device_id}[/yellow bold]
[cyan]设备名称:[/cyan] {self.device_info['name']}
[cyan]采样率:[/cyan] {self.sample_rate} Hz
[cyan]声道数:[/cyan] {self.channels}
[cyan]缓冲区:[/cyan] {self.chunk_size} 帧""",
            title="🎤 设备信息",
            border_style="cyan"
        )
        
        # 中间：实时音量
        current_volume = self.volume_history[-1] if self.volume_history else 0.0
        current_peak = self.peak_history[-1] if self.peak_history else 0.0
        
        volume_panel = Panel(
            f"""[bold]当前音量 (RMS):[/bold]
{self._create_volume_bar(current_volume, 60)} [bold]{current_volume:5.1f}%[/bold]

[bold]峰值:[/bold]
{self._create_volume_bar(current_peak, 60)} [bold]{current_peak:5.1f}%[/bold]""",
            title="📊 实时音量",
            border_style="green"
        )
        
        # 波形图
        waveform_panel = Panel(
            self._create_waveform(self.volume_history, width=60, height=12),
            title="📈 音量波形 (最近 50 帧)",
            border_style="yellow"
        )
        
        # 统计信息
        runtime = time.time() - self.start_time
        fps = self.frame_count / runtime if runtime > 0 else 0
        
        stats_table = Table.grid(padding=(0, 2))
        stats_table.add_column(style="cyan")
        stats_table.add_column(style="white")
        
        stats_table.add_row("运行时间:", f"{runtime:.1f} 秒")
        stats_table.add_row("帧数:", f"{self.frame_count}")
        stats_table.add_row("帧率:", f"{fps:.1f} FPS")
        stats_table.add_row("峰值音量:", f"{self.peak_volume:.1f}%")
        stats_table.add_row("平均音量:", f"{self.avg_volume:.1f}%")
        
        stats_panel = Panel(
            stats_table,
            title="📈 统计信息",
            border_style="blue"
        )
        
        # 组合布局
        layout.split_column(
            Layout(device_panel, size=8),
            Layout(volume_panel, size=7),
            Layout(waveform_panel, size=16),
            Layout(stats_panel, size=10)
        )
        
        return layout
    
    def start(self):
        """启动监控"""
        try:
            console.print(f"[green]正在启动音量监控...[/green]")
            console.print(f"[dim]按 Ctrl+C 停止监控[/dim]\n")
            
            # 打开音频流
            self.stream = sd.InputStream(
                device=self.device_id,
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='int16',
                blocksize=self.chunk_size,
                callback=self._audio_callback
            )
            
            self.stream.start()
            self.running = True
            self.start_time = time.time()
            
            # 实时更新显示
            with Live(self._generate_display(), refresh_per_second=10, console=console) as live:
                while self.running:
                    time.sleep(0.1)
                    live.update(self._generate_display())
        
        except KeyboardInterrupt:
            console.print("\n[yellow]用户中断监控[/yellow]")
        except Exception as e:
            console.print(f"\n[red]错误: {e}[/red]")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()
    
    def stop(self):
        """停止监控"""
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        console.print("\n[green]✓ 监控已停止[/green]")


def list_devices():
    """列出所有可用设备"""
    console.print("\n[bold cyan]可用音频设备:[/bold cyan]\n")
    
    devices = sd.query_devices()
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("ID", style="yellow", width=4)
    table.add_column("设备名称", style="white", width=50)
    table.add_column("输入", style="green", width=6)
    table.add_column("输出", style="blue", width=6)
    table.add_column("采样率", style="magenta", width=10)
    
    for i, dev in enumerate(devices):
        input_ch = dev['max_input_channels']
        output_ch = dev['max_output_channels']
        
        if input_ch > 0 or output_ch > 0:
            table.add_row(
                str(i),
                dev['name'][:48] + "..." if len(dev['name']) > 48 else dev['name'],
                f"{input_ch}ch" if input_ch > 0 else "-",
                f"{output_ch}ch" if output_ch > 0 else "-",
                f"{int(dev['default_samplerate'])}Hz"
            )
    
    console.print(table)


def main():
    """主函数"""
    console.clear()
    
    # 显示标题
    title = Text()
    title.append("🎤 ", style="bold cyan")
    title.append("实时音量监控工具", style="bold white")
    title.append(" 🎤", style="bold cyan")
    
    console.print(Panel(
        title,
        subtitle="ClubVoice Audio Monitor",
        border_style="cyan",
        padding=(1, 2)
    ))
    console.print()
    
    # 列出设备
    list_devices()
    console.print()
    
    # 选择设备
    try:
        device_input = console.input("[bold yellow]请输入要监控的设备 ID (留空退出): [/bold yellow]").strip()
        
        if not device_input:
            console.print("[dim]已取消[/dim]")
            return
        
        device_id = int(device_input)
        
        # 验证设备
        device_info = sd.query_devices(device_id)
        if device_info['max_input_channels'] == 0:
            console.print(f"[red]错误: 设备 {device_id} 不支持输入![/red]")
            return
        
        # 获取参数
        sample_rate = int(device_info['default_samplerate'])
        channels = min(device_info['max_input_channels'], 2)  # 最多2声道
        
        console.print(f"\n[green]✓ 选择设备: {device_info['name']}[/green]")
        console.print(f"[dim]采样率: {sample_rate}Hz, 声道数: {channels}[/dim]\n")
        
        # 启动监控
        monitor = VolumeMonitor(
            device_id=device_id,
            sample_rate=sample_rate,
            channels=channels,
            chunk_size=512
        )
        
        monitor.start()
    
    except ValueError:
        console.print("[red]错误: 请输入有效的设备 ID 数字[/red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
