"""
Blender Config Sync - PyQt6 图形用户界面 (GUI)
现代化、跨平台桌面应用，解决 macOS Tkinter 兼容性问题
"""

import sys
from pathlib import Path
from typing import Optional, List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QTabWidget, QTextEdit, QGroupBox, QMessageBox, QFileDialog,
    QTreeWidget, QTreeWidgetItem, QSplitter, QFrame,
    QProgressBar, QStatusBar, QMenuBar, QMenu,
    QDialog, QDialogButtonBox, QCheckBox, QAbstractItemView,
    QLineEdit
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QMimeData
from PyQt6.QtGui import QIcon, QFont, QColor, QAction, QDragEnterEvent, QDropEvent

from blender_config_sync.path_manager import BlenderPathManager, BlenderInstallation
from blender_config_sync.config_scanner import ConfigScanner
from blender_config_sync.backup_engine import BackupEngine
from blender_config_sync.diff_engine import (
    DiffEngine, ComparisonResult, DiffType, SyncAction, generate_text_report
)


class BlenderConfigSyncPyQt(QMainWindow):
    """主窗口类 - PyQt6 版本"""

    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("🎨 Blender 配置同步工具 v0.3 (PyQt6)")
        self.setGeometry(100, 100, 1100, 750)
        self.setMinimumSize(900, 650)
        
        # 设置深色主题（macOS 友好）
        self._setup_style()
        
        # 核心组件
        self.path_manager = BlenderPathManager()
        self.backup_engine = BackupEngine()
        self.diff_engine = DiffEngine()
        
        # 数据存储
        self.source_version_var = ""
        self.target_version_var = ""
        self.current_result: Optional[ComparisonResult] = None
        self.detected_versions: List[BlenderInstallation] = []
        
        # 创建 UI
        self._create_menu_bar()
        self._create_central_widget()
        self._create_status_bar()
        
        # 显示欢迎信息
        QTimer.singleShot(100, self._show_welcome)
    
    def _setup_style(self):
        """设置应用样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QGroupBox {
                border: 1px solid #555;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:pressed {
                background-color: #006cbd;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
            QComboBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #555;
                padding: 6px;
                border-radius: 4px;
                min-width: 200px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                selection-background-color: #0078d4;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #383838;
                color: #aaa;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #2b2b2b;
                color: white;
                font-weight: bold;
            }
            QTableWidget {
                gridline-color: #444;
                border: 1px solid #444;
                border-radius: 4px;
                alternate-background-color: #333;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: white;
                padding: 6px;
                border: 1px solid #555;
                font-weight: bold;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 8px;
            }
            QStatusBar {
                background-color: #007acc;
                color: white;
                font-size: 12px;
            }
            QLabel#titleLabel {
                font-size: 18px;
                font-weight: bold;
                color: #fff;
            }
        """)
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("📁 文件")
        file_menu.addAction("🔍 扫描配置", self.on_scan_source)
        file_menu.addSeparator()
        file_menu.addAction("❌ 退出", self.close)
        
        tools_menu = menubar.addMenu("🛠️ 工具")
        tools_menu.addAction("💾 备份当前配置", self.on_backup)
        tools_menu.addAction("⚖️ 比较两个版本", self.on_compare)
        tools_menu.addAction("📋 列出所有备份", self.on_list_backups)
        
        help_menu = menubar.addMenu("❓ 帮助")
        help_menu.addAction("ℹ️ 关于", self.show_about)
    
    def _create_central_widget(self):
        """创建中央部件"""
        central = QWidget()
        self.setCentralWidget(central)
        
        # 启用拖放功能
        self.setAcceptDrops(True)
        
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 顶部：版本选择区域
        version_group = QGroupBox("📍 版本选择与操作")
        version_main_layout = QVBoxLayout(version_group)
        
        # 拖拽区域（虚线框）
        drop_frame = QFrame()
        drop_frame.setFrameShape(QFrame.Shape.StyledPanel)
        drop_frame.setStyleSheet("""
            QFrame {
                border: 2px dashed #666;
                border-radius: 8px;
                background-color: #333;
                padding: 10px;
            }
        """)
        drop_layout = QHBoxLayout(drop_frame)
        drop_layout.setSpacing(20)
        drop_layout.setContentsMargins(15, 15, 15, 15)
        
        # 左侧：源版本
        source_col = QVBoxLayout()
        source_col.setSpacing(8)
        source_header = QHBoxLayout()
        source_label = QLabel("📤 源版本:")
        source_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #4FC3F7;")
        source_header.addWidget(source_label)
        source_header.addStretch()
        
        source_controls = QHBoxLayout()
        source_controls.setSpacing(8)
        self.source_combo = QComboBox()
        self.source_combo.setMinimumWidth(180)
        self.source_browse_btn = QPushButton("📂 浏览")
        self.source_browse_btn.setToolTip("手动选择 Blender 配置目录\n或拖拽文件夹到窗口上")
        self.source_browse_btn.clicked.connect(lambda: self.browse_blender_path('source'))
        source_controls.addWidget(self.source_combo)
        source_controls.addWidget(self.source_browse_btn)
        
        self.source_path_label = QLabel("")
        self.source_path_label.setStyleSheet("color: #888; font-size: 10px;")
        self.source_path_label.setWordWrap(True)
        
        source_col.addLayout(source_header)
        source_col.addLayout(source_controls)
        source_col.addWidget(self.source_path_label)
        
        # 中间分隔
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setStyleSheet("background-color: #555;")
        
        # 右侧：目标版本
        target_col = QVBoxLayout()
        target_col.setSpacing(8)
        target_header = QHBoxLayout()
        target_label = QLabel("📥 目标版本:")
        target_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #81C784;")
        target_header.addWidget(target_label)
        target_header.addStretch()
        
        target_controls = QHBoxLayout()
        target_controls.setSpacing(8)
        self.target_combo = QComboBox()
        self.target_combo.setMinimumWidth(180)
        self.target_browse_btn = QPushButton("📂 浏览")
        self.target_browse_btn.setToolTip("手动选择 Blender 配置目录\n或拖拽文件夹到窗口上")
        self.target_browse_btn.clicked.connect(lambda: self.browse_blender_path('target'))
        target_controls.addWidget(self.target_combo)
        target_controls.addWidget(self.target_browse_btn)
        
        self.target_path_label = QLabel("")
        self.target_path_label.setStyleSheet("color: #888; font-size: 10px;")
        self.target_path_label.setWordWrap(True)
        
        target_col.addLayout(target_header)
        target_col.addLayout(target_controls)
        target_col.addWidget(self.target_path_label)
        
        drop_layout.addLayout(source_col, 1)
        drop_layout.addWidget(divider)
        drop_layout.addLayout(target_col, 1)
        
        # 第三行：操作按钮
        btn_layout = QHBoxLayout()
        detect_btn = QPushButton("🔄 检测版本")
        detect_btn.clicked.connect(self.detect_versions)
        scan_src_btn = QPushButton("🔍 扫描源配置")
        scan_src_btn.clicked.connect(lambda: self.scan_config('source'))
        scan_tgt_btn = QPushButton("🔍 扫描目标配置")
        scan_tgt_btn.clicked.connect(lambda: self.scan_config('target'))
        compare_btn = QPushButton("⚖️ 比较差异")
        compare_btn.clicked.connect(self.on_compare)
        compare_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #34ce57;
            }
        """)
        
        btn_layout.addWidget(detect_btn)
        btn_layout.addWidget(scan_src_btn)
        btn_layout.addWidget(scan_tgt_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(compare_btn)
        
        # 提示标签
        hint_label = QLabel("💡 提示：可以拖拽 Blender 配置文件夹到窗口上快速添加")
        hint_label.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        
        version_main_layout.addWidget(drop_frame)
        version_main_layout.addLayout(btn_layout)
        version_main_layout.addWidget(hint_label)
        
        layout.addWidget(version_group)
        
        # 中间：标签页区域
        self.tab_widget = QTabWidget()
        
        # 标签页 1：差异对比
        diff_tab = QWidget()
        diff_layout = QVBoxLayout(diff_tab)
        
        self.diff_table = QTableWidget()
        self.diff_table.setColumnCount(6)
        self.diff_table.setHorizontalHeaderLabels([
            '分类', '类型', '名称', '差异类型', '推荐操作', '风险'
        ])
        self.diff_table.setAlternatingRowColors(True)
        self.diff_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.diff_table.doubleClicked.connect(self.on_diff_double_click)
        self.diff_table.horizontalHeader().setStretchLastSection(True)
        
        diff_btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("✅ 全选")
        select_all_btn.clicked.connect(self.select_all_diffs)
        deselect_all_btn = QPushButton("❌ 取消全选")
        deselect_all_btn.clicked.connect(self.deselect_all_diffs)
        sync_btn = QPushButton("📥 同步到目标")
        sync_btn.setStyleSheet("background-color: #17a2b8;")
        sync_btn.clicked.connect(self.sync_to_target)
        export_btn = QPushButton("💾 导出报告")
        export_btn.clicked.connect(self.export_report)
        
        diff_btn_layout.addWidget(select_all_btn)
        diff_btn_layout.addWidget(deselect_all_btn)
        diff_btn_layout.addStretch()
        diff_btn_layout.addWidget(sync_btn)
        diff_btn_layout.addWidget(export_btn)
        
        diff_layout.addWidget(self.diff_table)
        diff_layout.addLayout(diff_btn_layout)
        
        self.tab_widget.addTab(diff_tab, "📊 差异对比")
        
        # 标签页 2：详细信息
        detail_tab = QWidget()
        detail_layout = QVBoxLayout(detail_tab)
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setFont(QFont("Monaco", 11))
        detail_layout.addWidget(self.detail_text)
        
        self.tab_widget.addTab(detail_tab, "📋 详细信息")
        
        # 标签页 3：备份管理
        backup_tab = QWidget()
        backup_layout = QVBoxLayout(backup_tab)
        
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(4)
        self.backup_table.setHorizontalHeaderLabels(['备份文件名', '大小 (MB)', 'Blender 版本', '创建时间'])
        self.backup_table.setAlternatingRowColors(True)
        self.backup_table.doubleClicked.connect(self.on_backup_double_click)
        self.backup_table.horizontalHeader().setStretchLastSection(True)
        
        backup_btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 刷新列表")
        refresh_btn.clicked.connect(self.on_list_backups)
        delete_btn = QPushButton("🗑️ 删除选中")
        delete_btn.setStyleSheet("background-color: #dc3545;")
        delete_btn.clicked.connect(self.delete_backup)
        
        backup_btn_layout.addWidget(refresh_btn)
        backup_btn_layout.addWidget(delete_btn)
        
        backup_layout.addWidget(self.backup_table)
        backup_layout.addLayout(backup_btn_layout)
        
        self.tab_widget.addTab(backup_tab, "💾 备份管理")
        
        layout.addWidget(self.tab_widget)
    
    def _create_status_bar(self):
        """创建状态栏"""
        status = QStatusBar()
        self.setStatusBar(status)
        self.status_label = QLabel("就绪 - 点击 '🔄 检测版本' 开始使用")
        status.addWidget(self.status_label, 1)
    
    def _show_welcome(self):
        """显示欢迎信息"""
        welcome_text = """
