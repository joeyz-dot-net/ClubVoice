"""
Main Entry Point
"""
import sys
import signal
import os
from rich.console import Console

from .bootstrap import Bootstrap
from .config.settings import config
from .audio.vb_cable_bridge import VBCableBridge
from .server.app import create_app
from .server.websocket_handler import WebSocketHandler


# Configure console to avoid Unicode issues on Windows
console = Console(no_color=True, force_terminal=False, legacy_windows=True)

# 全局变量，用于清理
bridge = None
ws_handler = None
_exiting = False


def signal_handler(sig, frame):
    """处理退出信号"""
    global _exiting
    
    # 防止重复调用
    if _exiting:
        return
    _exiting = True
    
    console.print("\n[yellow]正在关闭服务...[/yellow]")
    
    # 停止音频处理
    if ws_handler:
        try:
            ws_handler.stop()
        except Exception:
            pass
    if bridge:
        try:
            bridge.stop()
        except Exception:
            pass
    
    # 使用 os._exit 避免 gevent 的问题
    os._exit(0)


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
        
        # 创建音频桥接器 - 支持单输入或双输入混音模式
        bridge = VBCableBridge(
            input_device_id=audio_config.input_device_id,
            output_device_id=audio_config.output_device_id,
            browser_sample_rate=audio_config.sample_rate,
            input_sample_rate=audio_config.input_sample_rate,
            output_sample_rate=audio_config.output_sample_rate,
            input_channels=audio_config.input_channels,
            output_channels=audio_config.output_channels,
            browser_channels=audio_config.channels,
            chunk_size=audio_config.chunk_size,
            # 混音模式参数
            mix_mode=audio_config.mix_mode,
            input_device_id_2=audio_config.input_device_id_2,
            input_sample_rate_2=audio_config.input_sample_rate_2,
            input_channels_2=audio_config.input_channels_2
        )
        
        # 创建 Flask 应用
        app, socketio = create_app()
        
        # 创建 WebSocket 处理器
        ws_handler = WebSocketHandler(socketio, bridge)
        
        # Start audio bridge
        bridge.start()
        
        # Start WebSocket handler
        ws_handler.start()
        
        console.print("\n[bold green]Server started successfully![/bold green]")
        console.print(f"[cyan]Open in browser: http://localhost:{config.server.port}[/cyan]\n")
        
        # Start server with socket reuse options
        socketio.run(
            app,
            host=config.server.host,
            port=config.server.port,
            debug=config.server.debug,
            use_reloader=False,
            log_output=not config.server.debug,  # Production: disable detailed logging
            allow_unsafe_werkzeug=True  # Allow socket address reuse
        )
        
    except KeyboardInterrupt:
        signal_handler(None, None)
    except Exception as e:
        console.print(f"\n[bold red]{'=' * 50}[/bold red]")
        console.print(f"[bold red]Application Error[/bold red]")
        console.print(f"[bold red]{'=' * 50}[/bold red]")
        console.print(f"[red]Error Type: {type(e).__name__}[/red]")
        console.print(f"[red]Error Message: {e}[/red]")
        console.print()
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        
        # 错误退出时也清理临时文件 - 已禁用
        # from .utils.cleanup import cleanup_on_exit
        # cleanup_on_exit(verbose=False)
        raise
    finally:
        # 确保无论如何都清理资源
        if ws_handler:
            try:
                ws_handler.stop()
            except:
                pass
        if bridge:
            try:
                bridge.stop()
            except:
                pass


if __name__ == '__main__':
    main()