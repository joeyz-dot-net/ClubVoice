"""
MPV 音乐播放器控制器
通过 named pipe 控制 MPV 音量，实现 Audio Ducking
"""
import os
import time
import threading
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class MPVConfig:
    """MPV 配置"""
    enabled: bool = True
    pipe_path: str = r'\\.\pipe\mpv-pipe'
    normal_volume: int = 100
    ducking_volume: int = 15
    transition_time: float = 0.1


class MPVController:
    """
    MPV 控制器
    通过 Windows Named Pipe 控制 MPV 音量
    """
    
    def __init__(self, config: MPVConfig):
        """
        Args:
            config: MPV 配置
        """
        self.config = config
        self.pipe_path = config.pipe_path
        self.normal_volume = config.normal_volume
        self.ducking_volume = config.ducking_volume
        self.transition_time = config.transition_time
        
        # 状态
        self.current_volume = self.normal_volume
        self.target_volume = self.normal_volume
        self.is_ducking = False
        self.pipe_handle = None
        self.pipe_lock = threading.Lock()
        
        # 音量平滑过渡线程
        self.transition_thread = None
        self.transition_active = False
        
        if config.enabled:
            self._test_connection()
    
    def _test_connection(self):
        """Test MPV pipe connection"""
        try:
            self._send_command('{ "command": ["get_property", "volume"] }')
            print(f"[MPV] * Connected to MPV pipe: {self.pipe_path}")
        except Exception as e:
            print(f"[MPV] ! Cannot connect to MPV: {e}")
            print(f"[MPV] Hint: Enable IPC in MPV: --input-ipc-server={self.pipe_path}")
    
    def _send_command(self, command: str, retry: int = 3) -> bool:
        """
        发送命令到 MPV
        
        Args:
            command: JSON 格式的命令
            retry: 重试次数
            
        Returns:
            是否成功
        """
        for attempt in range(retry):
            try:
                # Windows Named Pipe 使用文件方式打开
                with open(self.pipe_path, 'w', encoding='utf-8') as pipe:
                    pipe.write(command + '\n')
                    pipe.flush()
                return True
                
            except FileNotFoundError:
                if attempt == 0:
                    # 只在第一次失败时提示
                    pass
                return False
                
            except Exception as e:
                if attempt == retry - 1:
                    print(f"[MPV] Command failed: {e}")
                time.sleep(0.1)
        
        return False
    
    def set_volume(self, volume: int) -> bool:
        """
        设置 MPV 音量
        
        Args:
            volume: 音量 (0-100)
            
        Returns:
            是否成功
        """
        volume = max(0, min(100, volume))
        command = f'{{"command": ["set_property", "volume", {volume}]}}'
        
        if self._send_command(command):
            self.current_volume = volume
            return True
        return False
    
    def set_ducking(self, should_duck: bool):
        """
        设置是否启用音频闪避
        
        Args:
            should_duck: True = 降低音量，False = 恢复音量
        """
        if not self.config.enabled:
            return
        
        new_target = self.ducking_volume if should_duck else self.normal_volume
        
        if new_target != self.target_volume:
            self.target_volume = new_target
            self.is_ducking = should_duck
            
            # 启动平滑过渡
            self._start_volume_transition()
    
    def _start_volume_transition(self):
        """启动音量平滑过渡线程"""
        if self.transition_thread and self.transition_thread.is_alive():
            # 已有过渡在进行，更新目标即可
            return
        
        self.transition_active = True
        self.transition_thread = threading.Thread(
            target=self._volume_transition_worker,
            daemon=True
        )
        self.transition_thread.start()
    
    def _volume_transition_worker(self):
        """音量过渡工作线程"""
        step_interval = 0.02  # 20ms 一步
        steps = int(self.transition_time / step_interval)
        
        while self.transition_active:
            if abs(self.current_volume - self.target_volume) < 1:
                # 已到达目标
                if self.current_volume != self.target_volume:
                    self.set_volume(self.target_volume)
                break
            
            # 计算步进
            diff = self.target_volume - self.current_volume
            step = diff / max(steps, 1)
            new_volume = int(self.current_volume + step)
            
            # 更新音量
            self.set_volume(new_volume)
            time.sleep(step_interval)
        
        self.transition_active = False
    
    def get_current_volume(self) -> int:
        """获取当前音量"""
        return self.current_volume
    
    def is_enabled(self) -> bool:
        """是否启用 MPV 控制"""
        return self.config.enabled
    
    def stop(self):
        """停止控制器"""
        self.transition_active = False
        if self.transition_thread:
            self.transition_thread.join(timeout=1.0)
        
        # Restore normal volume
        if self.config.enabled and self.current_volume != self.normal_volume:
            self.set_volume(self.normal_volume)
            print("[MPV] Volume restored")