╔════════════════════════════════════════════════════════════╗
║                                                              ║
║   🎨 Blender 配置同步工具 v0.3 (PyQt6 版)                  ║
║                                                              ║
║   欢迎使用！本工具可以帮助你：                               ║
║   • 检测已安装的 Blender 版本                                ║
║   • 扫描和备份配置文件                                        ║
║   • 比较不同版本的配置差异                                    ║
║   • 选择性同步配置到目标版本                                  ║
║                                                              ║
║   快速开始：                                                 ║
║   1. 点击 [🔄 检测版本] 按钮                                 ║
║   2. 选择源版本和目标版本                                     ║
║   3. 点击 [⚖️ 比较差异] 查看详细对比                          ║
║   4. 勾选需要同步的项目并点击 [📥 同步到目标]                 ║
║                                                              ║
║   💡 提示：如果没有检测到 Blender，请确保已安装并保存过设置     ║
║                                                              ║
╚════════════════════════════════════════════════════════════╝
"""
        self.detail_text.setText(welcome_text.strip())
        self.tab_widget.setCurrentIndex(1)  # 切换到详情标签页
    
    def detect_versions(self):
        """检测已安装的 Blender 版本"""
        self.status_label.setText("🔄 正在检测 Blender 版本...")
        QApplication.processEvents()
        
        self.detected_versions = self.path_manager.detect_installed_versions()
        
        if not self.detected_versions:
            QMessageBox.warning(
                self, "未找到 Blender",
                "未检测到任何 Blender 安装！\n\n"
                "请确保：\n"
                "• 已安装 Blender\n"
                "• 至少保存过一次用户设置（Edit → Preferences → Save Preferences）"
            )
            self.status_label.setText("❌ 未检测到 Blender 版本")
            return
        
        self.source_combo.clear()
        self.target_combo.clear()
        
        for inst in self.detected_versions:
            display_text = f"Blender {inst.version}"
            self.source_combo.addItem(display_text, inst.version)
            self.target_combo.addItem(display_text, inst.version)
        
        if len(self.detected_versions) >= 2:
            self.source_combo.setCurrentIndex(0)
            self.target_combo.setCurrentIndex(1)
        else:
            self.source_combo.setCurrentIndex(0)
        
        self.status_label.setText(f"✅ 检测到 {len(self.detected_versions)} 个 Blender 版本")
    
    def scan_config(self, config_type: str):
        """扫描指定版本的配置"""
        if not self.detected_versions:
            QMessageBox.warning(self, "警告", "请先检测 Blender 版本")
            return
        
        if config_type == 'source':
            idx = self.source_combo.currentIndex()
            ver_str = self.source_combo.currentData() or self.source_combo.currentText().replace("Blender ", "")
        else:
            idx = self.target_combo.currentIndex()
            ver_str = self.target_combo.currentData() or self.target_combo.currentText().replace("Blender ", "")
        
        if idx < 0 or idx >= len(self.detected_versions):
            QMessageBox.warning(self, "警告", f"请先选择{'源' if config_type == 'source' else '目标'} Blender 版本")
            return
        
        installation = self.detected_versions[idx]
        scanner = ConfigScanner(installation.config_path)
        report = scanner.scan_all_configs()
        
        detail_text = f"{'源' if config_type == 'source' else '目标'}配置扫描结果 - Blender {installation.version}\n"
        detail_text += "=" * 70 + "\n\n"
        detail_text += f"📍 配置路径: {report['config_base']}\n"
        detail_text += f"⏰ 扫描时间: {report['scan_time']}\n\n"
        
        detail_text += f"📈 统计:\n"
        detail_text += f"  • 已存在配置项: {report['summary']['existing_count']}/{report['summary']['total_types_scanned']}\n"
        detail_text += f"  • 总大小: {report['summary']['total_size_bytes'] / 1024:.1f} KB\n\n"
        
        detail_text += "📋 详细配置:\n"
        detail_text += "-" * 50 + "\n"
        for cfg_type, info in report['configs'].items():
            status = "✅" if info['exists'] else "❌"
            size = f"{info['size_bytes'] / 1024:.1f} KB" if info['size_bytes'] > 0 else "-"
            modified = info.get('modified_time', 'N/A')[:19] if info.get('modified_time') else 'N/A'
            detail_text += f"  {status} {cfg_type:<25} {size:>10}  {modified}\n"
        
        bookmarks = scanner.read_bookmarks()
        detail_text += f"\n📑 书签 ({bookmarks.count} 个):\n"
        for bm in bookmarks.paths[:15]:
            detail_text += f"  📁 {bm}\n"
        if len(bookmarks.paths) > 15:
            detail_text += f"  ... 还有 {len(bookmarks.paths) - 15} 个\n"
        
        addons = scanner.list_addons()
        detail_text += f"\n🔌 插件 ({len(addons)} 个):\n"
        for addon in addons[:20]:
            bl_ver = addon.bl_info.get('blender', '?') if addon.bl_info else '?'
            detail_text += f"  🔌 {addon.name:<30} [支持: {bl_ver}]\n"
        if len(addons) > 20:
            detail_text += f"  ... 还有 {len(addons) - 20} 个\n"
        
        self.detail_text.setText(detail_text)
        self.tab_widget.setCurrentIndex(1)
        self.status_label.setText(f"✅ {'源' if config_type == 'source' else '目标'}配置扫描完成")
    
    def on_compare(self):
        """执行配置比较"""
        src_idx = self.source_combo.currentIndex()
        tgt_idx = self.target_combo.currentIndex()
        
        if src_idx < 0 or tgt_idx < 0 or not self.detected_versions:
            QMessageBox.warning(self, "警告", "请先选择源版本和目标版本")
            return
        
        if src_idx == tgt_idx:
            QMessageBox.warning(self, "警告", "源版本和目标版本不能相同")
            return
        
        source_inst = self.detected_versions[src_idx]
        target_inst = self.detected_versions[tgt_idx]
        
        self.status_label.setText(f"⚖️ 正在比较 {source_inst.version} → {target_inst.version} ...")
        QApplication.processEvents()
        
        try:
            result = self.diff_engine.compare(
                source_path=source_inst.config_path,
                target_path=target_inst.config_path,
                source_version=source_inst.version,
                target_version=target_inst.version
            )
            
            self._display_comparison_result(result)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"比较失败: {str(e)}")
            self.status_label.setText("❌ 比较失败")
    
    def _display_comparison_result(self, result: ComparisonResult):
        """显示比较结果"""
        self.current_result = result
        
        # 清空表格
        self.diff_table.setRowCount(0)
        
        category_icons = {'bookmarks': '📑', 'addons': '🔌', 'preferences': '⚙️', 'startup_scripts': '🚀'}
        diff_icons = {
            'only_in_source': '➕', 'only_in_target': '➖',
            'modified': '✏️', 'identical': '✅', 'conflict': '⚠️'
        }
        action_texts = {
            'sync_to_target': '→ 同步', 'keep_target': '← 保留',
            'merge': '↔ 合并', 'skip': '⊘ 跳过'
        }
        risk_colors = {'low': '#28a745', 'medium': '#ffc107', 'high': '#dc3545'}
        
        for item in result.diff_items:
            row = self.diff_table.rowCount()
            self.diff_table.insertRow(row)
            
            cat_icon = category_icons.get(item.category, '')
            diff_icon = diff_icons.get(item.diff_type.value, '')
            action_text = action_texts.get(item.recommended_action.value, '')
            
            self.diff_table.setItem(row, 0, QTableWidgetItem(f"{cat_icon} {item.category}"))
            self.diff_table.setItem(row, 1, QTableWidgetItem(item.item_type))
            self.diff_table.setItem(row, 2, QTableWidgetItem(item.name))
            self.diff_table.setItem(row, 3, QTableWidgetItem(f"{diff_icon} {item.diff_type.value.replace('_', ' ').title()}"))
            self.diff_table.setItem(row, 4, QTableWidgetItem(action_text))
            
            risk_item = QTableWidgetItem(item.risk_level.upper())
            risk_item.setForeground(QColor(risk_colors.get(item.risk_level, '#999')))
            self.diff_table.setItem(row, 5, risk_item)
        
        # 显示文本报告
        text_report = generate_text_report(result)
        self.detail_text.setText(text_report)
        
        # 切换到差异标签页
        self.tab_widget.setCurrentIndex(0)
        
        self.status_label.setText(
            f"✅ 比较完成 - 共发现 {result.total_items} 项差异 | "
            f"仅源端: {result.get_stats()['only_in_source']} | "
            f"仅目标: {result.get_stats()['only_in_target']} | "
            f"已修改: {result.get_stats()['modified']}"
        )
    
    def select_all_diffs(self):
        self.diff_table.selectAll()
    
    def deselect_all_diffs(self):
        self.diff_table.clearSelection()
    
    def sync_to_target(self):
        selected_rows = set(item.row() for item in self.diff_table.selectedItems())
        
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先在差异表格中选择要同步的项目")
            return
        
        if not self.current_result:
            QMessageBox.warning(self, "警告", "还没有执行过比较操作")
            return
        
        confirm = QMessageBox.question(
            self, "确认同步",
            f"确定要将选中的 {len(selected_rows)} 项配置同步到目标版本吗？\n\n"
            "建议先备份目标配置！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm != QMessageBox.StandardButton.Yes:
            return
        
        self.status_label.setText(f"🔄 正在标记 {len(selected_rows)} 项待同步...")
        QApplication.processEvents()
        
        synced_count = len(selected_rows)
        
        QMessageBox.information(
            self, "完成",
            f"已标记 {synced_count} 项用于同步\n\n"
            "实际同步功能将在下一版本实现。\n"
            "当前版本支持导出报告手动处理。"
        )
        
        self.status_label.setText(f"✅ 已选择 {synced_count} 项待同步")
    
    def export_report(self):
        if not self.current_result:
            QMessageBox.warning(self, "警告", "还没有可导出的比较结果")
            return
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, "导出报告", 
            f"comparison_{self.current_result.source_version}_to_{self.current_result.target_version}.json",
            "JSON 文件 (*.json);;所有文件 (*)"
        )
        
        if save_path:
            output_path = Path(save_path)
            result_path = self.diff_engine.export_comparison_report(self.current_result, output_path)
            QMessageBox.information(self, "成功", f"报告已导出到:\n{result_path}")
    
    def on_backup(self):
        if not self.detected_versions:
            QMessageBox.warning(self, "警告", "请先检测 Blender 版本")
            return
        
        idx = self.source_combo.currentIndex()
        if idx < 0:
            idx = 0
        
        installation = self.detected_versions[idx]
        
        confirm = QMessageBox.question(
            self, "确认备份",
            f"是否要备份 Blender {installation.version} 的配置？\n\n"
            "这将包含所有配置文件、插件和脚本。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm != QMessageBox.StandardButton.Yes:
            return
        
        self.status_label.setText(f"💾 正在备份 Blender {installation.version}...")
        QApplication.processEvents()
        
        result = self.backup_engine.create_backup(
            config_path=installation.config_path,
            blender_version=installation.version,
            include_addons=True
        )
        
        if result.success:
            QMessageBox.information(
                self, "备份成功",
                f"{result.message}\n\n位置: {result.backup_path}"
            )
            self.on_list_backups()
        else:
            QMessageBox.critical(self, "备份失败", result.message)
        
        self.status_label.setText("就绪")
    
    def on_list_backups(self):
        backups = self.backup_engine.list_backups()
        
        self.backup_table.setRowCount(0)
        
        for backup in backups:
            row = self.backup_table.rowCount()
            self.backup_table.insertRow(row)
            
            self.backup_table.setItem(row, 0, QTableWidgetItem(backup['filename']))
            self.backup_table.setItem(row, 1, QTableWidgetItem(f"{backup['size_mb']:.2f}"))
            self.backup_table.setItem(row, 2, QTableWidgetItem(backup['blender_version']))
            self.backup_table.setItem(row, 3, QTableWidgetItem(backup['created_at'][:19]))
        
        self.tab_widget.setCurrentIndex(2)
        self.status_label.setText(f"✅ 共 {len(backups)} 个备份记录")
    
    def delete_backup(self):
        selected = self.backup_table.selectedItems()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择要删除的备份")
            return
        
        row = selected[0].row()
        filename = self.backup_table.item(row, 0).text()
        
        confirm = QMessageBox.warning(
            self, "确认删除",
            f"确定要删除备份:\n{filename}\n\n此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            backups_dir = Path.cwd() / 'backups'
            backup_path = backups_dir / filename
            
            if self.backup_engine.delete_backup(backup_path):
                QMessageBox.information(self, "成功", "备份已删除")
                self.on_list_backups()
            else:
                QMessageBox.critical(self, "错误", "删除失败")
    
    def on_scan_source(self):
        self.scan_config('source')
    
    def on_diff_double_click(self, index):
        """双击查看差异详情"""
        if not self.current_result:
            return
        
        row = index.row()
        if row < 0 or row >= len(self.current_result.diff_items):
            return
        
        item = self.current_result.diff_items[row]
        
        detail = f"项目详情: {item.name}\n"
        detail += "=" * 50 + "\n\n"
        detail += f"分类: {item.category}\n"
        detail += f"类型: {item.item_type}\n"
        detail += f"差异: {item.diff_type.value}\n"
        detail += f"推荐操作: {item.recommended_action.value}\n"
        detail += f"风险等级: {item.risk_level}\n\n"
        
        if item.details:
            detail += "详细信息:\n"
            for key, value in item.details.items():
                detail += f"  • {key}: {value}\n"
        
        QMessageBox.information(self, "详情", detail)
    
    def on_backup_double_click(self, index):
        """双击查看备份信息"""
        row = index.row()
        filename = self.backup_table.item(row, 0).text()
        
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
            
            QMessageBox.information(self, "备份信息", info)
    
    # ========== 拖放功能 ==========
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.status_label.setText("📥 检测到文件拖入...")
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """拖拽放下事件"""
        urls = event.mimeData().urls()
        
        if not urls:
            return
        
        for url in urls:
            path = url.toLocalFile()
            path_obj = Path(path)
            
            if not path_obj.exists():
                continue
            
            # 检测是否是 Blender 配置目录
            if self._is_blender_config_dir(path_obj):
                version = self._extract_version_from_path(path_obj)
                
                # 询问用户添加到源还是目标
                choice = QMessageBox.question(
                    self, "添加配置目录",
                    f"检测到 Blender 配置目录:\n\n"
                    f"📍 路径: {path}\n"
                    f"🔢 版本: {version or '未知'}\n\n"
                    f"要将此目录添加到哪里？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if choice == QMessageBox.StandardButton.Yes:
                    # 添加到源版本
                    self._add_custom_path('source', path_obj, version)
                else:
                    # 添加到目标版本
                    self._add_custom_path('target', path_obj, version)
            
            elif path_obj.is_dir():
                # 可能是父目录，尝试查找子目录
                blender_dirs = list(path_obj.glob("[0-9]*.[0-9]*"))
                if blender_dirs:
                    for bd in blender_dirs[:3]:  # 最多显示前3个
                        self._add_custom_path('source', bd, bd.name)
                else:
                    QMessageBox.information(
                        self, "提示",
                        f"文件夹 '{path}' 中未找到 Blender 配置目录。\n\n"
                        "请选择包含版本号的子目录（如 '4.2' 或 '3.6'）"
                    )
        
        self.status_label.setText("✅ 拖拽操作完成")
    
    def _is_blender_config_dir(self, path: Path) -> bool:
        """检查是否是有效的 Blender 配置目录"""
        config_dir = path / 'config'
        scripts_dir = path / 'scripts'
        
        return (config_dir.exists() or scripts_dir.exists() or 
                (path / 'userpref.blend').exists())
    
    def _extract_version_from_path(self, path: Path) -> str:
        """从路径中提取版本号"""
        # 尝试从目录名获取版本
        if path.name.replace('.', '').isdigit():
            return path.name
        
        # 检查父目录名是否是版本号（如拖拽的是 config 子目录）
        if path.parent.name.replace('.', '').isdigit():
            return path.parent.name
        
        # 尝试从 userpref.blend 获取（如果存在）
        userpref = path / 'userpref.blend'
        if not userpref.exists():
            userpref = path.parent / 'userpref.blend'
        if userpref.exists():
            return path.parent.name
        
        return path.name
    
    def _add_custom_path(self, target_type: str, path: Path, version: str):
        """添加自定义路径到下拉框"""
        combo = self.source_combo if target_type == 'source' else self.target_combo
        label = self.source_path_label if target_type == 'source' else self.target_path_label
        
        display_text = f"Blender {version} (自定义)"
        existing_index = combo.findText(display_text)
        
        if existing_index < 0:
            combo.addItem(display_text, str(path))
            combo.setCurrentIndex(combo.count() - 1)
        else:
            combo.setCurrentIndex(existing_index)
        
        # 更新路径标签显示
        label.setText(f"✅ {path}")
        label.setStyleSheet("color: #4CAF50; font-size: 11px;")
        
        # 存储到 detected_versions 列表
        custom_install = BlenderInstallation(
            version=version,
            config_path=path,
            is_portable=True
        )
        
        # 避免重复添加
        exists = any(inst.config_path == path for inst in self.detected_versions)
        if not exists:
            self.detected_versions.append(custom_install)
        
        self.status_label.setText(f"✅ 已添加 {target_type} 版本: Blender {version}")
    
    # ========== 浏览功能 ==========
    def browse_blender_path(self, target_type: str):
        """浏览并选择 Blender 配置目录"""
        try:
            dialog_title = f"选择{'源' if target_type == 'source' else '目标'} Blender 配置目录"
            
            # 使用静态方法创建对话框（避免 macOS 崩溃）
            dialog = QFileDialog(self, dialog_title)
            dialog.setFileMode(QFileDialog.FileMode.Directory)
            dialog.setOptions(QFileDialog.Option.DontUseNativeDialog)  # 关键：不使用原生对话框
            
            if dialog.exec():
                paths = dialog.selectedFiles()
                if not paths:
                    return
                
                path = paths[0]
                path_obj = Path(path)
                
                if not path_obj.exists():
                    QMessageBox.warning(self, "错误", "选择的路径不存在")
                    return
                
                # 检查是否是 Blender 配置目录
                if not self._is_blender_config_dir(path_obj):
                    confirm = QMessageBox.question(
                        self, "确认选择",
                        f"所选目录可能不是标准的 Blender 配置目录：\n\n"
                        f"📍 {path}\n\n"
                        "是否仍要使用此目录？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    
                    if confirm != QMessageBox.StandardButton.Yes:
                        return
                
                version = self._extract_version_from_path(path_obj)
                self._add_custom_path(target_type, path_obj, version)
                
        except Exception as e:
            QMessageBox.critical(
                self, "错误",
                f"浏览文件夹时发生错误:\n\n{str(e)}\n\n"
                "请尝试使用拖拽功能作为替代方案。"
            )
            print(f"❌ 浏览错误: {e}")
            import traceback
            traceback.print_exc()
    
    def show_about(self):
        about_text = """
<h2>🎨 Blender 配置同步工具 v0.3</h2>
<p><b>PyQt6 版本</b></p>
<hr>
<p>一款专业的 Blender 个人配置管理工具，帮助你轻松在不同版本间同步收藏夹、快捷键、插件等配置。</p>

<h3>核心功能</h3>
<ul>
<li>✅ 自动检测已安装的 Blender 版本</li>
<li>✅ 配置文件扫描与分析</li>
<li>✅ 一键备份与恢复</li>
<li>✅ 跨版本配置差异比较</li>
<li>✅ 插件兼容性检查</li>
<li>✅ 选择性同步功能</li>
</ul>

<h3>技术栈</h3>
<p><b>Python 3.9+ | PyQt6 | 纯标准库核心模块</b></p>

<h3>作者 & 许可证</h3>
<p><b>作者:</b> MMY<br>
<b>License:</b> MIT<br>
<b>GitHub:</b> github.com/yuyeming0115/mmy_BlenderPortableVS</p>
"""
        msg = QMessageBox(self)
        msg.setWindowTitle("关于")
        msg.setTextFormat(Qt.RichText)
        msg.setText(about_text)
        msg.exec()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Blender Config Sync")
    
    window = BlenderConfigSyncPyQt()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
