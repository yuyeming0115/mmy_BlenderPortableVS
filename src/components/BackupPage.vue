<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, h } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage, useDialog } from 'naive-ui'
import { useAppStore } from '../stores/app'
import { open as shellOpen } from '@tauri-apps/plugin-shell'
import { open } from '@tauri-apps/plugin-dialog'
import { getCurrentWebview } from '@tauri-apps/api/webview'
import type { UnlistenFn } from '@tauri-apps/api/event'

const { t } = useI18n()
const store = useAppStore()
const msg = useMessage()
const dialog = useDialog()

const loading = ref(false)
const createLoading = ref(false)
const restoreLoading = ref(false)

// 备份源路径（独立于主页 pathA/pathB）
const backupSourcePath = ref('')
// 备份保存目录
const backupSaveDir = ref(store.config.backup_dir || '')
// 选项
const includeAddons = ref(true)
// 恢复对话框
const showRestoreModal = ref(false)
const restoreTargetPath = ref('')
const restoreOverwrite = ref(false)
const restoreBackupPath = ref('')

// 拖拽
const sourceRef = ref<HTMLElement | null>(null)
let unlistenDrag: UnlistenFn | null = null
const isDragging = ref(false)

// 收藏夹
function getFavoriteOptions(currentPath: string) {
  const opts = store.favoritePaths.filter(p => p !== currentPath)
  if (currentPath) opts.push(currentPath)
  return opts
}

async function onPathSelect(path: string) {
  backupSourcePath.value = path
}

// ===== 拖拽支持 =====
function getDropTarget(physicalX: number, physicalY: number): boolean {
  const dpr = window.devicePixelRatio || 1
  const x = physicalX / dpr
  const y = physicalY / dpr
  const el = sourceRef.value
  if (!el) return false
  const rect = el.getBoundingClientRect()
  return x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom
}

onMounted(async () => {
  store.loadFavorites()
  loadBackupList()

  // 监听从其他页面跳转过来的路径预填充
  window.addEventListener('backup-prefill', onBackupPrefill as EventListener)

  const webview = getCurrentWebview()
  unlistenDrag = await webview.onDragDropEvent((event) => {
    const payload = event.payload
    if (payload.type === 'over' || payload.type === 'enter') {
      isDragging.value = getDropTarget(payload.position.x, payload.position.y)
    } else if (payload.type === 'drop') {
      isDragging.value = false
      if (getDropTarget(payload.position.x, payload.position.y) && payload.paths.length > 0) {
        backupSourcePath.value = payload.paths[0]
      }
    } else if (payload.type === 'leave') {
      isDragging.value = false
    }
  })
})

onUnmounted(() => {
  unlistenDrag?.()
  window.removeEventListener('backup-prefill', onBackupPrefill as EventListener)
})

function onBackupPrefill(e: CustomEvent) {
  const path = e.detail?.path
  if (path) backupSourcePath.value = path
}

async function loadBackupList() {
  loading.value = true
  try {
    await store.loadBackups()
    const diag = await store.diagnoseBackups()
    if (!diag.dir_exists) {
      msg.warning(`备份目录不存在: ${diag.scanned_dir}`)
    }
  } catch (e: any) {
    msg.error(`加载备份列表失败: ${e}`)
  } finally {
    loading.value = false
  }
}

async function browseSource() {
  const selected = await open({ directory: true, multiple: false, title: t('backup_source') })
  if (selected) backupSourcePath.value = selected as string
}

async function browseSaveDir() {
  const selected = await open({ directory: true, multiple: false, title: t('backup_save_to') })
  if (selected) {
    backupSaveDir.value = selected as string
    store.config.backup_dir = selected as string
    store.saveConfig()
  }
}

async function doCreateBackup() {
  if (!backupSourcePath.value) {
    msg.warning(t('no_path'))
    return
  }
  createLoading.value = true
  try {
    // 尝试验证是否为 Blender 配置目录以获取版本号
    let version = ''
    try {
      const validation = await store.validatePath(backupSourcePath.value)
      if (validation.valid && validation.version) {
        version = validation.version
      }
    } catch { }

    const outputDir = backupSaveDir.value || undefined
    const result = await store.createBackup(
      backupSourcePath.value,
      version || backupSourcePath.value.split('/').pop() || 'unknown',
      includeAddons.value,
      outputDir,
    )
    if (result.success) {
      msg.success(t('backup_success'))
      await loadBackupList()
    } else {
      msg.error(`备份失败: ${result.message}`)
    }
  } catch (e: any) {
    msg.error(`创建备份失败: ${e}`)
  } finally {
    createLoading.value = false
  }
}

// 恢复 - 打开模态对话框
function openRestoreModal(backup: any) {
  restoreBackupPath.value = backup.path
  restoreTargetPath.value = backup.source_config_path || ''
  restoreOverwrite.value = false
  showRestoreModal.value = true
}

