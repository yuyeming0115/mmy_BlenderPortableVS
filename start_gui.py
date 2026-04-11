#!/usr/bin/env python3
"""
Blender Config Sync - 独立 PyQt6 启动器
避免与 Tkinter 冲突的纯净启动方式
"""

import sys
import os

# 重要：在任何其他导入之前设置环境变量
os.environ['QT_MAC_DISABLE_FOREGROUND_APPLICATION_TRANSFORM'] = '1'

def main():
    """主入口函数"""
    print("🚀 启动 Blender 配置同步工具 (PyQt6)...")
    
    # 确保项目路径在 sys.path 中
    project_dir = Path(__file__).parent
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))
    
    try:
        # 直接导入并启动（避免通过 CLI 触发 tkinter 导入）
        from blender_config_sync.gui_pyqt import main as pyqt_main
        print("✅ PyQt6 模块加载成功\n")
        pyqt_main()
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("\n请先安装依赖:")
        print("   pip install PyQt6")
        input("\n按回车键退出...")
        
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")


if __name__ == '__main__':
    from pathlib import Path
    main()
