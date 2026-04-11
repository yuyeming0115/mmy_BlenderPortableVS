#!/usr/bin/env python3
"""
Tkinter GUI 诊断工具 - 用于测试和调试界面问题
"""

import tkinter as tk
from tkinter import ttk


def test_basic_tkinter():
    """测试 1: 最基本的 Tkinter 窗口"""
    print("🔍 测试 1: 基本 Tkinter 窗口...")
    
    root = tk.Tk()
    root.title("测试窗口 1")
    root.geometry("400x300")
    
    label = tk.Label(root, text="如果你能看到这个文字，Tkinter 正常工作！", 
                     font=("Arial", 14), fg="blue")
    label.pack(pady=50)
    
    btn = tk.Button(root, text="点击关闭", command=root.destroy)
    btn.pack(pady=20)
    
    print("   ✅ 基本窗口已创建")
    print("   ⏳ 请检查是否弹出了窗口...")
    
    # 强制更新显示
    root.update()
    root.mainloop()


def test_ttk_widgets():
    """测试 2: TTK 组件（我们实际使用的）"""
    print("\n🔍 测试 2: TTK 组件...")
    
    root = tk.Tk()
    root.title("测试窗口 2 - TTK 组件")
    root.geometry("600x500")
    
    # 使用与我们的应用相同的组件
    frame = ttk.Frame(root, padding="10")
    frame.pack(fill=tk.BOTH, expand=True)
    
    # 标签页
    notebook = ttk.Notebook(frame)
    notebook.pack(fill=tk.BOTH, expand=True)
    
    tab1 = ttk.Frame(notebook, padding="10")
    tab2 = ttk.Frame(notebook, padding="10")
    notebook.add(tab1, text="标签页 1")
    notebook.add(tab2, text="标签页 2")
    
    # 在标签页1中添加内容
    ttk.Label(tab1, text="这是 TTK Label", font=("Arial", 12)).pack(pady=20)
    
    var = tk.StringVar(value="选项 A")
    combo = ttk.Combobox(tab1, textvariable=var, values=["选项 A", "选项 B", "选项 C"])
    combo.pack(pady=10)
    
    tree = ttk.Treeview(tab2, columns=('col1', 'col2'), show='headings', height=8)
    tree.heading('col1', text='列 1')
    tree.heading('col2', text='列 2')
    tree.column('col1', width=200)
    tree.column('col2', width=200)
    
    # 添加一些示例数据
    for i in range(5):
        tree.insert('', tk.END, values=(f'项目 {i+1}', f'值 {i+1}'))
    
    tree.pack(fill=tk.BOTH, expand=True, pady=10)
    
    # 按钮
    btn_frame = ttk.Frame(tab2)
    btn_frame.pack(fill=tk.X, pady=10)
    ttk.Button(btn_frame, text="按钮 1").pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="按钮 2").pack(side=tk.LEFT, padx=5)
    
    # 状态栏
    status = ttk.Label(root, text="状态栏: TTK 组件测试中...", relief=tk.SUNKEN)
    status.pack(side=tk.BOTTOM, fill=tk.X)
    
    print("   ✅ TTK 组件已创建")
    print("   ⏳ 请检查窗口是否正常显示所有组件...")
    
    root.update_idletasks()
    root.mainloop()


def test_our_gui():
    """测试 3: 实际的 Blender Config Sync GUI"""
    print("\n🔍 测试 3: 完整的 Blender Config Sync GUI...")
    
    try:
        import sys
        from pathlib import Path
        
        # 添加项目路径
        sys.path.insert(0, str(Path(__file__).parent))
        
        from blender_config_sync.gui import BlenderConfigSyncApp
        
        print("   ✅ 导入成功，正在创建应用实例...")
        
        app = BlenderConfigSyncApp()
        print("   ✅ 应用实例已创建")
        print("   ⏳ 启动主循环...")
        
        app.run()
        
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")


if __name__ == '__main__':
    print("=" * 60)
    print("🔧 Tkinter GUI 诊断工具")
    print("=" * 60)
    print("\n这个工具会依次打开 3 个测试窗口来诊断问题。")
    print("请观察每个窗口是否正常显示。\n")
    
    print("请选择要运行的测试:")
    print("  1. 基本 Tkinter 窗口（最简单）")
    print("  2. TTK 组件窗口（中等复杂度）")
    print("  3. 完整的 Blender Config Sync GUI（完整版）")
    print("  0. 运行全部测试")
    
    choice = input("\n请输入选择 (0-3): ").strip()
    
    if choice == '1':
        test_basic_tkinter()
    elif choice == '2':
        test_ttk_widgets()
    elif choice == '3':
        test_our_gui()
    elif choice == '0':
        print("\n" + "="*60)
        print("开始测试 1/3: 基本 Tkinter 窗口")
        print("="*60 + "\n")
        test_basic_tkinter()
        
        print("\n" + "="*60)
        print("开始测试 2/3: TTK 组件窗口")
        print("="*60 + "\n")
        test_ttk_widgets()
        
        print("\n" + "="*60)
        print("开始测试 3/3: 完整 GUI")
        print("="*60 + "\n")
        test_our_gui()
    else:
        print("❌ 无效选择，默认运行测试 1...")
        test_basic_tkinter()
    
    print("\n✅ 所有测试完成！")
