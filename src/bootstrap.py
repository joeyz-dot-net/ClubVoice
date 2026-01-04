"""
Bootstrap wizard
"""
import sounddevice as sd
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .audio.device_manager import DeviceManager
from .config.settings import config, AudioConfig, AppConfig


# Configure console to avoid Unicode issues on Windows
console = Console(no_color=True, force_terminal=False, legacy_windows=True)


class Bootstrap:
    """启动引导器"""
    
    def __init__(self):
        self.device_manager = DeviceManager()
    
    def _display_welcome(self):
        """显示欢迎信息"""
        title = Text()
        title.append("Voice Communication App\n", style="bold cyan")
        title.append("Browser <-> Clubdeck Real-Time Voice", style="dim")
        
        console.print(Panel(
            title,
            title="Welcome",
            border_style="cyan",
            padding=(1, 2)
        ))
        console.print()
    
    def _select_devices(self) -> AudioConfig:
        """Select audio devices"""
        console.print("[bold]Step 1/2: Configure Audio Devices[/bold]\n")
        
        # Check if mix mode is enabled
        mix_mode = config.audio.mix_mode
        
        # Check for default device ID
        default_device_id = config.audio.input_device_id
        if default_device_id is not None:
            console.print(f"[dim]Default device ID: {default_device_id}[/dim]\n")
        
        (input_id, input_sample_rate, input_channels) = self.device_manager.interactive_select(default_device_id)
        
        audio_config = AudioConfig(
            input_device_id=input_id,
            output_device_id=config.audio.output_device_id,
            sample_rate=48000,  # 浏览器端使用 48kHz
            input_sample_rate=input_sample_rate,
            output_sample_rate=config.audio.output_sample_rate,
            channels=2,  # 浏览器端始终立体声
            input_channels=input_channels,
            output_channels=config.audio.output_channels,
            mix_mode=mix_mode,
            input_device_id_2=config.audio.input_device_id_2,
            duplex_mode=config.audio.duplex_mode  # 保持原有的双工模式设置
        )
        
        # 如果启用混音模式，获取第二个设备的参数
        if mix_mode and config.audio.input_device_id_2 is not None:
            device_2 = self.device_manager.get_device_info(config.audio.input_device_id_2)
            if device_2:
                audio_config.input_sample_rate_2 = device_2['sample_rate']
                audio_config.input_channels_2 = device_2['input_channels'] if device_2['input_channels'] > 0 else 2
                console.print(f"[dim]Secondary input: ID {config.audio.input_device_id_2}, {audio_config.input_sample_rate_2}Hz, {audio_config.input_channels_2}ch[/dim]\n")
        
        return audio_config
    
    def _display_summary(self, audio_config: AudioConfig):
        """显示配置摘要"""
        console.print()
        console.print("[bold]Step 2/2: Launch Server[/bold]\n")
        
        bitrate_str = f"{audio_config.bitrate // 1000}kbps" if audio_config.bitrate else "N/A"
        
        # Display mix mode
        if audio_config.mix_mode and audio_config.input_device_id_2:
            mode_text = f"[bold yellow]Dual-Input Mix[/bold yellow]"
            device_info = f"""  * Input Device 1: {audio_config.input_device_id}
    {audio_config.input_channels}ch @ {audio_config.input_sample_rate}Hz
  * Input Device 2: {audio_config.input_device_id_2}
    {audio_config.input_channels_2}ch @ {audio_config.input_sample_rate_2}Hz"""
        else:
            mode_text = "[yellow]Listen-Only[/yellow]"
            device_info = f"""  * Input Device: {audio_config.input_device_id}
    {audio_config.input_channels}ch @ {audio_config.input_sample_rate}Hz"""
        
        summary = f"""
[cyan]Audio Config:[/cyan]
{device_info}
  * Browser: {audio_config.channels}ch @ {audio_config.sample_rate}Hz
  * Bitrate: {bitrate_str}
  * Mode: {mode_text}

[cyan]Server Config:[/cyan]
  * Address: http://{config.server.host}:{config.server.port}
  * Debug: {'ON' if config.server.debug else 'OFF'}

[cyan]Access:[/cyan]
  * Local: http://localhost:{config.server.port}
  * Network: http://<your-ip>:{config.server.port}

[dim]config.ini[/dim]
"""
        console.print(Panel(summary, title="Configuration", border_style="green"))
    
    def run(self) -> AudioConfig:
        """
        运行设备配置向导
        
        Returns:
            AudioConfig: 音频配置对象
        """
        console.print(Panel(
            Text("🎤 ClubVoice 音频设备配置", style="bold cyan"),
            subtitle="初始化音频设备",
            border_style="cyan"
        ))
        
        # 加载配置文件
        app_config = AppConfig().load_from_file()
        
        # 检查配置文件中的设备ID（支持新旧字段名）
        clubdeck_id = app_config.audio.clubdeck_input_device_id or app_config.audio.input_device_id_2
        mpv_id = app_config.audio.mpv_input_device_id or app_config.audio.input_device_id
        browser_out_id = app_config.audio.browser_output_device_id or app_config.audio.output_device_id
        
        # 验证配置文件中的设备ID是否有效
        if (mpv_id is not None and browser_out_id is not None):
            try:
                mpv_device = sd.query_devices(mpv_id)
                browser_out_device = sd.query_devices(browser_out_id)
                
                # 验证设备是否支持所需功能
                if (mpv_device['max_input_channels'] > 0 and 
                    browser_out_device['max_output_channels'] > 0):
                    
                    console.print(f"\n[bold green]✓ 使用配置文件中的3-Cable架构设备:[/bold green]")
                    console.print(f"  [cyan]CABLE-B (MPV音乐输入) 设备 {mpv_id}:[/cyan]")
                    console.print(f"    {mpv_device['name']}")
                    console.print(f"    {min(mpv_device['max_input_channels'], 2)}ch @ {int(mpv_device['default_samplerate'])}Hz")
                    
                    console.print(f"\n  [cyan]CABLE-A (浏览器→Clubdeck) 设备 {browser_out_id}:[/cyan]")
                    console.print(f"    {browser_out_device['name']}")
                    console.print(f"    {min(browser_out_device['max_output_channels'], 2)}ch @ {int(browser_out_device['default_samplerate'])}Hz")
                    
                    # 处理Clubdeck输入设备（3-Cable混音模式）
                    if app_config.audio.mix_mode and clubdeck_id is not None:
                        try:
                            clubdeck_device = sd.query_devices(clubdeck_id)
                            if clubdeck_device['max_input_channels'] > 0:
                                console.print(f"\n  [cyan]CABLE-C (Clubdeck→浏览器) 设备 {clubdeck_id}:[/cyan]")
                                console.print(f"    {clubdeck_device['name']}")
                                console.print(f"    {min(clubdeck_device['max_input_channels'], 2)}ch @ {int(clubdeck_device['default_samplerate'])}Hz")
                            else:
                                console.print(f"\n  [yellow]⚠️ Clubdeck输入设备 {clubdeck_id} 不支持输入，将忽略[/yellow]")
                                clubdeck_id = None
                        except Exception as e:
                            console.print(f"\n  [yellow]⚠️ Clubdeck输入设备 {clubdeck_id} 无效: {e}，将忽略[/yellow]")
                            clubdeck_id = None
                
                console.print(f"\n[dim]配置文件: config.ini[/dim]")
                console.print(f"[dim]如需修改设备，请编辑 config.ini 文件[/dim]\n")
                
                # 使用配置文件中的设置（3-Cable架构）
                return AudioConfig(
                        # 新字段名（3-Cable）
                        mpv_input_device_id=mpv_id,
                        clubdeck_input_device_id=clubdeck_id,
                        browser_output_device_id=browser_out_id,
                        mpv_sample_rate=int(mpv_device['default_samplerate']),
                        clubdeck_sample_rate=int(sd.query_devices(clubdeck_id)['default_samplerate']) if clubdeck_id else 48000,
                        browser_output_sample_rate=int(browser_out_device['default_samplerate']),
                        mpv_channels=min(mpv_device['max_input_channels'], 2),
                        clubdeck_channels=min(sd.query_devices(clubdeck_id)['max_input_channels'], 2) if clubdeck_id else 2,
                        browser_output_channels=min(browser_out_device['max_output_channels'], 2),
                        # 旧字段名（向后兼容）
                        input_device_id=mpv_id,
                        input_device_id_2=clubdeck_id,
                        output_device_id=browser_out_id,
                        input_sample_rate=int(mpv_device['default_samplerate']),
                        input_sample_rate_2=int(sd.query_devices(clubdeck_id)['default_samplerate']) if clubdeck_id else 48000,
                        output_sample_rate=int(browser_out_device['default_samplerate']),
                        input_channels=min(mpv_device['max_input_channels'], 2),
                        input_channels_2=min(sd.query_devices(clubdeck_id)['max_input_channels'], 2) if clubdeck_id else 2,
                        output_channels=min(browser_out_device['max_output_channels'], 2),
                        # 通用字段
                        sample_rate=app_config.audio.sample_rate,
                        channels=app_config.audio.channels,
                        chunk_size=app_config.audio.chunk_size,
                        bitrate=app_config.audio.bitrate,
                        dtype=app_config.audio.dtype,
                        duplex_mode=app_config.audio.duplex_mode,
                        mix_mode=app_config.audio.mix_mode,
                        mpv_ducking_enabled=app_config.audio.mpv_ducking_enabled,
                        browser_ducking_enabled=app_config.audio.browser_ducking_enabled,
                        ducking_threshold=app_config.audio.ducking_threshold,
                        ducking_gain=app_config.audio.ducking_gain,
                        ducking_min_duration=app_config.audio.ducking_min_duration,
                        ducking_release_time=app_config.audio.ducking_release_time,
                        ducking_transition_time=app_config.audio.ducking_transition_time
                    )
                
            except Exception as e:
                console.print(f"\n[red]✗ 配置文件中的设备ID无效: {e}[/red]")
                console.print(f"[yellow]请检查 config.ini 中的设备ID配置[/yellow]\n")
        
        # 如果配置文件中没有设备ID或设备无效，显示可用设备并提示
        console.print("\n[cyan]可用音频设备:[/cyan]")
        self.device_manager.display_devices()
        console.print()
        console.print("[yellow]⚠️ 配置文件中未找到有效的设备配置[/yellow]")
        console.print("[yellow]请编辑 config.ini 文件设置正确的设备ID[/yellow]\n")
        
        # 显示配置示例
        console.print("[dim]配置示例 (config.ini):[/dim]")
        console.print("[dim]clubdeck_input_device_id = 36  # CABLE-C Output[/dim]")
        console.print("[dim]mpv_input_device_id = 35       # CABLE-B Output[/dim]")
        console.print("[dim]browser_output_device_id = 34  # CABLE-A Input[/dim]\n")
        
        raise SystemExit(1)
