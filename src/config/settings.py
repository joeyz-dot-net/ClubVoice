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
    """音频配置 - 3-Cable VB-Cable 架构"""
    # === 3-Cable 架构设备配置 ===
    # CABLE-C Output: Clubdeck 房间音频 → Python (读取)
    clubdeck_input_device_id: Optional[int] = None
    clubdeck_sample_rate: int = 48000
    clubdeck_channels: int = 2
    
    # CABLE-B Output: MPV 音乐 → Python (读取)
    mpv_input_device_id: Optional[int] = None
    mpv_sample_rate: int = 48000
    mpv_channels: int = 2
    
    # CABLE-A Input: 浏览器麦克风 → Clubdeck (写入)
    browser_output_device_id: Optional[int] = None
    browser_output_sample_rate: int = 48000
    browser_output_channels: int = 2
    
    # === 通用配置 ===
    sample_rate: int = 48000                # Python 内部处理采样率
    channels: int = 2                       # Python 内部处理声道数
    chunk_size: int = 512                   # 缓冲区大小
    bitrate: int = 128000                   # 128kbps
    dtype: str = 'int16'                    # 数据类型
    duplex_mode: str = 'full'               # 通信模式: 'half' = 半双工, 'full' = 全双工
    mix_mode: bool = True                   # 是否启用混音模式 (3-Cable 架构默认开启)
    
    # 音频闪避配置
    mpv_ducking_enabled: bool = True        # Clubdeck 房间语音降低 MPV 音乐音量
    browser_ducking_enabled: bool = True    # 浏览器麦克风降低 Clubdeck 接收音量
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
            
            # 加载音频通信模式
            if 'audio' in parser:
                self.audio.duplex_mode = parser.get('audio', 'duplex_mode', fallback='full')
                self.audio.mix_mode = parser.getboolean('audio', 'mix_mode', fallback=True)
            
            # 从 VAD Browser 节读取浏览器闪避配置
            if 'VAD Browser' in parser:
                self.audio.browser_ducking_enabled = parser.getboolean('VAD Browser', 'browser_ducking_enabled', fallback=False)
                self.audio.ducking_threshold = parser.getfloat('VAD Browser', 'ducking_threshold', fallback=150.0)
                self.audio.ducking_gain = parser.getfloat('VAD Browser', 'ducking_gain', fallback=0.15)
            
            # 从 VAD MPV 节读取 MPV 闪避配置
            if 'VAD MPV' in parser:
                self.audio.mpv_ducking_enabled = parser.getboolean('VAD MPV', 'mpv_ducking_enabled', fallback=True)
                self.audio.ducking_min_duration = parser.getfloat('VAD MPV', 'ducking_min_duration', fallback=0.1)
                self.audio.ducking_release_time = parser.getfloat('VAD MPV', 'ducking_release_time', fallback=0.5)
                self.audio.ducking_transition_time = parser.getfloat('VAD MPV', 'ducking_transition_time', fallback=0.1)
            
            # 加载 VB Cable 设备配置 (3-Cable 架构)
            if 'VB Cable' in parser:
                clubdeck_id = parser.get('VB Cable', 'clubdeck_input_device_id', fallback=None)
                if clubdeck_id is not None:
                    try:
                        self.audio.clubdeck_input_device_id = int(clubdeck_id)
                    except ValueError:
                        pass
                
                mpv_id = parser.get('VB Cable', 'mpv_input_device_id', fallback=None)
                if mpv_id is not None:
                    try:
                        self.audio.mpv_input_device_id = int(mpv_id)
                    except ValueError:
                        pass
                
                browser_out_id = parser.get('VB Cable', 'browser_output_device_id', fallback=None)
                if browser_out_id is not None:
                    try:
                        self.audio.browser_output_device_id = int(browser_out_id)
                    except ValueError:
                        pass
            
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
            
            # 从 VAD MPV 节读取 ducking 音量配置
            if 'VAD MPV' in parser:
                self.mpv.normal_volume = parser.getint('VAD MPV', 'normal_volume', fallback=100)
                self.mpv.ducking_volume = parser.getint('VAD MPV', 'ducking_volume', fallback=15)
            
            print(f"[OK] Config loaded from {config_path}")
            
        except configparser.Error as e:
            print(f"[ERROR] Config file error: {e}")
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")
        
        return self
    
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
            'mpv_ducking_enabled': str(self.audio.mpv_ducking_enabled).lower(),
            'browser_ducking_enabled': str(self.audio.browser_ducking_enabled).lower(),
            'ducking_threshold': str(self.audio.ducking_threshold),
            'ducking_gain': str(self.audio.ducking_gain),
            'ducking_min_duration': str(self.audio.ducking_min_duration),
            'ducking_release_time': str(self.audio.ducking_release_time),
            'ducking_transition_time': str(self.audio.ducking_transition_time)
        }
        
        # 保存 3-Cable 设备配置
        if self.audio.clubdeck_input_device_id is not None:
            audio_section['clubdeck_input_device_id'] = str(self.audio.clubdeck_input_device_id)
        if self.audio.mpv_input_device_id is not None:
            audio_section['mpv_input_device_id'] = str(self.audio.mpv_input_device_id)
        if self.audio.browser_output_device_id is not None:
            audio_section['browser_output_device_id'] = str(self.audio.browser_output_device_id)
        
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
    
    def update_device_ids_in_file(self, config_path: Optional[Path] = None) -> None:
        """
        仅更新配置文件中的设备ID，保留其他内容和注释
        """
        import re
        
        if config_path is None:
            config_path = get_config_path()
        
        if not config_path.exists():
            print(f"[ERROR] Config file not found: {config_path}")
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 定义要更新的设备ID字段及其新值
            updates = {
                'clubdeck_input_device_id': self.audio.clubdeck_input_device_id,
                'mpv_input_device_id': self.audio.mpv_input_device_id,
                'browser_output_device_id': self.audio.browser_output_device_id,
            }
            
            # 逐个替换设备ID
            for key, value in updates.items():
                if value is not None:
                    # 匹配 key = 任意数字 (可能有空格)
                    pattern = rf'^(\s*{key}\s*=\s*)\d+(.*)$'
                    replacement = rf'\g<1>{value}\g<2>'
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"[OK] Device IDs updated in {config_path}")
        except Exception as e:
            print(f"[ERROR] Failed to update device IDs: {e}")


# 全局配置实例 - 自动加载配置文件
config = AppConfig().load_from_file()
