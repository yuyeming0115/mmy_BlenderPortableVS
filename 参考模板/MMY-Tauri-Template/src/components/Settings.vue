<template>
  <div class="page">
    <header class="page-header">
      <n-button text size="large" @click="emit('back')">←</n-button>
      <span class="page-title">{{ t('settings') }}</span>
    </header>

    <div class="page-content">
      <n-form label-placement="left" label-width="80px">
        <!-- 语言设置 -->
        <n-form-item :label="t('language')">
          <n-radio-group :value="store.config.language" @update:value="setLang">
            <n-radio value="zh">中文</n-radio>
            <n-radio value="en">English</n-radio>
          </n-radio-group>
        </n-form-item>

        <!-- TODO: 添加你的设置项 -->
        <n-divider>{{ t('more_settings') }}</n-divider>

      </n-form>
    </div>

    <footer class="page-footer">
      <n-button size="large" @click="emit('back')">{{ t('cancel') }}</n-button>
      <n-button type="primary" size="large" @click="save">{{ t('save') }}</n-button>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '../stores/app'
import { useMessage } from 'naive-ui'
import { i18n } from '../i18n'

const { t } = useI18n()
const store = useAppStore()
const msg = useMessage()
const emit = defineEmits<{ back: [] }>()

// TODO: 添加你的设置状态变量

function setLang(lang: string) {
  store.config.language = lang
  i18n.global.locale.value = lang as 'zh' | 'en'
}

async function save() {
  await store.saveConfig(store.config)
  msg.success(t('save_success'))
  emit('back')
}
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
  background: #fff;
  flex-shrink: 0;
}
body.dark .page-header { background: #242424; border-bottom-color: #333; }
.page-title { font-size: 18px; font-weight: 700; }
.page-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  padding-bottom: 80px;
  scrollbar-width: thin;
  scrollbar-color: rgba(128,128,128,0.2) transparent;
}
.page-content::-webkit-scrollbar { width: 6px; }
.page-content::-webkit-scrollbar-track { background: transparent; }
.page-content::-webkit-scrollbar-thumb { background: rgba(128,128,128,0.2); border-radius: 10px; }
body.dark .page-content { scrollbar-color: rgba(200,200,200,0.12) transparent; }
.page-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-top: 1px solid #eee;
  background: #fafafa;
  flex-shrink: 0;
}
body.dark .page-footer { background: #242424; border-top-color: #333; }
</style>