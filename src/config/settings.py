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
    input_device_id: Optional[int] = None   # VB-Cable Output (从Clubdeck接收)
    output_device_id: Optional[int] = None  # VB-Cable Input (发送到Clubdeck)
    sample_rate: int = 48000                # 采样率 48kHz
    channels: int = 2                       # 立体声
    chunk_size: int = 512                   # 减小缓冲区以降低延迟
    bitrate: int = 128000                   # 128kbps
    dtype: str = 'int16'                    # 数据类型


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
        """从配置文件加载"""
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
            
            # 加载音频配置
            if 'audio' in data:
                audio_data = data['audio']
                self.audio.sample_rate = audio_data.get('sample_rate', self.audio.sample_rate)
                self.audio.channels = audio_data.get('channels', self.audio.channels)
                self.audio.bitrate = audio_data.get('bitrate', self.audio.bitrate)
                self.audio.chunk_size = audio_data.get('chunk_size', self.audio.chunk_size)
            
            print(f"[✓] 已从 {config_path} 加载配置")
            
        except json.JSONDecodeError as e:
            print(f"[错误] 配置文件格式错误: {e}")
        except Exception as e:
            print(f"[错误] 加载配置文件失败: {e}")
        
        return self
    
    def save_to_file(self, config_path: Optional[Path] = None) -> None:
        """保存配置到文件"""
        if config_path is None:
            config_path = get_config_path()
        
        data = {
            'server': {
                'host': self.server.host,
                'port': self.server.port,
                'debug': self.server.debug
            },
            'audio': {
                'sample_rate': self.audio.sample_rate,
                'channels': self.audio.channels,
                'bitrate': self.audio.bitrate,
                'chunk_size': self.audio.chunk_size
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
