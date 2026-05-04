<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import { useAppStore, type ConfigFileInfo, type DirectoryEntry } from '../stores/app'
import { open } from '@tauri-apps/plugin-dialog'
import { getCurrentWebview } from '@tauri-apps/api/webview'
import type { UnlistenFn } from '@tauri-apps/api/event'

const { t } = useI18n()
const store = useAppStore()
const msg = useMessage()

interface PanelSide {
  label: string
  path: string
  isDragging: boolean
}

const sideA = ref<PanelSide>({ label: 'A', path: '', isDragging: false })
const sideB = ref<PanelSide>({ label: 'B', path: '', isDragging: false })

// 面板 DOM ref，用于位置判断
const panelARef = ref<HTMLElement | null>(null)
const panelBRef = ref<HTMLElement | null>(null)

function parsePath(path: string) {
  if (!path) return { folder: '-', file: '-' }
  const parts = path.split('/')
  const file = parts[parts.length - 1] || '-'
  // 取 config 或 scripts 后的相对路径作为文件夹
  const configIdx = parts.indexOf('config')
  const scriptsIdx = parts.indexOf('scripts')
  if (configIdx >= 0 && configIdx < parts.length - 1) {
    return { folder: 'config', file }
  }
  if (scriptsIdx >= 0 && scriptsIdx < parts.length - 1) {
    return { folder: parts.slice(scriptsIdx, -1).join('/'), file }
  }
  // 通用情况：取倒数第二级作为文件夹
  return { folder: parts.slice(-2, -1).join('/') || '-', file }
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

// 将 ConfigFileInfo 转换为表格行
function configToRow(row: ConfigFileInfo) {
  const { folder, file } = parsePath(row.path)
  return {
    ...row,
    _folder: folder,
    _file: file,
    _time: formatTime(row.modified_time),
    _is_dir: row.file_type.endsWith('_dir'),
    _from_scan: true,
  }
}

// 将 DirectoryEntry 转换为表格行
// entry.path 现在是相对路径，如 "scripts/addons/my_addon" 或 "config"
function dirEntryToRow(entry: DirectoryEntry) {
  const parts = entry.path.split('/')
  const folder = parts.length > 1 ? parts.slice(0, -1).join('/') : '-'
  return {
    _folder: folder,
    _file: entry.name,
    _time: formatTime(entry.modified_time),
    _is_dir: entry.is_dir,
    exists: true,
    _from_scan: false,
  }
}

// A区表格数据：合并 config 扫描结果 + 目录扫描结果
const tableDataA = computed(() => {
  const rows: any[] = []

  // 添加 config 扫描结果（过滤空路径）
  if (store.scanResultA) {
    for (const row of Object.values(store.scanResultA.configs)) {
      if (row.path) {
        rows.push(configToRow(row))
      }
    }
  }

  // 添加目录扫描结果（去重：按文件名匹配，跳过已存在的）
  if (store.dirEntriesA.length > 0) {
    const existingNames = new Set(rows.map(r => r._file))
    for (const entry of store.dirEntriesA) {
      if (!existingNames.has(entry.name)) {
        rows.push(dirEntryToRow(entry))
      }
    }
  }

  return rows
})

// B区表格数据
const tableDataB = computed(() => {
  const rows: any[] = []

  if (store.scanResultB) {
    for (const row of Object.values(store.scanResultB.configs)) {
      if (row.path) {
        rows.push(configToRow(row))
      }
    }
  }

  if (store.dirEntriesB.length > 0) {
    const existingNames = new Set(rows.map(r => r._file))
    for (const entry of store.dirEntriesB) {
      if (!existingNames.has(entry.name)) {
        rows.push(dirEntryToRow(entry))
      }
    }
  }

  return rows
})

// 新旧标注：只有两边都扫描了才显示
const showSyncStatus = computed(() => {
  return store.scanResultA !== null && store.scanResultB !== null
})

function getSyncLabel(row: any) {
  if (!showSyncStatus.value) return '-'
  // 目录级别的匹配（按文件名匹配）
  const aMatch = tableDataA.value.find(a => a._file === row._file && a._is_dir === row._is_dir)
  const bMatch = tableDataB.value.find(b => b._file === row._file && b._is_dir === row._is_dir)
  if (aMatch && bMatch) return '都有'
  if (aMatch) return '仅A'
  if (bMatch) return '仅B'
  return '-'
}

async function browsePath(side: 'A' | 'B') {
  try {
    const selected = await open({
      directory: true,
      multiple: false,
      title: side === 'A' ? '选择 A 目录' : '选择 B 目录',
    })
    let path = ''
    if (selected && typeof selected === 'string') {
      path = selected
    } else if (Array.isArray(selected) && selected.length > 0) {
      path = selected[0]
    }
    if (!path) return

    if (side === 'A') sideA.value.path = path
    else sideB.value.path = path

    // 验证路径并更新版本号到 store
    try {
      const validation = await store.validatePath(path)
      if (validation.valid) {
        store.setSideVersion(side, path, validation.version || '')
      } else {
        store.setSideVersion(side, path, '')
      }
    } catch {
      store.setSideVersion(side, path, '')
    }
  } catch (e: any) {
    msg.error(`选择路径失败: ${e}`)
  }
}

async function scanSide(side: 'A' | 'B') {
  const path = side === 'A' ? sideA.value.path : sideB.value.path
  if (!path) {
    msg.warning(t('no_path'))
    return
  }
  try {
    if (side === 'A') {
      await store.scanPathA(path)
    } else {
      await store.scanPathB(path)
    }
  } catch (e: any) {
    msg.error(`扫描失败: ${e}`)
  }
}

// ===== Tauri 拖拽事件（替代 HTML5 drag events） =====

let unlistenDrag: UnlistenFn | null = null

/** 根据鼠标物理坐标判断落在哪个面板区域 */
function getSideFromPosition(physicalX: number, physicalY: number): 'A' | 'B' | null {
  const dpr = window.devicePixelRatio || 1
  const x = physicalX / dpr
  const y = physicalY / dpr
  const checks: Array<[side: 'A' | 'B', el: HTMLElement | null]> = [
    ['A', panelARef.value],
    ['B', panelBRef.value],
  ]
  for (const [side, el] of checks) {
    if (!el) continue
    const rect = el.getBoundingClientRect()
    if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) {
      return side
    }
  }
  return null
}

