# 临时文件清理功能说明

## 概述

ClubVoice 现已集成自动临时文件清理功能，在程序退出时自动清理运行期间产生的临时文件和缓存。

## 清理内容

### 自动清理的文件/目录
- `**/__pycache__/` - Python 字节码缓存目录
- `**/*.pyc` - Python 编译字节码文件
- `**/*.pyo` - Python 优化字节码文件
- `**/*.pyd` - Python 动态链接库文件
- `*.log` - 日志文件
- `*.tmp` - 临时文件
- `.pytest_cache/` - pytest 测试缓存
- `.coverage` - 代码覆盖率文件
- `htmlcov/` - HTML 覆盖率报告

### 运行时资源清理
- 音频输入/输出流正确关闭
- 音频队列清空（input_queue、output_queue、mpv_queue）
- 音频缓冲区清零
- WebSocket 客户端连接清理
- 所有状态变量重置

## 使用方式

### 1. 自动清理（推荐）

程序在以下情况会自动执行清理：

```python
# 正常退出 (Ctrl+C)
# 程序会自动：
# 1. 停止音频处理
# 2. 关闭 WebSocket 连接
# 3. 清理临时文件
# 4. 清空音频缓冲

# 异常退出
# 即使程序出错，finally 块也会确保资源清理
```

### 2. 手动清理

如需单独清理临时文件而不运行程序：

```bash
python cleanup.py
```

输出示例：
```
开始清理临时文件...

删除目录: src/__pycache__
删除目录: src/audio/__pycache__
删除目录: src/config/__pycache__
删除文件: test.log

✓ 清理完成: 删除 1 个文件, 3 个目录
```

## 技术实现

### 文件结构

```
src/
└── utils/
    └── cleanup.py          # 清理工具类
cleanup.py                  # 独立清理脚本
```

### 核心类：TempFileCleanup

```python
class TempFileCleanup:
    """临时文件清理器"""
    
    def find_temp_files(self) -> List[Path]:
        """查找所有临时文件和目录"""
        
    def clean(self, verbose: bool = True) -> tuple[int, int]:
        """清理临时文件，返回 (删除的文件数, 删除的目录数)"""
```

### 集成点

1. **src/main.py** - signal_handler()
   - Ctrl+C 退出时调用清理

2. **src/main.py** - main() 异常处理
   - 程序错误时也执行清理

3. **src/main.py** - finally 块
   - 确保资源释放

4. **src/audio/vb_cable_bridge.py** - stop()
   - 清理音频队列和缓冲区

5. **src/server/websocket_handler.py** - stop()
   - 清理客户端连接和状态

## 注意事项

### 安全性
- 只清理项目内的临时文件，不会影响系统其他区域
- 权限错误会被捕获并提示，不会中断程序退出

### 性能
- 清理操作在退出时执行，不影响运行时性能
- 使用 `verbose=False` 模式，退出时无额外输出（保持界面简洁）

### PyInstaller 兼容性
- 自动检测是否运行在打包后的 EXE 中
- 开发模式：清理项目根目录
- 打包模式：清理 EXE 所在目录

## 故障排除

### 问题：某些文件无法删除

**可能原因**：
- 文件正在被其他进程使用
- 权限不足

**解决方案**：
- 程序会跳过无法删除的文件并继续
- 检查是否有其他程序占用文件（如编辑器、杀毒软件）
- 以管理员权限运行

### 问题：清理后 __pycache__ 又出现

这是正常现象！Python 运行时会自动创建 `__pycache__` 目录来缓存字节码，提高启动速度。这些文件会在下次退出时再次清理。

## 扩展清理规则

如需添加新的清理模式，编辑 `src/utils/cleanup.py`：

```python
self.temp_patterns = [
    '**/__pycache__',
    '**/*.pyc',
    # 添加您的自定义模式
    '*.backup',
    'temp/**',
]
```

支持 glob 模式：
- `*` - 匹配任意字符（不包括路径分隔符）
- `**` - 递归匹配所有子目录
- `?` - 匹配单个字符
- `[seq]` - 匹配序列中的任一字符

## 相关文件

- [src/utils/cleanup.py](src/utils/cleanup.py) - 清理工具实现
- [cleanup.py](cleanup.py) - 独立清理脚本
- [src/main.py](src/main.py) - 主程序集成
- [README.md](README.md) - 用户文档
