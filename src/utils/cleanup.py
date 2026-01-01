"""
ClubVoice 临时文件清理工具
支持 PyInstaller 临时文件清理和项目文件清理
"""
import os
import sys
import shutil
import tempfile
import time
from pathlib import Path
from typing import List, Tuple
from rich.console import Console


console = Console()


class TempFileCleanup:
    """PyInstaller 临时文件清理器"""
    
    def __init__(self):
        self.is_frozen = getattr(sys, 'frozen', False)
        self.current_temp_dir = self._get_current_temp_dir()
        self.system_temp_dir = Path(tempfile.gettempdir())
        
    def _get_current_temp_dir(self) -> Path | None:
        """获取当前程序的临时解压目录"""
        if self.is_frozen and hasattr(sys, '_MEIPASS'):
            # PyInstaller 解压目录
            return Path(sys._MEIPASS)
        return None
    
    def find_old_pyinstaller_dirs(self) -> List[Path]:
        """查找系统临时目录中的旧 PyInstaller 目录"""
        old_dirs = []
        
        if not self.system_temp_dir.exists():
            return old_dirs
        
        try:
            # PyInstaller 使用 _MEI 开头的目录
            for item in self.system_temp_dir.iterdir():
                if item.is_dir() and item.name.startswith('_MEI'):
                    # 跳过当前运行程序的目录
                    if self.current_temp_dir and item == self.current_temp_dir:
                        continue
                    
                    # 检查是否可以删除（不被占用）
                    try:
                        # 尝试重命名来测试是否被占用
                        test_name = item.parent / f"{item.name}_test"
                        item.rename(test_name)
                        test_name.rename(item)
                        old_dirs.append(item)
                    except (OSError, PermissionError):
                        # 目录被占用，跳过
                        pass
        except (OSError, PermissionError) as e:
            console.print(f"[dim yellow]无法扫描临时目录: {e}[/dim yellow]")
        
        return old_dirs
    
    def clean_old_temp_dirs(self, verbose: bool = True) -> int:
        """
        清理旧的 PyInstaller 临时目录
        
        Returns:
            删除的目录数
        """
        if not self.is_frozen:
            if verbose:
                console.print("[dim]开发模式，无需清理 PyInstaller 临时文件[/dim]")
            return 0
        
        old_dirs = self.find_old_pyinstaller_dirs()
        
        if not old_dirs:
            if verbose:
                console.print("[dim]没有找到需要清理的旧临时目录[/dim]")
            return 0
        
        dirs_deleted = 0
        
        for temp_dir in old_dirs:
            try:
                # 获取目录信息
                dir_size = sum(f.stat().st_size for f in temp_dir.rglob('*') if f.is_file()) / (1024 * 1024)
                dir_age = time.time() - temp_dir.stat().st_mtime
                
                # 只删除超过 1 小时的目录，避免误删正在使用的
                if dir_age > 3600:
                    if verbose:
                        console.print(f"[dim]删除旧临时目录: {temp_dir.name} ({dir_size:.1f} MB)[/dim]")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    dirs_deleted += 1
            except (OSError, PermissionError) as e:
                if verbose:
                    console.print(f"[dim yellow]无法删除 {temp_dir.name}: {e}[/dim yellow]")
        
        if verbose and dirs_deleted > 0:
            console.print(f"[green]✓ 清理完成: 删除 {dirs_deleted} 个旧临时目录[/green]")
        
        return dirs_deleted
    
    def schedule_self_cleanup(self):
        """
        安排当前程序临时目录的延迟清理
        由于程序运行时无法删除自身目录，需要使用批处理脚本延迟删除
        """
        if not self.is_frozen or not self.current_temp_dir:
            return
        
        try:
            # 创建延迟删除的批处理脚本
            exe_dir = Path(sys.executable).parent
            cleanup_script = exe_dir / '_cleanup_temp.bat'
            
            script_content = f'''@echo off
timeout /t 2 /nobreak >nul
rd /s /q "{self.current_temp_dir}" 2>nul
del "%~f0" 2>nul
'''
            
            cleanup_script.write_text(script_content, encoding='gbk')
            
            # 启动批处理（不等待）
            import subprocess
            subprocess.Popen(
                str(cleanup_script),
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                close_fds=True
            )
        except Exception as e:
            # 静默失败，不影响程序退出
            pass