/** 处理拖放的路径：验证 + 自动扫描 */
async function handleDroppedPath(side: 'A' | 'B', rawPath: string) {
  let path = rawPath

  // 先用原始路径验证
  let validation = await store.validatePath(path)

  // 如果无效，尝试父目录（可能用户拖入的是文件而非文件夹）
  if (!validation.valid) {
    const sep = path.includes('\\') ? '\\' : '/'
    const parts = path.split(sep)
    const parentPath = parts.slice(0, -1).join(sep)
    if (parentPath && parentPath !== path) {
      const parentValidation = await store.validatePath(parentPath)
      if (parentValidation.valid) {
        path = parentPath
        validation = parentValidation
        msg.info(t('drop_file_fallback'))
      }
    }
  }

  // 设置路径
  if (side === 'A') sideA.value.path = path
  else sideB.value.path = path

  // 更新 store 中的版本号
  store.setSideVersion(side, path, validation.valid ? (validation.version || '') : '')

  // 根据验证结果处理
  if (validation.valid) {
    msg.success(t('drop_auto_scan'))
    await scanSide(side)
  } else {
    msg.warning(`${t('invalid_blender_path')}: ${validation.message}`)
  }
}

onMounted(async () => {
  const webview = getCurrentWebview()
  unlistenDrag = await webview.onDragDropEvent((event) => {
    const payload = event.payload
    if (payload.type === 'over') {
      // 悬浮时高亮对应面板
      const side = getSideFromPosition(payload.position.x, payload.position.y)
      sideA.value.isDragging = side === 'A'
      sideB.value.isDragging = side === 'B'
    } else if (payload.type === 'enter') {
      // 进入窗口时高亮
      const side = getSideFromPosition(payload.position.x, payload.position.y)
      sideA.value.isDragging = side === 'A'
      sideB.value.isDragging = side === 'B'
    } else if (payload.type === 'drop') {
      // 松开：清除高亮，处理路径
      sideA.value.isDragging = false
      sideB.value.isDragging = false
      const side = getSideFromPosition(payload.position.x, payload.position.y)
      if (side && payload.paths.length > 0) {
        handleDroppedPath(side, payload.paths[0])
      }
    } else if (payload.type === 'leave') {
      // 离开窗口
      sideA.value.isDragging = false
      sideB.value.isDragging = false
    }
  })
})

