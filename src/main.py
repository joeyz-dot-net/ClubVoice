"""
主入口
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


console = Console()

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
            browser_sample_rate=audio_config.sample_rate,
            input_sample_rate=audio_config.input_sample_rate,
            input_channels=audio_config.input_channels,
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
            use_reloader=False,
            log_output=not config.server.debug  # 生产环境关闭详细日志
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