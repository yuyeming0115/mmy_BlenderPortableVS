<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage, useDialog } from 'naive-ui'
import { useAppStore } from '../stores/app'
import { i18n } from '../i18n'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { invoke } from '@tauri-apps/api/core'
import CardGrid from './CardGrid.vue'
import Settings from './Settings.vue'

const { t } = useI18n()
const store = useAppStore()
const msg = useMessage()
const dialog = useDialog()

const currentPage = ref<'main' | 'settings'>('main')
const isDark = defineModel<boolean>('isDark', { default: false })

const appWindow = getCurrentWindow()

/// 全局窗口拖拽（macOS 透明窗口兜底）
async function startWindowDrag(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (target.closest('button, a, input, select, textarea, [role="button"], .n-button, .n-input, .n-select, .n-checkbox, .n-switch, .card, .n-modal, .n-popover, .n-dropdown')) {
    return
  }
  try {
    await appWindow.startDragging()
  } catch (_) {}
}

onMounted(async () => {
  await store.init()
  i18n.global.locale.value = store.config.language as 'zh' | 'en'

  // 恢复深浅色模式
  try {
    const saved = await invoke<{ isDark?: boolean } | null>('get_window_state') as any
    if (saved && typeof saved.isDark === 'boolean') {
      isDark.value = saved.isDark
    }
  } catch (_) { }
})

// 监听深浅模式变化，保存状态
watch(isDark, async (val) => {
  try {
    await invoke('save_window_state', { isDark: val })
  } catch (_) {}
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
  } catch (e) {
    await appWindow.hide().catch(() => {})
  }
}

function openSettings() {
  currentPage.value = 'settings'
}

function goBack() {
  currentPage.value = 'main'
}
</script>

<template>
  <div class="app" @mousedown="startWindowDrag">
    <!-- 自定义标题栏 -->
    <div class="titlebar" data-tauri-drag-region>
      <div class="titlebar-left">
        <img class="titlebar-icon" src="/icon.png" width="20" height="20" />
        <span class="titlebar-title">MMY Tauri App</span>
      </div>
      <div class="titlebar-controls">
        <button class="titlebar-btn" @click="appWindow.minimize()">─</button>
        <button class="titlebar-btn" @click="toggleMax">□</button>
        <button class="titlebar-btn close" @click="doCloseWindow">✕</button>
      </div>
    </div>

    <!-- 主页面 -->
    <div v-if="currentPage === 'main'" class="page-main">
      <div class="content">
        <!-- TODO: 替换为你的业务组件 -->
        <CardGrid
          :items="[]"
          @click="(item) => console.log('click', item)"
          @edit="(item) => console.log('edit', item)"
          @delete="(item) => console.log('delete', item)"
          @add="() => console.log('add')"
        />
      </div>

      <footer class="toolbar">
        <n-button size="large" secondary @click="isDark = !isDark">{{ isDark ? '☀️' : '🌙' }}</n-button>
        <n-button size="large" secondary @click="openSettings">⚙️</n-button>
      </footer>

      <footer class="statusbar">
        <span>{{ t('right_click_hint') }}</span>
      </footer>
    </div>

    <!-- 设置页面 -->
    <Settings
      v-if="currentPage === 'settings'"
      @back="goBack"
    />
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}
.page-main {
  display: grid;
  grid-template-rows: 1fr auto auto;
  flex: 1;
  min-height: 0;
}
.content {
  min-height: 0;
  overflow-y: auto;
  padding: 8px 16px 0;
  scrollbar-width: thin;
  scrollbar-color: rgba(128,128,128,0.25) transparent;
}
.content::-webkit-scrollbar { width: 5px; }
.content::-webkit-scrollbar-track { background: transparent; }
.content::-webkit-scrollbar-thumb { background: rgba(128,128,128,0.25); border-radius: 10px; }
.toolbar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  border-top: 1px solid #eee;
  flex-shrink: 0;
  background: #fafafa;
  min-height: 52px;
}
.statusbar {
  display: flex;
  align-items: center;
  padding: 6px 16px;
  font-size: 11px;
  color: #888;
  background: #f5f5f5;
  flex-shrink: 0;
  min-height: 32px;
}

/* 深色模式适配 */
body.dark .toolbar { border-top-color: #333; background: #242424; }
body.dark .statusbar { color: #888; background: #1a1a1a; }
body.dark .content { scrollbar-color: rgba(200,200,200,0.12) transparent; }
body.dark .content::-webkit-scrollbar-thumb { background: rgba(200,200,200,0.12); }

@media (max-width: 400px) {
  .toolbar { gap: 6px; padding: 8px 12px; }
}
</style>