onUnmounted(() => {
  unlistenDrag?.()
})

function scanAll() {
  if (sideA.value.path) scanSide('A')
  if (sideB.value.path) scanSide('B')
}

async function doCompare() {
  if (!sideA.value.path || !sideB.value.path) {
    msg.warning('请先设置 A 和 B 两个目录路径')
    return
  }
  try {
    await store.comparePaths(
      sideA.value.path,
      sideB.value.path,
      sideA.value.path,
      sideB.value.path,
    )
    msg.success('比较完成')
  } catch (e: any) {
    msg.error(`比较失败: ${e}`)
  }
}

// 表格列定义
const columns = [
  { type: 'selection' as const, width: 40 },
  {
    title: '文件夹',
    key: '_folder',
    width: 100,
    resizable: true,
    ellipsis: { tooltip: true },
  },
  {
    title: '文件',
    key: '_file',
    resizable: true,
    ellipsis: { tooltip: true },
  },
  {
    title: '时间',
    key: '_time',
    width: 90,
    resizable: true,
  },
  {
    title: '新旧',
    key: '_syncLabel',
    width: 60,
    resizable: true,
  },
]
</script>

<template>
  <div class="directory-panels">
    <!-- A/B 并排 -->
    <div class="panels-row">
      <!-- A 区 -->
      <div
        ref="panelARef"
        class="panel"
        :class="{ dragging: sideA.isDragging }"
      >
        <!-- 拖拽覆盖层（纯视觉反馈，事件由 Tauri onDragDropEvent 处理） -->
        <div class="drag-overlay"></div>
        <div class="panel-header">
          <div class="panel-path-row">
            <span class="panel-label">A 区</span>
            <n-input
              v-model:value="sideA.path"
              :placeholder="t('select_path')"
              size="small"
              class="path-input"
            />
            <n-button size="small" @click="browsePath('A')">{{ t('browse') }}</n-button>
            <n-button size="small" type="primary" @click="scanSide('A')">{{ t('scan') }}</n-button>
          </div>
        </div>
        <div class="panel-body">
          <n-data-table
            v-if="tableDataA.length > 0"
            :columns="columns"
            :data="tableDataA.map(row => ({
              ...row,
              _syncLabel: getSyncLabel(row),
            }))"
            size="small"
            striped
            class="config-table"
            :row-key="(row: any) => row._folder + '/' + row._file"
          />
          <div v-else class="empty-hint">
            {{ t('drag_hint') }}
          </div>
        </div>
      </div>

      <!-- B 区 -->
      <div
        ref="panelBRef"
        class="panel"
        :class="{ dragging: sideB.isDragging }"
      >
        <!-- 拖拽覆盖层（纯视觉反馈，事件由 Tauri onDragDropEvent 处理） -->
        <div class="drag-overlay"></div>
        <div class="panel-header">
          <div class="panel-path-row">
            <span class="panel-label">B 区</span>
            <n-input
              v-model:value="sideB.path"
              :placeholder="t('select_path')"
              size="small"
              class="path-input"
            />
            <n-button size="small" @click="browsePath('B')">{{ t('browse') }}</n-button>
            <n-button size="small" type="primary" @click="scanSide('B')">{{ t('scan') }}</n-button>
          </div>
        </div>
        <div class="panel-body">
          <n-data-table
            v-if="tableDataB.length > 0"
            :columns="columns"
            :data="tableDataB.map(row => ({
              ...row,
              _syncLabel: getSyncLabel(row),
            }))"
            size="small"
            striped
            class="config-table"
            :row-key="(row: any) => row._folder + '/' + row._file"
          />
          <div v-else class="empty-hint">
            {{ t('drag_hint') }}
          </div>
        </div>
      </div>
    </div>

    <!-- 底部操作栏 -->
    <div class="action-bar">
      <n-button type="primary" size="large" @click="scanAll">全部扫描</n-button>
      <n-button type="info" size="large" @click="doCompare">{{ t('compare') }}</n-button>
    </div>
  </div>
