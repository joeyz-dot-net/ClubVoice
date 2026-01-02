"""
音频闪避控制器 (Audio Ducker)
当检测到 Clubdeck 语音时，自动降低音乐音量
"""
import numpy as np


class AudioDucker:
    """
    音频闪避控制器
    用于控制 VB-Cable B（音乐）的音量
    """
    
    def __init__(self, 
                 sample_rate: int = 48000,
                 normal_gain: float = 1.0,      # 正常音量（100%）
                 ducked_gain: float = 0.15,     # 闪避音量（15%）
                 transition_time: float = 0.1): # 音量变化过渡时间
        """
        Args:
            sample_rate: 采样率
            normal_gain: 正常音量增益（0.0-1.0）
            ducked_gain: 降低后的音量增益（0.0-1.0）
            transition_time: 音量变化过渡时间（秒）
        """
        self.sample_rate = sample_rate
        self.normal_gain = normal_gain
        self.ducked_gain = ducked_gain
        self.transition_time = transition_time
        
        # 当前增益状态
        self.current_gain = normal_gain
        self.target_gain = normal_gain
        
        # 计算每帧的增益变化量（假设 512 samples/frame）
        samples_per_frame = 512
        frames_per_transition = max(1, int(
            transition_time * sample_rate / samples_per_frame
        ))
        self.gain_step = abs(normal_gain - ducked_gain) / frames_per_transition
        
        print(f"[Ducker] 初始化 - 正常: {int(normal_gain*100)}%, "
              f"闪避: {int(ducked_gain*100)}%, "
              f"过渡: {transition_time}s")
    
    def set_ducking(self, should_duck: bool):
        """
        设置是否启用闪避
        
        Args:
            should_duck: True = 降低音量（有语音），False = 恢复音量（无语音）
        """
        new_target = self.ducked_gain if should_duck else self.normal_gain
        
        if new_target != self.target_gain:
            self.target_gain = new_target
            action = "降低" if should_duck else "恢复"
            print(f"[Ducker] {action}音量 → {int(new_target*100)}%")
    
    def process(self, audio_data: np.ndarray) -> np.ndarray:
        """
        处理音频数据，应用音量闪避
        
        Args:
            audio_data: 输入音频数据（int16 或 float32）
            
        Returns:
            处理后的音频数据（保持输入类型）
        """
        # 平滑过渡到目标增益
        if abs(self.current_gain - self.target_gain) > 0.001:
            if self.current_gain < self.target_gain:
                # 增加音量
                self.current_gain = min(
                    self.current_gain + self.gain_step, 
                    self.target_gain
                )
            else:
                # 降低音量
                self.current_gain = max(
                    self.current_gain - self.gain_step, 
                    self.target_gain
                )
        
        # 应用增益
        if audio_data.dtype == np.int16:
            # int16: 转换为 float，应用增益，转回 int16
            float_data = audio_data.astype(np.float32) / 32768.0
            float_data *= self.current_gain
            # 防止溢出
            np.clip(float_data, -1.0, 1.0, out=float_data)
            return (float_data * 32767).astype(np.int16)
        else:
            # float32: 直接应用增益
            result = audio_data * self.current_gain
            np.clip(result, -1.0, 1.0, out=result)
            return result
    
    def get_current_gain(self) -> float:
        """获取当前增益值（0.0-1.0）"""
        return self.current_gain
    
    def get_current_gain_percent(self) -> int:
        """获取当前增益百分比（0-100）"""
        return int(self.current_gain * 100)
    
    def reset(self):
        """重置到正常音量"""
        self.current_gain = self.normal_gain
        self.target_gain = self.normal_gain
        print("[Ducker] 音量已重置")
