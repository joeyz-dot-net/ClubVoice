"""
Bootstrap wizard
"""
import sounddevice as sd
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm

from .audio.device_manager import DeviceManager
from .config.settings import config, AudioConfig, AppConfig, get_config_path


# Configure console to avoid Unicode issues on Windows
console = Console(no_color=True, force_terminal=False, legacy_windows=True)


class Bootstrap:
    """启动引导器"""
    
    def __init__(self):
        self.device_manager = DeviceManager()
        self.selected_audio_config = None  # 保存选择的配置用于退出时保存
        self.config_changed = False  # 标记配置是否被修改
    
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
    
    def _interactive_device_select(self, app_config: AppConfig) -> AudioConfig:
        """
        交互式设备选择
        
        Args:
            app_config: 当前应用配置
            
        Returns:
            AudioConfig: 音频配置对象
        """
        # 获取当前配置的设备ID
        clubdeck_id = app_config.audio.clubdeck_input_device_id or app_config.audio.input_device_id_2
        mpv_id = app_config.audio.mpv_input_device_id or app_config.audio.input_device_id
        browser_out_id = app_config.audio.browser_output_device_id or app_config.audio.output_device_id
        
        console.print("\n[bold cyan]========== 设备选择 ==========[/bold cyan]\n")
        
        # 显示所有可用设备
        self.device_manager.display_devices()
        
        # === MPV 输入设备 (CABLE-B Output) ===
        console.print("\n[bold yellow]1. MPV 音乐输入设备 (CABLE-B Output)[/bold yellow]")
        console.print("[dim]   从 MPV 读取背景音乐[/dim]")
        if mpv_id is not None:
            try:
                dev = sd.query_devices(mpv_id)
                console.print(f"   当前: [green]ID {mpv_id} - {dev['name']}[/green]")
            except:
                console.print(f"   当前: [red]ID {mpv_id} (无效)[/red]")
        else:
            console.print("   当前: [yellow]未配置[/yellow]")
        
        mpv_input = Prompt.ask(
            "   输入设备ID (留空保持不变)",
            default=""
        )
        if mpv_input.strip():
            try:
                new_mpv_id = int(mpv_input.strip())
                dev = sd.query_devices(new_mpv_id)
                if dev['max_input_channels'] > 0:
                    mpv_id = new_mpv_id
                    self.config_changed = True
                    console.print(f"   [green]✓ 已选择: {dev['name']}[/green]")
                else:
                    console.print(f"   [red]✗ 设备 {new_mpv_id} 不支持输入[/red]")
            except Exception as e:
                console.print(f"   [red]✗ 无效设备ID: {e}[/red]")
        
        # === Clubdeck 输入设备 (CABLE-C Output) ===
        console.print("\n[bold yellow]2. Clubdeck 房间输入设备 (CABLE-C Output)[/bold yellow]")
        console.print("[dim]   从 Clubdeck 读取房间音频[/dim]")
        if clubdeck_id is not None:
            try:
                dev = sd.query_devices(clubdeck_id)
                console.print(f"   当前: [green]ID {clubdeck_id} - {dev['name']}[/green]")
            except:
                console.print(f"   当前: [red]ID {clubdeck_id} (无效)[/red]")
        else:
            console.print("   当前: [yellow]未配置[/yellow]")
        
        clubdeck_input = Prompt.ask(
            "   输入设备ID (留空保持不变)",
            default=""
        )
        if clubdeck_input.strip():
            try:
                new_clubdeck_id = int(clubdeck_input.strip())
                dev = sd.query_devices(new_clubdeck_id)
                if dev['max_input_channels'] > 0:
                    clubdeck_id = new_clubdeck_id
                    self.config_changed = True
                    console.print(f"   [green]✓ 已选择: {dev['name']}[/green]")
                else:
                    console.print(f"   [red]✗ 设备 {new_clubdeck_id} 不支持输入[/red]")
            except Exception as e:
                console.print(f"   [red]✗ 无效设备ID: {e}[/red]")
        
        # === 浏览器输出设备 (CABLE-A Input) ===
        console.print("\n[bold yellow]3. 浏览器输出设备 (CABLE-A Input)[/bold yellow]")
        console.print("[dim]   发送浏览器麦克风+MPV混音到 Clubdeck[/dim]")
        if browser_out_id is not None:
            try:
                dev = sd.query_devices(browser_out_id)
                console.print(f"   当前: [green]ID {browser_out_id} - {dev['name']}[/green]")
            except:
                console.print(f"   当前: [red]ID {browser_out_id} (无效)[/red]")
        else:
            console.print("   当前: [yellow]未配置[/yellow]")
        
        browser_input = Prompt.ask(
            "   输入设备ID (留空保持不变)",
            default=""
        )
        if browser_input.strip():
            try:
                new_browser_id = int(browser_input.strip())
                dev = sd.query_devices(new_browser_id)
                if dev['max_output_channels'] > 0:
                    browser_out_id = new_browser_id
                    self.config_changed = True
                    console.print(f"   [green]✓ 已选择: {dev['name']}[/green]")
                else:
                    console.print(f"   [red]✗ 设备 {new_browser_id} 不支持输出[/red]")
            except Exception as e:
                console.print(f"   [red]✗ 无效设备ID: {e}[/red]")
        
        # 验证设备配置
        if mpv_id is None or browser_out_id is None:
            console.print("\n[red]✗ MPV输入和浏览器输出设备必须配置！[/red]")
            raise SystemExit(1)
        
        # 获取设备参数
        mpv_device = sd.query_devices(mpv_id)
        browser_out_device = sd.query_devices(browser_out_id)
        clubdeck_device = sd.query_devices(clubdeck_id) if clubdeck_id else None
        
        # 创建音频配置
        audio_config = AudioConfig(
            # 新字段名（3-Cable）
            mpv_input_device_id=mpv_id,
            clubdeck_input_device_id=clubdeck_id,
            browser_output_device_id=browser_out_id,
            mpv_sample_rate=int(mpv_device['default_samplerate']),
            clubdeck_sample_rate=int(clubdeck_device['default_samplerate']) if clubdeck_device else 48000,
            browser_output_sample_rate=int(browser_out_device['default_samplerate']),
            mpv_channels=min(mpv_device['max_input_channels'], 2),
            clubdeck_channels=min(clubdeck_device['max_input_channels'], 2) if clubdeck_device else 2,
            browser_output_channels=min(browser_out_device['max_output_channels'], 2),
            # 旧字段名（向后兼容）
            input_device_id=mpv_id,
            input_device_id_2=clubdeck_id,
            output_device_id=browser_out_id,
            input_sample_rate=int(mpv_device['default_samplerate']),
            input_sample_rate_2=int(clubdeck_device['default_samplerate']) if clubdeck_device else 48000,
            output_sample_rate=int(browser_out_device['default_samplerate']),
            input_channels=min(mpv_device['max_input_channels'], 2),
            input_channels_2=min(clubdeck_device['max_input_channels'], 2) if clubdeck_device else 2,
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
        
        return audio_config
    
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
        devices_valid = False
        if (mpv_id is not None and browser_out_id is not None):
            try:
                mpv_device = sd.query_devices(mpv_id)
                browser_out_device = sd.query_devices(browser_out_id)
                
                # 验证设备是否支持所需功能
                if (mpv_device['max_input_channels'] > 0 and 
                    browser_out_device['max_output_channels'] > 0):
                    devices_valid = True
                    
                    console.print(f"\n[bold green]✓ 当前配置的3-Cable架构设备:[/bold green]")
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
                
            except Exception as e:
                console.print(f"\n[red]✗ 配置文件中的设备ID无效: {e}[/red]")
        
        # 询问用户是否要修改设备
        console.print()
        if devices_valid:
            change_devices = Prompt.ask(
                "[bold yellow]是否修改设备配置?[/bold yellow] (输入 'y' 修改, 直接回车使用当前配置)",
                default=""
            )
            
            if change_devices.lower() in ['y', 'yes', '是']:
                # 进入交互式设备选择
                audio_config = self._interactive_device_select(app_config)
                self.selected_audio_config = audio_config
                return audio_config
            else:
                # 使用配置文件中的设置（3-Cable架构）
                console.print("\n[green]✓ 使用当前配置启动...[/green]\n")
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
        else:
            # 设备无效，必须进入交互式选择
            console.print("[yellow]⚠️ 配置文件中未找到有效的设备配置[/yellow]")
            console.print("[yellow]请选择音频设备...[/yellow]\n")
            audio_config = self._interactive_device_select(app_config)
            self.selected_audio_config = audio_config
            return audio_config
    
    def save_config_on_exit(self):
        """
        程序退出时保存配置到文件
        仅当设备配置被修改时保存，只更新设备ID，保留其他配置和注释
        """
        if not self.config_changed or not self.selected_audio_config:
            return
        
        try:
            app_config = AppConfig().load_from_file()
            
            # 更新设备ID
            app_config.audio.mpv_input_device_id = self.selected_audio_config.mpv_input_device_id
            app_config.audio.clubdeck_input_device_id = self.selected_audio_config.clubdeck_input_device_id
            app_config.audio.browser_output_device_id = self.selected_audio_config.browser_output_device_id
            
            # 同时更新旧字段（向后兼容）
            app_config.audio.input_device_id = self.selected_audio_config.mpv_input_device_id
            app_config.audio.input_device_id_2 = self.selected_audio_config.clubdeck_input_device_id
            app_config.audio.output_device_id = self.selected_audio_config.browser_output_device_id
            
            # 仅更新设备ID，保留其他配置和注释
            app_config.update_device_ids_in_file()
            console.print("[green]✓ 设备配置已保存到 config.ini[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️ 保存配置失败: {e}[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠️ 保存配置失败: {e}[/yellow]")
