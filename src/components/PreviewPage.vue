<script setup lang="ts">
import { ref, h, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '../stores/app'

const { t } = useI18n()
const store = useAppStore()

interface PendingRow {
  _path: string
  a_time: string
  a_status: string
  b_time: string
  b_status: string
}

// 辅助函数：文件夹对比用的时间格式化
function formatTimeForPreview(modified: string | null) {
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

// 辅助函数：差异类型转状态文字
function diffTypeToStatus(diffType: string, side: 'a' | 'b') {
  if (diffType === 'OnlyInSource') return side === 'a' ? '仅A' : '-'
  if (diffType === 'OnlyInTarget') return side === 'a' ? '-' : '仅B'
  if (diffType === 'Modified') return side === 'a' ? 'New' : 'Old'
  return '-'
}

// 优先使用 pendingPreviewItems（从主页面"比较"按钮传来）
// 为空时从文件夹对比结果或 checkedPaths + scanResult/dirEntries 构建
const pendingRows = computed<PendingRow[]>(() => {
  // 1. 如果 pendingPreviewItems 有数据，直接用
  if (store.pendingPreviewItems.length > 0) {
    return store.pendingPreviewItems as unknown as PendingRow[]
  }
  // 1.5 如果文件夹对比有结果，用它的数据构建
  if (store.folderDiffResult && store.folderDiffResult.entries.length > 0) {
    return store.folderDiffResult.entries
      .filter(e => store.checkedPaths.has(e.rel_path))
      .map(e => ({
        _path: e.rel_path,
        a_time: formatTimeForPreview(e.a_time),
        a_status: diffTypeToStatus(e.diff_type, 'a'),
        b_time: formatTimeForPreview(e.b_time),
        b_status: diffTypeToStatus(e.diff_type, 'b'),
      }))
      .sort((a, b) => a._path.localeCompare(b._path))
  }
  // 2. 否则从 checkedPaths + 扫描结果构建
  if (store.checkedPaths.size === 0) return []

  function formatTimeStr(modified: string | null) {
    if (!modified) return null
    try {
      const d = new Date(modified)
      const mm = String(d.getMonth() + 1).padStart(2, '0')
      const dd = String(d.getDate()).padStart(2, '0')
      const hh = String(d.getHours()).padStart(2, '0')
      const min = String(d.getMinutes()).padStart(2, '0')
      return { time: `${mm}-${dd} ${hh}:${min}`, raw: modified }
    } catch {
      return null
    }
  }

  // 构建 A/B 侧时间查找表（key = 文件名）
  const aFiles: Record<string, { time: string; raw: string }> = {}
  const bFiles: Record<string, { time: string; raw: string }> = {}

  if (store.scanResultA) {
    for (const cfg of Object.values(store.scanResultA.configs)) {
      if (cfg.modified_time) {
        const fileName = cfg.path.split('/').pop() || cfg.path
        const fmt = formatTimeStr(cfg.modified_time)
        if (fmt) aFiles[fileName] = fmt
      }
    }
  }
  if (store.scanResultB) {
    for (const cfg of Object.values(store.scanResultB.configs)) {
      if (cfg.modified_time) {
        const fileName = cfg.path.split('/').pop() || cfg.path
        const fmt = formatTimeStr(cfg.modified_time)
        if (fmt) bFiles[fileName] = fmt
      }
    }
  }

  // 用 dirEntries 补充
  for (const e of store.dirEntriesA) {
    const fmt = formatTimeStr(e.modified_time)
    if (fmt && !aFiles[e.name]) aFiles[e.name] = fmt
  }
  for (const e of store.dirEntriesB) {
    const fmt = formatTimeStr(e.modified_time)
    if (fmt && !bFiles[e.name]) bFiles[e.name] = fmt
  }

  const rows: PendingRow[] = []
  for (const path of store.checkedPaths) {
    const fileName = path.split('/').pop() || path
    const a = aFiles[fileName]
    const b = bFiles[fileName]
    let aStatus = '-'
    let bStatus = '-'
    if (a && b) {
      if (a.raw > b.raw) { aStatus = 'New'; bStatus = 'Old' }
      else if (b.raw > a.raw) { aStatus = 'Old'; bStatus = 'New' }
    } else if (a) {
      aStatus = '仅A'
    } else if (b) {
      bStatus = '仅B'
    }
    rows.push({
      _path: path,
      a_time: a ? a.time : '-',
      a_status: aStatus,
      b_time: b ? b.time : '-',
      b_status: bStatus,
    })
  }

  rows.sort((a, b) => a._path.localeCompare(b._path))
  return rows
})

// 默认全选（主页面传来的都是用户勾选过的）
// 用 ref + watch 确保 pendingRows 变化时自动重置
const selectedForSync = ref<Set<string>>(new Set())

watch(pendingRows, (rows) => {
  selectedForSync.value = new Set(rows.map(r => r._path))
}, { immediate: true })

function selectAll() {
  pendingRows.value.forEach(r => selectedForSync.value.add(r._path))
  selectedForSync.value = new Set(selectedForSync.value)
}

function deselectAll() {
  selectedForSync.value.clear()
  selectedForSync.value = new Set()
}

// 加入传输队列
function addToTransfer() {
  store.selectedSyncItems = pendingRows.value
    .filter(r => selectedForSync.value.has(r._path))
    .map(r => ({
      category: 'folder_file',
      item_type: 'file',
      name: r._path,
      diff_type: r.a_status === '仅A' ? 'OnlyInSource' : r.b_status === '仅B' ? 'OnlyInTarget' : 'Modified',
      source_value: null,
      target_value: null,
      recommended_action: 'SyncToTarget',
      user_action: null,
      details: null,
      risk_level: 'low',
      checked: true,
    }))
  // 跳转到传输页面
  window.dispatchEvent(new CustomEvent('navigate', { detail: 'transfer' }))
}

function getStatusLabel(status: string) {
  if (status === 'New') return { text: 'New', color: '#ff4444' }
  if (status === 'Old') return { text: 'Old', color: '#4caf50' }
  if (status === '仅A' || status === '仅源') return { text: status, color: '#ff9800' }
  if (status === '仅B' || status === '仅目标') return { text: status, color: '#2196f3' }
  return { text: status, color: undefined }
}

// 根据 A/B 状态给文件名着色：只有一侧有的文件，文件名染成对应侧颜色
function renderFileName(row: PendingRow) {
  const path = row._path
  const fileName = path.split('/').pop() || path
  const dirPath = path.substring(0, path.lastIndexOf('/') + 1)

  // 判断是否需要染色
  const aLabel = getStatusLabel(row.a_status)
  const bLabel = getStatusLabel(row.b_status)

  // 仅A 或 仅B 的情况，文件名染对应颜色
  let fileColor: string | undefined
  if (row.a_status === '仅A' || row.a_status === '仅源') {
    fileColor = aLabel.color
  } else if (row.b_status === '仅B' || row.b_status === '仅目标') {
    fileColor = bLabel.color
  } else if (aLabel.color && bLabel.color && aLabel.color !== bLabel.color) {
    // 两侧都有但状态不同（Old/New），文件名也标一个提示色
    fileColor = '#aaa'
  }

  if (fileColor) {
    return h('span', {}, [
      h('span', { style: { color: '#ccc' } }, dirPath),
      h('span', { style: { color: fileColor, fontWeight: 600 } }, fileName),
    ])
  }
  return path
}
</script>

<template>
  <div class="preview-page">
    <div class="page-header">
      <span class="page-title">{{ t('nav_preview') }}</span>
      <div class="header-actions">
        <n-button size="small" @click="selectAll">全选</n-button>
        <n-button size="small" @click="deselectAll">取消全选</n-button>
      </div>
    </div>

    <!-- 统计 -->
    <div v-if="pendingRows.length > 0" class="risk-summary">
      <span class="stats-text">
        共 {{ pendingRows.length }} 项 | 已选 {{ selectedForSync.size }} 项
      </span>
      <span v-if="store.pathA && store.pathB" class="transfer-direction">
        <span class="dir-side">
          <span class="dir-badge dir-badge-a">A</span>
          <span class="dir-path" :title="store.pathA">{{ store.pathA }}</span>
        </span>
        <span class="dir-arrow">➡️</span>
        <span class="dir-side">
          <span class="dir-badge dir-badge-b">B</span>
          <span class="dir-path" :title="store.pathB">{{ store.pathB }}</span>
        </span>
      </span>
    </div>
    <!-- 无数据时也显示方向提示 -->
    <div v-else-if="store.pathA && store.pathB" class="risk-summary">
      <span class="stats-text">共 0 项</span>
      <span class="transfer-direction">
        <span class="dir-side">
          <span class="dir-badge dir-badge-a">A</span>
          <span class="dir-path" :title="store.pathA">{{ store.pathA }}</span>
        </span>
        <span class="dir-arrow">➡️</span>
        <span class="dir-side">
          <span class="dir-badge dir-badge-b">B</span>
          <span class="dir-path" :title="store.pathB">{{ store.pathB }}</span>
        </span>
      </span>
    </div>

    <!-- 勾选列表 -->
    <div v-if="pendingRows.length > 0" class="diff-list">
      <n-data-table
        :columns="[
          {
            type: 'selection',
            width: 40,
          },
          { title: '文件', key: '_path', resizable: true, ellipsis: { tooltip: true }, render: renderFileName },
          { title: 'A', key: 'a_status', width: 70, resizable: true, render: (row: PendingRow) => {
            const s = getStatusLabel(row.a_status)
            return h('span', { style: { color: s.color, fontWeight: s.color ? 600 : 400 } }, s.text)
          }},
          { title: t('col_a_time'), key: 'a_time', width: 120, resizable: true },
          { title: 'B', key: 'b_status', width: 70, resizable: true, render: (row: PendingRow) => {
            const s = getStatusLabel(row.b_status)
            return h('span', { style: { color: s.color, fontWeight: s.color ? 600 : 400 } }, s.text)
          }},
          { title: t('col_b_time'), key: 'b_time', width: 120, resizable: true },
        ]"
        :data="pendingRows"
        size="small"
        striped
        :row-key="(row: PendingRow) => row._path"
        :checked-row-keys="Array.from(selectedForSync)"
        @update:checked-row-keys="(keys: string[]) => { selectedForSync = new Set(keys) }"
      />
    </div>

    <div v-else class="empty-hint">
      请先在主页面勾选需要预览的文件
    </div>

    <!-- 底部 -->
    <div class="action-bar">
      <n-button type="info" size="large" :disabled="selectedForSync.size === 0" @click="addToTransfer">
        {{ t('add_to_transfer_queue') }} ({{ selectedForSync.size }})
      </n-button>
    </div>
  </div>
</template>

<style scoped>
.preview-page {
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

.header-actions {
  display: flex;
  gap: 8px;
}

.page-title {
  font-size: 16px;
  font-weight: 700;
}

.risk-summary {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 16px;
  border-bottom: 1px solid #444;
  flex-shrink: 0;
}
body:not(.dark) .risk-summary {
  border-bottom-color: #ddd;
}

.stats-text {
  font-size: 12px;
  color: #888;
}

.transfer-direction {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  flex: 1;
  min-width: 0;
}

.dir-side {
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
  font-size: 14px;
}

.diff-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  margin: 8px;
}
/* 滚动条样式 */
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
body:not(.dark) .diff-list::-webkit-scrollbar-thumb:hover {
  background: #aaa;
}
.diff-list :deep(.n-data-table-wrapper) {
  overflow-x: auto;
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
.diff-list :deep(.n-data-table-th__resize-handle) {
  width: 6px;
  cursor: col-resize;
  background: transparent;
}
.diff-list :deep(.n-data-table-th__resize-handle:hover),
.diff-list :deep(.n-data-table-th__resize-handle--active) {
  background: rgba(33, 150, 243, 0.4);
}

.empty-hint {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-size: 14px;
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
</style>
