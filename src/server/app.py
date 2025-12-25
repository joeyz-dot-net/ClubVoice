"""
Flask 应用
"""
import os
import sys
from flask import Flask, send_from_directory
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


@app.route('/')
def index():
    """主页"""
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/health')
def health():
    """健康检查"""
    return {'status': 'ok'}


def create_app():
    """创建应用"""
    return app, socketio
