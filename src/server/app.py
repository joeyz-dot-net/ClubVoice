"""
Flask 应用
"""
import os
import sys
import queue
import struct
from flask import Flask, send_from_directory, Response
from flask_socketio import SocketIO

# 判断是否为 PyInstaller 打包环境
if getattr(sys, 'frozen', False):
    # 打包后的路径
    BASE_DIR = sys._MEIPASS
    STATIC_DIR = os.path.join(BASE_DIR, 'static')
else:
    # 开发环境路径
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    STATIC_DIR = os.path.join(BASE_DIR, 'static')

# 创建 Flask 应用
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static')
app.config['SECRET_KEY'] = 'voice-communication-secret-key'

# 创建 SocketIO - 使用 threading 模式，兼容性最好
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 音频流队列 - 供 HTTP 流端点使用
audio_stream_queue = queue.Queue(maxsize=100)


def add_audio_to_stream(audio_data):
    """添加音频数据到流队列"""
    try:
        audio_stream_queue.put_nowait(audio_data)
    except queue.Full:
        # 队列满了，丢弃最旧的数据
        try:
            audio_stream_queue.get_nowait()
            audio_stream_queue.put_nowait(audio_data)
        except:
            pass


@app.route('/')
def index():
    """主页"""
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/health')
def health():
    """健康检查"""
    return {'status': 'ok'}


@app.route('/stream')
def audio_stream():
    """HTTP 音频流端点 - 用于 iOS Safari 后台播放
    
    使用 chunked transfer 的原始 PCM 音频流
    iOS Safari 需要特殊处理
    """
    sample_rate = 48000
    channels = 2
    bits_per_sample = 16
    
    def generate_audio_stream():
        # 生成一个完整的 WAV 文件头
        # 使用一个很大但不是无限的大小
        data_size = 0x7FFFFFFF  # 约 2GB
        file_size = data_size + 36
        
        # RIFF header
        header = b'RIFF'
        header += struct.pack('<I', file_size)
        header += b'WAVE'
        
        # fmt chunk
        header += b'fmt '
        header += struct.pack('<I', 16)  # fmt chunk size
        header += struct.pack('<H', 1)   # PCM format
        header += struct.pack('<H', channels)
        header += struct.pack('<I', sample_rate)
        header += struct.pack('<I', sample_rate * channels * bits_per_sample // 8)
        header += struct.pack('<H', channels * bits_per_sample // 8)
        header += struct.pack('<H', bits_per_sample)
        
        # data chunk
        header += b'data'
        header += struct.pack('<I', data_size)
        
        yield header
        
        # 持续发送音频数据
        while True:
            try:
                audio_data = audio_stream_queue.get(timeout=0.5)
                yield audio_data.tobytes()
            except queue.Empty:
                # 没有数据时发送静音（保持连接活跃）
                silence = bytes(1024 * channels * (bits_per_sample // 8))
                yield silence
    
    response = Response(
        generate_audio_stream(),
        mimetype='audio/wav',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Accept-Ranges': 'none',
        }
    )
    return response


def create_app():
    """创建应用"""
    return app, socketio
