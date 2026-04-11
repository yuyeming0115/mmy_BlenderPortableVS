"""
Blender Config Sync - 图形用户界面 (GUI)
使用 Tkinter 实现跨平台桌面应用
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from pathlib import Path
from typing import Optional, List
import json

from blender_config_sync.path_manager import BlenderPathManager, BlenderInstallation
from blender_config_sync.config_scanner import ConfigScanner
from blender_config_sync.backup_engine import BackupEngine
from blender_config_sync.diff_engine import DiffEngine, ComparisonResult, SyncAction


class BlenderConfigSyncApp:
    """主应用程序类"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Blender 配置同步工具 v0.2")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)

        # macOS 特定配置：改善外观和性能
        if self.root.tk.call('tk', 'windowingsystem') == 'aqua':
            self.root.createcommand('tk::mac::About', self.show_about)

        # 核心组件
        self.path_manager = BlenderPathManager()
        self.backup_engine = BackupEngine()
        self.diff_engine = DiffEngine()

        # 状态变量
        self.source_version_var = tk.StringVar()
        self.target_version_var = tk.StringVar()
        self.selected_diff_items = []

        # 创建界面
        self._create_menu()
        self._create_main_layout()

        # 强制刷新界面（解决 macOS 渲染延迟问题）
        self.root.update_idletasks()
        self.root.after(100, self._on_startup)

    def _create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="扫描配置", command=self.on_scan)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="备份当前配置", command=self.on_backup)
        tools_menu.add_command(label="比较两个版本", command=self.on_compare)
        tools_menu.add_command(label="列出所有备份", command=self.on_list_backups)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)

    def _create_main_layout(self):
        """创建主布局"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 顶部：版本选择区域
        version_frame = ttk.LabelFrame(main_frame, text="版本选择", padding="10")
        version_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(version_frame, text="源版本:").grid(row=0, column=0, padx=5, sticky='w')
        source_combo = ttk.Combobox(version_frame, textvariable=self.source_version_var,
                                    state="readonly", width=30)
        source_combo.grid(row=0, column=1, padx=5, sticky='w')

        ttk.Label(version_frame, text="→ 目标版本:").grid(row=0, column=2, padx=(20, 5), sticky='w')
        target_combo = ttk.Combobox(version_frame, textvariable=self.target_version_var,
                                    state="readonly", width=30)
        target_combo.grid(row=0, column=3, padx=5, sticky='w')

        btn_frame = ttk.Frame(version_frame)
        btn_frame.grid(row=1, column=0, columnspan=4, pady=(10, 0))

        ttk.Button(btn_frame, text="🔄 检测版本", command=self.detect_versions).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔍 扫描源配置", command=lambda: self.scan_config('source')).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔍 扫描目标配置", command=lambda: self.scan_config('target')).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="⚖️ 比较差异", command=self.on_compare).pack(side=tk.LEFT, padx=5)

        # 中间：Notebook 多标签页
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 标签页1：差异对比
        diff_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(diff_tab, text="📊 差异对比")

        self.diff_tree = ttk.Treeview(diff_tab, columns=('category', 'type', 'name', 'diff', 'action', 'risk'),
                                      show='headings', height=15)
        self.diff_tree.heading('category', text='分类')
        self.diff_tree.heading('type', text='类型')
        self.diff_tree.heading('name', text='名称')
        self.diff_tree.heading('diff', text='差异类型')
        self.diff_tree.heading('action', text='推荐操作')
        self.diff_tree.heading('risk', text='风险')

        self.diff_tree.column('category', width=100)
        self.diff_tree.column('type', width=100)
        self.diff_tree.column('name', width=250)
        self.diff_tree.column('diff', width=120)
        self.diff_tree.column('action', width=100)
        self.diff_tree.column('risk', width=60)

        scrollbar_y = ttk.Scrollbar(diff_tab, orient=tk.VERTICAL, command=self.diff_tree.yview)
        self.diff_tree.configure(yscrollcommand=scrollbar_y.set)

        self.diff_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        # 差异操作按钮
        diff_btn_frame = ttk.Frame(diff_tab)
        diff_btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(diff_btn_frame, text="✅ 全选", command=self.select_all_diffs).pack(side=tk.LEFT, padx=5)
        ttk.Button(diff_btn_frame, text="❌ 取消全选", command=self.deselect_all_diffs).pack(side=tk.LEFT, padx=5)
        ttk.Button(diff_btn_frame, text="📥 同步到目标", command=self.sync_to_target).pack(side=tk.LEFT, padx=5)
        ttk.Button(diff_btn_frame, text="💾 导出报告", command=self.export_report).pack(side=tk.LEFT, padx=5)

        # 标签页2：详细信息
        detail_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(detail_tab, text="📋 详细信息")

        self.detail_text = scrolledtext.ScrolledText(detail_tab, wrap=tk.WORD, height=25)
        self.detail_text.pack(fill=tk.BOTH, expand=True)

        # 标签页3：备份管理
        backup_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(backup_tab, text="💾 备份管理")

        self.backup_tree = ttk.Treeview(backup_tab, columns=('filename', 'size', 'version', 'time'),
                                         show='headings', height=12)
        self.backup_tree.heading('filename', text='备份文件名')
        self.backup_tree.heading('size', text='大小 (MB)')
        self.backup_tree.heading('version', text='Blender 版本')
        self.backup_tree.heading('time', text='创建时间')

        self.backup_tree.column('filename', width=300)
        self.backup_tree.column('size', width=80)
        self.backup_tree.column('version', width=100)
        self.backup_tree.column('time', width=150)

        self.backup_tree.pack(fill=tk.BOTH, expand=True)

        backup_btn_frame = ttk.Frame(backup_tab)
        backup_btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(backup_btn_frame, text="🔄 刷新列表", command=self.on_list_backups).pack(side=tk.LEFT, padx=5)
        ttk.Button(backup_btn_frame, text="🗑️ 删除选中", command=self.delete_backup).pack(side=tk.LEFT, padx=5)

        # 底部：状态栏
        status_bar = ttk.Frame(main_frame)
        status_bar.pack(fill=tk.X, pady=(10, 0))
        self.status_label = ttk.Label(status_bar, text="就绪 - 请先检测 Blender 版本")
        self.status_label.pack(side=tk.LEFT)

        # 绑定事件
        self.diff_tree.bind('<Double-1>', self.on_diff_double_click)
        self.backup_tree.bind('<Double-1>', self.on_backup_double_click)

    def detect_versions(self):
        """检测已安装的 Blender 版本"""
        self.status_label.config(text="正在检测 Blender 版本...")
        self.root.update()

        versions = self.path_manager.detect_installed_versions()

        if not versions:
            messagebox.showwarning("警告", "未检测到任何 Blender 安装！\n\n请确保已安装 Blender 并至少保存过一次用户设置。")
            self.status_label.config(text="未找到 Blender 版本")
            return

        version_list = [v.version for v in versions]
        source_combo = None
        for child in self.root.winfo_children():
            for subchild in child.winfo_children():
                if isinstance(subcombo := subchild, ttk.Combobox) and 'source' in str(subcombo.cget('textvariable')):
                    source_combo = subcombo

        for widget in self.root.winfo_children():
            self._update_combos(widget, version_list)

        if len(versions) >= 2:
            self.source_version_var.set(versions[0].version)
            self.target_version_var.set(versions[1].version)
        else:
            self.source_version_var.set(versions[0].version)

        self.status_label.config(text=f"✅ 检测到 {len(versions)} 个 Blender 版本")

    def _update_combos(self, parent, values):
        """递归更新 Combobox"""
        for child in parent.winfo_children():
            if isinstance(child, ttk.Combobox):
                child['values'] = values
            else:
                self._update_combos(child, values)

    def scan_config(self, config_type: str):
        """扫描指定版本的配置"""
        version_str = self.source_version_var.get() if config_type == 'source' else self.target_version_var.get()

        if not version_str:
            messagebox.showwarning("警告", f"请先选择{'源' if config_type == 'source' else '目标'} Blender 版本")
            return

        installations = [v for v in self.path_manager.detect_installed_versions() if v.version == version_str]
        if not installations:
            messagebox.showerror("错误", f"未找到 Blender {version_str}")
            return

        scanner = ConfigScanner(installations[0].config_path)
        report = scanner.scan_all_configs()

        detail_text = f"{'源' if config_type == 'source' else '目标'}配置扫描结果 - Blender {version_str}\n"
        detail_text += "=" * 60 + "\n\n"
        detail_text += f"配置路径: {report['config_base']}\n"
        detail_text += f"扫描时间: {report['scan_time']}\n\n"

        detail_text += f"统计:\n"
        detail_text += f"  • 已存在配置项: {report['summary']['existing_count']}/{report['summary']['total_types_scanned']}\n"
        detail_text += f"  • 总大小: {report['summary']['total_size_bytes'] / 1024:.1f} KB\n\n"

        detail_text += "详细配置:\n"
        for cfg_type, info in report['configs'].items():
            status = "✅" if info['exists'] else "❌"
            size = f"{info['size_bytes'] / 1024:.1f} KB" if info['size_bytes'] > 0 else "-"
            detail_text += f"  {status} {cfg_type:<25} {size:>10}\n"

        bookmarks = scanner.read_bookmarks()
        detail_text += f"\n书签 ({bookmarks.count} 个):\n"
        for bm in bookmarks.paths[:10]:
            detail_text += f"  📁 {bm}\n"

        addons = scanner.list_addons()
        detail_text += f"\n插件 ({len(addons)} 个):\n"
        for addon in addons[:15]:
            bl_ver = addon.bl_info.get('blender', '?') if addon.bl_info else '?'
            detail_text += f"  🔌 {addon.name:<30} [支持: {bl_ver}]\n"

        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(tk.END, detail_text)
        self.notebook.select(1)

        self.status_label.config(text=f"✅ {'源' if config_type == 'source' else '目标'}配置扫描完成")

    def on_compare(self):
        """执行配置比较"""
        source_ver = self.source_version_var.get()
        target_ver = self.target_version_var.get()

        if not source_ver or not target_ver:
            messagebox.showwarning("警告", "请先选择源版本和目标版本")
            return

        if source_ver == target_ver:
            messagebox.showwarning("警告", "源版本和目标版本不能相同")
            return

        self.status_label.config(text=f"正在比较 {source_ver} → {target_ver} ...")
        self.root.update()

        installations = {v.version: v for v in self.path_manager.detect_installed_versions()}

        if source_ver not in installations or target_ver not in installations:
            messagebox.showerror("错误", "选择的版本不存在")
            return

        try:
            result = self.diff_engine.compare(
                source_path=installations[source_ver].config_path,
                target_path=installations[target_ver].config_path,
                source_version=source_ver,
                target_version=target_ver
            )

            self._display_comparison_result(result)

            self.status_label.config(
                text=f"✅ 比较完成 - 共发现 {result.total_items} 项差异"
            )

        except Exception as e:
            messagebox.showerror("错误", f"比较失败: {str(e)}")
            self.status_label.config(text="❌ 比较失败")

    def _display_comparison_result(self, result: ComparisonResult):
        """显示比较结果"""
        # 清空树视图
        for item in self.diff_tree.get_children():
            self.diff_tree.delete(item)

        category_icons = {
            'bookmarks': '📑',
            'addons': '🔌',
            'preferences': '⚙️',
            'startup_scripts': '🚀'
        }

        diff_type_icons = {
            'only_in_source': '➕',
            'only_in_target': '➖',
            'modified': '✏️',
            'identical': '✅',
            'conflict': '⚠️'
        }

        action_texts = {
            'sync_to_target': '→ 同步',
            'keep_target': '← 保留',
            'merge': '↔ 合并',
            'skip': '⊘ 跳过'
        }

        risk_icons = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🔴'
        }

        for item in result.diff_items:
            cat_icon = category_icons.get(item.category, '')
            diff_icon = diff_type_icons.get(item.diff_type.value, '')
            action_text = action_texts.get(item.recommended_action.value, '')
            risk_icon = risk_icons.get(item.risk_level, '')

            self.diff_tree.insert('', tk.END, values=(
                f"{cat_icon} {item.category}",
                item.item_type,
                item.name,
                f"{diff_icon} {item.diff_type.value.replace('_', ' ').title()}",
                action_text,
                risk_icon
            ), tags=(item.risk_level,))

        # 设置颜色标签
        self.diff_tree.tag_configure('low', foreground='green')
        self.diff_tree.tag_configure('medium', foreground='orange')
        self.diff_tree.tag_configure('high', foreground='red')

        # 显示文本报告
        from blender_config_sync.diff_engine import generate_text_report
        text_report = generate_text_report(result)
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(tk.END, text_report)

        # 切换到差异标签页
        self.notebook.select(0)

        # 保存结果供后续操作
        self.current_result = result

    def select_all_diffs(self):
        """全选所有差异项"""
        for item in self.diff_tree.get_children():
            self.diff_tree.selection_add(item)

    def deselect_all_diffs(self):
        """取消全选"""
        self.diff_tree.selection_remove(self.diff_tree.get_children())

    def sync_to_target(self):
        """同步选中的差异到目标"""
        selected = self.diff_tree.selection()

        if not selected:
            messagebox.showinfo("提示", "请先在差异列表中选择要同步的项目")
            return

        if not hasattr(self, 'current_result'):
            messagebox.showwarning("警告", "还没有执行过比较操作")
            return

        confirm = messagebox.askyesno(
            "确认同步",
            f"确定要将选中的 {len(selected)} 项配置同步到目标版本吗？\n\n"
            "建议先备份目标配置！"
        )

        if not confirm:
            return

        self.status_label.config(text=f"正在同步 {len(selected)} 项配置...")
        self.root.update()

        try:
            synced_count = 0
            for idx, item_id in enumerate(selected):
                item_idx = int(str(item_id)) - 1 if str(item_id).isdigit() else 0
                if item_idx < len(self.current_result.diff_items):
                    diff_item = self.current_result.diff_items[item_idx]
                    diff_item.user_action = SyncAction.SYNC_TO_TARGET
                    synced_count += 1

            messagebox.showinfo("成功", f"已标记 {synced_count} 项用于同步\n\n实际同步功能将在下一版本实现")
            self.status_label.config(text=f"✅ 已选择 {synced_count} 项待同步")

        except Exception as e:
            messagebox.showerror("错误", f"同步失败: {str(e)}")

    def export_report(self):
        """导出比较报告"""
        if not hasattr(self, 'current_result'):
            messagebox.showwarning("警告", "还没有可导出的比较结果")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            initialfilename=f"comparison_{self.current_result.source_version}_to_{self.current_result.target_version}.json"
        )

        if save_path:
            output_path = Path(save_path)
            result_path = self.diff_engine.export_comparison_report(self.current_result, output_path)
            messagebox.showinfo("成功", f"报告已导出到:\n{result_path}")

    def on_backup(self):
        """执行备份操作"""
        version_str = self.source_version_var.get()
        if not version_str:
            messagebox.showwarning("警告", "请先选择要备份的 Blender 版本")
            return

        installations = [v for v in self.path_manager.detect_installed_versions() if v.version == version_str]
        if not installations:
            messagebox.showerror("错误", f"未找到 Blender {version_str}")
            return

        self.status_label.config(text=f"正在备份 Blender {version_str} 的配置...")
        self.root.update()

        result = self.backup_engine.create_backup(
            config_path=installations[0].config_path,
            blender_version=version_str,
            include_addons=True
        )

        if result.success:
            messagebox.showinfo("备份成功", f"{result.message}\n\n位置: {result.backup_path}")
            self.on_list_backups()
        else:
            messagebox.showerror("备份失败", result.message)

        self.status_label.config(text="就绪")

    def on_list_backups(self):
        """列出所有备份"""
        for item in self.backup_tree.get_children():
            self.backup_tree.delete(item)

        backups = self.backup_engine.list_backups()

        for backup in backups:
            self.backup_tree.insert('', tk.END, values=(
                backup['filename'],
                f"{backup['size_mb']:.2f}",
                backup['blender_version'],
                backup['created_at'][:19]
            ))

        self.notebook.select(2)
        self.status_label.config(text=f"✅ 共 {len(backups)} 个备份记录")

    def delete_backup(self):
        """删除选中的备份"""
        selected = self.backup_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择要删除的备份")
            return

        filename = self.backup_tree.item(selected[0], 'values')[0]
        confirm = messagebox.askyesno("确认删除", f"确定要删除备份:\n{filename}\n\n此操作不可恢复！")

        if confirm:
            backups_dir = Path.cwd() / 'backups'
            backup_path = backups_dir / filename
            if self.backup_engine.delete_backup(backup_path):
                messagebox.showinfo("成功", "备份已删除")
                self.on_list_backups()
            else:
                messagebox.showerror("错误", "删除失败")

    def on_scan(self):
        """菜单：扫描配置"""
        self.scan_config('source')

    def on_diff_double_click(self, event):
        """双击差异项查看详情"""
        selection = self.diff_tree.selection()
        if not selection or not hasattr(self, 'current_result'):
            return

        item_id = selection[0]
        values = self.diff_tree.item(item_id, 'values')
        name = values[2]

        detail = f"项目详情: {name}\n"
        detail += "=" * 50 + "\n\n"

        for item in self.current_result.diff_items:
            if item.name == name:
                detail += f"分类: {item.category}\n"
                detail += f"类型: {item.item_type}\n"
                detail += f"差异: {item.diff_type.value}\n"
                detail += f"推荐操作: {item.recommended_action.value}\n"
                detail += f"风险等级: {item.risk_level}\n\n"

                if item.details:
                    detail += "详细信息:\n"
                    for key, value in item.details.items():
                        detail += f"  • {key}: {value}\n"

                break

        messagebox.showinfo("详情", detail)

    def on_backup_double_click(self, event):
        """双击备份查看信息"""
        selection = self.backup_tree.selection()
        if not selection:
            return

        values = self.backup_tree.item(selection[0], 'values')
        filename = values[0]

        backups_dir = Path.cwd() / 'backups'
        backup_path = backups_dir / filename

        manifest = self.backup_engine.read_manifest(backup_path)

        if manifest:
            info = f"备份信息: {filename}\n"
            info += "=" * 50 + "\n\n"
            info += f"创建时间: {manifest.created_at}\n"
            info += f"源版本: {manifest.source_blender_version}\n"
            info += f"文件数量: {len(manifest.files)}\n"
            info += f"总大小: {manifest.total_size / 1024:.1f} KB\n"
            info += f"校验和: {manifest.checksum[:32]}..."

            messagebox.showinfo("备份信息", info)

    def _on_startup(self):
        """启动时自动执行的操作"""
        # 显示欢迎信息
        welcome_text = """
