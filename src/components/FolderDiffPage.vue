<script setup lang="ts">
import { ref, computed, h, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import { useAppStore } from '../stores/app'
import { open } from '@tauri-apps/plugin-dialog'
import { getCurrentWebview } from '@tauri-apps/api/webview'
import type { UnlistenFn } from '@tauri-apps/api/event'

const { t } = useI18n()
const store = useAppStore()
const msg = useMessage()

const scanning = ref(false)
const localPathA = ref(store.pathA || '')
const localPathB = ref(store.pathB || '')
const dragTarget = ref<'none' | 'A' | 'B'>('none')
let lastClickedIndex = -1

const pathARef = ref<HTMLElement | null>(null)
const pathBRef = ref<HTMLElement | null>(null)

// ===== 收藏夹 =====
// 收藏夹下拉选项（去重 + 当前路径排最后）
function getFavoriteOptions(currentPath: string) {
  const opts = store.favoritePaths.filter(p => p !== currentPath)
  if (currentPath) opts.push(currentPath)
  return opts
}

async function onPathSelect(side: 'A' | 'B', path: string) {
  if (side === 'A') {
    localPathA.value = path
    store.pathA = path
  } else {
    localPathB.value = path
    store.pathB = path
  }
  store.saveLastPaths()
}

// ===== 拖拽支持 =====
let unlistenDrag: UnlistenFn | null = null

function getDropTarget(physicalX: number, physicalY: number): 'A' | 'B' | null {
  const dpr = window.devicePixelRatio || 1
  const x = physicalX / dpr
  const y = physicalY / dpr
  const checks: Array<[target: 'A' | 'B', el: HTMLElement | null]> = [
    ['A', pathARef.value],
    ['B', pathBRef.value],
  ]
  for (const [target, el] of checks) {
    if (!el) continue
    const rect = el.getBoundingClientRect()
    if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) {
      return target
    }
  }
  return null
}

async function handleDroppedPath(target: 'A' | 'B', rawPath: string) {
  // 文件夹对比模块，直接接受拖入的路径，同步到 store
  if (target === 'A') {
    localPathA.value = rawPath
    store.pathA = rawPath
  } else {
    localPathB.value = rawPath
    store.pathB = rawPath
  }
  store.saveLastPaths()
}

// 同步本地路径回 store（浏览选择后也更新）
watch(localPathA, (val) => {
  if (val !== store.pathA) {
    store.pathA = val
    store.saveLastPaths()
  }
})
watch(localPathB, (val) => {
  if (val !== store.pathB) {
    store.pathB = val
    store.saveLastPaths()
  }
})

// 交换 A/B 路径
function swapAB() {
  const tmpA = localPathA.value
  localPathA.value = localPathB.value
  localPathB.value = tmpA
  // store 通过 watch 自动同步
}

onMounted(async () => {
  store.loadFavorites()
  const webview = getCurrentWebview()
  unlistenDrag = await webview.onDragDropEvent((event) => {
    const payload = event.payload
    if (payload.type === 'over' || payload.type === 'enter') {
      const target = getDropTarget(payload.position.x, payload.position.y)
      dragTarget.value = target || 'none'
    } else if (payload.type === 'drop') {
      dragTarget.value = 'none'
      const target = getDropTarget(payload.position.x, payload.position.y)
      if (target && payload.paths.length > 0) {
        handleDroppedPath(target, payload.paths[0])
      }
    } else if (payload.type === 'leave') {
      dragTarget.value = 'none'
    }
  })
})

onUnmounted(() => {
  unlistenDrag?.()
})

async function browsePath(side: 'A' | 'B') {
  const selected = await open({ directory: true, multiple: false, title: side === 'A' ? t('select_folder_a') : t('select_folder_b') })
  if (selected) {
    if (side === 'A') localPathA.value = selected as string
    else localPathB.value = selected as string
    // store 通过 watch 自动同步
  }
}

