# 🎨 Blender 配置同步工具 (BlenderPortableVS)

<p align="center">
  <strong>一款专业的 Blender 个人配置管理工具</strong><br>
  <sub>轻松在不同版本间同步收藏夹、快捷键、插件等配置</sub>
</p>

---

## ✨ 功能特性

### 🎯 核心功能

| 功能 | 描述 |
|------|------|
| 🔍 **版本检测** | 自动检测系统上所有已安装的 Blender 版本 |
| 📂 **手动选择** | 支持浏览和拖拽自定义配置目录（便携版/非标准安装） |
| 📊 **配置扫描** | 深度分析 userpref.blend、书签、插件、快捷键等 |
| 💾 **一键备份** | ZIP 压缩备份，包含完整清单和校验值 |
| ⚖️ **差异比较** | 智能对比两个版本的配置差异，可视化展示 |
| ✅ **选择性同步** | 勾选需要同步的项目，支持合并策略 |
| 🔌 **插件检查** | 自动评估插件兼容性，标记风险等级 |

### 🖥️ 多界面支持

| 界面类型 | 启动命令 | 特点 |
|---------|----------|------|
| **PyQt6 GUI** ⭐ | `python start_gui.py` | 现代化深色主题，macOS 完美支持 |
| **终端 TUI** | `python -m blender_config_sync.tui` | 100% 可靠，适合远程使用 |
| **命令行 CLI** | `python -m blender_config_sync.cli --help` | 自动化脚本集成 |

---

## 📸 界面预览

### PyQt6 图形界面（推荐）

```
┌─────────────────────────────────────────────────────────────┐
│ 🎨 Blender 配置同步工具 v0.3 (PyQt6)              ● □ ─ │
├─────────────────────────────────────────────────────────────┤
│ 📍 版本选择与操作                                           │
│                                                             │
│ 📤 源版本: [Blender 4.2 (自定义) ▼] [📂 浏览...]  ✅ 路径   │
│ → 📥 目标版本: [Blender 3.6 (自定义)▼] [📂 浏览...]      │
│                                                             │
│ [🔄检测版][🔍扫源][🔍扫目标]        [⚖️比较差异(绿)]       │
│ 💡 提示：可以拖拽 Blender 配置文件夹到窗口上快速添加         │
├─────────────────────────────────────────────────────────────┤
│ [📊 差异对比] [📋 详细信息] [💾 备份管理]                     │
├─────────────────────────────────────────────────────────────┤
│ 📑 书签 (3项)    ⌨️ 快捷键 (8项)    🔌 插件 (15项)          │
│ ...详细对比表格...                                          │
├─────────────────────────────────────────────────────────────┤
│ ✅ 就绪 - 点击 '🔄 检测版本' 开始使用                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 方式一：使用预编译版本（最简单）

1. 从 [Releases](../../releases) 下载对应平台的可执行文件
2. 直接运行，无需安装任何依赖！

**macOS:**
```bash
# 方法 A: 双击 .app 文件
open dist/BlenderConfigSync.app

# 方法 B: 运行可执行文件
./dist/BlenderConfigSync
```

**Windows:**
```bash
dist\BlenderConfigSync.exe
```

**Linux:**
```bash
chmod +x dist/BlenderConfigSync
./dist/BlenderConfigSync
```

---

### 方式二：从源码运行（开发者）

#### 1. 克隆仓库

```bash
git clone https://github.com/yuyeming0115/mmy_BlenderPortableVS.git
cd mmy_BlenderPortableVS
```

#### 2. 创建虚拟环境

```bash
# Python 3.9+
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 4. 启动应用

```bash
# GUI 界面（推荐）
python start_gui.py

# 或终端界面
python -m blender_config_sync.tui

# 或查看帮助
python -m blender_config_sync.cli --help
```

---

## 📖 使用指南

### 基本工作流程

```
步骤 1: 启动应用
       python start_gui.py

步骤 2: 添加源版本（要同步的配置）
       • 点击 "📂 浏览..." 选择配置目录
       • 或从 Finder 拖拽文件夹到窗口
       • 示例路径:
         macOS: ~/Library/Application Support/Blender/4.2/
         Windows: %APPDATA%\Blender Foundation\Blender\4.2\
         Linux: ~/.config/blender/4.2/

步骤 3: 添加目标版本（被同步到的目标）
       • 同样的方式添加目标配置

步骤 4: 扫描和分析
       • 点击 "🔍 扫描源配置"
       • 点击 "🔍 扫描目标配置"

步骤 5: 比较差异
       • 点击 "⚖️ 比较差异"
       • 查看详细的差异报告

步骤 6: 选择性同步
       • 在差异表格中勾选需要的项目
       • 点击 "📥 同步到目标"
```

