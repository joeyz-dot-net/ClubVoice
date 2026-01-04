"""
所有音频设备测试和实时监控程序
显示所有输入和输出设备，并实时监控输入设备音量
"""
import sounddevice as sd
import numpy as np
import time
import threading
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout


console = Console()

# 全局音量数据存储
volume_data = {}
volume_lock = threading.Lock()


def calculate_volume(audio_data: np.ndarray) -> float:
    """计算音量 (RMS)"""
    if audio_data.dtype == np.int16:
        float_data = audio_data.astype(np.float32) / 32768.0
    else:
        float_data = audio_data
    
    rms = np.sqrt(np.mean(float_data ** 2))
    return min(100.0, rms * 100.0 * 10.0)


def create_volume_bar(volume: float, width: int = 12) -> str:
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


def test_input_device(device_id: int, device_info: dict) -> bool:
    """测试输入设备是否可用"""
    try:
        channels = min(device_info['max_input_channels'], 2)
        sample_rate = int(device_info['default_samplerate'])
        
        stream = sd.InputStream(
            device=device_id,
            samplerate=sample_rate,
            channels=channels,
            dtype='int16',
            blocksize=512
        )
        stream.start()
        data, overflowed = stream.read(512)
        stream.stop()
        stream.close()
        return True
    except:
        return False


def test_output_device(device_id: int, device_info: dict) -> bool:
    """测试输出设备是否可用"""
    try:
        channels = min(device_info['max_output_channels'], 2)
        sample_rate = int(device_info['default_samplerate'])
        
        test_audio = np.zeros((512, channels), dtype='int16')
        
        stream = sd.OutputStream(
            device=device_id,
            samplerate=sample_rate,
            channels=channels,
            dtype='int16',
            blocksize=512
        )
        stream.start()
        stream.write(test_audio)
        stream.stop()
        stream.close()
        return True
    except:
        return False


def monitor_input_device(device_id: int, device_info: dict, stop_event: threading.Event):
    """后台监控输入设备音量"""
    try:
        sample_rate = int(device_info['default_samplerate'])
        channels = min(device_info['max_input_channels'], 2)
        
        def callback(indata, frames, time_info, status):
            if stop_event.is_set():
                raise sd.CallbackAbort
            
            volume = calculate_volume(indata)
            with volume_lock:
                volume_data[device_id] = volume
        
        with sd.InputStream(
            device=device_id,
            samplerate=sample_rate,
            channels=channels,
            dtype='int16',
            blocksize=512,
            callback=callback
        ):
            while not stop_event.is_set():
                time.sleep(0.1)
    except:
        pass  # 静默失败


def highlight_cable_device(device_name: str) -> str:
    """高亮 VB-Cable 设备名称"""
    name_upper = device_name.upper()
    
    if 'CABLE-A' in name_upper or 'VIRTUAL CABLE A' in name_upper:
        return f"[cyan bold]{device_name}[/cyan bold] 🅰️"
    elif 'CABLE-B' in name_upper or 'VIRTUAL CABLE B' in name_upper:
        return f"[magenta bold]{device_name}[/magenta bold] 🅱️"
    elif 'CABLE-C' in name_upper or 'VIRTUAL CABLE C' in name_upper:
        return f"[yellow bold]{device_name}[/yellow bold] 🅲"
    elif 'CABLE' in name_upper or 'VB-AUDIO' in name_upper:
        return f"[green]{device_name}[/green] ⭐"
    else:
        return device_name


def get_hostapi_name(hostapi_index: int) -> str:
    """获取 HostAPI 名称"""
    try:
        hostapis = sd.query_hostapis()
        return hostapis[hostapi_index]['name']
    except:
        return f"API {hostapi_index}"