async function doScan() {
  if (!localPathA.value || !localPathB.value) {
    msg.warning('请先选择两个文件夹')
    return
  }
  scanning.value = true
  store.checkedPaths.clear()
  try {
    await store.scanAndDiffFolders(localPathA.value, localPathB.value)
    // 默认勾选有差异的项
    if (store.folderDiffResult) {
      for (const entry of store.folderDiffResult.entries) {
        if (entry.diff_type !== 'Same') {
          store.checkedPaths.add(entry.rel_path)
        }
      }
    }
  } catch (e: any) {
    msg.error(`扫描失败: ${e}`)
  } finally {
    scanning.value = false
  }
}

function formatTime(timeStr: string | null) {
  if (!timeStr) return '-'
  try {
    const d = new Date(timeStr)
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    const hh = String(d.getHours()).padStart(2, '0')
    const min = String(d.getMinutes()).padStart(2, '0')
    return `${mm}-${dd} ${hh}:${min}`
  } catch {
    return '-'
  }
}

function getStatusLabel(type: string) {
  if (type === 'OnlyInSource') return { text: t('diff_only_a'), color: '#ff9800' }
  if (type === 'OnlyInTarget') return { text: t('diff_only_b'), color: '#2196f3' }
  if (type === 'Modified') return { text: t('diff_modified'), color: '#ff4d4f' }
  if (type === 'Same') return { text: t('diff_same'), color: '#52c41a' }
  return { text: type, color: '#888' }
}

// 渲染文件名：差异部分染对应颜色
function renderFileName(entry: any) {
  const relPath = entry.rel_path
  const fileName = relPath.split('/').pop() || relPath
  const dirPath = relPath.substring(0, relPath.lastIndexOf('/') + 1)

  const label = getStatusLabel(entry.diff_type)
  let fileColor: string | undefined

  if (entry.diff_type === 'OnlyInSource') {
    fileColor = '#ff9800'
  } else if (entry.diff_type === 'OnlyInTarget') {
    fileColor = '#2196f3'
  } else if (entry.diff_type === 'Modified') {
    fileColor = '#ff4d4f'
  }

  if (fileColor && dirPath) {
    return h('span', {}, [
      h('span', { style: { color: '#888' } }, dirPath),
      h('span', { style: { color: fileColor, fontWeight: 600 } }, fileName),
    ])
  }
  return relPath
}

// 全选/取消全选
function toggleSelectAll() {
  if (!store.folderDiffResult) return
  if (store.checkedPaths.size === store.folderDiffResult.entries.length) {
    store.checkedPaths.clear()
  } else {
    for (const entry of store.folderDiffResult.entries) {
      store.checkedPaths.add(entry.rel_path)
    }
  }
}

const checkedCount = computed(() => store.checkedPaths.size)
const totalCount = computed(() => store.folderDiffResult?.entries.length || 0)

// 加入预览清单
function addToPreview() {
  if (!store.folderDiffResult || store.checkedPaths.size === 0) return
  // 将勾选项传入 store.pendingPreviewItems
  store.pendingPreviewItems.value = store.folderDiffResult.entries
    .filter(e => store.checkedPaths.has(e.rel_path))
    .map(e => ({
      _path: e.rel_path,
      a_time: formatTime(e.a_time),
      b_time: formatTime(e.b_time),
      a_status: e.diff_type === 'OnlyInSource' ? '仅A' : e.diff_type === 'OnlyInTarget' ? '仅B' : e.diff_type === 'Modified' ? 'New' : '-',
      b_status: e.diff_type === 'OnlyInSource' ? '-' : e.diff_type === 'OnlyInTarget' ? '仅B' : e.diff_type === 'Modified' ? 'Old' : '-',
    }))
  navigate('preview')
}

function navigate(page: string) {
  window.dispatchEvent(new CustomEvent('navigate', { detail: page }))
}

