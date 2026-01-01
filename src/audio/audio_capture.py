#!/usr/bin/env python3
"""
ClubVoice Audio Capture Module

音频捕获模块，提供共享音频捕获功能，支持多客户端连接。
使用 sounddevice 进行音频捕获，支持实时音频处理和分发。
"""

import logging
import threading
import time
from typing import Dict, Set, Optional

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


class SharedAudioCapture:
    """共享音频捕获类 - 多客户端共享同一个音频源"""
    
    def __init__(self, device_id: int, sample_rate: int = 48000, channels: int = 2, chunk_size: int = 960, auto_start: bool = False):
        self.device_id = device_id
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.auto_start = auto_start
        
        # 音频流管理
        self.stream: Optional[sd.InputStream] = None
        self.is_running = False
        
        # 客户端连接管理
        self.frame_queues: Dict[str, list] = {}  # conn_id -> frame_queue
        self.connections: Set[str] = set()
        
        # 线程安全锁
        self.lock = threading.Lock()
        
        logger.info(f"初始化共享音频捕获: 设备{device_id}, {sample_rate}Hz, {channels}声道, 块大小{chunk_size}")
        
        # 如果启用自动开始，立即启动音频捕获
        if auto_start:
            self.add_connection("test_connection")
            logger.info("自动启动模式：已开始音频采集")
    
    def add_connection(self, conn_id: str):
        """添加新连接"""
        with self.lock:
            if conn_id not in self.connections:
                self.frame_queues[conn_id] = []
                self.connections.add(conn_id)
                logger.info(f"添加连接 {conn_id}, 当前连接数: {len(self.connections)}")
                
                # 如果是第一个连接，启动音频捕获
                if len(self.connections) == 1:
                    self._start_capture()
    
    def remove_connection(self, conn_id: str):
        """移除连接"""
        with self.lock:
            if conn_id in self.connections:
                self.connections.discard(conn_id)
                if conn_id in self.frame_queues:
                    del self.frame_queues[conn_id]
                logger.info(f"移除连接 {conn_id}, 当前连接数: {len(self.connections)}")
                
                # 如果没有连接了，停止音频捕获
                if len(self.connections) == 0:
                    self._stop_capture()
    
    def get_frame(self, conn_id: str) -> Optional[np.ndarray]:
        """获取指定连接的音频帧"""
        with self.lock:
            if conn_id in self.frame_queues and self.frame_queues[conn_id]:
                return self.frame_queues[conn_id].pop(0)
            return None
    
    def _audio_callback(self, indata, frames, time_info, status):
        """音频回调函数 - 在主线程中运行"""
        if status:
            print(f"音频回调状态: {status}")
            logger.warning(f"音频回调状态: {status}")
        
        # 简单的音频活动检测
        audio_level = np.abs(indata).mean()
        if audio_level > 0.001:  # 检测到音频信号
            print(f"\r检测到音频信号，电平: {audio_level:.6f}", end='', flush=True)
        
        # 转换为 int16 格式
        audio_data = (indata * 32767).astype(np.int16)
        
        # 确保是 chunk_size 的整数倍
        if len(audio_data) >= self.chunk_size:
            # 分割成 chunk_size 的块
            for i in range(0, len(audio_data) - self.chunk_size + 1, self.chunk_size):
                chunk = audio_data[i:i + self.chunk_size]
                
                # 分发到所有连接的队列
                with self.lock:
                    for conn_id in list(self.connections):
                        if conn_id in self.frame_queues:
                            # 限制队列长度防止内存泄露
                            if len(self.frame_queues[conn_id]) > 10:
                                self.frame_queues[conn_id].pop(0)
                            self.frame_queues[conn_id].append(chunk.copy())
    
    def _start_capture(self):
        """启动音频捕获 - 必须在主线程中调用"""
        if not self.is_running:
            try:
                print(f"启动音频捕获，设备ID: {self.device_id}")
                self.stream = sd.InputStream(
                    device=self.device_id,
                    channels=self.channels,
                    samplerate=self.sample_rate,
                    blocksize=self.chunk_size,
                    callback=self._audio_callback,
                    dtype=np.float32
                )
                self.stream.start()
                self.is_running = True
                print("✓ 音频捕获已启动")
                logger.info(f"音频捕获已启动 - 设备{self.device_id}, {self.sample_rate}Hz, {self.channels}声道")
            except Exception as e:
                print(f"✗ 启动音频捕获失败: {e}")
                logger.error(f"启动音频捕获失败: {e}")
                self.is_running = False
    
    def _stop_capture(self):
        """停止音频捕获"""
        if self.is_running and self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                self.stream = None
                self.is_running = False
                logger.info("音频捕获已停止")
            except Exception as e:
                logger.error(f"停止音频捕获失败: {e}")
    
    def get_connection_count(self) -> int:
        """获取当前连接数"""
        with self.lock:
            return len(self.connections)
    
    def cleanup(self):
        """清理资源"""
        self._stop_capture()
        with self.lock:
            self.connections.clear()
            self.frame_queues.clear()
        logger.info("音频捕获资源已清理")
    
    def is_active(self) -> bool:
        """检查音频捕获是否活跃"""
        return self.is_running and self.stream is not None
    
    def get_device_info(self) -> dict:
        """获取音频设备信息"""
        try:
            device_info = sd.query_devices(self.device_id)
            return {
                'device_id': self.device_id,
                'name': device_info['name'],
                'channels': self.channels,
                'sample_rate': self.sample_rate,
                'chunk_size': self.chunk_size,
                'max_input_channels': device_info['max_input_channels'],
                'max_output_channels': device_info['max_output_channels']
            }
        except Exception as e:
            logger.error(f"获取设备信息失败: {e}")
            return {
                'device_id': self.device_id,
                'error': str(e)
            }


class AudioCaptureManager:
    """音频捕获管理器 - 单例模式管理全局音频捕获"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized') or not self._initialized:
            self.capture: Optional[SharedAudioCapture] = None
            self._initialized = True
    
    def create_capture(self, device_id: int, sample_rate: int = 48000, 
                      channels: int = 2, chunk_size: int = 960, 
                      auto_start: bool = False) -> SharedAudioCapture:
        """创建或获取音频捕获实例"""
        if self.capture is None:
            self.capture = SharedAudioCapture(
                device_id=device_id,
                sample_rate=sample_rate,
                channels=channels,
                chunk_size=chunk_size,
                auto_start=auto_start
            )
        return self.capture
    
    def get_capture(self) -> Optional[SharedAudioCapture]:
        """获取当前音频捕获实例"""
        return self.capture
    
    def cleanup(self):
        """清理音频捕获"""
        if self.capture:
            self.capture.cleanup()
            self.capture = None


# 全局音频捕获管理器实例
audio_manager = AudioCaptureManager()