---

### 高级功能

#### 手动选择配置目录

当自动检测不到 Blender 时（如便携式安装）：

1. **浏览按钮**: 点击 "📂 浏览..." 选择包含 `config/` 和 `scripts/` 的目录
2. **拖拽操作**: 从 Finder/资源管理器直接拖拽文件夹到窗口

**支持的拖拽目录结构：**
- `Blender/portable/4.2/config` → 自动识别 `portable` 为配置，`4.2` 为版本号
- `Blender/portable/4.2` → 同上
- `Blender/4.2/config` → 标准 Blender 配置目录

#### 命令行完整用法

```bash
# 显示帮助
python -m blender_config_sync.cli --help

# 子命令示例:

# GUI 模式
python -m blender_config_sync.cli gui           # 默认 PyQt6
python -m blender_config_sync.cli gui --tk     # 强制 Tkinter
python -m blender_config_sync.cli gui --pyqt   # 强制 PyQt6

# 扫描配置
python -m blender_config_sync.cli scan
python -m blender_config_sync.cli scan -v 4.2
python -m blender_config_sync.cli scan -v 4.2 -e report.json

# 备份配置
python -m blender_config_sync.cli backup
python -m blender_config_sync.cli backup -v 4.2
python -m blender_config_sync.cli backup --no-addons  # 不含插件

# 比较版本
python -m blender_config_sync.cli compare --source 4.2 --target 3.6
python -m blender_config_sync.cli compare -s 4.2 -t 3.6 -e diff.json

# 列出备份
python -m blender_config_sync.cli list

# 查看已安装版本
python -m blender_config_sync.cli versions
```

---

## 🛠️ 技术架构

### 项目结构

```
mmy_BlenderPortableVS/
├── blender_config_sync/           # 核心代码包
│   ├── __init__.py               # 包信息 (v0.3)
│   ├── path_manager.py            # Blender 路径检测器
│   ├── config_scanner.py          # 配置文件扫描器
│   ├── backup_engine.py           # 备份与恢复引擎
│   ├── diff_engine.py             # 差异比较引擎
│   ├── cli.py                     # 命令行入口
│   ├── gui_pyqt.py               # PyQt6 图形界面 ⭐
│   ├── gui.py                     # Tkinter 图形界面
│   ├── tui.py                     # 终端交互界面
│   └── blender_config_sync.spec   # PyInstaller 打包配置
├── assets/                        # 应用图标资源
│   ├── icons/app.ico              # Windows 应用图标
│   └── png/                       # 各尺寸 PNG 图标
├── tests/                         # 单元测试
│   ├── test_config_scanner.py     # (12 用例)
│   ├── test_backup_engine.py      # (9 用例)
│   └── test_diff_engine.py        # (10 用例)
├── dist/                          # 打包输出目录
│   ├── BlenderConfigSync          # Linux/macOS 可执行文件
│   ├── BlenderConfigSync.exe      # Windows 可执行文件
│   └── BlenderConfigSync.app      # macOS 应用包
├── start_gui.py                   # GUI 启动器
├── build.py                       # 跨平台打包脚本
├── build.bat                      # Windows 一键打包（双击运行）
├── build_simple.py                # 简化打包脚本
├── diagnose_gui.py                # GUI 诊断工具
├── requirements.txt               # 依赖清单
├── .gitignore
└── README.md                      # 本文件
```

### 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| **语言** | Python 3.9+ | 纯标准库核心 + PyQt6 GUI |
| **GUI 框架** | PyQt6 6.4+ | 现代、跨平台、macOS 友好 |
| **备选 GUI** | Tkinter | 内置，轻量级（有 macOS 兼容性问题） |
| **测试框架** | pytest 7.0+ | 31 个单元测试，100% 通过率 |
| **打包工具** | PyInstaller 6.x | 生成独立可执行文件 |

### 设计模式

- **模块化设计**: 核心逻辑与 UI 分离，易于扩展
- **策略模式**: 多种 GUI 后端可切换（PyQt6/Tkinter/TUI）
- **工厂模式**: 统一的组件创建接口
- **观察者模式**: 状态变化实时更新 UI

---

## 🧪 开发指南

### 运行测试

```bash
# 安装开发依赖
pip install pytest pytest-cov

# 运行全部测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_diff_engine.py -v

# 生成覆盖率报告
pytest tests/ --cov=blender_config_sync
```