// 整行点击切换勾选（含复选框列、Shift 范围选择）
function handleRowClick(row: any, event: MouseEvent) {
  const td = (event.target as HTMLElement).closest('td')
  if (td && td.classList.contains('n-data-table-td--selection')) return

  const entries = store.folderDiffResult?.entries || []
  const currentIdx = entries.findIndex(e => e.rel_path === row.rel_path)

  if (event.shiftKey) {
    if (lastClickedIndex >= 0 && currentIdx >= 0) {
      const start = Math.min(lastClickedIndex, currentIdx)
      const end = Math.max(lastClickedIndex, currentIdx)
      for (let i = start; i <= end; i++) {
        store.checkedPaths.add(entries[i].rel_path)
      }
    } else {
      if (store.checkedPaths.has(row.rel_path)) {
        store.checkedPaths.delete(row.rel_path)
      } else {
        store.checkedPaths.add(row.rel_path)
      }
    }
    lastClickedIndex = currentIdx
  } else {
    if (store.checkedPaths.has(row.rel_path)) {
      store.checkedPaths.delete(row.rel_path)
    } else {
      store.checkedPaths.add(row.rel_path)
    }
    lastClickedIndex = currentIdx
  }
}

function clearAll() {
  localPathA.value = ''
  localPathB.value = ''
  store.pathA = ''
  store.pathB = ''
  store.folderDiffResult = null
  store.checkedPaths.clear()
  store.saveLastPaths()
}

// 跳转备份页面，预填充 A 侧路径
function goBackup() {
  const path = localPathA.value || localPathB.value || ''
  navigate('backup')
  if (path) {
    setTimeout(() => {
      window.dispatchEvent(new CustomEvent('backup-prefill', { detail: { path } }))
    }, 100)
  }
}
</script>

