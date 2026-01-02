
"""
VB-Cable 音频桥接器
"""
import threading
import queue
import numpy as np
import sounddevice as sd
from typing import Optional, Callable
from rich.console import Console

from .processor import AudioProcessor
from .voice_detector import VoiceActivityDetector, VoiceDetectionConfig
from .mpv_controller import MPVController


console = Console()


class VBCableBridge:
    """VB-Cable 音频桥接器 - 支持单/双输入混音模式"""
    
    def __init__(
        self,
        input_device_id: int,
        browser_sample_rate: int = 48000,  # 浏览器端采样率
        input_sample_rate: int = 48000,    # 输入设备采样率
        input_channels: int = 2,           # 输入设备声道数
        browser_channels: int = 2,         # 浏览器端声道数
        chunk_size: int = 512,
        output_device_id: Optional[int] = None,  # 可选：保持向后兼容
        output_sample_rate: Optional[int] = None,
        output_channels: Optional[int] = None,
        # 混音参数
        input_device_id_2: Optional[int] = None,  # 第二个输入设备ID（混音模式）
        input_sample_rate_2: Optional[int] = None,  # 第二个设备采样率
        input_channels_2: Optional[int] = None,     # 第二个设备声道数
        mix_mode: bool = False  # 是否启用混音模式
    ):
        self.input_device_id = input_device_id
        self.output_device_id = output_device_id  # 现在是可选的
        self.browser_sample_rate = browser_sample_rate
        self.input_sample_rate = input_sample_rate
        self.output_sample_rate = output_sample_rate or browser_sample_rate
        self.input_channels = input_channels
        self.output_channels = output_channels or browser_channels
        self.browser_channels = browser_channels
        self.chunk_size = chunk_size
        
        # 混音模式配置
        self.mix_mode = mix_mode
        self.input_device_id_2 = input_device_id_2
        self.input_sample_rate_2 = input_sample_rate_2 or input_sample_rate
        self.input_channels_2 = input_channels_2 or input_channels
        
        self.processor = AudioProcessor(browser_sample_rate, browser_channels)
        
        # 音频队列
        self.input_queue: queue.Queue = queue.Queue(maxsize=200)   # 从设备1接收
        self.input_queue_2: queue.Queue = queue.Queue(maxsize=200) if mix_mode else None  # 从设备2接收
        self.mixed_queue: queue.Queue = queue.Queue(maxsize=200)   # 混音后的输出队列
        
        # 状态
        self.running = False
        self.input_stream: Optional[sd.InputStream] = None
        self.input_stream_2: Optional[sd.InputStream] = None  # 第二个输入流
        self.output_stream: Optional[sd.OutputStream] = None  # 保留但可能不使用
        
        # 混音线程
        self.mixer_thread: Optional[threading.Thread] = None
        
        # 回调
        self.on_audio_received: Optional[Callable[[np.ndarray], None]] = None
        
        # === 音频闪避功能 ===
        from ..config.settings import config
        
        self.ducking_enabled = config.audio.ducking_enabled
        
        if self.ducking_enabled:
            # 语音检测器（监测 VB-Cable A / Clubdeck 房间语音）
            self.voice_detector = VoiceActivityDetector(
                sample_rate=input_sample_rate,
                config=VoiceDetectionConfig(
                    threshold=config.audio.ducking_threshold,
                    min_duration=config.audio.ducking_min_duration,
                    release_time=config.audio.ducking_release_time
                )
            )
            
            # MPV 控制器（通过 named pipe 控制 MPV 音乐音量）
            self.mpv_controller = MPVController(config.mpv)
            
            console.print(f"\n{'='*60}")
            console.print(f"[bold cyan]🎵 音频闪避 (Audio Ducking) 已启用[/bold cyan]")
            console.print(f"{'='*60}")
            console.print(f"  检测源: VB-Cable A (Clubdeck 房间语音)")
            console.print(f"  控制目标: MPV 音乐播放器 (通过 Named Pipe)")
            console.print(f"  语音阈值: {config.audio.ducking_threshold}")
            console.print(f"  正常音量: {config.mpv.normal_volume}%")
            console.print(f"  闪避音量: {config.mpv.ducking_volume}%")
            console.print(f"  MPV Pipe: {config.mpv.pipe_path}")
            console.print(f"{'='*60}\n")
        else:
            self.voice_detector = None
            self.mpv_controller = None
        
        # 调试计数器
        self._frame_count = 0
        
        console.print(f"[dim]音频桥接器配置:[/dim]")
        console.print(f"[dim]  输入1: {input_channels}ch @ {input_sample_rate}Hz (设备 {input_device_id})[/dim]")
        if mix_mode and input_device_id_2 is not None:
            console.print(f"[dim]  输入2: {self.input_channels_2}ch @ {self.input_sample_rate_2}Hz (设备 {input_device_id_2})[/dim]")
        console.print(f"[dim]  浏览器: {browser_channels}ch @ {browser_sample_rate}Hz[/dim]")
        console.print(f"[dim]  Chunk Size: {chunk_size} frames[/dim]")
        if mix_mode:
            console.print(f"[yellow]✓ 模式: 双输入混音[/yellow]")
        else:
            console.print(f"[yellow]✓ 模式: 单向接收（仅监听）[/yellow]")
    
    def _resample(self, audio_data: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
        """简单的线性插值重采样"""
        if from_rate == to_rate:
            return audio_data
        
        # 计算新长度
        ratio = to_rate / from_rate
        old_length = len(audio_data)
        new_length = int(old_length * ratio)
        
        # 线性插值
        old_indices = np.arange(old_length)
        new_indices = np.linspace(0, old_length - 1, new_length)
        resampled = np.interp(new_indices, old_indices, audio_data.astype(np.float32))
        
        return resampled.astype(np.int16)
    
    def _resample_stereo(self, audio_data: np.ndarray, from_rate: int, to_rate: int, channels: int) -> np.ndarray:
        """重采样立体声数据"""
        if from_rate == to_rate:
            return audio_data
        
        frames = len(audio_data) // channels
        reshaped = audio_data.reshape(frames, channels)
        
        # 分别重采样每个声道
        resampled_channels = []
        for ch in range(channels):
            resampled = self._resample(reshaped[:, ch], from_rate, to_rate)
            resampled_channels.append(resampled)
        
        # 合并声道
        new_frames = len(resampled_channels[0])
        result = np.zeros((new_frames, channels), dtype=np.int16)
        for ch in range(channels):
            result[:, ch] = resampled_channels[ch]
        
        return result
    
    def _convert_to_stereo(self, audio_data: np.ndarray, source_channels: int) -> np.ndarray:
        """将多声道音频转换为立体声"""
        if source_channels == self.browser_channels:
            return audio_data
        
        # 处理多维数组：sounddevice 返回 (frames, channels) 形状
        if audio_data.ndim == 2:
            frames = audio_data.shape[0]
            if source_channels == 1:
                # 单声道 -> 立体声
                mono = audio_data[:, 0]
                stereo = np.zeros((frames, 2), dtype=np.int16)
                stereo[:, 0] = mono
                stereo[:, 1] = mono
                return stereo
            else:
                # 多声道 -> 立体声：只取前两个声道
                return audio_data[:, :2].copy()
        
        # 处理一维数组
        frames = len(audio_data) // source_channels
        
        if source_channels == 1:
            # 单声道 -> 立体声：复制到两个声道
            mono = audio_data.flatten()
            stereo = np.zeros(frames * 2, dtype=np.int16)
            stereo[0::2] = mono
            stereo[1::2] = mono
            return stereo.reshape(frames, 2)
        else:
            # 多声道 -> 立体声：只取前两个声道
            reshaped = audio_data.reshape(frames, source_channels)
            return reshaped[:, :2].copy()
    
    def _convert_from_stereo(self, audio_data: np.ndarray, target_channels: int) -> np.ndarray:
        """将立体声转换为目标声道数"""
        if target_channels == self.browser_channels:
            return audio_data
        
        frames = len(audio_data) // self.browser_channels
        stereo = audio_data.reshape(frames, self.browser_channels)
        
        if target_channels == 1:
            # 立体声 -> 单声道：混合两个声道
            mono = ((stereo[:, 0].astype(np.int32) + stereo[:, 1].astype(np.int32)) // 2).astype(np.int16)
            return mono.reshape(frames, 1)
        else:
            # 立体声 -> 多声道：复制立体声到前两个声道，其余填零
            multi = np.zeros((frames, target_channels), dtype=np.int16)
            multi[:, 0] = stereo[:, 0]
            multi[:, 1] = stereo[:, 1]
            return multi
    
    def _input_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """输入流1回调 - 接收第一个设备音频"""
        if status:
            console.print(f"[yellow]输入1状态: {status}[/yellow]")
        
        # 正确处理数据类型 - indata 是 int16 格式
        audio_data = indata.copy().astype(np.int16)
        
        # 1. 先转换为立体声（浏览器端格式）
        stereo_data = self._convert_to_stereo(audio_data, self.input_channels)
        
        # 2. 如果采样率不同，进行重采样
        if self.input_sample_rate != self.browser_sample_rate:
            stereo_data = self._resample_stereo(
                stereo_data.flatten(), 
                self.input_sample_rate, 
                self.browser_sample_rate,
                self.browser_channels
            )
        
        # 3. 放入对应队列
        try:
            if self.mix_mode:
                self.input_queue.put_nowait(stereo_data)
            else:
                # 单输入模式：直接放入混音队列
                self.mixed_queue.put_nowait(stereo_data)
        except queue.Full:
            pass  # 队列满时丢弃
    
    def _input_callback_2(self, indata: np.ndarray, frames: int, time_info, status):
        """输入流2回调 - 接收第二个设备音频"""
        if status:
            console.print(f"[yellow]输入2状态: {status}[/yellow]")
        
        # 正确处理数据类型 - indata 是 int16 格式
        audio_data = indata.copy().astype(np.int16)
        
        # 1. 先转换为立体声（浏览器端格式）
        stereo_data = self._convert_to_stereo(audio_data, self.input_channels_2)
        
        # 2. 如果采样率不同，进行重采样
        if self.input_sample_rate_2 != self.browser_sample_rate:
            stereo_data = self._resample_stereo(
                stereo_data.flatten(), 
                self.input_sample_rate_2, 
                self.browser_sample_rate,
                self.browser_channels
            )
        
        # 3. 放入第二个输入队列
        try:
            self.input_queue_2.put_nowait(stereo_data)
        except queue.Full:
            pass  # 队列满时丢弃
    
    def _calculate_volume(self, audio_data: np.ndarray) -> float:
        """
        计算音量 (RMS)
        
        Args:
            audio_data: 音频数据 (int16)
            
        Returns:
            音量值 (0-100)
        """
        # 转换为 float32
        float_data = audio_data.astype(np.float32) / 32768.0
        
        # 计算 RMS
        rms = np.sqrt(np.mean(float_data ** 2))
        
        # 转换为百分比 (0-100)
        return min(100.0, rms * 100.0 * 10.0)
    
    def _create_volume_bar(self, volume: float, width: int = 20) -> str:
        """
        创建音量条
        
        Args:
            volume: 音量值 (0-100)
            width: 条宽度
            
        Returns:
            音量条字符串
        """
        filled = int(volume / 100.0 * width)
        empty = width - filled
        return '█' * filled + '░' * empty
    
    def _mixer_worker(self):
        """混音工作线程 - 混合两个输入队列的音频"""
        console.print(f"[dim]✓ 混音线程已启动[/dim]")
        
        import sys
        
        while self.running:
            try:
                # 从两个输入队列获取数据
                # audio1 = VB-Cable A (Clubdeck 房间语音)
                # audio2 = VB-Cable B (音乐播放)
                audio1 = self.input_queue.get(timeout=0.05)
                audio2 = self.input_queue_2.get(timeout=0.05)
                
                # === 计算音量 ===
                volume1 = self._calculate_volume(audio1.flatten())
                volume2 = self._calculate_volume(audio2.flatten())
                
                # === 语音活动检测（针对 Clubdeck 语音）===
                has_voice = False
                if self.ducking_enabled and self.voice_detector:
                    # 检测 Clubdeck 房间中是否有人说话
                    has_voice = self.voice_detector.detect(audio1.flatten())
                    
                    # 根据检测结果控制 MPV 音量
                    if self.mpv_controller and self.mpv_controller.is_enabled():
                        self.mpv_controller.set_ducking(has_voice)
                
                # 确保形状一致
                if audio1.shape != audio2.shape:
                    # 调整到相同长度（取较短的）
                    min_len = min(len(audio1.flatten()), len(audio2.flatten()))
                    audio1 = audio1.flatten()[:min_len].reshape(-1, self.browser_channels)
                    audio2 = audio2.flatten()[:min_len].reshape(-1, self.browser_channels)
                
                # 混音：简单相加（MPV 音量由 MPV Controller 控制）
                # 使用 int32 避免溢出，然后限制到 int16 范围
                mixed_int32 = audio1.astype(np.int32) + audio2.astype(np.int32)
                mixed = np.clip(mixed_int32, -32768, 32767).astype(np.int16)
                
                # 放入混音队列
                try:
                    self.mixed_queue.put_nowait(mixed)
                except queue.Full:
                    pass
                
                # === 实时显示音量（每帧刷新）===
                self._frame_count += 1
                if self._frame_count % 5 == 0:  # 每5帧刷新一次显示
                    bar1 = self._create_volume_bar(volume1, 20)
                    bar2 = self._create_volume_bar(volume2, 20)
                    
                    # 语音状态指示
                    voice_icon = "🔊" if has_voice else "  "
                    
                    # 获取 MPV 当前音量
                    mpv_vol = self.mpv_controller.get_current_volume() if self.mpv_controller else 100
                    
                    # 单行显示（使用 \r 回到行首）- 包含设备 ID 和 MPV 音量
                    sys.stdout.write(f"\r音量 | Clubdeck [ID:{self.input_device_id}]: [{bar1}] {volume1:5.1f}% {voice_icon} | 音乐 [ID:{self.input_device_id_2}]: [{bar2}] {volume2:5.1f}% | MPV: {mpv_vol:3d}%  ")
                    sys.stdout.flush()
                    
            except queue.Empty:
                continue
            except Exception as e:
                if self.running:
                    console.print(f"[red]混音错误: {e}[/red]")
                    import traceback
                    traceback.print_exc()
        
        # 退出时换行
        sys.stdout.write("\n")
        sys.stdout.flush()
        console.print(f"[dim]✓ 混音线程已停止[/dim]")
    
    def _mpv_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """MPV 输入流回调 - 接收 MPV 音乐，缓存以供混音使用"""
        if status:
            console.print(f"[yellow]MPV 输入状态: {status}[/yellow]")
        
    def _output_callback(self, outdata: np.ndarray, frames: int, time_info, status):
        """输出流回调 - 发送音频到 Clubdeck，处理采样率和声道转换"""
        if status:
            console.print(f"[yellow]输出状态: {status}[/yellow]")
        
        # 计算需要的输出设备采样数（考虑采样率转换）
        # 输出设备需要 frames 帧，对应浏览器端的采样数
        ratio = self.browser_sample_rate / self.output_sample_rate
        needed_browser_frames = int(frames * ratio)
        needed_stereo_samples = needed_browser_frames * self.browser_channels
        
        # 从队列收集数据到缓冲区（立体声、浏览器采样率格式）
        while not self.output_queue.empty() and len(self.output_buffer) < needed_stereo_samples * 4:
            try:
                chunk = self.output_queue.get_nowait()
                self.output_buffer = np.concatenate([self.output_buffer, chunk.flatten()])
            except queue.Empty:
                break
        
        # 从缓冲区输出
        if len(self.output_buffer) >= needed_stereo_samples:
            stereo_data = self.output_buffer[:needed_stereo_samples]
            self.output_buffer = self.output_buffer[needed_stereo_samples:]
            
            # 1. 先重采样到输出设备采样率
            if self.browser_sample_rate != self.output_sample_rate:
                stereo_data = self._resample_stereo(
                    stereo_data, 
                    self.browser_sample_rate, 
                    self.output_sample_rate,
                    self.browser_channels
                )
            
            # 2. 转换为输出设备的声道数
            output_data = self._convert_from_stereo(stereo_data.flatten(), self.output_channels)
            
            # 确保数据长度匹配
            expected_samples = frames * self.output_channels
            if len(output_data.flatten()) >= expected_samples:
                outdata[:] = output_data.flatten()[:expected_samples].reshape(frames, self.output_channels)
            else:
                outdata[:len(output_data)] = output_data
                outdata[len(output_data):] = 0
        else:
            outdata.fill(0)
    
    def start(self) -> None:
        """启动音频桥接"""
        if self.running:
            return
        
        self.running = True
        
        # 验证设备是否存在
        try:
            devices = sd.query_devices()
            if self.input_device_id < 0 or self.input_device_id >= len(devices):
                raise ValueError(f"输入设备 ID {self.input_device_id} 无效（总设备数: {len(devices)}）")
            
            # 只在有输出设备时验证输出设备
            if self.output_device_id is not None:
                if self.output_device_id < 0 or self.output_device_id >= len(devices):
                    raise ValueError(f"输出设备 ID {self.output_device_id} 无效（总设备数: {len(devices)}）")
        except Exception as e:
            console.print(f"[red]设备验证失败: {e}[/red]")
            self.running = False
            raise
        
        try:
            # 启动输入流1
            self.input_stream = sd.InputStream(
                device=self.input_device_id,
                samplerate=self.input_sample_rate,
                channels=self.input_channels,
                dtype='int16',
                blocksize=self.chunk_size,
                callback=self._input_callback
            )
            self.input_stream.start()
            console.print(f"[dim]✓ 输入流1已启动: 设备 {self.input_device_id}, {self.input_sample_rate}Hz, {self.input_channels}ch[/dim]")
            
            # 如果启用混音模式，启动第二个输入流
            if self.mix_mode and self.input_device_id_2 is not None:
                self.input_stream_2 = sd.InputStream(
                    device=self.input_device_id_2,
                    samplerate=self.input_sample_rate_2,
                    channels=self.input_channels_2,
                    dtype='int16',
                    blocksize=self.chunk_size,
                    callback=self._input_callback_2
                )
                self.input_stream_2.start()
                console.print(f"[dim]✓ 输入流2已启动: 设备 {self.input_device_id_2}, {self.input_sample_rate_2}Hz, {self.input_channels_2}ch[/dim]")
                
                # 启动混音线程
                self.mixer_thread = threading.Thread(target=self._mixer_worker, daemon=True)
                self.mixer_thread.start()
            
            # 只在双向模式时启动输出流
            if self.output_device_id is not None:
                self.output_stream = sd.OutputStream(
                    device=self.output_device_id,
                    samplerate=self.output_sample_rate,
                    channels=self.output_channels,
                    dtype='int16',
                    blocksize=self.chunk_size,
                    callback=self._output_callback
                )
                self.output_stream.start()
                console.print(f"[dim]✓ 输出流已启动: {self.output_sample_rate}Hz, {self.output_channels}ch[/dim]")
            else:
                console.print(f"[dim]⚠ 单向接收模式：未启动输出流[/dim]")
            
            console.print("[green]✓ 音频桥接已启动[/green]")
        except Exception as e:
            console.print(f"[red]启动音频流失败: {e}[/red]")
            # 清理已启动的流
            if self.input_stream:
                try:
                    self.input_stream.stop()
                    self.input_stream.close()
                except:
                    pass
            if self.output_stream:
                try:
                    self.output_stream.stop()
                    self.output_stream.close()
                except:
                    pass
            self.input_stream = None
            self.output_stream = None
            self.running = False
            raise
        except Exception as e:
            console.print(f"[red]启动音频流失败: {e}[/red]")
            # 清理已启动的流
            if self.input_stream:
                try:
                    self.input_stream.stop()
                    self.input_stream.close()
                except:
                    pass
            if self.output_stream:
                try:
                    self.output_stream.stop()
                    self.output_stream.close()
                except:
                    pass
            self.input_stream = None
            self.output_stream = None
            self.running = False
            raise
    
    def stop(self) -> None:
        """停止音频桥接"""
        self.running = False
        
        # 停止 MPV 控制器
        if self.mpv_controller:
            self.mpv_controller.stop()
        
        # 等待混音线程结束
        if self.mixer_thread and self.mixer_thread.is_alive():
            self.mixer_thread.join(timeout=1.0)
        
        if self.input_stream:
            self.input_stream.stop()
            self.input_stream.close()
            self.input_stream = None
        
        if self.input_stream_2:
            self.input_stream_2.stop()
            self.input_stream_2.close()
            self.input_stream_2 = None
        
        if self.output_stream:
            self.output_stream.stop()
            self.output_stream.close()
            self.output_stream = None
        
        # 清理音频队列
        self.clear_queues()
        
        # 清空缓冲区
        self.output_buffer = np.zeros(0, dtype=np.int16)
        
        console.print("[yellow]音频桥接已停止[/yellow]")
    
    def send_to_clubdeck(self, audio_data: np.ndarray) -> None:
        """发送浏览器音频到 Clubdeck"""
        try:
            self.output_queue.put_nowait(audio_data.astype(np.int16))
        except queue.Full:
            pass
    
    def receive_from_clubdeck(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """从 Clubdeck 接收音频 (混音后或单输入)"""
        try:
            return self.mixed_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def clear_queues(self) -> None:
        """清空音频队列"""
        while not self.input_queue.empty():
            try:
                self.input_queue.get_nowait()
            except queue.Empty:
                break
        
        if self.input_queue_2 is not None:
            while not self.input_queue_2.empty():
                try:
                    self.input_queue_2.get_nowait()
                except queue.Empty:
                    break
        
        while not self.mixed_queue.empty():
            try:
                self.mixed_queue.get_nowait()
            except queue.Empty:
                break
