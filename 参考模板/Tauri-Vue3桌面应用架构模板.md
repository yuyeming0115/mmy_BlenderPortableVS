# Tauri + Vue 3 桌面应用架构模板

> 基于 MMYCodeSwitch-API 项目提炼，适用于小型工具类桌面应用

## 技术栈选择

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3 + TypeScript | 响应式、组合式 API |
| UI 组件库 | Naive UI | 轻量、支持深色模式、组件丰富 |
| 状态管理 | Pinia | Vue 3 官方推荐，简洁的 store 设计 |
| 国际化 | vue-i18n | 支持中英文切换 |
| 后端框架 | Tauri 2 + Rust | 跨平台、体积小、性能好 |
| 构建工具 | Vite | 快速热更新、简洁配置 |

## 目录结构

```
project/
├── src/                      # Vue 前端代码
│   ├── main.ts               # 入口文件（挂载 Pinia + i18n + Naive UI）
│   ├── App.vue               # 根组件（NConfigProvider 包装）
│   ├── components/           # UI 组件
│   │   ├── AppContent.vue    # 主内容区（页面路由逻辑）
│   │   ├── ProviderGrid.vue  # 卡片网格组件
│   │   ├── ProjectList.vue   # 列表组件
│   │   ├── Settings.vue      # 设置页面
│   │   └── ...               # 其他业务组件
│   ├── stores/               # Pinia 状态管理
│   │   └ app.ts              # 主 store（数据 + API 调用）
│   └── i18n/                 # 国际化
│       ├── index.ts          # i18n 配置
│       ├── zh.ts             # 中文
│       └── en.ts             # 英文
│
├── src-tauri/                # Rust 后端
│   ├── src/
│   │   ├── main.rs           # 入口（极简）
│   │   ├── lib.rs            # Tauri commands 定义
│   │   ├── config.rs         # 配置管理
│   │   └ crypto.rs           # 加密工具
│   │   └ inject.rs           # 业务逻辑
│   │   └ ...
│   ├── tauri.conf.json       # Tauri 配置
│   ├── Cargo.toml            # Rust 依赖
│   └── icons/                # 应用图标
│
├── public/                   # 静态资源（Vite 直接服务）
│   ├── icons/                # 内置图标
│   └ icon.png                # 标题栏图标
│
├── package.json              # npm 依赖
├── vite.config.ts            # Vite 配置
└── index.html                # HTML 入口
```

## 核心设计模式

### 1. 自定义标题栏（无边框窗口）

**tauri.conf.json 配置：**
```json
{
  "app": {
    "windows": [{
      "decorations": false,    // 移除系统标题栏
      "transparent": true      // 透明背景
    }]
  }
}
```

**App.vue 标题栏实现：**
```vue
<div class="titlebar" data-tauri-drag-region>
  <div class="titlebar-left">
    <img class="titlebar-icon" src="/icon.png" />
    <span class="titlebar-title">App Name</span>
  </div>
  <div class="titlebar-controls">
    <button class="titlebar-btn" @click="appWindow.minimize()">─</button>
    <button class="titlebar-btn" @click="toggleMax">□</button>
    <button class="titlebar-btn close" @click="doClose">✕</button>
  </div>
</div>
```

**关键 CSS：**
```css
.titlebar {
  height: 36px;
  -webkit-app-region: drag;    /* 可拖拽区域 */
  user-select: none;
}
.titlebar-controls {
  -webkit-app-region: no-drag; /* 控件不可拖拽 */
}
```

### 2. 简单页面路由（无 vue-router）

使用 `currentPage` ref 控制页面切换，适合小应用：
```ts
const currentPage = ref<'main' | 'settings' | 'form'>('main')

// 页面切换函数
function openSettings() { currentPage.value = 'settings' }
function goBack() { currentPage.value = 'main' }
```

```vue
<div v-if="currentPage === 'main'">...</div>
<Settings v-if="currentPage === 'settings'" @back="goBack" />
```

### 3. Pinia Store 设计模式

**统一 store 负责数据 + API 调用：**
```ts
export const useAppStore = defineStore('app', () => {
  const providers = ref<Provider[]>([])
  const config = ref<AppConfig>({ ... })

  // 初始化（调用后端）
  async function init() {
    await invoke('init_app')
    await loadConfig()
    await loadProviders()
  }

  // 数据加载
  async function loadProviders() {
    providers.value = await invoke<Provider[]>('get_providers')
  }

  // 数据更新
  async function upsertProvider(input: object) {
    await invoke('upsert_provider', { input })
    await loadProviders()  // 重新加载
  }

  return { providers, config, init, loadProviders, upsertProvider }
})
```

**在组件中使用：**
```ts
const store = useAppStore()
onMounted(async () => {
  await store.init()
})
```

### 4. Tauri 前后端通信

**前端调用后端：**
```ts
import { invoke } from '@tauri-apps/api/core'

const result = await invoke<ResultType>('command_name', { param1, param2 })
```

**后端定义 Command：**
```rust
#[tauri::command]
fn command_name(param1: String, param2: String) -> Result<ResultType, String> {
    // 业务逻辑
    Ok(result)
}
```

