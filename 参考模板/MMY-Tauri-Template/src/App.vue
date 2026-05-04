<script setup lang="ts">
import { ref, watchEffect } from 'vue'
import { darkTheme } from 'naive-ui'
import AppContent from './components/AppContent.vue'

const isDark = ref(false)
watchEffect(() => {
  document.body.classList.toggle('dark', isDark.value)
})
</script>

<template>
  <n-config-provider :theme="isDark ? darkTheme : null">
    <n-message-provider>
      <n-dialog-provider>
        <AppContent v-model:is-dark="isDark" />
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
html {
  scrollbar-width: thin;
  scrollbar-color: rgba(128,128,128,0.2) transparent;
}
html::-webkit-scrollbar { width: 6px; }
html::-webkit-scrollbar-track { background: transparent; }
html::-webkit-scrollbar-thumb {
  background: rgba(128,128,128,0.2);
  border-radius: 10px;
}
html::-webkit-scrollbar-thumb:hover {
  background: rgba(128,128,128,0.4);
}

body { font-family: Inter, system-ui, sans-serif; background: #f5f5f5; color: #333; }
body.dark { background: #1a1a1a; color: #eee; }

body.dark,
body.dark html { scrollbar-color: rgba(200,200,200,0.12) transparent; }
body.dark ::-webkit-scrollbar-thumb { background: rgba(200,200,200,0.12); }
body.dark ::-webkit-scrollbar-thumb:hover { background: rgba(200,200,200,0.25); }

.app { display: flex; flex-direction: column; height: 100vh; overflow: hidden; }

/* 自定义标题栏 - Tauri 拖拽 */
.titlebar {
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  -webkit-app-region: drag;
  app-region: drag;
  user-select: none;
  background: #fff;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}
body.dark .titlebar {
  background: #242424;
  border-bottom-color: #333;
}
.titlebar-left {
  display: flex;
  align-items: center;
}
.titlebar-icon {
  width: 20px;
  height: 20px;
  margin-right: 8px;
}
.titlebar-title {
  font-size: 13px;
  font-weight: 600;
  color: #555;
}
body.dark .titlebar-title { color: #ccc; }
.titlebar-controls {
  display: flex;
  gap: 0;
  -webkit-app-region: no-drag;
  app-region: no-drag;
}
.titlebar-btn {
  width: 46px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 16px;
  color: #666;
  transition: background 0.15s;
  border: none;
  background: transparent;
}
.titlebar-btn:hover { background: #e8e8e8; }
body.dark .titlebar-btn:hover { background: #3a3a3a; }
.titlebar-btn.close:hover { background: #e81123 !important; color: #fff; }
</style>