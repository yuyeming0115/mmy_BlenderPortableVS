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
| 📁 **文件夹对比** | 通用文件夹差异对比与同步功能 |

### 🖥️ 界面特点

- **现代化 UI**: 深色/浅色主题切换，自定义无边框窗口
- **系统托盘**: 最小化到托盘，托盘菜单快速操作
- **拖拽支持**: 直接拖拽 Blender 配置文件夹到窗口
- **多语言**: 支持中文/英文切换
- **窗口记忆**: 自动保存窗口大小和主题设置

---

## 🚀 快速开始

### 方式一：使用安装包（推荐）

1. 从 [Releases](../../releases) 下载最新安装包
2. 运行安装程序完成安装
3. 启动应用即可使用

**Windows:**
```
双击 Blender Config Sync_1.0.0_x64-setup.exe 安装
```

---

### 方式二：从源码运行（开发者）

#### 1. 克隆仓库

```bash
git clone https://github.com/yuyeming0115/mmy_BlenderPortableVS.git
cd mmy_BlenderPortableVS
```

#### 2. 安装依赖

```bash
# 安装前端依赖
npm install

# 安装 Rust（如未安装）
# Windows: https://rustup.rs
# 或运行: winget install Rustlang.Rustup
```

#### 3. 开发模式

```bash
# 启动开发服务器
npm run tauri:dev
```

#### 4. 构建发布

```bash
# 构建安装包
npm run tauri:build

# 输出位置
# src-tauri/target/release/bundle/nsis/
```

---

## 📖 使用指南

### 基本工作流程

```
步骤 1: 启动应用
       双击桌面图标或从开始菜单启动

步骤 2: 选择源版本（要同步的配置）
       • 点击左侧导航的版本槽位
       • 拖拽配置文件夹到窗口
       • 或使用"检测版本"自动发现
       • 示例路径:
         Windows: %APPDATA%\Blender Foundation\Blender\4.2\
         macOS: ~/Library/Application Support/Blender/4.2/
         Linux: ~/.config/blender/4.2/

步骤 3: 选择目标版本（被同步到的目标）
       • 同样方式添加目标配置

步骤 4: 扫描和比较
       • 点击"扫描配置"按钮
       • 查看配置详情和差异

步骤 5: 选择性同步
       • 勾选需要的项目
       • 点击同步按钮执行
```

---

## 🛠️ 技术架构

### 项目结构

```
mmy_BlenderPortableVS/
├── src/                          # Vue 前端代码
│   ├── App.vue                   # 主应用组件
│   ├── components/               # UI 组件
│   │   ├── AppContent.vue        # 主界面
│   │   ├── DirectoryPanel.vue    # 目录选择面板
│   │   ├── BackupPage.vue        # 备份管理页
│   │   ├── PreviewPage.vue       # 预览清单页
│   │   ├── TransferPage.vue      # 传输进度页
│   │   └── FolderDiffPage.vue    # 文件夹对比页
│   ├── stores/                   # Pinia 状态管理
│   │   └── app.ts                # 应用状态
│   └── i18n/                     # 国际化
│       ├── zh.ts                 # 中文
│       ├── en.ts                 # 英文
│       └── index.ts              # i18n 配置
├── src-tauri/                    # Tauri 后端代码
│   ├── src/
│   │   ├── main.rs               # 主入口、命令定义
│   │   ├── path_manager.rs       # Blender 路径检测
│   │   ├── config_scanner.rs     # 配置文件扫描
│   │   ├── backup_engine.rs      # 备份恢复引擎
│   │   ├── diff_engine.rs        # 差异比较引擎
│   │   ├── dir_diff.rs           # 目录差异对比
│   │   └── app_config.rs         # 应用配置管理
│   ├── icons/                    # 应用图标
│   ├── tauri.conf.json           # Tauri 配置
│   └── Cargo.toml                # Rust 依赖
├── build.bat                     # Windows 一键打包脚本
├── package.json                  # Node.js 依赖
└── README.md                     # 本文件
```

### 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| **前端框架** | Vue 3.5 | Composition API |
| **UI 组件** | Naive UI | 现代化 Vue 3 组件库 |
| **状态管理** | Pinia | Vue 官方状态管理 |
| **国际化** | Vue I18n | 多语言支持 |
| **构建工具** | Vite 6 | 快速构建 |
| **后端框架** | Tauri 2.x | Rust 跨平台桌面框架 |
| **系统托盘** | Tauri Tray | 原生托盘集成 |

---

## 📋 支持的配置文件

| 文件/目录 | 用途 | 是否备份 |
|-----------|------|---------|
| `config/userpref.blend` | 用户偏好设置（快捷键、主题、插件状态） | ✅ |
| `config/bookmarks.txt` | 文件浏览器书签/收藏夹 | ✅ |
| `config/startup.blend` | 启动时加载的默认文件 | ✅ |
| `scripts/addons/*.py` | 用户安装的插件 | ✅（可选） |
| `scripts/startup/` | 启动脚本及模板资源 | ✅ |
| `scripts/presets/keyconfig/*.py` | 自定义键盘映射预设 | ✅ |

---

## 🔧 开发指南

### 开发命令

```bash
# 开发模式（热重载）
npm run tauri:dev

# 仅前端开发
npm run dev

# 类型检查
npm run build  # 包含 vue-tsc --noEmit

# 构建生产版本
npm run tauri:build
```

### 一键打包（Windows）

双击运行 `build.bat`，自动完成：
- 检查环境依赖
- 执行前端构建
- 执行 Tauri 打包
- 打包完成后打开输出目录

---

## ❓ 常见问题

### Q: 检测不到我的 Blender 安装？

**A:** 可能的原因：
- Blender 未在标准路径安装
- 从未保存过用户设置（需执行一次 Edit → Preferences → Save Preferences）
- 使用的是便携版（portable）安装

**解决方案:** 使用拖拽功能手动指定配置目录。

---

### Q: 如何找到我的 Blender 配置目录？

**A:** 运行以下命令：

**Windows:**
```cmd
dir "%APPDATA%\Blender Foundation\Blender\"
```

**macOS:**
```bash
ls ~/Library/Application\ Support/Blender/
```

**Linux:**
```bash
ls ~/.config/blender/
```

---

## 🗺️ 路线图

### ✅ 已完成
- [x] Blender 版本自动检测
- [x] 配置文件扫描与分析
- [x] 一键备份与恢复
- [x] 配置差异比较引擎
- [x] 选择性同步功能
- [x] 通用文件夹对比
- [x] 系统托盘支持
- [x] 多语言支持（中/英）
- [x] 深色/浅色主题

### 🔮 规划中
- [ ] 云端同步服务（可选）
- [ ] 团队配置模板共享
- [ ] 自动更新机制

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

## 🙏 致谢

- [Blender](https://www.blender.org/) - 开源 3D 创作套件
- [Tauri](https://tauri.app/) - 跨平台桌面应用框架
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Naive UI](https://naiveui.com/) - Vue 3 组件库

---

<div align="center">

**如果这个工具对你有帮助，请给一个 ⭐ Star！**

 Made with ❤️ by [MMY](https://github.com/yuyeming0115)

</div>