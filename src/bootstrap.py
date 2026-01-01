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
        
        # 检查是否启用混音模式
        mix_mode = config.audio.mix_mode
        
        # 检查是否有默认设备ID
        default_device_id = config.audio.input_device_id
        if default_device_id is not None:
            console.print(f"[dim]检测到默认设备ID: {default_device_id}[/dim]\n")
        
        (input_id, input_sample_rate, input_channels) = self.device_manager.interactive_select(default_device_id)
        
        audio_config = AudioConfig(
            input_device_id=input_id,
            sample_rate=48000,  # 浏览器端使用 48kHz
            input_sample_rate=input_sample_rate,
            channels=2,  # 浏览器端始终立体声
            input_channels=input_channels,
            mix_mode=mix_mode,
            input_device_id_2=config.audio.input_device_id_2
        )
        
        # 如果启用混音模式，获取第二个设备的参数
        if mix_mode and config.audio.input_device_id_2 is not None:
            device_2 = self.device_manager.get_device_info(config.audio.input_device_id_2)
            if device_2:
                audio_config.input_sample_rate_2 = device_2['sample_rate']
                audio_config.input_channels_2 = device_2['input_channels'] if device_2['input_channels'] > 0 else 2
                console.print(f"[dim]第二个输入设备: ID {config.audio.input_device_id_2}, {audio_config.input_sample_rate_2}Hz, {audio_config.input_channels_2}ch[/dim]\n")
        
        return audio_config
    
    def _display_summary(self, audio_config: AudioConfig):
        """显示配置摘要"""
        console.print()
        console.print("[bold]步骤 2/2: 启动服务器[/bold]\n")
        
        bitrate_str = f"{audio_config.bitrate // 1000}kbps" if audio_config.bitrate else "N/A"
        
        # 混音模式显示
        if audio_config.mix_mode and audio_config.input_device_id_2:
            mode_text = f"[bold yellow]双输入混音模式[/bold yellow]"
            device_info = f"""  • 输入设备1 ID: {audio_config.input_device_id}
    {audio_config.input_channels}ch @ {audio_config.input_sample_rate}Hz
  • 输入设备2 ID: {audio_config.input_device_id_2}
    {audio_config.input_channels_2}ch @ {audio_config.input_sample_rate_2}Hz
    [dim](混合两路音频后转发到浏览器)[/dim]"""
        else:
            mode_text = "[yellow]单向接收 (监听)[/yellow]"
            device_info = f"""  • 输入设备 ID: {audio_config.input_device_id}
    {audio_config.input_channels}ch @ {audio_config.input_sample_rate}Hz
    [dim](从 Clubdeck 接收音频)[/dim]"""
        
        summary = f"""
[cyan]音频配置:[/cyan]
{device_info}
  • 浏览器端: {audio_config.channels}ch @ {audio_config.sample_rate}Hz
  • 比特率: {bitrate_str}
  • 模式: {mode_text}

[cyan]服务器配置:[/cyan]
  • 地址: http://{config.server.host}:{config.server.port}
  • 调试模式: {'开启' if config.server.debug else '关闭'}

[cyan]访问方式:[/cyan]
  • 本地: http://localhost:{config.server.port}
  • 局域网: http://<your-ip>:{config.server.port}

[dim]配置文件: config.ini[/dim]
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
        
        # 保存设备ID到配置文件
        config.save_to_file()
        
        # 显示摘要
        self._display_summary(audio_config)
        
        return audio_config