<template>
  <div class="folder-diff-page">
    <div class="page-header">
      <span class="page-title">{{ t('folder_diff_title') }}</span>
    </div>

    <!-- 路径选择：左右两列一行 -->
    <div class="path-section">
      <div class="panels-row">
        <div class="panel" ref="pathARef" :class="{ 'drag-over': dragTarget === 'A' }">
          <div class="panel-path-row">
            <span class="panel-label">A 区</span>
            <div class="path-input-wrap">
              <n-dropdown
                trigger="click"
                :options="getFavoriteOptions(localPathA).map(p => ({ label: p, key: p }))"
                @select="(key: string) => onPathSelect('A', key)"
                :disabled="store.favoritePaths.length === 0"
              >
                <n-input v-model:value="localPathA" :placeholder="t('select_folder_a')" size="small" class="path-input" readonly />
              </n-dropdown>
            </div>
            <n-button size="small" :title="store.isFavorite(localPathA) ? '取消收藏' : '加入收藏'" @click="store.toggleFavorite(localPathA)">
              <span :style="{ color: store.isFavorite(localPathA) ? '#f5c518' : undefined }">{{ store.isFavorite(localPathA) ? '★' : '☆' }}</span>
            </n-button>
            <n-button size="small" @click="browsePath('A')">{{ t('browse') }}</n-button>
          </div>
        </div>
        <div class="swap-divider">
          <n-button circle size="small" type="primary" @click="swapAB" title="交换 A/B 路径">
            <span style="font-size: 14px; line-height: 1">⇄</span>
          </n-button>
        </div>
        <div class="panel" ref="pathBRef" :class="{ 'drag-over': dragTarget === 'B' }">
          <div class="panel-path-row">
            <span class="panel-label">B 区</span>
            <div class="path-input-wrap">
              <n-dropdown
                trigger="click"
                :options="getFavoriteOptions(localPathB).map(p => ({ label: p, key: p }))"
                @select="(key: string) => onPathSelect('B', key)"
                :disabled="store.favoritePaths.length === 0"
              >
                <n-input v-model:value="localPathB" :placeholder="t('select_folder_b')" size="small" class="path-input" readonly />
              </n-dropdown>
            </div>
            <n-button size="small" :title="store.isFavorite(localPathB) ? '取消收藏' : '加入收藏'" @click="store.toggleFavorite(localPathB)">
              <span :style="{ color: store.isFavorite(localPathB) ? '#f5c518' : undefined }">{{ store.isFavorite(localPathB) ? '★' : '☆' }}</span>
            </n-button>
            <n-button size="small" @click="browsePath('B')">{{ t('browse') }}</n-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 统计 -->
    <div v-if="store.folderDiffResult" class="stats-row">
      <n-tag type="info" size="small">A: {{ store.folderDiffResult.summary.total_a }} 项</n-tag>
      <n-tag type="info" size="small">B: {{ store.folderDiffResult.summary.total_b }} 项</n-tag>
      <n-tag type="warning" size="small">仅A: {{ store.folderDiffResult.summary.only_in_source }}</n-tag>
      <n-tag type="warning" size="small">仅B: {{ store.folderDiffResult.summary.only_in_target }}</n-tag>
      <n-tag type="error" size="small">已修改: {{ store.folderDiffResult.summary.modified }}</n-tag>
      <n-tag type="success" size="small">相同: {{ store.folderDiffResult.summary.same }}</n-tag>
    </div>

    <!-- 差异列表 -->
    <div v-if="store.folderDiffResult && store.folderDiffResult.entries.length > 0" class="diff-list">
      <n-data-table
        :columns="[
          {
            type: 'selection',
            width: 40,
          },
          {
            title: '文件',
            key: 'rel_path',
            resizable: true,
            ellipsis: { tooltip: true },
            render: renderFileName,
          },
          {
            title: 'A 时间',
            key: 'a_time',
            width: 110,
            render: (row: any) => formatTime(row.a_time),
          },
          {
            title: 'A',
            key: 'a_status',
            width: 60,
            render: (row: any) => {
              const s = getStatusLabel(row.diff_type === 'OnlyInTarget' ? 'Same' : row.diff_type)
              return h('span', { style: { color: row.diff_type === 'OnlyInSource' ? s.color : '#666', fontWeight: row.diff_type === 'OnlyInSource' ? 600 : 400 } }, row.diff_type === 'OnlyInSource' ? s.text : '-')
            },
          },
          {
            title: 'B 时间',
            key: 'b_time',
            width: 110,
            render: (row: any) => formatTime(row.b_time),
          },
          {
            title: 'B',
            key: 'b_status',
            width: 60,
            render: (row: any) => {
              const s = getStatusLabel(row.diff_type === 'OnlyInSource' ? 'Same' : row.diff_type)
              return h('span', { style: { color: row.diff_type === 'OnlyInTarget' ? s.color : '#666', fontWeight: row.diff_type === 'OnlyInTarget' ? 600 : 400 } }, row.diff_type === 'OnlyInTarget' ? s.text : '-')
            },
          },
        ]"
        :data="store.folderDiffResult.entries"
        size="small"
        striped
        :row-key="(row: any) => row.rel_path"
        :checked-row-keys="Array.from(store.checkedPaths)"
        @update:checked-row-keys="(keys: string[]) => { store.checkedPaths = new Set(keys) }"
        :row-props="(row: any) => ({
          style: { cursor: 'pointer' },
          onClick: (e: MouseEvent) => {
            e.stopPropagation()
            handleRowClick(row, e)
          },
        })"
      />
    </div>

    <div v-else-if="!store.folderDiffResult" class="empty-hint">
      <div class="empty-content">
        <div class="empty-text">{{ t('folder_diff_drop_hint') }}</div>
        <div class="drag-visual">
          <div class="drag-arrow drag-arrow-left">
            <div class="arrow-line"></div>
            <span class="arrow-label">A</span>
          </div>
          <div class="drop-icon">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="4" y="4" width="40" height="40" rx="8" stroke="#666" stroke-width="2" stroke-dasharray="6 4"/>
              <path d="M24 14V34M24 34L16 26M24 34L32 26" stroke="#666" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="drag-arrow drag-arrow-right">
            <div class="arrow-line"></div>
            <span class="arrow-label">B</span>
          </div>
        </div>
        <div class="empty-subtext">{{ t('folder_diff_drop_sub') }}</div>
      </div>
    </div>

    <!-- 底部操作栏 -->
    <div class="action-bar">
      <n-button :loading="scanning" :disabled="!localPathA || !localPathB" @click="doScan" size="large">
        {{ t('scan_folders') }}
      </n-button>
      <n-button type="primary" size="large" :disabled="checkedCount === 0" @click="addToPreview">
        {{ t('add_to_transfer_queue') }} ({{ checkedCount }})
      </n-button>
      <n-button size="large" :disabled="!localPathA && !localPathB" @click="goBackup">{{ t('backup') }}</n-button>
      <n-button size="large" @click="clearAll">清空</n-button>
    </div>
  </div>
