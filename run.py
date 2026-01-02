#!/usr/bin/env python
"""
启动脚本
"""
import sys
import os
import traceback

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import main


def wait_for_exit(error: bool = False):
    """Wait for user to press key before exiting"""
    if error:
        print("\n" + "=" * 50)
        print("An error occurred. See the details above.")
        print("=" * 50)
    input("\nPress Enter to exit...")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nUser interrupted program")
        wait_for_exit(error=False)
    except SystemExit as e:
        # 正常退出也等待用户确认
        wait_for_exit(error=e.code != 0)
        sys.exit(e.code)
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        traceback.print_exc()
        wait_for_exit(error=True)
        sys.exit(1)
