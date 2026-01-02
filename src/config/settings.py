"""
音频配置管理
"""
import configparser
import os
import sys
from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path


def get_config_path() -> Path:
    """获取配置文件路径"""
    # 打包后的exe路径
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent.parent.parent
    
    return base_path / 'config.ini'


@dataclass
class AudioConfig:
    """音频配置"""
    input_device_id: Optional[int] = None   # 第一个输入设备ID
    output_device_id: Optional[int] = None  # Hi-Fi Cable Input (发送浏览器音频到 Clubdeck)
    sample_rate: int = 48000                # 浏览器端采样率
    input_sample_rate: int = 48000          # 输入设备1采样率
    output_sample_rate: int = 48000         # 输出设备采样率
    channels: int = 2                       # 浏览器端声道数（始终立体声）
    input_channels: int = 2                 # 输入设备1声道数
    output_channels: int = 2                # 输出设备声道数
    chunk_size: int = 512                   # 减小缓冲区以降低延迟
    bitrate: int = 128000                   # 128kbps
    dtype: str = 'int16'                    # 数据类型
    duplex_mode: str = 'half'               # 通信模式: 'half' = 半双工, 'full' = 全双工
    # 混音模式参数
    mix_mode: bool = False                  # 是否启用混音模式
    input_device_id_2: Optional[int] = None # 第二个输入设备ID
    input_sample_rate_2: int = 48000        # 输入设备2采样率
    input_channels_2: int = 2               # 输入设备2声道数
    
    # 音频闪避配置
    ducking_enabled: bool = True
    ducking_threshold: float = 150.0
    ducking_gain: float = 0.15
    ducking_min_duration: float = 0.1
    ducking_release_time: float = 0.5
    ducking_transition_time: float = 0.1


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = '0.0.0.0'
    port: int = 5000
    debug: bool = False


@dataclass
class CorsConfig:
    """CORS 跨域配置"""
    enabled: bool = True
    allowed_origins: List[str] = field(default_factory=lambda: [
        'http://localhost:5000', 'http://127.0.0.1:5000'
    ])


@dataclass
class MPVConfig:
    """MPV 配置"""
    enabled: bool = True
    pipe_path: str = r'\\.\pipe\mpv-pipe'
    normal_volume: int = 100
    ducking_volume: int = 15
    transition_time: float = 0.1