### 打包发布

#### Windows 一键打包（推荐）

双击运行 `build.bat`，自动完成：
- 安装 PyInstaller 依赖
- 清理旧构建文件
- 执行打包
- 打包完成后自动打开 dist 文件夹

#### 命令行打包

```bash
# 一键打包（跨平台）
python build.py

# 手动打包
pyinstaller --name BlenderConfigSync --windowed --onefile blender_config_sync/gui_pyqt.py

# 输出位置
ls -lh dist/
```

### 代码规范

- 类型注解完善（Type Hints）
- Docstring 文档齐全
- 遵循 PEP 8 编码风格
- 无外部依赖的核心模块（纯标准库）

---

## 📋 支持的配置文件

| 文件/目录 | 用途 | 是否备份 |
|-----------|------|---------|
| `config/userpref.blend` | 用户偏好设置（快捷键、主题、插件状态） | ✅ |
| `config/bookmarks.txt` | 文件浏览器书签/收藏夹 | ✅ |
| `config/startup.blend` | 启动时加载的默认文件 | ✅ |
| `scripts/addons/*.py` | 用户安装的插件 | ✅（可选） |
| `scripts/startup/*.py` | 自动执行的启动脚本 | ✅ |
| `scripts/presets/keyconfig/*.py` | 自定义键盘映射预设 | ✅ |

---

## ❓ 常见问题

### Q: 检测不到我的 Blender 安装？

**A:** 这很正常！可能的原因：
- Blender 未在标准路径安装
- 从未保存过用户设置（需执行一次 Edit → Preferences → Save Preferences）
- 使用的是便携版（portable）安装

**解决方案:** 使用"浏览"或"拖拽"功能手动指定配置目录。

---

### Q: macOS 上 Tkinter GUI 显示空白？

**A:** 这是 macOS Tcl/Tk 的已知兼容性问题。

**解决方案:** 
- 推荐：使用 PyQt6 版本 (`python start_gui.py`)
- 或使用终端版 (`python -m blender_config_sync.tui`)

---

### Q: 如何找到我的 Blender 配置目录？

**A:** 运行以下命令：

**macOS:**
```bash
ls ~/Library/Application\ Support/Blender/
find ~/Library/Application\ Support/Blender -name "userpref.blend"
```

**Windows:**
```cmd
dir "%APPDATA%\Blender Foundation\Blender\"
```

**Linux:**
```bash
ls ~/.config/blender/
```

---

### Q: 打包后的文件可以在没有 Python 的电脑上运行吗？

**A:** ✅ 可以！PyInstaller 会将所有依赖打包进单个可执行文件，无需安装 Python 或任何库。

---

## 🗺️ 路线图

### ✅ Phase 1: MVP（已完成）
- [x] Blender 版本自动检测
- [x] 配置文件扫描与分析
- [x] 一键备份与恢复
- [x] 基础命令行界面
- [x] 单元测试覆盖

### ✅ Phase 2: 智能增强（已完成）
- [x] 配置差异比较引擎
- [x] PyQt6 图形界面
- [x] 手动选择 + 拖拽支持
- [x] 插件兼容性检查
- [x] 选择性同步功能
- [x] 终端交互界面 (TUI)

### 🔮 Phase 3: 生态集成（规划中）
- [ ] 云端同步服务（可选）
- [ ] 团队配置模板共享
- [ ] AI 辅助配置推荐
- [ ] 多语言国际化 (i18n)
- [ ] 插件市场联动
- [ ] 自动更新机制

---

## 🤝 贡献指南

欢迎贡献代码、报告 Bug 或提出建议！

### 如何贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码规范

- 遵循现有代码风格
- 添加适当的注释和文档字符串
- 确保测试通过 (`pytest tests/ -v`)
- 更新 README（如需要）

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

```
MIT License

Copyright (c) 2024 MMY

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## 🙏 致谢

- [Blender](https://www.blender.org/) - 开源 3D 创作套件
- [PyQt6](https://www.riverbankcomputing.com/pyqt/) - Qt for Python
- [PyInstaller](https://www.pyinstaller.org/) - 应用程序打包工具
- 所有贡献者和使用者

---

## 📞 联系方式

- **GitHub Issues**: [提交问题](../../issues)
- **作者**: MMY
- **邮箱**: yuyeming0115@gmail.com

---

<div align="center">

**如果这个工具对你有帮助，请给一个 ⭐ Star！**

 Made with ❤️ by [MMY](https://github.com/yuyeming0115)

</div>
