"""
Flask 应用
"""
import os
import sys
import queue
import struct
from flask import Flask, send_from_directory, Response, request, redirect
from flask_socketio import SocketIO, disconnect
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

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
# 禁用严格下划线处理，避免某些 HTTP 头问题
app.config['WERKZEUG_RUN_MAIN'] = False

# 加载配置
from ..config.settings import config

# 添加 CORS 支持 - 从配置文件读取
if config.cors.enabled:
    CORS(app, origins=config.cors.allowed_origins)

# Create SocketIO - use gevent mode with socket reuse options
socketio = SocketIO(
    app,
    cors_allowed_origins=config.cors.allowed_origins if config.cors.enabled else "*",
    async_mode='gevent',
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e6,
    engineio_logger=False,
    logger=False,
    # Enable socket address reuse to avoid "Address already in use" errors
    socket_options={
        'SO_REUSEADDR': 1
    }
)

# 添加全局错误处理器 - 防止 "write() before start_response" 错误
@app.errorhandler(Exception)
def handle_all_errors(e):
    """全局异常处理器 - 防止流中间的错误导致 start_response 问题"""
    import traceback
    traceback.print_exc()
    
    if isinstance(e, HTTPException):
        return {'error': str(e)}, e.code
    
    # 确保始终返回有效响应
    return {'error': 'Internal Server Error', 'type': type(e).__name__}, 500

# 添加 after_request 处理器确保所有响应都正确
@app.after_request
def after_request(response):
    """在响应后处理，确保头已设置"""
    if response.status_code >= 500:
        # 确保错误响应也有正确的内容类型
        response.headers['Content-Type'] = 'application/json'
    return response

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


@app.route('/favicon.ico')
def favicon():
    """网站图标"""
    return send_from_directory(STATIC_DIR, 'favicon.ico', mimetype='image/x-icon')


@app.route('/manifest.json')
def manifest():
    """PWA Manifest - 根路径访问"""
    return send_from_directory(STATIC_DIR, 'manifest.json', mimetype='application/manifest+json')


@app.route('/static/manifest.json')
def static_manifest():
    """PWA Manifest - static 路径访问"""
    return send_from_directory(STATIC_DIR, 'manifest.json', mimetype='application/manifest+json')


@app.route('/static/sw.js')
def service_worker():
    """Service Worker - 需要正确的 MIME 类型和作用域"""
    response = send_from_directory(STATIC_DIR, 'sw.js', mimetype='application/javascript')
    # Service Worker 需要设置正确的作用域
    response.headers['Service-Worker-Allowed'] = '/'
    return response


@app.route('/apple-touch-icon.png')
@app.route('/apple-touch-icon-precomposed.png')
def apple_touch_icon():
    """Apple Touch Icon - iOS Safari 会请求这些图标"""
    return send_from_directory(STATIC_DIR, 'icon-192.png', mimetype='image/png')


@app.route('/health')
def health():
    """健康检查"""
    return {'status': 'ok'}


@app.route('/status')
def status():
    """服务器状态"""
    # 尝试从 WebSocket 处理器获取连接数
    try:
        from .websocket_handler import get_connection_count
        peers = get_connection_count()
    except:
        peers = 0
    
    return {
        'status': 'running',
        'peers': peers
    }


@app.route('/sdk/clubvoice.js')
def serve_sdk():
    """提供 ClubVoice SDK"""
    return send_from_directory(os.path.join(STATIC_DIR, 'js'), 'clubvoice-sdk.js', 
                               mimetype='application/javascript')


@app.route('/api/sdk-info')
def sdk_info():
    """SDK 信息接口"""
    from ..config.settings import config
    
    return {
        'name': 'ClubVoice SDK',
        'version': '1.0.0',
        'server_url': request.url_root.rstrip('/'),
        'websocket_url': f"ws://{request.host}/socket.io/",
        'duplex_mode': config.audio.duplex_mode,
        'audio_format': {
            'sample_rate': 48000,
            'channels': 2,
            'encoding': 'int16_base64'
        },
        'features': ['listen_only', 'volume_control', 'real_time_audio']
    }


@app.errorhandler(404)
def not_found_error(error):
    """处理 404 错误"""
    import logging
    
    # 记录未找到的资源请求
    logging.warning(f"404 Not Found: {request.method} {request.path} from {request.remote_addr}")
    
    # 如果是 API 请求，返回 JSON
    if request.path.startswith('/api/') or request.path.endswith('.json'):
        return {"error": "Resource not found"}, 404
    
    # 如果是音频流请求，提供说明
    if request.path.endswith(('.m3u8', '.ts', '.aac', '.mp3')):
        return "ClubVoice uses WebSocket for real-time audio communication, not file streaming", 404
    
    # 其他情况重定向到主页
    return redirect('/')


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


# Socket.IO 错误处理
@socketio.on_error_default
def default_error_handler(e):
    """Handle all Socket.IO errors"""
    print(f"[SocketIO Error] {type(e).__name__}: {e}")
    if hasattr(e, '__traceback__'):
        import traceback
        print(''.join(traceback.format_tb(e.__traceback__)))
    return False  # Returning False will disconnect


# Flask 错误处理
@app.errorhandler(500)
def handle_500(error):
    """Handle 500 errors"""
    print(f"[500 Error] {error}")
    return {'error': 'Internal Server Error'}, 500


@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all unhandled exceptions"""
    # Skip HTTPException, let them be handled normally
    if isinstance(e, HTTPException):
        return e
    
    print(f"[Unhandled Exception] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    
    return {'error': 'Internal Server Error', 'message': str(e)}, 500


def create_app():
    """创建应用"""
    return app, socketio
