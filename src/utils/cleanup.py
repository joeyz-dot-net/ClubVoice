"""
临时文件清理工具 - 清理 PyInstaller 解压的临时文件
"""
import os
import sys
import shutil
import tempfile
import time
from pathlib import Path
from typing import List
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
