#!/usr/bin/env python
"""
ClubVoice 临时文件清理脚本

独立运行的清理工具，用于清理项目产生的临时文件和缓存。
可以在不启动主程序的情况下清理临时文件。

使用方法：
    python cleanup.py

清理内容：
- Python 字节码缓存 (__pycache__/, *.pyc, *.pyo, *.pyd)
- 日志文件 (*.log)
- 临时文件 (*.tmp)
- 测试缓存 (.pytest_cache/)
- 覆盖率文件 (.coverage, htmlcov/)
- PyInstaller 临时目录 (_MEI*)
"""
import os
import sys
import shutil
import tempfile
from pathlib import Path
from typing import List, Tuple
import glob


class ProjectCleanup:
    """项目临时文件清理器"""
    
    def __init__(self):
        # 获取项目根目录
        if getattr(sys, 'frozen', False):
            # 打包后的EXE
            self.project_root = Path(sys.executable).parent
        else:
            # 开发环境
            self.project_root = Path(__file__).parent
        
        # 要清理的文件模式
        self.temp_patterns = [
            '**/__pycache__',      # Python 字节码缓存目录
            '**/*.pyc',            # 编译字节码文件
            '**/*.pyo',            # 优化字节码文件
            '**/*.pyd',            # Python 动态链接库
            '*.log',               # 日志文件
            '*.tmp',               # 临时文件
            '.pytest_cache',       # pytest 缓存
            '.coverage',           # 覆盖率文件
            'htmlcov',             # HTML 覆盖率报告
            'build',               # 构建目录
            '*.egg-info',          # Python egg 信息
        ]
        
        # 要保护的关键目录（不清理）
        self.protected_dirs = {
            '.git', '.vscode', 'node_modules', 'venv', '.env'
        }

    def find_temp_files(self) -> Tuple[List[Path], List[Path]]:
        """
        查找所有临时文件和目录
        
        Returns:
            (files, directories) - 要删除的文件列表和目录列表
        """
        files_to_delete = []
        dirs_to_delete = []
        
        try:
            for pattern in self.temp_patterns:
                matches = list(self.project_root.glob(pattern))
                
                for path in matches:
                    # 跳过受保护的目录
                    if any(protected in path.parts for protected in self.protected_dirs):
                        continue
                    
                    if path.is_file():
                        files_to_delete.append(path)
                    elif path.is_dir():
                        dirs_to_delete.append(path)
        
        except Exception as e:
            print(f"扫描文件时出错: {e}")
        
        return files_to_delete, dirs_to_delete

    def clean_pyinstaller_temps(self) -> int:
        """清理 PyInstaller 临时目录"""
        cleaned = 0
        temp_dir = Path(tempfile.gettempdir())
        
        try:
            for item in temp_dir.iterdir():
                if item.is_dir() and item.name.startswith('_MEI'):
                    try:
                        # 检查是否可以删除（不被占用）
                        test_file = item / 'test_lock'
                        with open(test_file, 'w') as f:
                            f.write('test')
                        test_file.unlink()
                        
                        # 可以删除，清理目录
                        shutil.rmtree(item, ignore_errors=True)
                        print(f"删除 PyInstaller 临时目录: {item.name}")
                        cleaned += 1
                    except (OSError, PermissionError):
                        # 目录被占用，跳过
                        pass
        except Exception as e:
            print(f"清理 PyInstaller 临时目录时出错: {e}")
        
        return cleaned

    def clean(self, verbose: bool = True) -> Tuple[int, int]:
        """
        执行清理操作
        
        Args:
            verbose: 是否显示详细信息
            
        Returns:
            (files_count, dirs_count) - 删除的文件数和目录数
        """
        if verbose:
            print("🧹 开始清理 ClubVoice 临时文件...")
            print(f"项目目录: {self.project_root}")
            print()
        
        files_to_delete, dirs_to_delete = self.find_temp_files()
        files_deleted = 0
        dirs_deleted = 0
        
        # 删除文件
        for file_path in files_to_delete:
            try:
                if file_path.exists():
                    file_path.unlink()
                    files_deleted += 1
                    if verbose:
                        rel_path = file_path.relative_to(self.project_root)
                        print(f"删除文件: {rel_path}")
            except Exception as e:
                if verbose:
                    print(f"无法删除文件 {file_path}: {e}")
        
        # 删除目录
        for dir_path in dirs_to_delete:
            try:
                if dir_path.exists() and dir_path.is_dir():
                    shutil.rmtree(dir_path, ignore_errors=True)
                    dirs_deleted += 1
                    if verbose:
                        rel_path = dir_path.relative_to(self.project_root)
                        print(f"删除目录: {rel_path}")
            except Exception as e:
                if verbose:
                    print(f"无法删除目录 {dir_path}: {e}")
        
        # 清理 PyInstaller 临时目录
        pyinstaller_cleaned = self.clean_pyinstaller_temps()
        
        if verbose:
            print()
            print(f"✅ 清理完成:")
            print(f"   删除文件: {files_deleted} 个")
            print(f"   删除目录: {dirs_deleted} 个")
            if pyinstaller_cleaned > 0:
                print(f"   PyInstaller 临时目录: {pyinstaller_cleaned} 个")
            print(f"   项目更清洁了! 🎉")
        
        return files_deleted, dirs_deleted

    def get_cleanup_summary(self) -> dict:
        """获取清理预览"""
        files, dirs = self.find_temp_files()
        
        # 计算文件大小
        total_size = 0
        file_details = []
        dir_details = []
        
        for file_path in files:
            try:
                if file_path.exists():
                    size = file_path.stat().st_size
                    total_size += size
                    rel_path = file_path.relative_to(self.project_root)
                    file_details.append({
                        'path': str(rel_path),
                        'size': size,
                        'size_mb': round(size / (1024 * 1024), 3)
                    })
            except:
                pass
        
        for dir_path in dirs:
            try:
                if dir_path.exists():
                    dir_size = 0
                    file_count = 0
                    for file_path in dir_path.rglob('*'):
                        if file_path.is_file():
                            try:
                                file_size = file_path.stat().st_size
                                dir_size += file_size
                                total_size += file_size
                                file_count += 1
                            except:
                                pass
                    
                    rel_path = dir_path.relative_to(self.project_root)
                    dir_details.append({
                        'path': str(rel_path),
                        'size': dir_size,
                        'size_mb': round(dir_size / (1024 * 1024), 3),
                        'file_count': file_count
                    })
            except:
                pass
        
        return {
            'files_count': len(files),
            'dirs_count': len(dirs),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'file_details': file_details,
            'dir_details': dir_details
        }


