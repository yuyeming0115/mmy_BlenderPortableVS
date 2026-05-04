# MMY Tauri + Vue 3 桌面应用脚手架

最小化模板，用于快速启动小型工具类桌面应用开发。

## 使用方法

### 1. 复制到新项目
```bash
cp -r MMY-Tauri-Template/ your-new-project/
cd your-new-project/
```

### 2. 安装依赖
```bash
npm install
```

### 3. 开发调试
```bash
npm run tauri dev
```

### 4. 打包发布
```bash
npm run tauri build
```

## 包含内容

| 文件 | 说明 |
|------|------|
| `src/App.vue` | 自定义标题栏 + 深色模式骨架 |
| `src/components/AppContent.vue` | 页面容器（简单路由切换） |
| `src/components/CardGrid.vue` | 卡片网格模板（点击 + 右键菜单） |
| `src/components/Settings.vue` | 设置页模板（深色切换 + 语言） |
| `src/stores/app.ts` | Pinia Store 骨架（invoke 封装） |
| `src/i18n/*` | 中英文国际化模板 |
| `src-tauri/src/lib.rs` | Tauri Commands 骨架 |
| `src-tauri/src/config.rs` | 配置管理模板 |
| `tauri.conf.json` | 无边框窗口 + 系统托盘配置 |

## 开发流程

1. **修改应用名称**
   - `package.json` → `name`
   - `tauri.conf.json` → `productName`, `identifier`
   - `src/App.vue` → 标题栏标题
   - `src-tauri/src/lib.rs` → `APP_NAME`

2. **定义数据类型**
   - `src/stores/app.ts` → TypeScript 接口
   - `src-tauri/src/config.rs` → Rust 结构体

3. **添加 Tauri Commands**
   - `src-tauri/src/lib.rs` → 新增 `#[tauri::command]`
   - `src/stores/app.ts` → 新增 `invoke()` 调用

4. **添加页面/组件**
   - `src/components/` → 新增 Vue 组件
   - `src/components/AppContent.vue` → 注册页面路由

5. **国际化**
   - `src/i18n/zh.ts` / `en.ts` → 新增翻译 key

## 技术栈

- Vue 3 + TypeScript
- Naive UI（组件库）
- Pinia（状态管理）
- vue-i18n（国际化）
- Tauri 2 + Rust（后端）
- Vite（构建）

## 注意事项

- 标题栏使用 `data-tauri-drag-region`，按钮需 `no-drag`
- 深色模式用 `body.dark` 选择器，配合 Naive UI 的 `darkTheme`
- 小应用无需 vue-router，用 `currentPage` ref 切换页面
- 所有 API 调用封装在 Pinia store 里

---

Made with MMYCodeSwitch-API template extraction.