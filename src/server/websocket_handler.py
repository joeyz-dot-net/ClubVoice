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
from ..config.settings import config
from .app import add_audio_to_stream


console = Console()


# 全局连接数变量（用于 /status 端点）
_global_connection_count = 0


def get_connection_count() -> int:
    """获取当前连接数"""
    global _global_connection_count
    return _global_connection_count


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
        
        # 服务端 Ducking (闪避) - 麦克风说话时降低接收音量
        self.ducking_enabled = config.audio.browser_ducking_enabled  # 从配置读取
        self.ducking_volume = config.audio.ducking_gain   # 说话时的最低音量
        self.ducking_threshold = config.audio.ducking_threshold  # 音量阈值
        self.is_speaking = False      # 当前是否在说话
        self.speaking_decay = 0       # 说话状态衰减计数
        # 使用配置的release_time计算衰减上限 (约100帧/秒)
        self.speaking_decay_max = int(config.audio.ducking_release_time * 100)
        self._ducking_lock = threading.Lock()
        
        # 平滑过渡参数
        self.current_volume = 1.0     # 当前音量系数 (0.0 ~ 1.0)
        self.target_volume = 1.0      # 目标音量系数
        self.volume_smooth_speed = config.audio.ducking_transition_time  # 音量变化速度
        
        # 注册事件处理器
        self._register_handlers()
    
    def _register_handlers(self):
        """注册 WebSocket 事件处理器"""
        
        @self.socketio.on('connect')
        def handle_connect():
            global _global_connection_count
            try:
                from flask import request
                client_id = request.sid
                self.connected_clients.add(client_id)
                _global_connection_count = len(self.connected_clients)
                # 连接日志已集成到音量显示行（👤客户端数）
                # 发送连接确认和当前配置
                emit('connected', {
                    'client_id': client_id,
                    'duplex_mode': config.audio.duplex_mode
                })
            except Exception as e:
                console.print(f"[red]Connection handler error: {e}[/red]")
                import traceback
                traceback.print_exc()
        
        @self.socketio.on('get_config')
        def handle_get_config():
            """返回当前服务器配置"""
            emit('config', {
                'duplex_mode': config.audio.duplex_mode
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect(reason=None):
            global _global_connection_count
            try:
                from flask import request
                client_id = request.sid
                self.connected_clients.discard(client_id)
                _global_connection_count = len(self.connected_clients)
                # 断开日志已集成到音量显示行（👤客户端数）
            except Exception as e:
                console.print(f"[red]Disconnection handler error: {e}[/red]")
        
        @self.socketio.on('audio_data')
        def handle_audio_data(data):
            """接收浏览器音频并转发到 Clubdeck"""
            # 半双工模式下忽略浏览器麦克风
            if config.audio.duplex_mode == 'half':
                console.print(f"[dim red]Half-duplex mode, ignoring browser audio[/dim red]")
                return
            
            try:
                audio_base64 = data.get('audio')
                if audio_base64:
                    # 解码音频
                    audio_array = self.processor.base64_to_numpy(audio_base64)
                    max_amplitude = np.max(np.abs(audio_array))
                    
                    # 计算音量百分比（RMS）
                    rms = np.sqrt(np.mean((audio_array.astype(np.float32) / 32768.0) ** 2))
                    mic_volume = min(100.0, rms * 100.0 * 10.0)
                    
                    # 实时音量监控显示（每10帧显示一次）
                    if not hasattr(self, '_frame_counter'):
                        self._frame_counter = 0
                    self._frame_counter += 1
                    
                    if self._frame_counter % 10 == 0:
                        # 创建音量条
                        bar_width = 20
                        filled = int(mic_volume / 100.0 * bar_width)
                        bar = '█' * filled + '░' * (bar_width - filled)
                        console.print(f"[dim cyan]🎤 Mic: [{bar}] {mic_volume:5.1f}%[/dim cyan]", end='\r')
                    
                    # 检测是否在说话（用于 ducking）
                    if self.ducking_enabled:
                        with self._ducking_lock:
                            if max_amplitude > self.ducking_threshold:
                                if not self.is_speaking:
                                    console.print(f"[yellow]🔇 Ducking ON (amp={max_amplitude:.0f})[/yellow]")
                                self.is_speaking = True
                                self.speaking_decay = self.speaking_decay_max
                    
                    # 音频处理（降噪、滤波）
                    audio_array = self.processor.process_audio(audio_array)
                    # 发送到 VB-Cable (Clubdeck)
                    self.bridge.send_to_clubdeck(audio_array)
            except Exception as e:
                console.print(f"[red]Audio data processing error: {e}[/red]")
        
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
                    
                    # 应用 Ducking (闪避) - 说话时降低音量（平滑过渡）
                    if self.ducking_enabled:
                        with self._ducking_lock:
                            if self.speaking_decay > 0:
                                self.speaking_decay -= 1
                                self.target_volume = self.ducking_volume
                            else:
                                self.is_speaking = False
                                self.target_volume = 1.0
                            
                            # 平滑过渡到目标音量
                            if self.current_volume < self.target_volume:
                                self.current_volume = min(
                                    self.current_volume + self.volume_smooth_speed,
                                    self.target_volume
                                )
                            elif self.current_volume > self.target_volume:
                                self.current_volume = max(
                                    self.current_volume - self.volume_smooth_speed,
                                    self.target_volume
                                )
                            
                            # 应用当前音量
                            if self.current_volume < 1.0:
                                audio_data = (audio_data.astype(np.float32) * self.current_volume).astype(np.int16)
                    
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
                console.print(f"[red]Audio forwarding error: {e}[/red]")
            
            time.sleep(0.01)
    
    def start(self):
        """启动处理器"""
        if self.running:
            return
        
        self.running = True
        
        # 启动 Clubdeck 音频转发线程
        self.forward_thread = threading.Thread(target=self._forward_clubdeck_audio, daemon=True)
        self.forward_thread.start()
        
        # 显示 Browser Ducking 配置
        if self.ducking_enabled:
            console.print(f"[cyan]* Browser Ducking: enabled (threshold={self.ducking_threshold}, volume={self.ducking_volume*100:.0f}%)[/cyan]")
        else:
            console.print("[dim]* Browser Ducking: disabled[/dim]")
        
        console.print("[green]* WebSocket handler started[/green]")
    
    def stop(self):
        """停止处理器"""
        self.running = False
        
        if self.forward_thread:
            self.forward_thread.join(timeout=2)
            self.forward_thread = None
        
        # 清理所有客户端连接
        self.connected_clients.clear()
        
        # 重置状态
        self.is_speaking = False
        self.speaking_decay = 0
        self.current_volume = 1.0
        self.target_volume = 1.0
        
        console.print("[yellow]WebSocket handler stopped[/yellow]")
    
    @property
    def client_count(self) -> int:
        """获取连接的客户端数量"""
        return len(self.connected_clients)