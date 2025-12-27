#!/usr/bin/env python
"""
PyInstaller 临时文件清理脚本 - 独立运行
清理系统临时目录中残留的 _MEI* 目录
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.cleanup import TempFileCleanup
from rich.console import Console


def main():
    """清理 PyInstaller 临时文件的独立脚本"""
    console = Console()
    console.print("[cyan]开始清理 PyInstaller 临时目录...[/cyan]")
    console.print(f"[dim]扫描位置: {os.environ.get('TEMP', 'Unknown')}[/dim]\n")
    
    cleaner = TempFileCleanup()
    
    if not cleaner.is_frozen:
        console.print("[yellow]注意: 当前运行在开发模式[/yellow]")
        console.print("[dim]只有 EXE 运行时才会产生 _MEI 临时目录[/dim]\n")
    
    dirs_deleted = cleaner.clean_old_temp_dirs(verbose=True)
    
    if dirs_deleted == 0:
        console.print("\n[dim]没有找到需要清理的旧临时目录[/dim]")
    else:
        console.print(f"\n[bold green]✓ 清理完成！[/bold green]")
        console.print(f"[green]  删除了 {dirs_deleted} 个旧临时目录[/green]")
    
    if cleaner.is_frozen and cleaner.current_temp_dir:
        console.print(f"\n[dim]当前程序临时目录: {cleaner.current_temp_dir.name}[/dim]")
        console.print(f"[dim]将在程序退出后自动清理[/dim]")
    
    input("\n按 Enter 键退出...")


if __name__ == '__main__':
    main()
