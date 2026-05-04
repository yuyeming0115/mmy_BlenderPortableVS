<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import { useAppStore, type SyncItemInput } from '../stores/app'

const { t } = useI18n()
const store = useAppStore()
const msg = useMessage()

const executing = ref(false)

function getActionLabel(action: string) {
  const map: Record<string, string> = {
    SyncToTarget: t('action_sync_to_target'),
    KeepTarget: t('action_keep_target'),
    Merge: t('action_merge'),
    Skip: t('action_skip'),
  }
  return map[action] || action
}

function removeItem(item: any) {
  const idx = store.selectedSyncItems.indexOf(item)
  if (idx > -1) store.selectedSyncItems.splice(idx, 1)
}

async function doTransfer() {
  if (store.selectedSyncItems.length === 0) {
    msg.warning('没有待传输的项')
    return
  }
  executing.value = true
  try {
    const items: SyncItemInput[] = store.selectedSyncItems.map(item => ({
      category: item.category,
      item_type: item.item_type,
      name: item.name,
      action: item.recommended_action || 'SyncToTarget',
    }))
    await store.executeSync(items, store.pathA, store.pathB)
    if (store.transferResult) {
      msg.success(`传输完成！成功: ${store.transferResult.success_count}, 失败: ${store.transferResult.failed_count}, 跳过: ${store.transferResult.skipped_count}`)
      store.selectedSyncItems = []
    }
  } catch (e: any) {
    msg.error(`传输失败: ${e}`)
  } finally {
    executing.value = false
  }
}
</script>

<template>
  <div class="transfer-page">
    <div class="page-header">
      <span class="page-title">{{ t('transfer_title') }}</span>
      <n-button type="primary" :loading="executing" :disabled="store.selectedSyncItems.length === 0" @click="doTransfer">
        {{ t('transfer_start') }}
      </n-button>
    </div>

    <!-- 传输方向提示 -->
    <div v-if="store.pathA && store.pathB" class="transfer-direction-bar">
      <span class="dir-side">
        <span class="dir-badge dir-badge-a">A</span>
        <span class="dir-path" :title="store.pathA">{{ store.pathA }}</span>
      </span>
      <span class="dir-arrow">➡️</span>
      <span class="dir-side">
        <span class="dir-badge dir-badge-b">B</span>
        <span class="dir-path" :title="store.pathB">{{ store.pathB }}</span>
      </span>
    </div>

    <div class="transfer-list">
      <div v-if="store.selectedSyncItems.length === 0" class="empty-hint">
        请在"预览清单"页面选择需要同步的项
      </div>
      <div v-else class="item-list">
        <div
          v-for="item in store.selectedSyncItems"
          :key="item.category + item.name"
          class="transfer-item"
        >
          <span class="item-category">{{ item.category }}</span>
          <span class="item-name">{{ item.name }}</span>
          <span class="item-action">{{ getActionLabel(item.recommended_action) }}</span>
          <n-button text size="tiny" type="error" @click="removeItem(item)">✕</n-button>
        </div>
      </div>
    </div>

    <!-- 传输结果 -->
    <div v-if="store.transferResult" class="transfer-result">
      <h3>{{ t('transfer_complete') }}</h3>
      <div class="result-stats">
        <span class="stat success">{{ t('transfer_success') }}: {{ store.transferResult.success_count }}</span>
        <span class="stat failed">{{ t('transfer_failed') }}: {{ store.transferResult.failed_count }}</span>
        <span class="stat skipped">{{ t('transfer_skipped') }}: {{ store.transferResult.skipped_count }}</span>
      </div>
      <div v-if="store.transferResult.errors.length > 0" class="errors">
        <p>错误:</p>
        <ul>
          <li v-for="err in store.transferResult.errors" :key="err">{{ err }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.transfer-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid #444;
  flex-shrink: 0;
}
body:not(.dark) .page-header {
  border-bottom-color: #ddd;
}

.page-title {
  font-size: 16px;
  font-weight: 700;
}

.transfer-direction-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 16px;
  border-bottom: 1px solid #444;
  flex-shrink: 0;
  font-size: 13px;
}
body:not(.dark) .transfer-direction-bar {
  border-bottom-color: #ddd;
}

.dir-label, .dir-side {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.dir-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
  flex-shrink: 0;
  line-height: 1.4;
}

.dir-badge-a {
  background: rgba(255, 152, 0, 0.2);
  color: #ff9800;
  border: 1px solid rgba(255, 152, 0, 0.3);
}
body:not(.dark) .dir-badge-a {
  background: rgba(255, 152, 0, 0.1);
  color: #e65100;
  border-color: rgba(255, 152, 0, 0.25);
}

.dir-badge-b {
  background: rgba(33, 150, 243, 0.2);
  color: #64b5f6;
  border: 1px solid rgba(33, 150, 243, 0.3);
}
body:not(.dark) .dir-badge-b {
  background: rgba(33, 150, 243, 0.1);
  color: #1565c0;
  border-color: rgba(33, 150, 243, 0.25);
}

.dir-path {
  color: #aaa;
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
body:not(.dark) .dir-path {
  color: #666;
}

.dir-arrow {
  color: #64b5f6;
  font-size: 16px;
}

.transfer-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 8px 16px;
}

.empty-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #666;
  font-size: 14px;
}

.item-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.transfer-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 10px;
  border: 1px solid #444;
  border-radius: 4px;
  font-size: 12px;
}
body:not(.dark) .transfer-item {
  border-color: #ddd;
}

.item-category {
  color: #888;
  min-width: 80px;
}

.item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-action {
  color: #4caf50;
  min-width: 80px;
}

.transfer-result {
  padding: 12px 16px;
  border-top: 1px solid #444;
  flex-shrink: 0;
}
body:not(.dark) .transfer-result {
  border-top-color: #ddd;
}

.transfer-result h3 {
  margin: 0 0 8px;
  font-size: 14px;
  color: #4caf50;
}

.result-stats {
  display: flex;
  gap: 16px;
}

.stat { font-size: 12px; }
.stat.success { color: #4caf50; }
.stat.failed { color: #f44336; }
.stat.skipped { color: #ff9800; }

.errors {
  margin-top: 8px;
  font-size: 12px;
  color: #f44336;
}
.errors ul {
  margin: 4px 0 0;
  padding-left: 20px;
}
</style>