async function browseRestoreTarget() {
  const selected = await open({ directory: true, multiple: false, title: t('restore_to') })
  if (selected) restoreTargetPath.value = selected as string
}

async function doRestoreBackup() {
  if (!restoreTargetPath.value) {
    msg.warning(t('no_path'))
    return
  }
  restoreLoading.value = true
  try {
    const result = await store.restoreBackupItem(
      restoreBackupPath.value,
      restoreTargetPath.value,
      restoreOverwrite.value,
    )
    if (result.success) {
      msg.success(`${t('restore_success')}！恢复了 ${result.restored_files} 个文件`)
      showRestoreModal.value = false
    } else {
      msg.error(`恢复失败: ${result.errors.join(', ')}`)
    }
  } catch (e: any) {
    msg.error(`恢复失败: ${e}`)
  } finally {
    restoreLoading.value = false
  }
}

async function doDeleteBackup(backup: any) {
  dialog.warning({
    title: t('delete_confirm'),
    content: backup.filename,
    positiveText: t('confirm'),
    negativeText: t('cancel'),
    onPositiveClick: async () => {
      try {
        await store.deleteBackupItem(backup.path)
        msg.success(t('delete_success'))
        await loadBackupList()
      } catch (e: any) {
        msg.error(`删除失败: ${e}`)
      }
    },
  })
}

async function openBackupFolder(backup: any) {
  try {
    const folderPath = backup.path.substring(0, backup.path.lastIndexOf('/'))
    if (folderPath) {
      await shellOpen(`file://${folderPath}`)
    }
  } catch (e: any) {
    msg.error(`打开文件夹失败: ${e}`)
  }
}

function formatTimeStr(modified: string | null) {
  if (!modified) return '-'
  try {
    const d = new Date(modified)
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    const hh = String(d.getHours()).padStart(2, '0')
    const min = String(d.getMinutes()).padStart(2, '0')
    return `${mm}-${dd} ${hh}:${min}`
  } catch {
    return '-'
  }
}

// 统计
const totalSize = computed(() => {
  const bytes = store.backups.reduce((sum, b) => sum + (b.size_mb || 0), 0)
  return bytes < 1 ? `${(bytes * 1024).toFixed(0)} KB` : `${bytes.toFixed(1)} MB`
})

const totalCount = computed(() => store.backups.length)
</script>

