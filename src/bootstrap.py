"""
启动引导器
"""
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .audio.device_manager import DeviceManager
from .config.settings import config, AudioConfig


console = Console()


class Bootstrap:
    """启动引导器"""
    
    def __init__(self):
        self.device_manager = DeviceManager()
    
    def _display_welcome(self):
        """显示欢迎信息"""
        title = Text()
        title.append("🎙️ Voice Communication App\n", style="bold cyan")
        title.append("浏览器 ↔ Clubdeck 实时语音通信", style="dim")
        
        console.print(Panel(
            title,
            title="欢迎",
            border_style="cyan",
            padding=(1, 2)
        ))
        console.print()
    
    def _select_devices(self) -> AudioConfig:
        """选择音频设备"""
        console.print("[bold]步骤 1/2: 配置音频设备[/bold]\n")
        
        (input_id, output_id, input_sample_rate, output_sample_rate,
         input_channels, output_channels, browser_sample_rate) = self.device_manager.interactive_select()
        
        return AudioConfig(
            input_device_id=input_id,
            output_device_id=output_id,
            sample_rate=browser_sample_rate,
            input_sample_rate=input_sample_rate,
            output_sample_rate=output_sample_rate,
            channels=2,  # 浏览器端始终立体声
            input_channels=input_channels,
            output_channels=output_channels
        )
    
    def _display_summary(self, audio_config: AudioConfig):
        """显示配置摘要"""
        console.print()
        console.print("[bold]步骤 2/2: 启动服务器[/bold]\n")
        
        bitrate_str = f"{audio_config.bitrate // 1000}kbps" if audio_config.bitrate else "N/A"
        
        summary = f"""
[cyan]音频配置:[/cyan]
  • 输入设备 ID: {audio_config.input_device_id}
    {audio_config.input_channels}ch @ {audio_config.input_sample_rate}Hz
  • 输出设备 ID: {audio_config.output_device_id}
    {audio_config.output_channels}ch @ {audio_config.output_sample_rate}Hz
  • 浏览器端: {audio_config.channels}ch @ {audio_config.sample_rate}Hz
  • 比特率: {bitrate_str}

[cyan]服务器配置:[/cyan]
  • 地址: http://{config.server.host}:{config.server.port}
  • 调试模式: {'开启' if config.server.debug else '关闭'}

[cyan]访问方式:[/cyan]
  • 本地: http://localhost:{config.server.port}
  • 局域网: http://<your-ip>:{config.server.port}

[dim]配置文件: config.json[/dim]
"""
        console.print(Panel(summary, title="配置摘要", border_style="green"))
    
    def run(self) -> AudioConfig:
        """执行启动引导流程"""
        console.clear()
        self._display_welcome()
        
        # 选择设备
        audio_config = self._select_devices()
        
        # 更新全局配置
        config.audio = audio_config
        
        # 显示摘要
        self._display_summary(audio_config)
        
        return audio_config
