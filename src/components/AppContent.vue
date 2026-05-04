<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '../stores/app'
import { i18n } from '../i18n'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { invoke } from '@tauri-apps/api/core'
import DirectoryPanel from './DirectoryPanel.vue'
import PreviewPage from './PreviewPage.vue'
import BackupPage from './BackupPage.vue'
import TransferPage from './TransferPage.vue'

const { t } = useI18n()
const store = useAppStore()

type PageType = 'main' | 'preview' | 'backup' | 'transfer'
const currentPage = ref<PageType>('main')
const isDark = defineModel<boolean>('isDark', { default: true })
const appWindow = getCurrentWindow()

// 窗口拖拽
async function startWindowDrag(e: MouseEvent) {
  const target = e.target as HTMLElement
  // 按钮、输入框等交互元素不触发拖拽
  if (target.closest('button, a, input, select, textarea, [role="button"], .n-button, .n-input, .n-select, .n-checkbox, .n-switch, .nav-btn, .titlebar-btn')) {
    return
  }
  try {
    await appWindow.startDragging()
  } catch (err) {
    console.warn('[drag] startDragging failed:', err)
  }
}

onMounted(async () => {
  await store.init()
  i18n.global.locale.value = store.config.language as 'zh' | 'en'
  try {
    const saved = await invoke<{ isDark?: boolean } | null>('get_window_state')
    if (saved && typeof saved.isDark === 'boolean') {
      isDark.value = saved.isDark
    }
  } catch { }
})

watch(isDark, async (val) => {
  try {
    await invoke('save_window_state', { isDark: val })
  } catch { }
})

async function toggleMax() {
  if (await appWindow.isMaximized()) {
    await appWindow.unmaximize()
  } else {
    await appWindow.maximize()
  }
}

async function doCloseWindow() {
  try {
    await invoke('hide_to_tray')
  } catch {
    await appWindow.hide().catch(() => { })
  }
}

function navigate(page: PageType) {
  currentPage.value = page
}

function toggleLang() {
  const newLang = store.config.language === 'zh' ? 'en' : 'zh'
  store.config.language = newLang
  i18n.global.locale.value = newLang as 'zh' | 'en'
  store.saveConfig()
}
</script>

<template>
  <div class="app">
    <!-- 自定义标题栏 -->
    <div class="titlebar" @mousedown="startWindowDrag">
      <div class="titlebar-left">
        <span class="titlebar-title">{{ t('app_title') }}</span>
      </div>
      <div class="titlebar-controls">
        <button class="titlebar-btn" @click="appWindow.minimize()" :title="t('minimize')">─</button>
        <button class="titlebar-btn" @click="toggleMax" :title="t('maximize')">□</button>
        <button class="titlebar-btn close" @click="doCloseWindow" :title="t('close')">✕</button>
      </div>
    </div>

    <!-- 主体区域 -->
    <div class="main-body">
      <!-- 左侧导航栏 -->
      <div class="sidebar" @mousedown="startWindowDrag">
        <button
          class="nav-btn"
          :class="{ active: currentPage === 'main', 'has-version': !!store.versionA }"
          @click="navigate('main')"
        >
          <span class="nav-label">{{ store.versionA ? `A · ${store.versionA}` : t('nav_drag_a') }}</span>
        </button>
        <button
          class="nav-btn"
          :class="{ active: currentPage === 'main', 'has-version': !!store.versionB }"
          @click="navigate('main')"
        >
          <span class="nav-label">{{ store.versionB ? `B · ${store.versionB}` : t('nav_drag_b') }}</span>
        </button>
        <div class="nav-divider"></div>
        <button
          class="nav-btn"
          :class="{ active: currentPage === 'preview' }"
          @click="navigate('preview')"
        >
          <span class="nav-label">{{ t('nav_preview') }}</span>
        </button>
        <button
          class="nav-btn"
          :class="{ active: currentPage === 'backup' }"
          @click="navigate('backup')"
        >
          <span class="nav-label">{{ t('nav_backup') }}</span>
        </button>
        <button
          class="nav-btn"
          :class="{ active: currentPage === 'transfer' }"
          @click="navigate('transfer')"
        >
          <span class="nav-label">{{ t('nav_transfer') }}</span>
        </button>
        <div class="nav-spacer"></div>
        <div class="nav-divider"></div>
        <button class="nav-btn" @click="toggleLang">
          <span class="nav-label">{{ store.config.language === 'zh' ? '中/英' : 'En/Cn' }}</span>
        </button>
        <button class="nav-btn" @click="isDark = !isDark">
          <span class="nav-label">{{ isDark ? '黑/白' : '白/黑' }}</span>
        </button>
      </div>

      <!-- 内容区域 -->
      <div class="content-area">
        <!-- 主页面：A/B 双栏 -->
        <DirectoryPanel
          v-if="currentPage === 'main'"
        />
        <!-- 预览清单 -->
        <PreviewPage
          v-if="currentPage === 'preview'"
        />
        <!-- 备份 -->
        <BackupPage
          v-if="currentPage === 'backup'"
        />
        <!-- 传输 -->
        <TransferPage
          v-if="currentPage === 'transfer'"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.main-body {
  display: flex;
  flex: 1;
  min-height: 0;
}

/* 左侧导航 */
.sidebar {
  width: 80px;
  min-width: 80px;
  display: flex;
  flex-direction: column;
  padding: 8px 6px;
  gap: 4px;
  background: #2a2a2a;
  border-right: 1px solid #444;
  overflow-y: auto;
}
body:not(.dark) .sidebar {
  background: #e8e8e8;
  border-right-color: #ddd;
}

.nav-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 6px 4px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #ccc;
  cursor: pointer;
  font-size: 11px;
  text-align: center;
  transition: background 0.15s, color 0.15s;
  line-height: 1.3;
}
body:not(.dark) .nav-btn {
  color: #555;
}
.nav-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
body:not(.dark) .nav-btn:hover {
  background: rgba(0, 0, 0, 0.06);
  color: #222;
}
.nav-btn.active {
  background: rgba(33, 150, 243, 0.2);
  color: #64b5f6;
}
body:not(.dark) .nav-btn.active {
  background: rgba(33, 150, 243, 0.15);
  color: #1976d2;
}
.nav-btn.has-version {
  background: rgba(76, 175, 80, 0.15);
  color: #81c784;
}
body:not(.dark) .nav-btn.has-version {
  background: rgba(76, 175, 80, 0.1);
  color: #2e7d32;
}
.nav-btn.has-version.active {
  background: rgba(33, 150, 243, 0.2);
  color: #64b5f6;
}
.nav-label {
  display: block;
  word-break: break-all;
}

.nav-divider {
  height: 1px;
  background: #444;
  margin: 4px 8px;
}
body:not(.dark) .nav-divider {
  background: #ddd;
}

.nav-spacer {
  flex: 1;
}

/* 内容区域 */
.content-area {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}
</style>