<template>
  <div class="backup-page">
    <!-- Header -->
    <div class="page-header">
      <span class="page-title">{{ t('nav_backup') }}</span>
      <n-button
        type="primary"
        :loading="createLoading"
        :disabled="!backupSourcePath"
        @click="doCreateBackup"
      >
        {{ t('create_backup') }}
      </n-button>
    </div>

    <!-- 路径区 -->
    <div class="path-section" ref="sourceRef" :class="{ 'drag-over': isDragging }">
      <div class="path-row">
        <span class="path-label">{{ t('backup_source') }}</span>
        <div class="path-input-wrap">
          <n-dropdown
            trigger="click"
            :options="getFavoriteOptions(backupSourcePath).map(p => ({ label: p, key: p }))"
            @select="onPathSelect"
            :disabled="store.favoritePaths.length === 0"
          >
            <n-input
              v-model:value="backupSourcePath"
              :placeholder="t('backup_source_placeholder')"
              size="small"
              class="path-input"
              readonly
            />
          </n-dropdown>
        </div>
        <n-button
          size="small"
          :title="store.isFavorite(backupSourcePath) ? t('remove_favorite') : t('add_favorite')"
          @click="store.toggleFavorite(backupSourcePath)"
        >
          <span :style="{ color: store.isFavorite(backupSourcePath) ? '#f5c518' : undefined }">
            {{ store.isFavorite(backupSourcePath) ? '★' : '☆' }}
          </span>
        </n-button>
        <n-button size="small" @click="browseSource">{{ t('browse') }}</n-button>
      </div>
      <div class="path-row">
        <span class="path-label">{{ t('backup_save_to') }}</span>
        <n-input
          v-model:value="backupSaveDir"
          :placeholder="t('backup_dir')"
          size="small"
          style="flex:1"
          readonly
        />
        <n-button size="small" @click="browseSaveDir">{{ t('browse') }}</n-button>
        <n-checkbox v-model:checked="includeAddons" size="small" style="margin-left: 8px">
          {{ t('include_addons') }}
        </n-checkbox>
      </div>
    </div>

    <!-- 备份列表 -->
    <div v-if="store.backups.length > 0" class="backup-list">
      <n-data-table
        :columns="[
          {
            title: '',
            key: 'open_folder',
            width: 36,
            render: (row: any) =>
              h('span', {
                style: { cursor: 'pointer', fontSize: '16px' },
                onClick: () => openBackupFolder(row),
                title: t('open_folder'),
              }, '📦'),
          },
          { title: t('backup_name'), key: 'filename', ellipsis: { tooltip: true } },
          { title: t('backup_version'), key: 'blender_version', width: 100 },
          { title: t('backup_size'), key: 'size_mb', width: 80, render: (row: any) => row.size_mb.toFixed(1) + ' MB' },
          { title: t('backup_date'), key: 'created_at', width: 110, render: (row: any) => formatTimeStr(row.created_at) },
          {
            title: '',
            key: 'actions',
            width: 120,
            render: (row: any) =>
              h('div', { style: { display: 'flex', gap: '6px' } }, [
                h('button', {
                  class: 'n-button n-button--small n-button--info-type n-button--secondary',
                  onClick: () => openRestoreModal(row),
                }, t('restore')),
                h('button', {
                  class: 'n-button n-button--small n-button--error-type n-button--secondary',
                  onClick: () => doDeleteBackup(row),
                }, t('delete')),
              ]),
          },
        ]"
        :data="store.backups"
        size="small"
        striped
        :loading="loading"
        :row-key="(row: any) => row.path"
      />
    </div>

    <div v-else class="empty-hint">
      {{ t('no_backups') }}
    </div>

    <!-- 底部统计 -->
    <div class="action-bar">
      <span>{{ t('backup_total', [totalCount, totalSize]) }}</span>
      <n-button size="small" @click="loadBackupList">{{ t('scan') }}</n-button>
    </div>

    <!-- 恢复模态对话框 -->
    <n-modal v-model:show="showRestoreModal" preset="dialog" :title="t('restore')" positive-text="">
      <div class="restore-form">
        <div class="restore-form-row">
          <span class="restore-form-label">{{ t('restore_to') }}</span>
          <n-input
            v-model:value="restoreTargetPath"
            :placeholder="t('restore_to_placeholder')"
            size="small"
            style="flex:1"
            readonly
          />
          <n-button size="small" @click="browseRestoreTarget">{{ t('browse') }}</n-button>
        </div>
        <n-checkbox v-model:checked="restoreOverwrite" style="margin-top: 12px">
          {{ t('overwrite') }}
        </n-checkbox>
        <p class="restore-hint">{{ t('restore_overwrite_hint') }}</p>
      </div>
      <template #action>
        <n-button @click="showRestoreModal = false">{{ t('cancel') }}</n-button>
        <n-button
          type="primary"
          :loading="restoreLoading"
          :disabled="!restoreTargetPath"
          @click="doRestoreBackup"
        >
          {{ t('restore') }}
        </n-button>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.backup-page {
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

/* 路径区 */
.path-section {
  padding: 10px 12px;
  border-bottom: 1px solid #444;
  flex-shrink: 0;
  transition: background 0.2s;
}
body:not(.dark) .path-section {
  border-bottom-color: #ddd;
}
.path-section.drag-over {
  background: rgba(33, 150, 243, 0.08);
}

.path-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.path-row:last-child {
  margin-bottom: 0;
}

.path-label {
  font-size: 12px;
  font-weight: 600;
  color: #888;
  white-space: nowrap;
  flex-shrink: 0;
  min-width: 48px;
}

.path-input-wrap {
  flex: 1;
}
.path-input-wrap :deep(.n-input) {
  cursor: pointer;
}

/* 备份列表 */
.backup-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  margin: 8px;
}

.backup-list :deep(.n-data-table-wrapper) {
  height: 100%;
}

.backup-list :deep(.n-data-table-thead) {
  position: sticky;
  top: 0;
  z-index: 10;
}
.backup-list :deep(.n-data-table-th) {
  background: #2a2a2a !important;
}
body:not(.dark) .backup-list :deep(.n-data-table-th) {
  background: #f5f5f5 !important;
}

.empty-hint {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-size: 14px;
}

/* 底部 */
.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-top: 1px solid #444;
  flex-shrink: 0;
  font-size: 12px;
  color: #888;
}
body:not(.dark) .action-bar {
  border-top-color: #ddd;
}

/* 恢复对话框 */
.restore-form {
  padding: 4px 0;
}

.restore-form-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.restore-form-label {
  font-size: 13px;
  font-weight: 600;
  color: #888;
  white-space: nowrap;
  flex-shrink: 0;
  min-width: 56px;
}

.restore-hint {
  font-size: 12px;
  color: #666;
  margin: 8px 0 0;
}

/* 滚动条 */
.backup-list::-webkit-scrollbar {
  width: 8px;
}
.backup-list::-webkit-scrollbar-track {
  background: #1e1e1e;
  border-radius: 4px;
}
.backup-list::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 4px;
}
.backup-list::-webkit-scrollbar-thumb:hover {
  background: #777;
}
body:not(.dark) .backup-list::-webkit-scrollbar-track {
  background: #f0f0f0;
}
body:not(.dark) .backup-list::-webkit-scrollbar-thumb {
  background: #ccc;
}
</style>
