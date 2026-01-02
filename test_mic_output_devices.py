"""
测试设备21-24哪些可以用作麦克风输出设备
用于接收浏览器音频数据并发送到Clubdeck
"""
import sounddevice as sd
import numpy as np
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def test_output_device(device_id: int, duration: float = 2.0) -> dict:
    """
    测试输出设备是否可用
    
    Args:
        device_id: 设备ID
        duration: 测试时长（秒）
    
    Returns:
        测试结果字典
    """
    result = {
        'device_id': device_id,
        'success': False,
        'error': None,
        'device_info': None,
        'test_details': {}
    }
    
    try:
        # 获取设备信息
        device_info = sd.query_devices(device_id)
        result['device_info'] = device_info
        
        if device_info['max_output_channels'] == 0:
            result['error'] = "设备不支持音频输出"
            return result
        
        # 测试参数
        sample_rate = int(device_info['default_samplerate']) 
        channels = min(device_info['max_output_channels'], 2)  # 最多2声道
        
        # 生成测试音频（440Hz + 880Hz 双音调）
        frames = int(sample_rate * duration)
        t = np.linspace(0, duration, frames, dtype=np.float32)
        
        if channels == 1:
            # 单声道
            audio_data = 0.1 * (np.sin(2 * np.pi * 440 * t) + 0.5 * np.sin(2 * np.pi * 880 * t))
            audio_data = audio_data.reshape(-1, 1)
        else:
            # 立体声
            left = 0.1 * np.sin(2 * np.pi * 440 * t)   # 左声道440Hz
            right = 0.1 * np.sin(2 * np.pi * 880 * t)  # 右声道880Hz
            audio_data = np.column_stack([left, right])
        
        # 转换为int16格式（与ClubVoice一致）
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        console.print(f"[dim]测试设备 {device_id}: 播放 {duration}s 测试音频...[/dim]")
        
        # 尝试播放音频
        sd.play(audio_int16, samplerate=sample_rate, device=device_id)
        sd.wait()  # 等待播放完成
        
        result['success'] = True
        result['test_details'] = {
            'sample_rate': sample_rate,
            'channels': channels,
            'duration': duration,
            'frames': frames
        }
        
    except Exception as e:
        result['error'] = str(e)
    
    return result

def display_device_info(device_id: int):
    """显示设备详细信息"""
    try:
        device = sd.query_devices(device_id)
        
        table = Table.grid(padding=(0, 2))
        table.add_column(style="cyan")
        table.add_column(style="white")
        
        table.add_row("设备ID:", str(device_id))
        table.add_row("设备名称:", device['name'])
        table.add_row("输入声道:", f"{device['max_input_channels']}ch")
        table.add_row("输出声道:", f"{device['max_output_channels']}ch")
        table.add_row("默认采样率:", f"{int(device['default_samplerate'])}Hz")
        table.add_row("延迟 (输出):", f"{device['default_low_output_latency']:.3f}s")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]无法获取设备 {device_id} 信息: {e}[/red]")

def main():
    """主函数"""
    console.print(Panel(
        "[bold cyan]设备 21-24 麦克风输出能力测试[/bold cyan]\n" +
        "测试哪些设备可以接收浏览器音频数据发送到Clubdeck",
        title="🎤 麦克风输出设备测试",
        border_style="cyan"
    ))
    
    # 要测试的设备范围
    device_range = range(21, 25)  # 21, 22, 23, 24
    results = []
    
    console.print(f"\n[bold]第一步: 设备信息查看[/bold]\n")
    
    # 显示所有设备信息
    for device_id in device_range:
        console.print(f"[yellow]设备 {device_id}:[/yellow]")
        display_device_info(device_id)
        console.print()
    
    console.print(f"\n[bold]第二步: 输出能力测试[/bold]")
    console.print("[dim]将播放测试音频，请注意听是否有声音输出[/dim]\n")
    
    # 测试每个设备
    for device_id in device_range:
        console.print(f"[yellow]正在测试设备 {device_id}...[/yellow]")
        
        result = test_output_device(device_id, duration=1.5)
        results.append(result)
        
        if result['success']:
            console.print(f"[green]✓ 设备 {device_id}: 测试成功[/green]")
            details = result['test_details']
            console.print(f"  参数: {details['sample_rate']}Hz, {details['channels']}ch")
        else:
            console.print(f"[red]✗ 设备 {device_id}: {result['error']}[/red]")
        
        console.print()
        time.sleep(0.5)  # 短暂暂停
    
    # 汇总结果
    console.print(f"\n[bold]测试结果汇总:[/bold]\n")
    
    success_devices = [r for r in results if r['success']]
    failed_devices = [r for r in results if not r['success']]
    
    if success_devices:
        console.print("[green]✓ 可用作麦克风输出的设备:[/green]")
        for result in success_devices:
            device_info = result['device_info']
            details = result['test_details']
            console.print(f"  设备 {result['device_id']}: {device_info['name']}")
            console.print(f"    - {details['sample_rate']}Hz, {details['channels']}ch")
            console.print(f"    - 延迟: {device_info['default_low_output_latency']:.3f}s")
    
    if failed_devices:
        console.print(f"\n[red]✗ 不可用设备:[/red]")
        for result in failed_devices:
            console.print(f"  设备 {result['device_id']}: {result['error']}")
    
    # 推荐配置
    if success_devices:
        console.print(f"\n[bold cyan]推荐配置:[/bold cyan]")
        
        # 寻找最佳设备（通常是CABLE-A Input类型）
        cable_devices = [r for r in success_devices 
                        if 'CABLE' in r['device_info']['name'].upper() 
                        and 'INPUT' in r['device_info']['name'].upper()]
        
        if cable_devices:
            best_device = cable_devices[0]
            console.print(f"推荐使用设备 {best_device['device_id']} 作为麦克风输出:")
            console.print(f"  {best_device['device_info']['name']}")
            console.print(f"\nconfig.ini 中应设置:")
            console.print(f"[dim]# 注意：这是输出设备，不是input_device_id[/dim]")
            console.print(f"output_device_id = {best_device['device_id']}")
        else:
            best_device = success_devices[0]  # 选择第一个可用的
            console.print(f"推荐使用设备 {best_device['device_id']}:")
            console.print(f"  {best_device['device_info']['name']}")
    
    console.print(f"\n[dim]测试完成！按任意键退出...[/dim]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]用户中断测试[/yellow]")
    except Exception as e:
        console.print(f"\n[red]测试过程中发生错误: {e}[/red]")
        import traceback
        traceback.print_exc()
    finally:
        input()  # 等待用户按键