🎨 Blender 配置同步工具 v0.2
========================

欢迎使用！本工具可以帮助你：
• 检测已安装的 Blender 版本
• 扫描和备份配置文件
• 比较不同版本的配置差异
• 选择性同步配置到目标版本

快速开始：
1. 点击 "🔄 检测版本" 按钮
2. 选择源版本和目标版本
3. 点击 "⚖️ 比较差异" 查看详细对比
4. 勾选需要同步的项目并点击 "📥 同步到目标"

提示：如果没有检测到 Blender，请确保已安装 Blender 并至少保存过一次用户设置。
"""
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(tk.END, welcome_text.strip())
        self.notebook.select(1)  # 切换到详细信息标签页

        # 自动检测版本（可选）
        self.status_label.config(text="就绪 - 点击 '🔄 检测版本' 开始使用")

    def show_about(self):
        """显示关于对话框"""
        about_text = """
Blender 配置同步工具 v0.2
========================

一款专业的 Blender 个人配置管理工具，
帮助你轻松在不同版本间同步收藏夹、快捷键、插件等配置。

核心功能:
• 自动检测已安装的 Blender 版本
• 配置文件扫描与分析
• 跨版本配置差异比较
• 一键备份与恢复
• 插件兼容性检查

技术栈:
Python 3.9+ | Tkinter | 纯标准库实现

作者: MMY
License: MIT
        """
        messagebox.showinfo("关于", about_text.strip())

    def run(self):
        """运行应用"""
        self.root.mainloop()


def main():
    """程序入口"""
    app = BlenderConfigSyncApp()
    app.run()


if __name__ == '__main__':
    main()
