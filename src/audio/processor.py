"""
音频处理器
"""
import numpy as np
from typing import Optional
import base64


class AudioProcessor:
    """音频处理器"""
    
    def __init__(self, sample_rate: int = 48000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        # 降噪参数
        self.noise_threshold = 150  # 噪声门限
        self.noise_floor = np.zeros(512, dtype=np.float32)  # 噪声底噪估计
        self.noise_alpha = 0.98  # 噪声估计平滑系数
    
    def denoise(self, audio: np.ndarray) -> np.ndarray:
        """简单降噪 - 噪声门限"""
        audio_float = audio.astype(np.float32)
        
        # 计算RMS能量
        rms = np.sqrt(np.mean(audio_float ** 2))
        
        # 如果低于门限，大幅衰减
        if rms < self.noise_threshold:
            audio_float *= 0.1  # 衰减 90%
        
        return np.clip(audio_float, -32768, 32767).astype(np.int16)
    
    def highpass_filter(self, audio: np.ndarray, cutoff: float = 80.0) -> np.ndarray:
        """简单高通滤波 - 去除低频噪声"""
        if len(audio) < 3:
            return audio
        
        audio_float = audio.astype(np.float32)
        
        # 一阶高通滤波器
        rc = 1.0 / (2.0 * np.pi * cutoff)
        dt = 1.0 / self.sample_rate
        alpha = rc / (rc + dt)
        
        filtered = np.zeros_like(audio_float)
        filtered[0] = audio_float[0]
        
        for i in range(1, len(audio_float)):
            filtered[i] = alpha * (filtered[i-1] + audio_float[i] - audio_float[i-1])
        
        return np.clip(filtered, -32768, 32767).astype(np.int16)
    
    def process_audio(self, audio: np.ndarray) -> np.ndarray:
        """完整的音频处理流水线"""
        # 1. 高通滤波去除低频噪声
        audio = self.highpass_filter(audio, cutoff=100.0)
        # 2. 降噪
        audio = self.denoise(audio)
        return audio
    
    def bytes_to_numpy(self, audio_bytes: bytes) -> np.ndarray:
        """将字节数据转换为 numpy 数组"""
        return np.frombuffer(audio_bytes, dtype=np.int16)
    
    def numpy_to_bytes(self, audio_array: np.ndarray) -> bytes:
        """将 numpy 数组转换为字节数据"""
        return audio_array.astype(np.int16).tobytes()
    
    def base64_to_numpy(self, audio_base64: str) -> np.ndarray:
        """将 base64 编码的音频转换为 numpy 数组"""
        audio_bytes = base64.b64decode(audio_base64)
        return self.bytes_to_numpy(audio_bytes)
    
    def numpy_to_base64(self, audio_array: np.ndarray) -> str:
        """将 numpy 数组转换为 base64 编码"""
        audio_bytes = self.numpy_to_bytes(audio_array)
        return base64.b64encode(audio_bytes).decode('utf-8')
    
    def normalize(self, audio: np.ndarray, target_level: float = 0.8) -> np.ndarray:
        """归一化音频电平"""
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            return (audio / max_val * target_level * 32767).astype(np.int16)
        return audio
    
    def apply_gain(self, audio: np.ndarray, gain_db: float) -> np.ndarray:
        """应用增益"""
        gain_linear = 10 ** (gain_db / 20)
        result = audio.astype(np.float32) * gain_linear
        return np.clip(result, -32768, 32767).astype(np.int16)
    
    def mix_audio(self, *audio_arrays: np.ndarray) -> np.ndarray:
        """混合多个音频流"""
        if not audio_arrays:
            return np.array([], dtype=np.int16)
        
        # 找到最短的数组长度
        min_length = min(len(a) for a in audio_arrays)
        
        # 混合
        mixed = np.zeros(min_length, dtype=np.float32)
        for audio in audio_arrays:
            mixed += audio[:min_length].astype(np.float32)
        
        # 防止削波
        mixed = mixed / len(audio_arrays)
        return np.clip(mixed, -32768, 32767).astype(np.int16)
    
    def resample(self, audio: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
        """简单重采样"""
        if orig_rate == target_rate:
            return audio
        
        ratio = target_rate / orig_rate
        new_length = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, new_length)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.int16)