def main():
    """主函数"""
    print("🎙️ ClubVoice 项目清理工具")
    print("=" * 50)
    
    cleaner = ProjectCleanup()
    
    # 显示清理预览
    summary = cleaner.get_cleanup_summary()
    if summary['files_count'] == 0 and summary['dirs_count'] == 0:
        print("✨ 项目已经很干净了，无需清理！")
        return
    
    print(f"发现临时文件: {summary['files_count']} 个文件, {summary['dirs_count']} 个目录")
    print(f"预计释放空间: {summary['total_size_mb']} MB")
    print()
    
    # 显示发现的文件列表
    if summary['file_details']:
        print("📄 发现的临时文件:")
        for file_info in summary['file_details'][:20]:  # 限制显示前20个文件
            size_str = f"{file_info['size_mb']:.2f} MB" if file_info['size_mb'] > 0.01 else f"{file_info['size']} B"
            print(f"   🗎 {file_info['path']} ({size_str})")
        
        if len(summary['file_details']) > 20:
            print(f"   ... 还有 {len(summary['file_details']) - 20} 个文件")
        print()
    
    # 显示发现的目录列表
    if summary['dir_details']:
        print("📁 发现的临时目录:")
        for dir_info in summary['dir_details']:
            size_str = f"{dir_info['size_mb']:.2f} MB" if dir_info['size_mb'] > 0.01 else f"{dir_info['size']} B"
            files_str = f"{dir_info['file_count']} 个文件" if dir_info['file_count'] > 0 else "空目录"
            print(f"   📂 {dir_info['path']} ({size_str}, {files_str})")
        print()
    
    # 询问是否继续
    try:
        response = input("是否继续清理? (y/n): ").lower().strip()
        if response not in ('y', 'yes', 'Y', '是'):
            print("已取消清理")
            return
    except KeyboardInterrupt:
        print("\n已取消清理")
        return
    
    print()
    
    # 执行清理
    try:
        files_count, dirs_count = cleaner.clean(verbose=True)
        
        print("\n" + "=" * 50)
        print("🎉 清理任务完成!")
        
        if files_count == 0 and dirs_count == 0:
            print("没有找到需要清理的文件")
        else:
            print(f"成功清理 {files_count} 个文件和 {dirs_count} 个目录")
            
    except KeyboardInterrupt:
        print("\n用户中断清理")
    except Exception as e:
        print(f"\n清理过程中出现错误: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())