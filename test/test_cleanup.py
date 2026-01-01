"""
测试 PyInstaller 临时文件清理功能
"""
import sys
import os
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.cleanup import TempFileCleanup
from rich.console import Console


def test_cleanup():
    """测试清理功能"""
    console = Console()
    console.print("[cyan]测试 PyInstaller 临时文件清理功能[/cyan]\n")
    
    cleaner = TempFileCleanup()
    
    # 显示当前状态
    console.print(f"[bold]当前状态:[/bold]")
    console.print(f"  运行模式: {'EXE (frozen)' if cleaner.is_frozen else '开发模式 (dev)'}")
    console.print(f"  系统临时目录: {cleaner.system_temp_dir}")
    
    if cleaner.current_temp_dir:
        console.print(f"  当前临时目录: {cleaner.current_temp_dir}")
    else:
        console.print(f"  当前临时目录: 无 (开发模式)")
    
    console.print()
    
    # 查找旧目录
    console.print("[bold]扫描旧的 _MEI 目录...[/bold]")
    old_dirs = cleaner.find_old_pyinstaller_dirs()
    
    if old_dirs:
        console.print(f"[yellow]找到 {len(old_dirs)} 个旧目录:[/yellow]")
        for d in old_dirs:
            try:
                size = sum(f.stat().st_size for f in d.rglob('*') if f.is_file()) / (1024 * 1024)
                age_hours = (Path(tempfile.gettempdir()).stat().st_mtime - d.stat().st_mtime) / 3600
                console.print(f"  • {d.name} - {size:.1f} MB")
            except:
                console.print(f"  • {d.name}")
    else:
        console.print("[green]✓ 没有找到旧目录[/green]")
    
    console.print()
    
    # 测试清理
    if old_dirs:
        console.print("[bold]是否执行清理？[/bold]")
        choice = input("输入 'y' 清理旧目录，其他键跳过: ").strip().lower()
        
        if choice == 'y':
            console.print()
            dirs_deleted = cleaner.clean_old_temp_dirs(verbose=True)
            console.print(f"\n[green]清理完成: 删除了 {dirs_deleted} 个目录[/green]")
        else:
            console.print("[dim]已跳过清理[/dim]")
    
    console.print()
    console.print("[bold green]✓ 测试完成[/bold green]")


if __name__ == '__main__':
    try:
        test_cleanup()
    except KeyboardInterrupt:
        print("\n测试中断")
    except Exception as e:
        import traceback
        print(f"\n错误: {e}")
        traceback.print_exc()
    finally:
        input("\n按 Enter 键退出...")
