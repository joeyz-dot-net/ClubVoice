#!/usr/bin/env python3
"""
简单的测试服务器 - 不需要音频设备
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.server.app import create_app
from src.server.websocket_handler import WebSocketHandler
from src.audio.processor import AudioProcessor
from rich.console import Console

console = Console()

def main():
    """启动测试服务器"""
    try:
        console.print("[cyan]启动 WebSocket 测试服务器...[/cyan]")
        
        # 创建应用
        app, socketio = create_app()
        
        # 创建假的音频处理器（无需实际设备）
        processor = AudioProcessor()
        
        # 创建 WebSocket 处理器（无音频桥接）
        handler = WebSocketHandler(socketio, bridge=None, processor=processor)
        
        console.print("[green]✓ 服务器已准备好[/green]")
        console.print("[cyan]访问: http://localhost:5000[/cyan]\n")
        
        # 运行服务器
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,
            debug=False,
            use_reloader=False,
            allow_unsafe_werkzeug=True
        )
        
    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
