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
    """VB-Cable 音频桥接器"""
    
    def __init__(
        self,
        input_device_id: int,
        output_device_id: int,
        sample_rate: int = 48000,
        channels: int = 2,  # 立体声
        chunk_size: int = 512  # 减小缓冲区降低延迟
    ):
        self.input_device_id = input_device_id
        self.output_device_id = output_device_id
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        
        self.processor = AudioProcessor(sample_rate, channels)
        
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
    
    def _input_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """输入流回调 - 接收 Clubdeck 音频"""
        if status:
            console.print(f"[yellow]输入状态: {status}[/yellow]")
        
        # 正确处理数据类型 - indata 是 int16 格式
        audio_data = indata.copy().astype(np.int16)
        
        try:
            self.input_queue.put_nowait(audio_data)
        except queue.Full:
            pass  # 队列满时丢弃
        
        # 触发回调
        if self.on_audio_received:
            self.on_audio_received(audio_data)
    
    def _output_callback(self, outdata: np.ndarray, frames: int, time_info, status):
        """输出流回调 - 发送音频到 Clubdeck"""
        if status:
            console.print(f"[yellow]输出状态: {status}[/yellow]")
        
        # 从队列收集数据到缓冲区
        needed_samples = frames * self.channels
        while not self.output_queue.empty() and len(self.output_buffer) < needed_samples * 4:
            try:
                chunk = self.output_queue.get_nowait()
                self.output_buffer = np.concatenate([self.output_buffer, chunk.flatten()])
            except queue.Empty:
                break
        
        # 从缓冲区输出
        if len(self.output_buffer) >= needed_samples:
            outdata[:] = self.output_buffer[:needed_samples].reshape(frames, self.channels)
            self.output_buffer = self.output_buffer[needed_samples:]
        elif len(self.output_buffer) > 0:
            available = len(self.output_buffer) // self.channels * self.channels
            if available > 0:
                outdata[:available // self.channels] = self.output_buffer[:available].reshape(-1, self.channels)
            outdata[available // self.channels:] = 0
            self.output_buffer = np.zeros(0, dtype=np.int16)
        else:
            outdata.fill(0)
    
    def start(self) -> None:
        """启动音频桥接"""
        if self.running:
            return
        
        self.running = True
        
        # 启动输入流 (从 VB-Cable 读取 Clubdeck 音频)
        self.input_stream = sd.InputStream(
            device=self.input_device_id,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='int16',
            blocksize=self.chunk_size,
            callback=self._input_callback
        )
        self.input_stream.start()
        
        # 启动输出流 (向 VB-Cable 写入浏览器音频)
        self.output_stream = sd.OutputStream(
            device=self.output_device_id,
            samplerate=self.sample_rate,
            channels=self.channels,
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
