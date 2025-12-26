"""
WebSocket 处理器
"""
import threading
import time
import numpy as np
from typing import Dict, Set, Optional
from flask_socketio import SocketIO, emit, join_room, leave_room
from rich.console import Console

from ..audio.vb_cable_bridge import VBCableBridge
from ..audio.processor import AudioProcessor
from .app import add_audio_to_stream


console = Console()


class WebSocketHandler:
    """WebSocket 处理器"""
    
    def __init__(self, socketio: SocketIO, bridge: VBCableBridge):
        self.socketio = socketio
        self.bridge = bridge
        self.processor = AudioProcessor(bridge.browser_sample_rate, bridge.browser_channels)
        
        # 连接管理
        self.connected_clients: Set[str] = set()
        
        # 音频转发线程
        self.running = False
        self.forward_thread: Optional[threading.Thread] = None
        
        # 注册事件处理器
        self._register_handlers()
    
    def _register_handlers(self):
        """注册 WebSocket 事件处理器"""
        
        @self.socketio.on('connect')
        def handle_connect():
            from flask import request
            client_id = request.sid
            self.connected_clients.add(client_id)
            console.print(f"[green]客户端已连接: {client_id}[/green]")
            emit('connected', {'client_id': client_id})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            from flask import request
            client_id = request.sid
            self.connected_clients.discard(client_id)
            console.print(f"[yellow]客户端已断开: {client_id}[/yellow]")
        
        @self.socketio.on('audio_data')
        def handle_audio_data(data):
            """接收浏览器音频并转发到 Clubdeck"""
            try:
                audio_base64 = data.get('audio')
                if audio_base64:
                    # 解码音频
                    audio_array = self.processor.base64_to_numpy(audio_base64)
                    # 音频处理（降噪、滤波）
                    audio_array = self.processor.process_audio(audio_array)
                    # 发送到 VB-Cable (Clubdeck)
                    self.bridge.send_to_clubdeck(audio_array)
            except Exception as e:
                console.print(f"[red]处理音频数据错误: {e}[/red]")
        
        @self.socketio.on('join_room')
        def handle_join_room(data):
            room = data.get('room', 'default')
            join_room(room)
            emit('room_joined', {'room': room})
        
        @self.socketio.on('leave_room')
        def handle_leave_room(data):
            room = data.get('room', 'default')
            leave_room(room)
            emit('room_left', {'room': room})
    
    def _forward_clubdeck_audio(self):
        """转发 Clubdeck 音频到所有浏览器客户端"""
        while self.running:
            try:
                # 从 VB-Cable 获取 Clubdeck 音频
                audio_data = self.bridge.receive_from_clubdeck(timeout=0.05)
                
                if audio_data is not None:
                    # 音频处理（降噪、滤波）- 只处理单声道
                    if audio_data.ndim == 1:
                        audio_data = self.processor.process_audio(audio_data)
                    
                    # 同时推送到 HTTP 音频流（用于 iOS 后台播放）
                    add_audio_to_stream(audio_data)
                    
                    if len(self.connected_clients) > 0:
                        # 编码为 base64
                        audio_base64 = self.processor.numpy_to_base64(audio_data)
                        
                        # 广播到所有客户端
                        self.socketio.emit('audio_from_clubdeck', {
                            'audio': audio_base64,
                            'sample_rate': self.bridge.browser_sample_rate,
                            'channels': self.bridge.browser_channels
                        })
            except Exception as e:
                console.print(f"[red]转发音频错误: {e}[/red]")
            
            time.sleep(0.01)
    
    def start(self):
        """启动处理器"""
        if self.running:
            return
        
        self.running = True
        
        # 启动 Clubdeck 音频转发线程
        self.forward_thread = threading.Thread(target=self._forward_clubdeck_audio, daemon=True)
        self.forward_thread.start()
        
        console.print("[green]✓ WebSocket 处理器已启动[/green]")
    
    def stop(self):
        """停止处理器"""
        self.running = False
        
        if self.forward_thread:
            self.forward_thread.join(timeout=2)
            self.forward_thread = None
        
        console.print("[yellow]WebSocket 处理器已停止[/yellow]")
    
    @property
    def client_count(self) -> int:
        """获取连接的客户端数量"""
        return len(self.connected_clients)