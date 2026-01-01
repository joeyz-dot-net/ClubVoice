# 无窗口模式日志查看

## 概述

PyInstaller 打包的 ClubVoice.exe 运行时，控制台窗口已被隐藏以提供更好的用户体验。所有日志会被自动保存到本地文件。

## 日志文件位置

### Windows
```
C:\Users\<你的用户名>\ClubVoice_Logs\
```

例如：
```
C:\Users\Administrator\ClubVoice_Logs\
clubvoice_20260101_120000.log
clubvoice_20260101_100000.log
```

### 快速访问
1. 按 `Win + R`
2. 输入：`%USERPROFILE%\ClubVoice_Logs`
3. 按 Enter

## 日志文件命名

日志文件使用时间戳命名：
```
clubvoice_YYYYMMDD_HHMMSS.log
```

- `YYYY` - 年份
- `MM` - 月份
- `DD` - 日期
- `HH` - 小时
- `MM` - 分钟
- `SS` - 秒钟

例如：`clubvoice_20260101_143025.log` 表示 2026年1月1日 14点30分25秒启动的程序

## 日志内容

日志文件包含：
- 程序启动信息
- 音频设备配置
- 服务器地址和端口
- WebSocket 连接事件
- 音频处理统计
- 错误和警告信息

## 故障排查

### 程序启动失败
1. 查看最新的日志文件
2. 查找 `[ERROR]` 或 `错误` 关键词
3. 常见问题：
   - 音频设备不可用
   - 端口被占用
   - 配置文件错误

### 查看日志命令

**PowerShell:**
```powershell
# 查看最新日志
Get-ChildItem "$env:USERPROFILE\ClubVoice_Logs" | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | % { type $_.FullName }

# 实时监视日志
Get-Content "$env:USERPROFILE\ClubVoice_Logs\clubvoice_*.log" -Tail 50 -Wait
```

**CMD:**
```cmd
REM 打开日志目录
explorer %USERPROFILE%\ClubVoice_Logs
```

**Git Bash:**
```bash
# 查看最新日志
tail -f ~/ClubVoice_Logs/clubvoice_*.log
```

## 禁用窗口隐藏（开发模式）

如果需要看到控制台输出，可以：

1. 使用命令行运行
```bash
python run.py
```

2. 或修改 ClubVoice.spec
```python
console=True  # 改为 True
```

然后重新打包：
```bash
pyinstaller ClubVoice.spec -y
```

## 清理旧日志

ClubVoice_Logs 目录中的日志文件会自动保留，用户可以手动删除旧日志：

```powershell
# PowerShell - 删除 7 天前的日志
$limit = (Get-Date).AddDays(-7)
Get-ChildItem "$env:USERPROFILE\ClubVoice_Logs" | Where-Object { $_.LastWriteTime -lt $limit } | Remove-Item
```

## 相关文档

- [README.md](README.md) - 项目总体说明
- [BUILD_DEPLOY_GUIDE.md](BUILD_DEPLOY_GUIDE.md) - 打包和部署指南
