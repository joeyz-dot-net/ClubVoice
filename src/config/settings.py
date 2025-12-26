"""
音频配置管理
"""
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


def get_config_path() -> Path:
    """获取配置文件路径"""
    # 打包后的exe路径
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent.parent.parent
    
    return base_path / 'config.json'


@dataclass
class AudioConfig:
    """音频配置"""
    input_device_id: Optional[int] = None   # Hi-Fi Cable Output (从 Clubdeck 接收，已包含 MPV 音乐)
    output_device_id: Optional[int] = None  # Hi-Fi Cable Input (发送浏览器音频到 Clubdeck)
    sample_rate: int = 48000                # 浏览器端采样率
    input_sample_rate: int = 48000          # 输入设备采样率
    output_sample_rate: int = 48000         # 输出设备采样率
    channels: int = 2                       # 浏览器端声道数（始终立体声）
    input_channels: int = 2                 # 输入设备声道数
    output_channels: int = 2                # 输出设备声道数
    chunk_size: int = 512                   # 减小缓冲区以降低延迟
    bitrate: int = 128000                   # 128kbps
    dtype: str = 'int16'                    # 数据类型
    duplex_mode: str = 'half'               # 通信模式: 'half' = 半双工, 'full' = 全双工


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = '0.0.0.0'
    port: int = 5000
    debug: bool = False


@dataclass
class AppConfig:
    """应用配置"""
    audio: AudioConfig = field(default_factory=AudioConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    
    def load_from_file(self, config_path: Optional[Path] = None) -> 'AppConfig':
        """从配置文件加载（仅加载服务器配置，音频参数由设备决定）"""
        if config_path is None:
            config_path = get_config_path()
        
        if not config_path.exists():
            print(f"[提示] 配置文件不存在: {config_path}，使用默认配置")
            return self
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 加载服务器配置
            if 'server' in data:
                server_data = data['server']
                self.server.host = server_data.get('host', self.server.host)
                self.server.port = server_data.get('port', self.server.port)
                self.server.debug = server_data.get('debug', self.server.debug)
            
            # 加载音频通信模式
            if 'audio' in data:
                audio_data = data['audio']
                self.audio.duplex_mode = audio_data.get('duplex_mode', 'half')
            
            print(f"[✓] 已从 {config_path} 加载服务器配置")
            
        except json.JSONDecodeError as e:
            print(f"[错误] 配置文件格式错误: {e}")
        except Exception as e:
            print(f"[错误] 加载配置文件失败: {e}")
        
        return self
    
    def update_audio_from_device(self, sample_rate: int, channels: int, 
                                    input_device_id: int = None, 
                                    output_device_id: int = None) -> None:
        """根据设备参数更新音频配置"""
        self.audio.sample_rate = sample_rate
        self.audio.channels = channels
        if input_device_id is not None:
            self.audio.input_device_id = input_device_id
        if output_device_id is not None:
            self.audio.output_device_id = output_device_id
        print(f"[✓] 音频参数已更新: {sample_rate}Hz, {channels}ch")
    
    def save_to_file(self, config_path: Optional[Path] = None) -> None:
        """保存配置到文件（仅保存服务器配置）"""
        if config_path is None:
            config_path = get_config_path()
        
        data = {
            'server': {
                'host': self.server.host,
                'port': self.server.port,
                'debug': self.server.debug
            }
        }
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"[✓] 配置已保存到 {config_path}")
        except Exception as e:
            print(f"[错误] 保存配置文件失败: {e}")


# 全局配置实例 - 自动加载配置文件
config = AppConfig().load_from_file()
