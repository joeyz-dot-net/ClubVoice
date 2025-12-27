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
    """等待用户按键后退出"""
    if error:
        print("\n" + "=" * 50)
        print("程序发生错误，请查看上方错误信息")
        print("=" * 50)
    input("\n按 Enter 键退出...")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断程序")
        wait_for_exit(error=False)
    except SystemExit as e:
        # 正常退出也等待用户确认
        wait_for_exit(error=e.code != 0)
        sys.exit(e.code)
    except Exception as e:
        print(f"\n[错误] {type(e).__name__}: {e}")
        traceback.print_exc()
        wait_for_exit(error=True)
        sys.exit(1)
