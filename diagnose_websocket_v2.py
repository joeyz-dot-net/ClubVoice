"""
WebSocket 连接诊断脚本
用于检测 Socket.IO 配置问题
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("ClubVoice WebSocket 诊断")
print("=" * 60)

# 1. 检查依赖包
print("\n1. 检查依赖包:")
packages = {
    'Flask': 'flask',
    'Flask-SocketIO': 'flask_socketio',
    'eventlet': 'eventlet',
    'python-socketio': 'socketio',
    'python-engineio': 'engineio'
}

for name, module in packages.items():
    try:
        mod = __import__(module)
        version = getattr(mod, '__version__', 'unknown')
        print(f"  ✓ {name}: {version}")
    except ImportError:
        print(f"  ✗ {name}: 未安装")

# 2. 测试 eventlet monkey patch
print("\n2. 测试 eventlet monkey patch:")
try:
    import eventlet
    eventlet.monkey_patch()
    print("  ✓ eventlet monkey patch 成功")
except Exception as e:
    print(f"  ✗ eventlet monkey patch 失败: {e}")

# 3. 创建测试应用
print("\n3. 创建测试 Flask-SocketIO 应用:")
try:
    from flask import Flask
    from flask_socketio import SocketIO
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-key'
    
    # 测试不同的 async_mode
    modes = ['threading', 'eventlet']
    for mode in modes:
        try:
            socketio = SocketIO(app, async_mode=mode, logger=False, engineio_logger=False)
            detected_mode = socketio.async_mode
            print(f"  ✓ async_mode='{mode}' → 实际使用: '{detected_mode}'")
        except Exception as e:
            print(f"  ✗ async_mode='{mode}' 失败: {e}")
    
except Exception as e:
    print(f"  ✗ 创建应用失败: {e}")
    import traceback
    traceback.print_exc()

# 4. 测试 WebSocket 路由
print("\n4. 测试 WebSocket 路由注册:")
try:
    from flask import Flask
    from flask_socketio import SocketIO, emit
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-key'
    socketio = SocketIO(app, async_mode='threading')
    
    @socketio.on('connect')
    def test_connect():
        print("    [Event] connect 触发")
        emit('response', {'data': 'Connected'})
    
    @socketio.on('test_event')
    def test_event(data):
        print(f"    [Event] test_event 触发: {data}")
        emit('response', {'data': 'Received'})
    
    print("  ✓ 事件处理器注册成功")
    print(f"    注册的事件: {list(socketio.handlers.get('/', {}).keys())}")
    
except Exception as e:
    print(f"  ✗ 事件注册失败: {e}")
    import traceback
    traceback.print_exc()

# 5. 检查 WSGI 兼容性
print("\n5. 检查 WSGI 兼容性:")
try:
    from werkzeug import __version__ as werkzeug_version
    print(f"  ✓ Werkzeug 版本: {werkzeug_version}")
    
    # 测试基本 WSGI 应用
    from flask import Flask
    from flask_socketio import SocketIO
    
    app = Flask(__name__)
    socketio = SocketIO(app, async_mode='threading')
    
    @app.route('/test')
    def test_route():
        return 'OK'
    
    # 测试应用是否可调用
    test_app = socketio.middleware if hasattr(socketio, 'middleware') else app
    print(f"  ✓ WSGI 应用类型: {type(test_app).__name__}")
    
except Exception as e:
    print(f"  ✗ WSGI 兼容性检查失败: {e}")

# 6. 推荐配置
print("\n" + "=" * 60)
print("推荐配置:")
print("=" * 60)

print("""
# 方案 1: 使用 threading 模式（最兼容，当前使用）
socketio = SocketIO(
    app,
    async_mode='threading',
    cors_allowed_origins='*',
    ping_timeout=60,
    ping_interval=25,
    logger=False,
    engineio_logger=False
)

socketio.run(
    app,
    host='0.0.0.0',
    port=5000,
    debug=False,
    use_reloader=False
)

# 方案 2: 使用 eventlet 模式（更高性能）
# 需要在文件开头添加:
import eventlet
eventlet.monkey_patch()

socketio = SocketIO(
    app,
    async_mode='eventlet',
    cors_allowed_origins='*',
    logger=False,
    engineio_logger=False
)

socketio.run(
    app,
    host='0.0.0.0',
    port=5000
)
""")

print("\n诊断完成!")
print("如果看到错误，请运行: pip install --upgrade flask flask-socketio eventlet")
