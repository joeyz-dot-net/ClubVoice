"""
语音活动检测器 (VAD) - 用于 Audio Ducking
检测 Clubdeck 房间中是否有人说话
"""
import numpy as np
from typing import Optional
from dataclasses import dataclass


@dataclass
class VoiceDetectionConfig:
    """语音检测配置"""
    threshold: float = 150.0          # RMS 阈值（int16 范围：0-32768）
    min_duration: float = 0.1         # 最小持续时间（秒）- 避免误触发
    release_time: float = 0.5         # 释放时间（秒）- 语音停止后多久恢复音量
    smooth_frames: int = 3            # 平滑帧数 - 避免频繁切换


class VoiceActivityDetector:
    """
    语音活动检测器
    用于检测 VB-Cable A（Clubdeck 房间）中的语音活动
    """
    
    def __init__(self, sample_rate: int = 48000, config: Optional[VoiceDetectionConfig] = None):
        """
        Args:
            sample_rate: 采样率
            config: 检测配置
        """
        self.sample_rate = sample_rate
        self.config = config or VoiceDetectionConfig()
        
        # 状态跟踪
        self.is_voice_active = False
        self.active_frames = 0      # 连续活跃帧数
        self.silent_frames = 0      # 连续静音帧数
        
        # 计算帧数阈值（假设每帧 512 samples）
        samples_per_frame = 512
        self.min_active_frames = max(1, int(
            self.config.min_duration * sample_rate / samples_per_frame
        ))
        self.release_frames = max(1, int(
            self.config.release_time * sample_rate / samples_per_frame
        ))
        
        print(f"[VAD] 初始化 - 阈值: {self.config.threshold}, "
              f"最小持续: {self.config.min_duration}s, "
              f"释放时间: {self.config.release_time}s")
    
    def detect(self, audio_data: np.ndarray) -> bool:
        """
        检测音频帧中是否有语音活动
        
        Args:
            audio_data: int16 格式的音频数据（可以是立体声或单声道）
            
        Returns:
            True 如果检测到语音活动
        """
        # 计算 RMS（均方根）音量
        rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
        
        # 判断是否超过阈值
        if rms > self.config.threshold:
            self.active_frames += 1
            self.silent_frames = 0
            
            # 达到最小持续帧数才认为是有效语音
            if self.active_frames >= self.min_active_frames:
                if not self.is_voice_active:
                    self.is_voice_active = True
                    print(f"[VAD] 🔊 检测到语音 (RMS: {rms:.1f})")
        else:
            self.active_frames = 0
            self.silent_frames += 1
            
            # 静音时间超过释放时间才关闭检测
            if self.silent_frames >= self.release_frames:
                if self.is_voice_active:
                    self.is_voice_active = False
                    print(f"[VAD] 🔇 语音停止")
        
        return self.is_voice_active
    
    def get_status(self) -> dict:
        """获取检测器状态信息"""
        return {
            'active': self.is_voice_active,
            'active_frames': self.active_frames,
            'silent_frames': self.silent_frames,
            'threshold': self.config.threshold
        }
    
    def reset(self):
        """重置检测器状态"""
        self.is_voice_active = False
        self.active_frames = 0
        self.silent_frames = 0
        print("[VAD] 检测器已重置")