</template>

<style scoped>
.directory-panels {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.panels-row {
  display: flex;
  flex: 1;
  min-height: 0;
  gap: 0;
}

.panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  border-right: 1px solid #444;
  position: relative;
  transition: background 0.2s;
}
.panel:last-child {
  border-right: none;
}
body:not(.dark) .panel {
  border-right-color: #ddd;
}

.panel.dragging {
  background: rgba(33, 150, 243, 0.1);
}

.drag-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 5;
  pointer-events: none;
}
.panel.dragging .drag-overlay {
  pointer-events: auto;
  background: rgba(33, 150, 243, 0.08);
}

.panel-header {
  padding: 8px 12px;
  border-bottom: 1px solid #444;
  flex-shrink: 0;
}
body:not(.dark) .panel-header {
  border-bottom-color: #ddd;
}

.panel-label {
  font-size: 13px;
  font-weight: 700;
  color: #888;
  white-space: nowrap;
  flex-shrink: 0;
}

.panel-path-row {
  display: flex;
  gap: 6px;
  align-items: center;
}

.path-input {
  flex: 1;
}

.panel-body {
  flex: 1;
  min-height: 0;
}

.empty-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #666;
  font-size: 13px;
  text-align: center;
  padding: 20px;
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

/* 表格撑满面板，滚动在表格内部 */
.config-table {
  width: 100%;
  height: 100%;
}
.config-table :deep(.n-data-table-wrapper) {
  height: 100%;
  overflow-y: auto !important;
}

/* 表头冻结 */
.config-table :deep(.n-data-table-thead) {
  position: sticky;
  top: 0;
  z-index: 10;
}
.config-table :deep(.n-data-table-th) {
  background: #2a2a2a !important;
}
body:not(.dark) .config-table :deep(.n-data-table-th) {
  background: #f5f5f5 !important;
}
.config-table :deep(.n-data-table-td) {
  white-space: nowrap;
}
.config-table :deep(.n-data-table-th__resize-handle) {
  width: 6px;
  cursor: col-resize;
  background: transparent;
}
.config-table :deep(.n-data-table-th__resize-handle:hover),
.config-table :deep(.n-data-table-th__resize-handle--active) {
  background: rgba(33, 150, 243, 0.4);
}

/* 滚动条样式 */
.config-table :deep(.n-data-table-wrapper::-webkit-scrollbar) {
  width: 8px;
}
.config-table :deep(.n-data-table-wrapper::-webkit-scrollbar-track) {
  background: #1e1e1e;
  border-radius: 4px;
}
.config-table :deep(.n-data-table-wrapper::-webkit-scrollbar-thumb) {
  background: #555;
  border-radius: 4px;
}
.config-table :deep(.n-data-table-wrapper::-webkit-scrollbar-thumb:hover) {
  background: #777;
}
body:not(.dark) .config-table :deep(.n-data-table-wrapper::-webkit-scrollbar-track) {
  background: #f0f0f0;
}
body:not(.dark) .config-table :deep(.n-data-table-wrapper::-webkit-scrollbar-thumb) {
  background: #ccc;
}
body:not(.dark) .config-table :deep(.n-data-table-wrapper::-webkit-scrollbar-thumb:hover) {
  background: #aaa;
}
</style>
