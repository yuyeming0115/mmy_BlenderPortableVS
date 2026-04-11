#!/usr/bin/env python3
"""
Blender Config Sync - GUI 启动器（macOS 兼容版）
解决 macOS Tkinter 渲染问题的特殊启动脚本
"""

import os
import sys


def setup_macos_tkinter():
    """配置 macOS 特定的 Tkinter 设置"""
    # 抑制 macOS Tk 废弃警告
    os.environ['TK_SILENCE_DEPRECATION'] = '1'
    
    try:
        import tkinter as tk
        
        # 在创建根窗口前设置一些参数
        # 这有助于解决 macOS 上的渲染问题
        root = tk.Tk()
        
        # 强制使用特定的窗口系统设置
        root.tk.call('tk', 'windowingsystem')
        
        # 设置背景色（确保可见）
        root.configure(bg='#2b2b2b')  # 深色主题背景
        
        return True, root
    except Exception as e:
        print(f"❌ Tkinter 初始化失败: {e}")
        return False, None


def launch_gui_with_fix():
    """使用修复方案启动 GUI"""
    print("🚀 正在启动 Blender 配置同步工具 (GUI)...")
    print("   正在应用 macOS 兼容性修复...\n")
    
    success, test_root = setup_macos_tkinter()
    
    if not success:
        print("❌ 无法初始化 Tkinter，请改用终端版:")
        print("   python -m blender_config_sync.tui\n")
        return False
    
    # 关闭测试窗口
    try:
        test_root.destroy()
    except:
        pass
    
    # 现在导入并启动实际的应用
    from pathlib import Path
    
    # 确保项目路径在 sys.path 中
    project_dir = Path(__file__).parent
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))
    
    try:
        from blender_config_sync.gui import BlenderConfigSyncApp
        
        print("✅ GUI 组件加载成功")
        print("   正在创建主窗口...\n")
        
        app = BlenderConfigSyncApp()
        
        # 额外的修复：强制多次更新
        for i in range(5):
            app.root.update_idletasks()
            app.root.after(50)
        
        print("🎨 GUI 已启动！如果窗口空白，请尝试：\n")
        print("   1. 点击窗口边缘拖动调整大小")
        print("   2. 按 Cmd+Q 退出后重新运行此命令\n")
        
        app.run()
        return True
        
    except Exception as e:
        print(f"\n❌ GUI 启动失败: {e}\n")
        print("💡 建议：使用终端版替代")
        print("   python -m blender_config_sync.tui\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主入口"""
    print("=" * 60)
    print("🎨 Blender 配置同步工具 v0.2 - GUI 启动器")
    print("=" * 60 + "\n")
    
    # 尝试启动 GUI
    success = launch_gui_with_fix()
    
    if not success:
        print("\n是否要启动终端版？(y/n): ", end='')
        choice = input().strip().lower()
        if choice == 'y':
            from blender_config_sync.tui import main as tui_main
            tui_main()


if __name__ == '__main__':
    main()