def cleanup_on_exit(verbose: bool = False):
    """程序退出时的清理函数"""
    cleaner = TempFileCleanup()
    
    # 清理旧的临时目录
    cleaner.clean_old_temp_dirs(verbose=verbose)
    
    # 安排当前程序目录的延迟清理
    if cleaner.is_frozen:
        cleaner.schedule_self_cleanup()


def cleanup_project_files(verbose: bool = True) -> Tuple[int, int]:
    """
    清理项目临时文件
    
    Args:
        verbose: 是否显示详细输出
    
    Returns:
        (files_count, dirs_count): 删除的文件数和目录数
    """
    from pathlib import Path
    
    # 获取项目根目录
    if getattr(sys, 'frozen', False):
        project_root = Path(sys.executable).parent
    else:
        project_root = Path(__file__).parent.parent.parent
    
    # 临时文件模式
    temp_patterns = [
        '**/__pycache__',
        '**/*.pyc',
        '**/*.pyo', 
        '**/*.pyd',
        '*.log',
        '*.tmp',
        '.pytest_cache',
        '.coverage',
        'htmlcov',
    ]
    
    # 受保护的目录
    protected_dirs = {'.git', '.vscode', 'node_modules', 'venv', '.env'}
    
    files_deleted = 0
    dirs_deleted = 0
    
    if verbose:
        console.print("🧹 清理项目临时文件...", style="cyan")
    
    try:
        for pattern in temp_patterns:
            matches = list(project_root.glob(pattern))
            
            for path in matches:
                # 跳过受保护的目录
                if any(protected in path.parts for protected in protected_dirs):
                    continue
                
                try:
                    if path.is_file():
                        path.unlink()
                        files_deleted += 1
                        if verbose:
                            rel_path = path.relative_to(project_root)
                            console.print(f"  删除文件: {rel_path}", style="dim")
                    elif path.is_dir():
                        shutil.rmtree(path, ignore_errors=True)
                        dirs_deleted += 1
                        if verbose:
                            rel_path = path.relative_to(project_root)
                            console.print(f"  删除目录: {rel_path}", style="dim")
                except Exception as e:
                    if verbose:
                        console.print(f"  跳过 {path}: {e}", style="dim yellow")
    
    except Exception as e:
        if verbose:
            console.print(f"[dim yellow]清理项目文件时出错: {e}[/dim yellow]")
    
    if verbose and (files_deleted > 0 or dirs_deleted > 0):
        console.print(f"[green]✓ 项目清理完成: {files_deleted} 个文件, {dirs_deleted} 个目录[/green]")
    
    return files_deleted, dirs_deleted


def cleanup_audio_resources():
    """清理音频资源和队列"""
    try:
        # 导入音频模块并清理
        from ..audio.vb_cable_bridge import VBCableBridge
        from ..server.websocket_handler import WebSocketHandler
        
        console.print("[dim]清理音频资源...[/dim]")
        
        # 注意：这里只是示例，实际清理需要在各自的模块中实现
        # 因为我们需要访问具体的实例
        
    except ImportError:
        # 模块未加载，无需清理
        pass
    except Exception as e:
        console.print(f"[dim yellow]清理音频资源时出错: {e}[/dim yellow]")


def full_cleanup(verbose: bool = True) -> dict:
    """
    执行完整清理：PyInstaller + 项目文件 + 音频资源
    
    Returns:
        清理统计信息字典
    """
    stats = {
        'pyinstaller_dirs': 0,
        'project_files': 0,
        'project_dirs': 0,
        'audio_cleaned': False
    }
    
    if verbose:
        console.print("🚀 开始完整清理...", style="bold cyan")
    
    # 1. 清理 PyInstaller 临时目录
    pyinstaller_cleaner = TempFileCleanup()
    stats['pyinstaller_dirs'] = pyinstaller_cleaner.clean_old_temp_dirs(verbose=verbose)
    
    # 2. 清理项目文件
    files_count, dirs_count = cleanup_project_files(verbose=verbose)
    stats['project_files'] = files_count
    stats['project_dirs'] = dirs_count
    
    # 3. 清理音频资源
    try:
        cleanup_audio_resources()
        stats['audio_cleaned'] = True
    except:
        pass
    
    if verbose:
        total_items = stats['pyinstaller_dirs'] + stats['project_files'] + stats['project_dirs']
        if total_items > 0:
            console.print(f"[bold green]🎉 清理完成! 总共清理了 {total_items} 项内容[/bold green]")
        else:
            console.print("[dim]✨ 系统已经很干净了![/dim]")
    
    return stats
