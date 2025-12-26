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


console = Console()


class VBCableBridge:
    """VB-Cable 音频桥接器 - 支持不同采样率和声道数的输入输出设备"""
    
    def __init__(
        self,
        input_device_id: int,
        output_device_id: int,
        browser_sample_rate: int = 48000,  # 浏览器端采样率
        input_sample_rate: int = 48000,    # 输入设备采样率
        output_sample_rate: int = 48000,   # 输出设备采样率
        input_channels: int = 2,           # 输入设备声道数
        output_channels: int = 2,          # 输出设备声道数
        browser_channels: int = 2,         # 浏览器端声道数
        chunk_size: int = 512
    ):
        self.input_device_id = input_device_id
        self.output_device_id = output_device_id
        self.browser_sample_rate = browser_sample_rate
        self.input_sample_rate = input_sample_rate
        self.output_sample_rate = output_sample_rate
        self.input_channels = input_channels
        self.output_channels = output_channels
        self.browser_channels = browser_channels
        self.chunk_size = chunk_size
        
        self.processor = AudioProcessor(browser_sample_rate, browser_channels)
        
        # 音频队列 - 增大容量避免丢帧
        self.input_queue: queue.Queue = queue.Queue(maxsize=200)   # 从 VB-Cable 接收
        self.output_queue: queue.Queue = queue.Queue(maxsize=200)  # 发送到 VB-Cable
        
        # 平滑播放缓冲
        self.output_buffer = np.zeros(0, dtype=np.int16)
        
        # 状态
        self.running = False
        self.input_stream: Optional[sd.InputStream] = None
        self.output_stream: Optional[sd.OutputStream] = None
        
        # 回调
        self.on_audio_received: Optional[Callable[[np.ndarray], None]] = None
        
        console.print(f"[dim]音频桥接器配置:[/dim]")
        console.print(f"[dim]  输入: {input_channels}ch @ {input_sample_rate}Hz[/dim]")
        console.print(f"[dim]  输出: {output_channels}ch @ {output_sample_rate}Hz[/dim]")
        console.print(f"[dim]  浏览器: {browser_channels}ch @ {browser_sample_rate}Hz[/dim]")
    
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
        """输入流回调 - 接收 Clubdeck 音频，转换采样率和声道数"""
        if status:
            console.print(f"[yellow]输入状态: {status}[/yellow]")
        
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
        
        try:
            self.input_queue.put_nowait(stereo_data)
        except queue.Full:
            pass  # 队列满时丢弃
        
        # 触发回调
        if self.on_audio_received:
            self.on_audio_received(stereo_data)
    
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
        
        # 启动输入流 (从 VB-Cable 读取 Clubdeck 音频) - 使用输入设备的参数
        self.input_stream = sd.InputStream(
            device=self.input_device_id,
            samplerate=self.input_sample_rate,
            channels=self.input_channels,
            dtype='int16',
            blocksize=self.chunk_size,
            callback=self._input_callback
        )
        self.input_stream.start()
        
        # 启动输出流 (向 VB-Cable 写入浏览器音频) - 使用输出设备的参数
        self.output_stream = sd.OutputStream(
            device=self.output_device_id,
            samplerate=self.output_sample_rate,
            channels=self.output_channels,
            dtype='int16',
            blocksize=self.chunk_size,
            callback=self._output_callback
        )
        self.output_stream.start()
        
        console.print("[green]✓ 音频桥接已启动[/green]")
    
    def stop(self) -> None:
        """停止音频桥接"""
        self.running = False
        
        if self.input_stream:
            self.input_stream.stop()
            self.input_stream.close()
            self.input_stream = None
        
        if self.output_stream:
            self.output_stream.stop()
            self.output_stream.close()
            self.output_stream = None
        
        console.print("[yellow]音频桥接已停止[/yellow]")
    
    def send_to_clubdeck(self, audio_data: np.ndarray) -> None:
        """发送音频到 Clubdeck (通过 VB-Cable)"""
        try:
            self.output_queue.put_nowait(audio_data.astype(np.int16))
        except queue.Full:
            pass
    
    def receive_from_clubdeck(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """从 Clubdeck 接收音频 (通过 VB-Cable)"""
        try:
            return self.input_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def clear_queues(self) -> None:
        """清空音频队列"""
        while not self.input_queue.empty():
            try:
                self.input_queue.get_nowait()
            except queue.Empty:
                break
        
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except queue.Empty:
                break