def main():
    """主函数"""
    console.clear()
    
    console.print(Panel.fit(
        "[bold cyan]🎵 所有音频设备测试 + 实时监控 🎵[/bold cyan]\n"
        "按照音频 API 分组显示所有设备，并实时监控输入设备音量",
        border_style="cyan"
    ))
    
    # 获取所有设备和 API 信息
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    
    console.print(f"\n[dim]找到 {len(devices)} 个音频设备，{len(hostapis)} 个音频 API[/dim]\n")
    
    # 按 API 分组设备
    devices_by_api = {}
    for i, dev in enumerate(devices):
        api_index = dev['hostapi']
        api_name = get_hostapi_name(api_index)
        
        if api_name not in devices_by_api:
            devices_by_api[api_name] = {'input': [], 'output': []}
        
        if dev['max_input_channels'] > 0:
            devices_by_api[api_name]['input'].append((i, dev))
        if dev['max_output_channels'] > 0:
            devices_by_api[api_name]['output'].append((i, dev))
    
    # 显示 API 选择菜单
    sorted_apis = sorted(devices_by_api.keys())
    # WASAPI 优先（如果存在）
    if 'Windows WASAPI' in sorted_apis:
        sorted_apis.remove('Windows WASAPI')
        sorted_apis.insert(0, 'Windows WASAPI')
    
    console.print("[yellow]选择要监控的音频 API:[/yellow]")
    for idx, api in enumerate(sorted_apis, 1):
        input_count = len(devices_by_api[api]['input'])
        output_count = len(devices_by_api[api]['output'])
        console.print(f"  [{idx}] {api:20s} - {input_count:2d}输入, {output_count:2d}输出")
    console.print(f"  [0] 显示全部")
    
    try:
        choice = console.input("\n[bold yellow]请选择 (留空=第一个API, 0=全部): [/bold yellow]").strip()
        
        if choice == '':
            selected_apis = [sorted_apis[0]]
        elif choice == '0':
            selected_apis = sorted_apis
        else:
            idx = int(choice) - 1
            if 0 <= idx < len(sorted_apis):
                selected_apis = [sorted_apis[idx]]
            else:
                console.print(f"[red]无效选项，使用 {sorted_apis[0]}[/red]")
                selected_apis = [sorted_apis[0]]
    except (ValueError, KeyboardInterrupt):
        console.print("\n[yellow]已取消[/yellow]")
        return
    
    # 过滤设备
    filtered_devices = {}
    for api in selected_apis:
        if api in devices_by_api:
            filtered_devices[api] = devices_by_api[api]
    
    console.print(f"\n[dim]正在测试选定的 API 设备...[/dim]\n")
    
    # 测试设备可用性（只测试选定的 API）
    available_input_devices = []
    available_output_devices = []
    
    for api in selected_apis:
        if api not in devices_by_api:
            continue
        for device_id, dev in devices_by_api[api]['input']:
            if test_input_device(device_id, dev):
                available_input_devices.append((device_id, dev))
        for device_id, dev in devices_by_api[api]['output']:
            if test_output_device(device_id, dev):
                available_output_devices.append((device_id, dev))
    
    # 启动所有可用输入设备的监控线程
    stop_event = threading.Event()
    monitor_threads = []
    
    for device_id, device_info in available_input_devices:
        thread = threading.Thread(
            target=monitor_input_device,
            args=(device_id, device_info, stop_event),
            daemon=True
        )
        thread.start()
        monitor_threads.append(thread)
        with volume_lock:
            volume_data[device_id] = 0.0
    
    # 等待监控启动
    time.sleep(0.5)
    
    def generate_display():
        """生成实时更新的按API分组显示"""
        
        # 为每个 API 创建表格组
        api_layouts = []
        
        # 按 API 名称排序，Windows WASAPI 优先
        sorted_api_list = sorted(filtered_devices.keys(), key=lambda x: (0 if 'WASAPI' in x else 1, x))
        
        for api_name in sorted_api_list:
            api_devices = filtered_devices[api_name]
            
            # 输入设备表格
            if api_devices['input']:
                input_table = Table(
                    show_header=True,
                    header_style="bold cyan",
                    title=f"📥 {api_name} - 输入设备",
                    title_style="bold cyan",
                    border_style="dim"
                )
                input_table.add_column("ID", style="yellow", width=4)
                input_table.add_column("设备名称", style="white", width=38)
                input_table.add_column("声道", style="magenta", width=4)
                input_table.add_column("采样率", style="blue", width=7)
                input_table.add_column("状态", style="green", width=4)
                input_table.add_column("实时音量", style="green", width=18)
                
                for device_id, device_info in api_devices['input']:
                    device_name = highlight_cable_device(device_info['name'][:36])
                    channels = device_info['max_input_channels']
                    sample_rate = int(device_info['default_samplerate'])
                    
                    is_available = device_id in [d[0] for d in available_input_devices]
                    status = "[green]✓[/green]" if is_available else "[red]✗[/red]"
                    
                    if is_available:
                        with volume_lock:
                            volume = volume_data.get(device_id, 0.0)
                        volume_display = f"{create_volume_bar(volume, 10)} {volume:4.1f}%"
                    else:
                        volume_display = "[dim]--[/dim]"
                    
                    input_table.add_row(
                        str(device_id),
                        device_name,
                        f"{channels}ch",
                        f"{sample_rate}Hz",
                        status,
                        volume_display
                    )
                
                api_layouts.append(input_table)
            
            # 输出设备表格
            if api_devices['output']:
                output_table = Table(
                    show_header=True,
                    header_style="bold yellow",
                    title=f"📤 {api_name} - 输出设备",
                    title_style="bold yellow",
                    border_style="dim"
                )
                output_table.add_column("ID", style="yellow", width=4)
                output_table.add_column("设备名称", style="white", width=38)
                output_table.add_column("声道", style="magenta", width=4)
                output_table.add_column("采样率", style="blue", width=7)
                output_table.add_column("状态", style="green", width=4)
                
                for device_id, device_info in api_devices['output']:
                    device_name = highlight_cable_device(device_info['name'][:36])
                    channels = device_info['max_output_channels']
                    sample_rate = int(device_info['default_samplerate'])
                    
                    is_available = device_id in [d[0] for d in available_output_devices]
                    status = "[green]✓[/green]" if is_available else "[red]✗[/red]"
                    
                    output_table.add_row(
                        str(device_id),
                        device_name,
                        f"{channels}ch",
                        f"{sample_rate}Hz",
                        status
                    )
                
                api_layouts.append(output_table)
        
        # 统计信息
        total_input = sum(len(api['input']) for api in filtered_devices.values())
        total_output = sum(len(api['output']) for api in filtered_devices.values())
        
        stats = f"""[cyan]📊 设备统计:[/cyan] API: {len(filtered_devices)} | 输入: {total_input}个 ([green]{len(available_input_devices)}可用[/green]) | 输出: {total_output}个 ([green]{len(available_output_devices)}可用[/green]) | 监控: {len(monitor_threads)}流"""
        
        # 创建主布局并添加所有内容
        main_layout = Layout()
        
        # 先添加统计面板
        all_panels = [Panel(stats, border_style="dim")] + api_layouts
        
        # 为每个面板创建独立的 Layout 并组合
        if len(all_panels) == 1:
            main_layout = all_panels[0]
        else:
            # 创建一个包含所有面板的组
            from rich.console import Group
            main_layout = Group(*all_panels)
        
        return main_layout
    
    # 显示提示
    console.print("\n[bold yellow]📡 实时监控已启动，按 Ctrl+C 停止[/bold yellow]\n")
    
    try:
        # 使用 Live 实时更新显示
        with Live(generate_display(), refresh_per_second=10, console=console) as live:
            while True:
                time.sleep(0.1)
                live.update(generate_display())
    except KeyboardInterrupt:
        console.print("\n\n[yellow]正在停止监控...[/yellow]")
        stop_event.set()
        time.sleep(0.3)
        
        # 显示 ClubVoice 3-Cable 配置建议
        console.print("\n")
        console.print(Panel(
            "[bold cyan]💡 ClubVoice 3-Cable 配置建议[/bold cyan]\n\n"
            "在 config.ini 中配置以下设备ID：\n\n"
            "[cyan]# CABLE-C (Clubdeck房间音频 → Python读取)[/cyan]\n"
            "[yellow]clubdeck_input_device_id[/yellow] = [green]<CABLE-A Output 设备ID>[/green]\n\n"
            "[cyan]# CABLE-B (MPV音乐 → Python读取)[/cyan]\n"
            "[yellow]mpv_input_device_id[/yellow] = [green]<CABLE-B Output 设备ID>[/green]\n\n"
            "[cyan]# CABLE-A (浏览器麦克风 → Clubdeck输入)[/cyan]\n"
            "[yellow]browser_output_device_id[/yellow] = [green]<CABLE-A Input 设备ID>[/green]\n\n"
            "[dim]提示: 带有 🅰️ 🅱️ ⭐ 标记的是 VB-Cable 设备[/dim]",
            border_style="green"
        ))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]测试已取消[/yellow]")
    except Exception as e:
        console.print(f"\n[red]错误: {e}[/red]")
        import traceback
        traceback.print_exc()
