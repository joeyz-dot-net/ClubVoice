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
        # 输入设备表格
        input_table = Table(title="🎤 输入设备 (从 Clubdeck 接收音频)", show_header=True, header_style="bold cyan")
        input_table.add_column("序号", style="dim", width=6)
        input_table.add_column("设备名称", width=45)
        input_table.add_column("声道", justify="center", width=6)
        input_table.add_column("采样率", justify="center", width=10)
        input_table.add_column("VB-Cable", justify="center", width=10)
        
        for idx, device in enumerate(self.input_devices, 1):
            is_vb = '✓' if 'CABLE' in device['name'].upper() else ''
            input_table.add_row(
                str(idx),
                device['name'],
                str(device['channels']),
                f"{device['sample_rate']} Hz",
                f"[green]{is_vb}[/green]"
            )
        
        console.print(input_table)
        console.print()
        
        # 输出设备表格
        output_table = Table(title="🔊 输出设备 (发送音频到 Clubdeck)", show_header=True, header_style="bold cyan")
        output_table.add_column("序号", style="dim", width=6)
        output_table.add_column("设备名称", width=45)
        output_table.add_column("声道", justify="center", width=6)
        output_table.add_column("采样率", justify="center", width=10)
        output_table.add_column("VB-Cable", justify="center", width=10)
        
        for idx, device in enumerate(self.output_devices, 1):
            is_vb = '✓' if 'CABLE' in device['name'].upper() else ''
            output_table.add_row(
                str(idx),
                device['name'],
                str(device['channels']),
                f"{device['sample_rate']} Hz",
                f"[green]{is_vb}[/green]"
            )
        
        console.print(output_table)
    
    def _find_best_device(self, devices: List[Dict], is_input: bool = True) -> Optional[int]:
        """
        找到最佳匹配的设备
        优先级：VB-Cable + 2声道 + 48kHz > VB-Cable + 2声道 > VB-Cable > 其他
        
        Returns:
            最佳设备的序号 (1-based)，如果没有找到返回 None
        """
        target_sample_rate = config.audio.sample_rate  # 48000
        target_channels = config.audio.channels  # 2
        keyword = 'CABLE OUTPUT' if is_input else 'CABLE INPUT'
        
        best_idx = None
        best_score = -1
        
        for idx, d in enumerate(devices, 1):
            name_upper = d['name'].upper()
            
            # 必须是 VB-Cable 设备
            if keyword not in name_upper:
                continue
            
            # 计算匹配分数
            score = 0
            
            # 采样率匹配 (+10分)
            if d['sample_rate'] >= target_sample_rate:
                score += 10
            
            # 声道数匹配 - 优先选择2声道 (+20分)
            if d['channels'] == target_channels:
                score += 20
            elif d['channels'] > target_channels:
                score += 5  # 声道数过多，扣分
            
            # 排除16声道设备（通常不需要）
            if d['channels'] > 8:
                score -= 10
            
            if score > best_score:
                best_score = score
                best_idx = idx
        
        return best_idx
    
    def interactive_select(self) -> Tuple[int, int, int, int]:
        """
        交互式选择设备
        
        Returns:
            (input_device_id, output_device_id, sample_rate, channels)
        """
        console.print()
        self.display_devices()
        console.print()
        
        # 自动检测最佳 VB-Cable 设备
        vb_inputs, vb_outputs = self.get_vb_cable_devices()
        
        # 找到最佳输入设备 (CABLE Output, 2ch, 48kHz)
        default_input = self._find_best_device(self.input_devices, is_input=True)
        
        console.print("[bold yellow]选择输入设备[/bold yellow] (接收 Clubdeck 音频，通常是 CABLE Output)")
        if default_input:
            best_device = self.input_devices[default_input - 1]
            console.print(f"[dim]检测到 VB-Cable，建议选择: {default_input} ({best_device['channels']}ch {best_device['sample_rate']}Hz)[/dim]")
        
        input_choice = IntPrompt.ask(
            "请输入序号",
            default=default_input if default_input else 1,
            choices=[str(i) for i in range(1, len(self.input_devices) + 1)]
        )
        selected_input = self.input_devices[input_choice - 1]
        
        console.print()
        
        # 找到最佳输出设备 (CABLE Input, 2ch, 48kHz)
        default_output = self._find_best_device(self.output_devices, is_input=False)
        
        console.print("[bold yellow]选择输出设备[/bold yellow] (发送到 Clubdeck，通常是 CABLE Input)")
        if default_output:
            best_device = self.output_devices[default_output - 1]
            console.print(f"[dim]检测到 VB-Cable，建议选择: {default_output} ({best_device['channels']}ch {best_device['sample_rate']}Hz)[/dim]")
        
        output_choice = IntPrompt.ask(
            "请输入序号",
            default=default_output if default_output else 1,
            choices=[str(i) for i in range(1, len(self.output_devices) + 1)]
        )
        selected_output = self.output_devices[output_choice - 1]
        
        # 使用配置文件中的采样率（如果设备支持），否则使用设备支持的最高采样率
        target_sample_rate = config.audio.sample_rate
        if selected_input['sample_rate'] >= target_sample_rate and selected_output['sample_rate'] >= target_sample_rate:
            sample_rate = target_sample_rate
        else:
            sample_rate = min(selected_input['sample_rate'], selected_output['sample_rate'])
        
        # 使用配置文件中的声道数（如果设备支持）
        target_channels = config.audio.channels
        max_channels = min(selected_input['channels'], selected_output['channels'])
        channels = target_channels if max_channels >= target_channels else max_channels
        
        console.print()
        console.print(Panel(
            f"[green]✓ 输入设备:[/green] {selected_input['name']}\n"
            f"[green]✓ 输出设备:[/green] {selected_output['name']}\n"
            f"[green]✓ 采样率:[/green] {sample_rate} Hz\n"
            f"[green]✓ 声道:[/green] {'立体声' if channels == 2 else '单声道'}",
            title="设备配置确认",
            border_style="green"
        ))
        
        if not Confirm.ask("确认使用以上配置?", default=True):
            return self.interactive_select()
        
        return selected_input['id'], selected_output['id'], sample_rate, channels
    
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