@dataclass
class AppConfig:
    """应用配置"""
    audio: AudioConfig = field(default_factory=AudioConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    cors: CorsConfig = field(default_factory=CorsConfig)
    mpv: MPVConfig = field(default_factory=MPVConfig)
    
    def load_from_file(self, config_path: Optional[Path] = None) -> 'AppConfig':
        """从配置文件加载（仅加载服务器配置，音频参数由设备决定）"""
        if config_path is None:
            config_path = get_config_path()
        
        if not config_path.exists():
            print(f"[提示] 配置文件不存在: {config_path}，使用默认配置")
            return self
        
        try:
            parser = configparser.ConfigParser()
            parser.read(config_path, encoding='utf-8')
            
            # 加载服务器配置
            if 'server' in parser:
                self.server.host = parser.get('server', 'host', fallback=self.server.host)
                self.server.port = parser.getint('server', 'port', fallback=self.server.port)
                self.server.debug = parser.getboolean('server', 'debug', fallback=self.server.debug)
            
            # 加载音频通信模式和设备ID
            if 'audio' in parser:
                self.audio.duplex_mode = parser.get('audio', 'duplex_mode', fallback='half')
                input_device_id = parser.get('audio', 'input_device_id', fallback=None)
                if input_device_id is not None:
                    try:
                        self.audio.input_device_id = int(input_device_id)
                    except ValueError:
                        pass
                
                # 添加 output_device_id 读取
                output_device_id = parser.get('audio', 'output_device_id', fallback=None)
                if output_device_id is not None:
                    try:
                        self.audio.output_device_id = int(output_device_id)
                    except ValueError:
                        pass
                
                # 加载混音配置
                self.audio.mix_mode = parser.getboolean('audio', 'mix_mode', fallback=False)
                input_device_id_2 = parser.get('audio', 'input_device_id_2', fallback=None)
                if input_device_id_2 is not None:
                    try:
                        self.audio.input_device_id_2 = int(input_device_id_2)
                    except ValueError:
                        pass
                
                # 加载音频闪避配置
                self.audio.ducking_enabled = parser.getboolean('audio', 'ducking_enabled', fallback=True)
                self.audio.ducking_threshold = parser.getfloat('audio', 'ducking_threshold', fallback=150.0)
                self.audio.ducking_gain = parser.getfloat('audio', 'ducking_gain', fallback=0.15)
                self.audio.ducking_min_duration = parser.getfloat('audio', 'ducking_min_duration', fallback=0.1)
                self.audio.ducking_release_time = parser.getfloat('audio', 'ducking_release_time', fallback=0.5)
                self.audio.ducking_transition_time = parser.getfloat('audio', 'ducking_transition_time', fallback=0.1)
            
            # 加载 CORS 配置
            if 'cors' in parser:
                self.cors.enabled = parser.getboolean('cors', 'enabled', fallback=True)
                allowed_origins = parser.get('cors', 'allowed_origins', fallback='')
                if allowed_origins:
                    # 解析逗号分隔的域名列表
                    self.cors.allowed_origins = [
                        origin.strip() for origin in allowed_origins.split(',')
                        if origin.strip()
                    ]
            
            # 加载 MPV 配置
            if 'mpv' in parser:
                self.mpv.enabled = parser.getboolean('mpv', 'enabled', fallback=True)
                self.mpv.pipe_path = parser.get('mpv', 'default_pipe', fallback=r'\\.\pipe\mpv-pipe')
                self.mpv.normal_volume = parser.getint('mpv', 'normal_volume', fallback=100)
                self.mpv.ducking_volume = parser.getint('mpv', 'ducking_volume', fallback=15)
            
            print(f"[OK] Config loaded from {config_path}")
            
        except configparser.Error as e:
            print(f"[ERROR] Config file error: {e}")
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")
        
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
        
        parser = configparser.ConfigParser()
        
        # 服务器配置
        parser['server'] = {
            'host': self.server.host,
            'port': str(self.server.port),
            'debug': str(self.server.debug).lower()
        }
        
        # 音频配置
        audio_section = {
            'duplex_mode': self.audio.duplex_mode,
            'mix_mode': str(self.audio.mix_mode).lower(),
            'ducking_enabled': str(self.audio.ducking_enabled).lower(),
            'ducking_threshold': str(self.audio.ducking_threshold),
            'ducking_gain': str(self.audio.ducking_gain),
            'ducking_min_duration': str(self.audio.ducking_min_duration),
            'ducking_release_time': str(self.audio.ducking_release_time),
            'ducking_transition_time': str(self.audio.ducking_transition_time)
        }
        if self.audio.input_device_id is not None:
            audio_section['input_device_id'] = str(self.audio.input_device_id)
        
        # 添加 output_device_id 保存
        if self.audio.output_device_id is not None:
            audio_section['output_device_id'] = str(self.audio.output_device_id)
            
        if self.audio.input_device_id_2 is not None:
            audio_section['input_device_id_2'] = str(self.audio.input_device_id_2)
        
        parser['audio'] = audio_section
        
        # CORS配置 - 使用多行格式
        cors_origins = self.cors.allowed_origins
        if len(cors_origins) > 4:  # 如果域名较多，使用多行格式
            cors_origins_str = cors_origins[0]
            for origin in cors_origins[1:]:
                cors_origins_str += ',\n                  ' + origin
        else:
            cors_origins_str = ','.join(cors_origins)
        
        parser['cors'] = {
            'enabled': str(self.cors.enabled).lower(),
            'allowed_origins': cors_origins_str
        }
        
        # MPV配置（如果存在）
        parser['mpv'] = {
            'enabled': 'true',
            'default_pipe': '\\\\.\\pipe\\mpv-pipe',
            'ducking_volume': '15',
            'normal_volume': '100'
        }
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                parser.write(f)
                
            # Manual add CORS comment (configparser doesn't preserve comments)
            self._add_cors_comment(config_path)
                
            print(f"[OK] Config saved to {config_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save config: {e}")
    
    def _add_cors_comment(self, config_path: Path) -> None:
        """为CORS配置添加注释"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 在 [cors] 节添加注释
            content = content.replace(
                '[cors]\nenabled = ',
                '[cors]\n# 允许访问的域名列表\nenabled = '
            )
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception:
            # 忽略注释添加失败
            pass


# 全局配置实例 - 自动加载配置文件
config = AppConfig().load_from_file()