**注册 Command：**
```rust
fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            command_name,
            // 其他 commands...
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### 5. 深色模式实现

**App.vue 根组件：**
```vue
<script setup>
const isDark = ref(false)
watchEffect(() => {
  document.body.classList.toggle('dark', isDark.value)
})
</script>

<template>
  <n-config-provider :theme="isDark ? darkTheme : null">
    <!-- 内容 -->
  </n-config-provider>
</template>
```

**CSS 深色模式：**
```css
body { background: #f5f5f5; color: #333; }
body.dark { background: #1a1a1a; color: #eee; }

/* 组件深色适配 */
.card { background: #fff; border-color: #e0e0e0; }
body.dark .card { background: #2a2a2a; border-color: #444; }
```

### 6. 卡片式交互设计

**卡片组件模板：**
```vue
<div class="card" @click="handleClick" @contextmenu.prevent="openMenu">
  <div class="icon-wrap">
    <span class="icon">{{ fallbackIcon }}</span>
  </div>
  <div class="label">{{ name }}</div>
</div>

<!-- 右键菜单 -->
<n-dropdown
  trigger="manual"
  :x="menuX"
  :y="menuY"
  :show="menuVisible"
  :options="menuOptions"
  @select="onMenuSelect"
/>
```

**卡片 CSS 要点：**
```css
.card {
  width: 108px;
  min-height: 100px;
  border-radius: 14px;
  cursor: pointer;
  transition: border-color .2s, box-shadow .2s;
}
.card:hover {
  border-color: #18a058;
  transform: translateY(-1px);
}
```

### 7. 系统托盘

**tauri.conf.json：**
```json
{
  "app": {
    "trayIcon": {
      "iconPath": "icons/icon.png",
      "id": "main"
    }
  }
}
```

**lib.rs 托盘菜单：**
```rust
use tauri::menu::{MenuItem, MenuBuilder};
use tauri::tray::TrayIconEvent;

fn setup_tray(app: &App) {
    let show_item = MenuItem::new(app, "显示窗口", true, None::<&str>);
    let quit_item = MenuItem::new(app, "退出", true, None::<&str>);

    let menu = MenuBuilder::new(app)
        .item(&show_item)
        .item(&quit_item)
        .build();

    // 处理托盘事件...
}
```

## 关键配置文件

### package.json
```json
{
  "dependencies": {
    "@tauri-apps/api": "^2",
    "@tauri-apps/plugin-dialog": "^2.7.0",
    "@tauri-apps/plugin-fs": "^2",
    "naive-ui": "^2.40.0",
    "pinia": "^2.2.0",
    "vue": "^3.5.13",
    "vue-i18n": "^9.14.0"
  },
  "devDependencies": {
    "@tauri-apps/cli": "^2",
    "@vitejs/plugin-vue": "^5.2.1",
    "vite": "^6.0.3"
  }
}
```

### vite.config.ts
```ts
export default defineConfig(async () => ({
  plugins: [vue()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,  // Tauri 需固定端口
  },
}));
```

### tauri.conf.json 核心配置
```json
{
  "productName": "App Name",
  "version": "1.0.0",
  "identifier": "com.your.app",
  "build": {
    "beforeDevCommand": "npm run dev",
    "devUrl": "http://localhost:1420",
    "beforeBuildCommand": "npm run build",
    "frontendDist": "../dist"
  },
  "app": {
    "windows": [{
      "width": 510,
      "height": 620,
      "resizable": true,
      "center": true,
      "decorations": false,
      "transparent": true
    }],
    "trayIcon": { "iconPath": "icons/icon.png" }
  },
  "bundle": {
    "targets": "all",
    "icon": ["icons/32x32.png", "icons/icon.icns", "icons/icon.ico"]
  }
}
```

## 开发流程

### 1. 初始化项目
```bash
npm create tauri-app@latest
# 选择 Vue + TypeScript

npm install naive-ui pinia vue-i18n
npm install @tauri-apps/plugin-dialog @tauri-apps/plugin-fs
```

### 2. 开发调试
```bash
npm run tauri dev
# Vite 热更新 + Tauri 窗口实时预览
```

### 3. 打包发布
```bash
npm run tauri build
# 输出到 src-tauri/target/release/bundle/
```

## 最佳实践总结

| 实践 | 说明 |
|------|------|
| 单 store 模式 | 小应用用一个 store 管理所有数据，简化状态同步 |
| invoke 封装 | 所有 API 调用放在 store 里，组件只需调用 store 方法 |
| 无 vue-router | 小于 5 个页面用 ref 切换，更轻量 |
| CSS 变量少用 | 直接用 `body.dark` 选择器，兼容性更好 |
| 响应式滚动条 | 自定义滚动条样式提升体感 |
| 状态栏提示 | 底部状态栏给用户操作指引 |
| 确认弹窗 | 删除/危险操作用 `useDialog` 确认 |

---

此模板适合：
- 工具类桌面应用（配置管理、文件处理等）
- 单窗口应用
- 5 个以内的页面
- 需要系统托盘
- 需要深色模式
- 需要国际化支持