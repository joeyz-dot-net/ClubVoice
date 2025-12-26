"""
音频设备管理器
"""
import sounddevice as sd
from typing import List, Dict, Tuple, Optional
from rich.console import Console
from rich.table import Table
from rich.prompt import IntPrompt, Confirm
from rich.panel import Panel

from ..config.settings import config


console = Console()


class DeviceManager:
    """音频设备管理器"""
    
    def __init__(self):
        self.input_devices: List[Dict] = []
        self.output_devices: List[Dict] = []
        self._scan_devices()
    
    def _scan_devices(self) -> None:
        """扫描所有音频设备"""
        devices = sd.query_devices()
        
        self.input_devices = []
        self.output_devices = []
        
        for i, device in enumerate(devices):
            device_info = {
                'id': i,
                'name': device['name'],
                'channels': device['max_input_channels'] if device['max_input_channels'] > 0 else device['max_output_channels'],
                'sample_rate': int(device['default_samplerate'])
            }
            
            if device['max_input_channels'] > 0:
                device_info['channels'] = device['max_input_channels']
                self.input_devices.append(device_info)
            
            if device['max_output_channels'] > 0:
                device_info_out = device_info.copy()
                device_info_out['channels'] = device['max_output_channels']
                self.output_devices.append(device_info_out)
    
    def get_vb_cable_devices(self) -> Tuple[List[Dict], List[Dict]]:
        """获取 VB-Cable 相关设备"""
        vb_inputs = [d for d in self.input_devices if 'CABLE' in d['name'].upper() or 'VB-AUDIO' in d['name'].upper()]
        vb_outputs = [d for d in self.output_devices if 'CABLE' in d['name'].upper() or 'VB-AUDIO' in d['name'].upper()]
        return vb_inputs, vb_outputs
    
    def display_devices(self) -> None:
        """显示设备列表"""
        # 先计算推荐设备
        recommended_input = self._find_best_device(self.input_devices, is_input=True)
        recommended_output = self._find_best_device(self.output_devices, is_input=False)
        
        # 输入设备表格
        input_table = Table(title="🎤 输入设备 (从 Clubdeck 接收音频)", show_header=True, header_style="bold cyan")
        input_table.add_column("序号", width=6)
        input_table.add_column("设备名称", width=50)
        input_table.add_column("声道", justify="center", width=8)
        input_table.add_column("采样率", justify="center", width=12)
        input_table.add_column("类型", justify="center", width=12)
        
        for idx, device in enumerate(self.input_devices, 1):
            is_recommended = idx == recommended_input
            name_upper = device['name'].upper()
            
            # 设备类型识别
            if 'VOICEMEETER' in name_upper:
                if 'OUT B2' in name_upper or 'AUX OUT' in name_upper:
                    dev_type = "[cyan]VM B2[/cyan]"
                elif 'OUT B1' in name_upper:
                    dev_type = "[blue]VM B1[/blue]"
                else:
                    dev_type = "[dim]VM[/dim]"
            elif 'HI-FI CABLE' in name_upper or 'HIFI CABLE' in name_upper:
                dev_type = "[bold magenta]Hi-Fi Cable[/bold magenta]"
            elif 'CABLE' in name_upper:
                dev_type = "[green]VB-Cable[/green]"
            else:
                dev_type = ""
            
            channels = device['channels']
            if channels >= 8:
                ch_str = f"[bold yellow]{channels}ch[/bold yellow]"
            elif channels == 2:
                ch_str = f"[green]{channels}ch[/green]"
            else:
                ch_str = f"{channels}ch"
            
            # 推荐行高亮
            if is_recommended:
                input_table.add_row(
                    f"[bold green]★ {idx}[/bold green]",
                    f"[bold green]{device['name']}[/bold green]",
                    ch_str,
                    f"[bold green]{device['sample_rate']} Hz[/bold green]",
                    dev_type,
                    style="on dark_green"
                )
            else:
                input_table.add_row(
                    f"  {idx}",
                    device['name'],
                    ch_str,
                    f"{device['sample_rate']} Hz",
                    dev_type
                )
        
        console.print(input_table)
        console.print()
        
        # 输出设备表格
        output_table = Table(title="🔊 输出设备 (发送音频到 Clubdeck)", show_header=True, header_style="bold cyan")
        output_table.add_column("序号", width=6)
        output_table.add_column("设备名称", width=50)
        output_table.add_column("声道", justify="center", width=8)
        output_table.add_column("采样率", justify="center", width=12)
        output_table.add_column("类型", justify="center", width=12)
        
        for idx, device in enumerate(self.output_devices, 1):
            is_recommended = idx == recommended_output
            name_upper = device['name'].upper()
            
            # 设备类型识别
            if 'VOICEMEETER' in name_upper:
                if 'INPUT' in name_upper and 'AUX' not in name_upper:
                    dev_type = "[cyan]VM VAIO[/cyan]"
                elif 'AUX INPUT' in name_upper:
                    dev_type = "[blue]VM AUX[/blue]"
                else:
                    dev_type = "[dim]VM[/dim]"
            elif 'HI-FI CABLE' in name_upper or 'HIFI CABLE' in name_upper:
                dev_type = "[bold magenta]Hi-Fi Cable[/bold magenta]"
            elif 'CABLE' in name_upper:
                dev_type = "[green]VB-Cable[/green]"
            else:
                dev_type = ""
            
            channels = device['channels']
            if channels >= 8:
                ch_str = f"[bold yellow]{channels}ch[/bold yellow]"
            elif channels == 2:
                ch_str = f"[green]{channels}ch[/green]"
            else:
                ch_str = f"{channels}ch"
            
            # 推荐行高亮
            if is_recommended:
                output_table.add_row(
                    f"[bold green]★ {idx}[/bold green]",
                    f"[bold green]{device['name']}[/bold green]",
                    ch_str,
                    f"[bold green]{device['sample_rate']} Hz[/bold green]",
                    dev_type,
                    style="on dark_green"
                )
            else:
                output_table.add_row(
                    f"  {idx}",
                    device['name'],
                    ch_str,
                    f"{device['sample_rate']} Hz",
                    dev_type
                )
        
        console.print(output_table)
    
    def _find_best_device(self, devices: List[Dict], is_input: bool = True) -> Optional[int]:
        """
        找到最佳匹配的设备（Clubdeck 通信）
        双线缆方案：Hi-Fi Cable 用于 Clubdeck，VB-Cable 用于 MPV
        
        Returns:
            最佳设备的序号 (1-based)，如果没有找到返回 None
        """
        best_idx = None
        best_score = -1
        
        for idx, d in enumerate(devices, 1):
            name_upper = d['name'].upper()
            
            # 识别设备类型
            is_hifi_cable = 'HI-FI CABLE' in name_upper or 'HIFI CABLE' in name_upper
            is_vb_cable = 'CABLE' in name_upper and not is_hifi_cable and 'VOICEMEETER' not in name_upper
            is_voicemeeter = 'VOICEMEETER' in name_upper
            
            if not is_vb_cable and not is_voicemeeter and not is_hifi_cable:
                continue
            
            # 计算匹配分数
            score = 0
            
            if is_input:
                # 输入设备：从 Clubdeck 接收音频
                # 推荐: VB-Cable 2ch Output
                if is_hifi_cable:
                    score += 150  # Hi-Fi Cable 优先级降低
                elif is_vb_cable:
                    if d['channels'] == 2 or '2CH' in name_upper:
                        score += 200  # 2ch VB-Cable 最高优先级
                    elif d['channels'] >= 16 or '16CH' in name_upper:
                        score += 50   # 16ch 优先级降低
                elif is_voicemeeter:
                    if 'OUT B2' in name_upper:
                        score += 50
                    elif 'AUX OUT' in name_upper:
                        score += 40
                    else:
                        score += 10
            else:
                # 输出设备：发送音频到 Clubdeck
                # 推荐: VB-Cable 2ch Input
                if is_hifi_cable:
                    score += 150  # Hi-Fi Cable 优先级降低
                elif is_vb_cable:
                    if d['channels'] == 2 or '2CH' in name_upper:
                        score += 200  # 2ch VB-Cable 最高优先级
                    elif d['channels'] >= 16 or '16CH' in name_upper:
                        score += 50   # 16ch 优先级降低
                elif is_voicemeeter:
                    if 'INPUT' in name_upper and 'AUX' not in name_upper and 'OUT' not in name_upper:
                        score += 50
                    else:
                        score += 10
            
            # 高采样率加分
            if d['sample_rate'] >= 48000:
                score += 5
            
            # 2ch 设备额外加分（优先选择立体声设备）
            if d['channels'] == 2 or '2CH' in name_upper:
                score += 30  # 提高2ch优先级
            
            if score > best_score:
                best_score = score
                best_idx = idx
        
        return best_idx
    
    def _find_best_mpv_device(self, devices: List[Dict]) -> Optional[int]:
        """
        找到最佳 MPV 输入设备
        推荐 VB-Cable 2ch Output（专用于 MPV 音乐）
        
        Returns:
            最佳设备的序号 (1-based)，如果没有找到返回 None
        """
        best_idx = None
        best_score = -1
        
        for idx, d in enumerate(devices, 1):
            name_upper = d['name'].upper()
            
            # 识别设备类型
            is_hifi_cable = 'HI-FI CABLE' in name_upper or 'HIFI CABLE' in name_upper
            is_vb_cable = 'CABLE' in name_upper and not is_hifi_cable and 'VOICEMEETER' not in name_upper
            is_voicemeeter = 'VOICEMEETER' in name_upper
            
            if not is_vb_cable and not is_voicemeeter and not is_hifi_cable:
                continue
            
            score = 0
            
            # MPV 输入设备：从 MPV 接收音乐
            # 推荐: VB-Cable 2ch Output（专用于 MPV，避免与 Clubdeck 冲突）
            if is_vb_cable:
                if d['channels'] == 2 or '2CH' in name_upper:
                    score += 200  # VB-Cable 2ch 最高优先级
                elif d['channels'] >= 16 or '16CH' in name_upper:
                    score += 50   # 16ch 优先级降低
            elif is_voicemeeter:
                if 'OUT B2' in name_upper:
                    score += 80
                elif 'AUX OUT' in name_upper:
                    score += 70
                else:
                    score += 30
            elif is_hifi_cable:
                score += 50  # Hi-Fi Cable 最低优先级（应该用于 Clubdeck）
            
            # 高采样率加分
            if d['sample_rate'] >= 48000:
                score += 5
            
            # 2ch 设备额外加分（优先选择立体声设备）
            if d['channels'] == 2 or '2CH' in name_upper:
                score += 30  # 提高2ch优先级
            
            if score > best_score:
                best_score = score
                best_idx = idx
        
        return best_idx
    
    def interactive_select(self) -> Tuple[int, int, int, int, int, int, int]:
        """
        交互式选择设备
        
        Returns:
            (input_device_id, output_device_id, 
             input_sample_rate, output_sample_rate,
             input_channels, output_channels, browser_sample_rate)
        """
        console.print()
        self.display_devices()
        console.print()
        
        # 自动检测最佳 VB-Cable 设备
        vb_inputs, vb_outputs = self.get_vb_cable_devices()
        
        # 找到最佳输入设备
        default_input = self._find_best_device(self.input_devices, is_input=True)
        
        console.print("[bold yellow]选择输入设备[/bold yellow] [dim](从 Clubdeck 接收音频)[/dim]")
        if default_input:
            best_device = self.input_devices[default_input - 1]
            console.print(f"[bold green]★ 推荐: {default_input} - {best_device['name'][:40]}[/bold green]")
        
        input_choice = IntPrompt.ask(
            "请输入序号",
            default=default_input if default_input else 1,
            choices=[str(i) for i in range(1, len(self.input_devices) + 1)]
        )
        selected_input = self.input_devices[input_choice - 1]
        
        console.print()
        
        # 找到最佳输出设备
        default_output = self._find_best_device(self.output_devices, is_input=False)
        
        console.print("[bold yellow]选择输出设备[/bold yellow] [dim](发送音频到 Clubdeck)[/dim]")
        if default_output:
            best_device = self.output_devices[default_output - 1]
            console.print(f"[bold green]★ 推荐: {default_output} - {best_device['name'][:40]}[/bold green]")
        
        output_choice = IntPrompt.ask(
            "请输入序号",
            default=default_output if default_output else 1,
            choices=[str(i) for i in range(1, len(self.output_devices) + 1)]
        )
        selected_output = self.output_devices[output_choice - 1]
        
        console.print()
        
        # 从配置文件读取双工模式（不再交互式选择）
        duplex_mode = config.audio.duplex_mode
        
        # 各设备使用各自的采样率
        input_sample_rate = selected_input['sample_rate']
        output_sample_rate = selected_output['sample_rate']
        
        # 浏览器端使用 48kHz
        browser_sample_rate = 48000
        
        # 输入输出设备可以有不同的声道数
        input_channels = selected_input['channels']
        output_channels = selected_output['channels']
        
        # 浏览器端始终使用立体声
        browser_channels = 2
        
        # 更新全局配置以匹配设备参数
        config.audio.sample_rate = browser_sample_rate
        config.audio.input_sample_rate = input_sample_rate
        config.audio.output_sample_rate = output_sample_rate
        config.audio.channels = browser_channels
        config.audio.input_channels = input_channels
        config.audio.output_channels = output_channels
        config.audio.input_device_id = selected_input['id']
        config.audio.output_device_id = selected_output['id']
        
        console.print()
        
        mode_text = "[yellow]半双工 (仅监听)[/yellow]" if duplex_mode == "half" else "[green]全双工 (双向通信)[/green]"
        console.print(Panel(
            f"[green]✓ 输入设备:[/green] {selected_input['name']}\n"
            f"    {input_channels}ch @ {input_sample_rate}Hz\n"
            f"    [dim](Clubdeck + MPV 已混合)[/dim]\n"
            f"[green]✓ 输出设备:[/green] {selected_output['name']}\n"
            f"    {output_channels}ch @ {output_sample_rate}Hz\n"
            f"[green]✓ 浏览器:[/green] {browser_channels}ch @ {browser_sample_rate}Hz\n"
            f"[green]✓ 通信模式:[/green] {mode_text}\n"
            f"[green]✓ 架构:[/green] [cyan]简化单输入单输出[/cyan]",
            title="设备配置确认",
            border_style="green"
        ))
        
        if not Confirm.ask("确认使用以上配置?", default=True):
            return self.interactive_select()
        
        return (selected_input['id'], selected_output['id'], 
                input_sample_rate, output_sample_rate,
                input_channels, output_channels, browser_sample_rate)
    
    def validate_device(self, device_id: int, is_input: bool = True) -> bool:
        """验证设备可用性"""
        try:
            device_info = sd.query_devices(device_id)
            if is_input:
                return device_info['max_input_channels'] > 0
            else:
                return device_info['max_output_channels'] > 0
        except Exception:
            return False
