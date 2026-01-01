"""
音频设备管理器 - 按 Host API 分类显示
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
        self.devices = sd.query_devices()
        self.hostapis = sd.query_hostapis()
        self.all_devices: List[Dict] = []
        self._scan_devices()
    
    def _scan_devices(self) -> None:
        """扫描所有音频设备，包含 Host API 信息"""
        self.all_devices = []
        
        for i, device in enumerate(self.devices):
            hostapi_name = self.hostapis[device['hostapi']]['name']
            
            device_info = {
                'id': i,
                'name': device['name'],
                'input_channels': device['max_input_channels'],
                'output_channels': device['max_output_channels'],
                'sample_rate': int(device['default_samplerate']),
                'hostapi': device['hostapi'],
                'hostapi_name': hostapi_name
            }
            self.all_devices.append(device_info)
    
    def get_vb_cable_devices(self) -> List[Dict]:
        """获取 VB-Cable 相关设备"""
        return [d for d in self.all_devices if 'CABLE' in d['name'].upper() or 'VB-AUDIO' in d['name'].upper()]
    
    def display_devices(self) -> None:
        """按 Host API 分类显示所有设备"""
        # 按 Host API 分组设备
        devices_by_hostapi = {}
        for device in self.all_devices:
            hostapi = device['hostapi_name']
            if hostapi not in devices_by_hostapi:
                devices_by_hostapi[hostapi] = []
            devices_by_hostapi[hostapi].append(device)
        
        # 显示设备表格
        console.print("\n[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]  🎧 音频设备列表 (按驱动分类)[/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]\n")
        
        for hostapi_name in sorted(devices_by_hostapi.keys()):
            devices = devices_by_hostapi[hostapi_name]
            
            table = Table(title=f"[yellow]{hostapi_name}[/yellow]", show_header=True, header_style="bold cyan", border_style="dim")
            table.add_column("ID", width=6, justify="right")
            table.add_column("设备名称", width=45)
            table.add_column("输入", justify="center", width=8)
            table.add_column("输出", justify="center", width=8)
            table.add_column("采样率", justify="center", width=12)
            table.add_column("类型", justify="center", width=15)
            
            for device in devices:
                name_upper = device['name'].upper()
                
                # 设备类型识别
                if 'VOICEMEETER' in name_upper:
                    if 'OUT B2' in name_upper or 'AUX OUT' in name_upper:
                        dev_type = "[cyan]VM B2[/cyan]"
                    elif 'OUT B1' in name_upper:
                        dev_type = "[blue]VM B1[/blue]"
                    elif 'INPUT' in name_upper and 'AUX' not in name_upper:
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
                
                # 输入通道显示
                if device['input_channels'] > 0:
                    if device['input_channels'] >= 8:
                        in_ch = f"[bold yellow]{device['input_channels']}ch[/bold yellow]"
                    elif device['input_channels'] == 2:
                        in_ch = f"[green]{device['input_channels']}ch[/green]"
                    else:
                        in_ch = f"{device['input_channels']}ch"
                else:
                    in_ch = "[dim]-[/dim]"
                
                # 输出通道显示
                if device['output_channels'] > 0:
                    if device['output_channels'] >= 8:
                        out_ch = f"[bold yellow]{device['output_channels']}ch[/bold yellow]"
                    elif device['output_channels'] == 2:
                        out_ch = f"[green]{device['output_channels']}ch[/green]"
                    else:
                        out_ch = f"{device['output_channels']}ch"
                else:
                    out_ch = "[dim]-[/dim]"
                
                # VB-Cable 设备行高亮
                if dev_type:
                    table.add_row(
                        f"[bold]{device['id']}[/bold]",
                        f"[bold]{device['name']}[/bold]",
                        in_ch,
                        out_ch,
                        f"[bold]{device['sample_rate']} Hz[/bold]",
                        dev_type
                    )
                else:
                    table.add_row(
                        str(device['id']),
                        device['name'],
                        in_ch,
                        out_ch,
                        f"{device['sample_rate']} Hz",
                        dev_type
                    )
            
            console.print(table)
            console.print()
    
    def _find_best_device(self, device_type: str = "both") -> Optional[int]:
        """
        找到最佳匹配的设备（Clubdeck 通信）
        优先级：WASAPI > 2ch > VB-Cable > 非16ch
        
        Args:
            device_type: "input"（有输入通道）, "output"（有输出通道）, "both"（都有）
        
        Returns:
            最佳设备的ID，如果没有找到返回 None
        """
        best_device = None
        best_score = -1
        
        for device in self.all_devices:
            name_upper = device['name'].upper()
            
            # 根据类型过滤
            if device_type == "input" and device['input_channels'] == 0:
                continue
            elif device_type == "output" and device['output_channels'] == 0:
                continue
            elif device_type == "both" and (device['input_channels'] == 0 or device['output_channels'] == 0):
                continue
            
            # 识别设备类型
            is_hifi_cable = 'HI-FI CABLE' in name_upper or 'HIFI CABLE' in name_upper
            is_vb_cable = 'CABLE' in name_upper and not is_hifi_cable and 'VOICEMEETER' not in name_upper
            is_voicemeeter = 'VOICEMEETER' in name_upper
            
            if not is_vb_cable and not is_voicemeeter and not is_hifi_cable:
                continue
            
            # 计算匹配分数
            score = 0
            
            # WASAPI 优先
            if 'WASAPI' in device['hostapi_name']:
                score += 100
            
            # 排除 16ch 设备
            has_16ch = '16CH' in name_upper or device['input_channels'] >= 16 or device['output_channels'] >= 16
            if has_16ch:
                score -= 100
            
            # VB-Cable/Hi-Fi Cable 优先
            if is_hifi_cable:
                score += 150
            elif is_vb_cable:
                if '2CH' in name_upper or (device['input_channels'] == 2 and device['output_channels'] == 2):
                    score += 200
                else:
                    score += 120
            elif is_voicemeeter:
                score += 50
            
            # 高采样率加分
            if device['sample_rate'] >= 48000:
                score += 10
            
            if score > best_score:
                best_score = score
                best_device = device['id']
        
        return best_device
    
    def interactive_select(self) -> Tuple[int, int, int]:
        """
        交互式选择设备（仅输入设备）
        
        Returns:
            (input_device_id, input_sample_rate, input_channels)
        """
        console.print()
        self.display_devices()
        console.print()
        
        # 自动检测最佳输入设备（有输入通道的设备）
        default_input_id = self._find_best_device("input")
        
        console.print("[bold yellow]选择输入设备[/bold yellow] [dim](从 Clubdeck 接收音频)[/dim]")
        if default_input_id is not None:
            default_device = next((d for d in self.all_devices if d['id'] == default_input_id), None)
            if default_device:
                console.print(f"[bold green]★ 推荐: ID {default_input_id} - {default_device['name'][:50]}[/bold green]")
        
        # 允许从所有设备中选择
        all_device_ids = [str(d['id']) for d in self.all_devices]
        
        input_choice = IntPrompt.ask(
            "请输入设备ID",
            default=default_input_id if default_input_id is not None else 0,
            choices=all_device_ids
        )
        selected_input = next(d for d in self.all_devices if d['id'] == input_choice)
        
        console.print()
        
        # 从配置文件读取双工模式
        duplex_mode = config.audio.duplex_mode
        
        # 使用选中设备的采样率和通道数
        input_sample_rate = selected_input['sample_rate']
        input_channels = selected_input['input_channels'] if selected_input['input_channels'] > 0 else 2
        
        # 浏览器端使用 48kHz 立体声
        browser_sample_rate = 48000
        browser_channels = 2
        
        # 更新全局配置
        config.audio.sample_rate = browser_sample_rate
        config.audio.input_sample_rate = input_sample_rate
        config.audio.channels = browser_channels
        config.audio.input_channels = input_channels
        config.audio.input_device_id = selected_input['id']
        
        return (selected_input['id'], input_sample_rate, input_channels)
    
    def validate_device(self, device_id: int, is_input: bool = True) -> bool:
        """验证设备可用性"""
        try:
            device = next((d for d in self.all_devices if d['id'] == device_id), None)
            if device is None:
                return False
            
            if is_input:
                return device['input_channels'] > 0
            else:
                return device['output_channels'] > 0
        except Exception:
            return False
