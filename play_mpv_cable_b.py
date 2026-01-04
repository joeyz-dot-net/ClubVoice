"""
使用 MPV 播放 music.mp3 到 CABLE-B Input
"""
import subprocess
import os
from pathlib import Path

print("🎵 MPV 播放到 CABLE-B 设置\n")

# 查找 music.mp3
music_file = None
search_paths = [
    Path.cwd(),
    Path.cwd().parent,
    Path.home() / "Music",
    Path.home() / "Downloads"
]

for path in search_paths:
    if path.exists():
        for mp3 in path.glob("**/*.mp3"):
            if mp3.is_file():
                music_file = mp3
                break
    if music_file:
        break

if not music_file:
    print("❌ 未找到 music.mp3 文件")
    print(f"\n搜索路径:")
    for path in search_paths:
        print(f"  - {path}")
    print("\n请将 music.mp3 放到当前目录或指定完整路径")
else:
    print(f"✓ 找到音乐文件: {music_file}\n")

# 生成 MPV 命令
print("=" * 70)
print("MPV 播放命令:")
print("=" * 70)

# 方法 1: 让 MPV 自动选择设备（如果 CABLE-B 是默认设备）
if music_file:
    print(f'\nmpv --audio-device=wasapi --volume=50 "{music_file}"')
else:
    print(f'\nmpv --audio-device=wasapi --volume=50 "music.mp3"')

# 方法 2: 列出所有 MPV 音频设备
print("\n" + "=" * 70)
print("查看所有 MPV 音频设备:")
print("=" * 70)
print('\nmpv --audio-device=help\n')
print("找到 CABLE-B Input 的设备 ID 后，使用:")
if music_file:
    print(f'mpv --audio-device=wasapi/{{DEVICE_ID}} --volume=50 "{music_file}"')
else:
    print(f'mpv --audio-device=wasapi/{{DEVICE_ID}} --volume=50 "music.mp3"')

print("\n" + "=" * 70)
print("监控命令 (另一个终端):")
print("=" * 70)
print('\necho "35" | python tools/simple_volume_monitor.py\n')
print("=" * 70)
