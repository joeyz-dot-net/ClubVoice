#!/usr/bin/env python3
"""
WebSocket 连接诊断脚本
用于测试修复后的 Flask-SocketIO 连接
"""
import sys
import time
from pathlib import Path
import subprocess
import requests
from rich.console import Console

console = Console()

def test_websocket_fix():
    """测试 WebSocket 连接修复"""
    
    console.print("[bold cyan]ClubVoice WebSocket 修复诊断[/bold cyan]\n")
    
    # 启动应用
    console.print("[yellow]1. 启动应用服务器...[/yellow]")
    process = subprocess.Popen(
        [sys.executable, 'server_test_simple.py'],
        cwd=Path(__file__).parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # 等待服务器启动
    console.print("[yellow]2. 等待服务器启动 (5 秒)...[/yellow]")
    time.sleep(5)
    
    try:
        # 测试 HTTP 健康检查
        console.print("[yellow]3. 测试 HTTP 健康检查...[/yellow]")
        try:
            response = requests.get('http://localhost:5000/health', timeout=5)
            if response.status_code == 200:
                console.print(f"   [green]✓ 健康检查通过: {response.json()}[/green]")
            else:
                console.print(f"   [red]✗ 健康检查失败: {response.status_code}[/red]")
        except Exception as e:
            console.print(f"   [red]✗ 健康检查错误: {e}[/red]")
        
        # 测试主页加载
        console.print("[yellow]4. 测试主页加载...[/yellow]")
        try:
            response = requests.get('http://localhost:5000/', timeout=5)
            if response.status_code == 200:
                console.print(f"   [green]✓ 主页加载成功 ({len(response.text)} bytes)[/green]")
            else:
                console.print(f"   [red]✗ 主页加载失败: {response.status_code}[/red]")
        except Exception as e:
            console.print(f"   [red]✗ 主页加载错误: {e}[/red]")
        
        # 测试 Socket.IO 连接
        console.print("[yellow]5. 测试 Socket.IO WebSocket 连接...[/yellow]")
        try:
            # 尝试建立 WebSocket 连接
            import socketio
            sio = socketio.Client()
            
            @sio.event
            def connect():
                console.print("   [green]✓ WebSocket 连接成功![/green]")
            
            @sio.event
            def disconnect():
                console.print("   [yellow]WebSocket 已断开[/yellow]")
            
            @sio.on('*')
            def catch_all(event, *args):
                console.print(f"   [dim]接收事件: {event}[/dim]")
            
            # 连接
            console.print("   正在建立 WebSocket 连接...")
            sio.connect('http://localhost:5000', transports=['websocket', 'polling'])
            time.sleep(2)
            sio.disconnect()
            
        except Exception as e:
            console.print(f"   [red]✗ WebSocket 连接失败: {e}[/red]")
        
        console.print("\n[bold green]✅ 诊断完成[/bold green]")
        return 0
        
    finally:
        # 停止服务器
        console.print("\n[yellow]6. 停止服务器...[/yellow]")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        console.print("[green]服务器已停止[/green]")

if __name__ == '__main__':
    try:
        sys.exit(test_websocket_fix())
    except KeyboardInterrupt:
        console.print("\n[yellow]诊断已中止[/yellow]")
        sys.exit(1)