</template>

<style scoped>
.folder-diff-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.page-header {
  display: flex;
  align-items: center;
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

.path-section {
  padding: 0;
  border-bottom: 1px solid #444;
  flex-shrink: 0;
}
body:not(.dark) .path-section {
  border-bottom-color: #ddd;
}

.panels-row {
  display: flex;
  gap: 0;
}

.panel {
  flex: 1;
  min-width: 0;
  transition: background 0.2s;
}
.panel.drag-over {
  background: rgba(33, 150, 243, 0.1);
}

.panel-path-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid #444;
}
body:not(.dark) .panel-path-row {
  border-bottom-color: #ddd;
}

.panel-label {
  font-size: 13px;
  font-weight: 700;
  color: #888;
  white-space: nowrap;
  flex-shrink: 0;
}

.path-input-wrap {
  flex: 1;
}

.path-input-wrap :deep(.n-input) {
  cursor: pointer;
}

.swap-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  flex-shrink: 0;
  border-right: 1px solid #444;
}
body:not(.dark) .swap-divider {
  border-right-color: #ddd;
}
.swap-divider .n-button {
  border-radius: 50%;
  width: 24px;
  height: 24px;
  min-width: 24px;
}

.stats-row {
  display: flex;
  gap: 8px;
  padding: 8px 16px;
  border-bottom: 1px solid #444;
  flex-shrink: 0;
  flex-wrap: wrap;
}
body:not(.dark) .stats-row {
  border-bottom-color: #ddd;
}

.diff-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  margin: 8px;
}

.diff-list :deep(.n-data-table-wrapper) {
  height: 100%;
}

.diff-list :deep(.n-data-table-thead) {
  position: sticky;
  top: 0;
  z-index: 10;
}
.diff-list :deep(.n-data-table-th) {
  background: #2a2a2a !important;
}
body:not(.dark) .diff-list :deep(.n-data-table-th) {
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

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.empty-text {
  font-size: 14px;
  color: #999;
}

.drag-visual {
  display: flex;
  align-items: center;
  gap: 12px;
}

.drag-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.arrow-line {
  width: 40px;
  height: 2px;
  border-top: 2px dashed #555;
  position: relative;
}

.drag-arrow-left .arrow-line {
  border-left: 2px solid transparent;
}

.drag-arrow-right .arrow-line {
  border-right: 2px solid transparent;
}

.arrow-label {
  font-size: 12px;
  font-weight: 700;
  color: #64b5f6;
}

.drop-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-subtext {
  font-size: 12px;
  color: #666;
}

.action-bar {
  display: flex;
  gap: 12px;
  justify-content: center;
  padding: 10px 16px;
  border-top: 1px solid #444;
  flex-shrink: 0;
}
body:not(.dark) .action-bar {
  border-top-color: #ddd;
}

/* 滚动条 */
.diff-list::-webkit-scrollbar {
  width: 8px;
}
.diff-list::-webkit-scrollbar-track {
  background: #1e1e1e;
  border-radius: 4px;
}
.diff-list::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 4px;
}
.diff-list::-webkit-scrollbar-thumb:hover {
  background: #777;
}
body:not(.dark) .diff-list::-webkit-scrollbar-track {
  background: #f0f0f0;
}
body:not(.dark) .diff-list::-webkit-scrollbar-thumb {
  background: #ccc;
}
</style>
