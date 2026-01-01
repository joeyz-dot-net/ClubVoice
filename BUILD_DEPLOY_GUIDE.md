# 打包和部署快速参考

## 自动化脚本（推荐）

### 完整构建和部署
```powershell
.\build_and_deploy.ps1
```

### 仅构建（不部署）
```powershell
.\build_and_deploy.ps1 -BuildOnly
```

### 仅部署（使用已有构建）
```powershell
.\build_and_deploy.ps1 -DeployOnly
```

### 跳过备份
```powershell
.\build_and_deploy.ps1 -SkipBackup
```

### 自定义部署路径
```powershell
.\build_and_deploy.ps1 -DeployPath "D:\MyDeployPath"
```

---

## 手动构建步骤

### 1. 清理旧文件
```powershell
Remove-Item dist, build -Recurse -Force -ErrorAction SilentlyContinue
```

### 2. 使用 PyInstaller 打包
```powershell
pyinstaller ClubVoice.spec -y
```

### 3. 复制配置文件
```powershell
Copy-Item config.ini dist\
```

### 4. 部署到远程服务器
```powershell
Copy-Item -Path .\dist\* -Destination '\\b560\code\voice-communication-app' -Recurse -Force
```

---

## 构建输出

### 目录结构
```
dist/
├── ClubVoice.exe       # 主程序
├── config.ini          # 配置文件
└── static/             # 静态资源
    ├── index.html
    ├── css/
    └── js/
```

### 文件说明

| 文件/目录 | 说明 |
|----------|------|
| `ClubVoice.exe` | 打包后的可执行文件（包含 Python 运行时） |
| `config.ini` | 服务器和音频配置文件 |
| `static/` | Web 界面静态资源（HTML/CSS/JS） |

---

## 配置文件说明

### config.ini 必须包含的配置

```ini
[server]
host = 0.0.0.0          # 监听地址
port = 5000             # 服务端口
debug = false           # 调试模式

[audio]
duplex_mode = half      # 通信模式: half/full
input_device_id = 27    # 主输入设备ID
input_device_id_2 = 26  # 第二输入设备ID（混音模式）
mix_mode = true         # 启用混音

[mpv]
enabled = true
default_pipe = \\.\pipe\mpv-pipe
ducking_volume = 15
normal_volume = 100
```

---

## PyInstaller 规范文件

### ClubVoice.spec 关键配置

```python
datas=[
    ('static', 'static'),  # 静态资源文件夹
    ('config.ini', '.')    # 配置文件
]

hiddenimports=[
    'engineio.async_drivers.threading',
    'rich.console',
    'rich.table',
    'rich.panel',
    'rich.prompt'
]
```

---

## 故障排查

### 问题: 构建失败

**解决方案:**
```powershell
# 1. 检查依赖是否安装
pip install -r requirements.txt

# 2. 清理缓存
Remove-Item __pycache__, *.pyc -Recurse -Force

# 3. 重新构建
pyinstaller ClubVoice.spec -y --clean
```

### 问题: 配置文件未包含在 dist 中

**解决方案:**
```powershell
# 手动复制
Copy-Item config.ini dist\

# 或修改 ClubVoice.spec 中的 datas 参数
datas=[('config.ini', '.')]
```

### 问题: 运行时找不到静态文件

**解决方案:**
检查 `ClubVoice.spec` 中是否包含：
```python
datas=[('static', 'static')]
```

### 问题: 部署路径无法访问

**解决方案:**
```powershell
# 测试网络路径
Test-Path \\b560\code\voice-communication-app

# 或使用本地路径测试
.\build_and_deploy.ps1 -DeployPath "D:\TestDeploy"
```

---

## VS Code 任务

在 `.vscode/tasks.json` 中已配置快捷任务：

- **Ctrl+Shift+B** → 选择 "Build+Deploy" （默认构建任务）
- **Build EXE** - 仅构建可执行文件
- **Deploy to B560** - 仅部署到远程服务器

---

## 版本管理

### 备份策略

自动脚本会在部署前自动备份，并保留最近3个版本：

```
\\b560\code\
├── voice-communication-app/              # 当前版本
├── voice-communication-app.backup_20260101_120000/
├── voice-communication-app.backup_20260101_100000/
└── voice-communication-app.backup_20260101_080000/
```

### 手动回滚

```powershell
# 查看可用备份
Get-ChildItem \\b560\code\ -Filter "*backup*"

# 回滚到特定版本
$BackupPath = "\\b560\code\voice-communication-app.backup_20260101_120000"
Copy-Item -Path $BackupPath\* -Destination "\\b560\code\voice-communication-app" -Recurse -Force
```

---

## 性能优化

### 减小 EXE 体积

在 `ClubVoice.spec` 中启用 UPX 压缩：

```python
exe = EXE(
    ...,
    upx=True,           # 启用 UPX 压缩
    upx_exclude=[],     # 排除特定文件
    ...
)
```

### 加快启动速度

```python
# 禁用优化可加快打包速度，但会增加体积
optimize=0  # 0=无优化, 1=基本优化, 2=完全优化
```

---

## 相关文档

- [MIXER_GUIDE.md](MIXER_GUIDE.md) - 混音功能使用指南
- [DUAL_CABLE_SETUP.md](DUAL_CABLE_SETUP.md) - 双虚拟音频线配置
- [README.md](README.md) - 项目总体说明
