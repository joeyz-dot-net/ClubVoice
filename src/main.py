"""
主入口
"""
import sys
import signal
from rich.console import Console

from .bootstrap import Bootstrap
from .config.settings import config
from .audio.vb_cable_bridge import VBCableBridge
from .server.app import create_app
from .server.websocket_handler import WebSocketHandler


console = Console()

# 全局变量，用于清理
bridge = None
ws_handler = None


def signal_handler(sig, frame):
    """处理退出信号"""
    console.print("\n[yellow]正在关闭服务...[/yellow]")
    
    if ws_handler:
        ws_handler.stop()
    if bridge:
        bridge.stop()
    
    sys.exit(0)


def main():
    """主函数"""
    global bridge, ws_handler
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 启动引导
        bootstrap = Bootstrap()
        audio_config = bootstrap.run()
        
        # 创建音频桥接器 - 支持不同采样率和声道数的输入输出设备
        bridge = VBCableBridge(
            input_device_id=audio_config.input_device_id,
            output_device_id=audio_config.output_device_id,
            browser_sample_rate=audio_config.sample_rate,
            input_sample_rate=audio_config.input_sample_rate,
            output_sample_rate=audio_config.output_sample_rate,
            input_channels=audio_config.input_channels,
            output_channels=audio_config.output_channels,
            browser_channels=audio_config.channels,
            chunk_size=audio_config.chunk_size
        )
        
        # 创建 Flask 应用
        app, socketio = create_app()
        
        # 创建 WebSocket 处理器
        ws_handler = WebSocketHandler(socketio, bridge)
        
        # 启动音频桥接
        bridge.start()
        
        # 启动 WebSocket 处理器
        ws_handler.start()
        
        console.print("\n[bold green]服务器启动成功！[/bold green]")
        console.print(f"[cyan]请在浏览器中打开: http://localhost:{config.server.port}[/cyan]\n")
        
        # 启动服务器
        socketio.run(
            app,
            host=config.server.host,
            port=config.server.port,
            debug=config.server.debug,
            use_reloader=False
        )
        
    except KeyboardInterrupt:
        signal_handler(None, None)
    except Exception as e:
        console.print(f"\n[bold red]{'=' * 50}[/bold red]")
        console.print(f"[bold red]程序错误[/bold red]")
        console.print(f"[bold red]{'=' * 50}[/bold red]")
        console.print(f"[red]错误类型: {type(e).__name__}[/red]")
        console.print(f"[red]错误信息: {e}[/red]")
        console.print()
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise


if __name__ == '__main__':
    main()