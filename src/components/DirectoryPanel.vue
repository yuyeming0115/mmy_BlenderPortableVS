<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, h, watch } from 'vue'
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

const sideA = ref<PanelSide>({ label: 'A', path: store.pathA, isDragging: false })
const sideB = ref<PanelSide>({ label: 'B', path: store.pathB, isDragging: false })

// 同步本地路径到 store
watch(() => sideA.value.path, (val) => { store.pathA = val })
watch(() => sideB.value.path, (val) => { store.pathB = val })

const panelARef = ref<HTMLElement | null>(null)
const panelBRef = ref<HTMLElement | null>(null)

function parsePath(path: string) {
  if (!path) return { folder: '-', file: '-' }
  const parts = path.split('/')
  const file = parts[parts.length - 1] || '-'
  const configIdx = parts.indexOf('config')
  const scriptsIdx = parts.indexOf('scripts')
  if (configIdx >= 0 && configIdx < parts.length - 1) {
    return { folder: 'config', file }
  }
  if (scriptsIdx >= 0 && scriptsIdx < parts.length - 1) {
    return { folder: parts.slice(scriptsIdx, -1).join('/'), file }
  }
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

function configToRow(row: ConfigFileInfo) {
  const { folder, file } = parsePath(row.path)
  return {
    ...row,
    _folder: folder,
    _file: file,
    _time: formatTime(row.modified_time),
    _raw_time: row.modified_time,
    _is_dir: row.file_type.endsWith('_dir'),
  }
}

function dirEntryToRow(entry: DirectoryEntry) {
  const parts = entry.path.split('/')
  const folder = parts.length > 1 ? parts.slice(0, -1).join('/') : '-'
  return {
    _folder: folder,
    _file: entry.name,
    _time: formatTime(entry.modified_time),
    _is_dir: entry.is_dir,
    exists: true,
    _raw_time: entry.modified_time,
  }
}

const tableDataA = computed(() => {
  const rows: any[] = []
  if (store.scanResultA) {
    for (const row of Object.values(store.scanResultA.configs)) {
      if (row.path) rows.push(configToRow(row))
    }
  }
  if (store.dirEntriesA.length > 0) {
    const existingNames = new Set(rows.map(r => r._file))
    for (const entry of store.dirEntriesA) {
      if (!existingNames.has(entry.name)) rows.push(dirEntryToRow(entry))
    }
  }
  return rows
})

const tableDataB = computed(() => {
  const rows: any[] = []
  if (store.scanResultB) {
    for (const row of Object.values(store.scanResultB.configs)) {
      if (row.path) rows.push(configToRow(row))
    }
  }
  if (store.dirEntriesB.length > 0) {
    const existingNames = new Set(rows.map(r => r._file))
    for (const entry of store.dirEntriesB) {
      if (!existingNames.has(entry.name)) rows.push(dirEntryToRow(entry))
    }
  }
  return rows
})

// 统一对比行
interface UnifiedRow {
  _path: string
  _file: string
  _is_dir: boolean
  a_time: string
  a_rawTime: string
  a_status: string
  b_time: string
  b_rawTime: string
  b_status: string
  _hasDiff: boolean
  _checked: boolean  // 复选框
}

// 用 store 中的 checkedPaths 持久化勾选状态（跨页面切换不丢失）
// autoCheckDone 也在 store 中，避免切换页面后组件重建导致重新自动勾选

const unifiedRows = computed((): UnifiedRow[] => {
  const aList = tableDataA.value
  const bList = tableDataB.value
  const result: UnifiedRow[] = []

  const fileMap = new Map<string, { a?: any; b?: any }>()

  for (const a of aList) {
    const key = a._file + '|' + a._is_dir
    if (!fileMap.has(key)) fileMap.set(key, { a })
    else fileMap.get(key)!.a = a
  }
  for (const b of bList) {
    const key = b._file + '|' + b._is_dir
    if (!fileMap.has(key)) fileMap.set(key, { b })
    else fileMap.get(key)!.b = b
  }

  for (const [, match] of fileMap) {
    const a = match.a
    const b = match.b
    const folder = a ? a._folder : b ? b._folder : '-'
    const file = a ? a._file : b ? b._file : '-'
    const isDir = a ? a._is_dir : b ? b._is_dir : false
    const combinedPath = folder === '-' ? file : `${folder}/${file}`

    const aRawTime = a ? (a.modified_time || a._raw_time || '') : ''
    const bRawTime = b ? (b.modified_time || b._raw_time || '') : ''

    let aStatus = '-'
    let bStatus = '-'

    if (a && b) {
      if (aRawTime && bRawTime) {
        if (aRawTime > bRawTime) {
          aStatus = 'New'
          bStatus = 'Old'
        } else if (bRawTime > aRawTime) {
          aStatus = 'Old'
          bStatus = 'New'
        } else {
          aStatus = '-'
          bStatus = '-'
        }
      }
    } else if (a) {
      aStatus = '仅A'
    } else if (b) {
      bStatus = '仅B'
    }

    const hasDiff = aStatus !== '-' && bStatus !== '-' && (aStatus === 'New' || aStatus === 'Old')

    result.push({
      _path: combinedPath,
      _file: file,
      _is_dir: isDir,
      a_time: a ? a._time : '-',
      a_rawTime: aRawTime,
      a_status: aStatus,
      b_time: b ? b._time : '-',
      b_rawTime: bRawTime,
      b_status: bStatus,
      _hasDiff: hasDiff,
      _checked: false, // 不由 computed 决定，由 Naive UI 控制
    })
  }

  result.sort((a, b) => a._path.localeCompare(b._path))

  // 首次初始化：有差异的默认勾选
  if (!store.autoCheckDone && result.length > 0) {
    store.autoCheckDone = true
    for (const row of result) {
      const isDiff = row._hasDiff || row.a_status === '仅A' || row.a_status === '仅B' || row.b_status === '仅B'
      if (isDiff) {
        store.checkedPaths.add(row._path)
      }
    }
  }

  return result
})

// 勾选计数：基于 store.checkedPaths 计算
const checkedCount = computed(() => {
  return unifiedRows.value.filter(r => store.checkedPaths.has(r._path)).length
})

function statusColor(status: string) {
  if (status === 'New') return '#ff4d4f'
  if (status === 'Old') return '#52c41a'
  if (status === '仅A') return '#ff9800'
  if (status === '仅B') return '#2196f3'
  return '#666'
}

function statusText(status: string) {
  if (status === 'New') return t('label_new')
  if (status === 'Old') return t('label_old')
  if (status === '仅A') return t('diff_only_source')
  if (status === '仅B') return t('diff_only_target')
  return '-'
}

// ===== 收藏夹 =====
async function onPathSelect(side: 'A' | 'B', path: string) {
  if (side === 'A') sideA.value.path = path
  else sideB.value.path = path
  // 自动验证并扫描
  try {
    const validation = await store.validatePath(path)
    store.setSideVersion(side, path, validation.valid ? (validation.version || '') : '')
    if (validation.valid) {
      msg.success(t('drop_auto_scan'))
      await scanSide(side)
    } else {
      msg.warning(`${t('invalid_blender_path')}: ${validation.message}`)
    }
  } catch (e: any) {
    msg.error(`扫描失败: ${e}`)
  }
}

// 收藏夹下拉选项（去重 + 当前路径排最后）
function getFavoriteOptions(currentPath: string) {
  const opts = store.favoritePaths.filter(p => p !== currentPath)
  if (currentPath) opts.push(currentPath)
  return opts
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
  // 重新扫描时重置勾选状态
  store.autoCheckDone = false
  store.checkedPaths.clear()
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

// ===== Tauri 拖拽事件 =====

let unlistenDrag: UnlistenFn | null = null

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

async function handleDroppedPath(side: 'A' | 'B', rawPath: string) {
  let path = rawPath
  let validation = await store.validatePath(path)
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

  if (side === 'A') sideA.value.path = path
  else sideB.value.path = path
  store.setSideVersion(side, path, validation.valid ? (validation.version || '') : '')

  if (validation.valid) {
    msg.success(t('drop_auto_scan'))
    await scanSide(side)
  } else {
    msg.warning(`${t('invalid_blender_path')}: ${validation.message}`)
  }
}

onMounted(async () => {
  store.loadFavorites()
  const webview = getCurrentWebview()
  unlistenDrag = await webview.onDragDropEvent((event) => {
    const payload = event.payload
    if (payload.type === 'over') {
      const side = getSideFromPosition(payload.position.x, payload.position.y)
      sideA.value.isDragging = side === 'A'
      sideB.value.isDragging = side === 'B'
    } else if (payload.type === 'enter') {
      const side = getSideFromPosition(payload.position.x, payload.position.y)
      sideA.value.isDragging = side === 'A'
      sideB.value.isDragging = side === 'B'
    } else if (payload.type === 'drop') {
      sideA.value.isDragging = false
      sideB.value.isDragging = false
      const side = getSideFromPosition(payload.position.x, payload.position.y)
      if (side && payload.paths.length > 0) {
        handleDroppedPath(side, payload.paths[0])
      }
    } else if (payload.type === 'leave') {
      sideA.value.isDragging = false
      sideB.value.isDragging = false
    }
  })
})

onUnmounted(() => {
  unlistenDrag?.()
})

function clearAll() {
  store.autoCheckDone = false
  store.checkedPaths.clear()
  store.pendingPreviewItems.value = []
  store.clearAll()
}

function scanAll() {
  store.autoCheckDone = false
  store.checkedPaths.clear()
  if (sideA.value.path) scanSide('A')
  if (sideB.value.path) scanSide('B')
}

function swapAB() {
  const tmpSide = { ...sideA.value }
  sideA.value = { ...sideB.value }
  sideB.value = { ...tmpSide }

  const tmpPath = store.pathA
  store.pathA = store.pathB
  store.pathB = tmpPath

  const tmpVer = store.versionA
  store.versionA = store.versionB
  store.versionB = tmpVer

  const tmpScan = store.scanResultA
  store.scanResultA = store.scanResultB
  store.scanResultB = tmpScan

  const tmpDir = store.dirEntriesA
  store.dirEntriesA = store.dirEntriesB
  store.dirEntriesB = tmpDir

  store.saveLastPaths()
}

// 比较：将勾选的项目放入 store，跳转到预览页
async function doCompare() {
  if (store.checkedPaths.size === 0) {
    msg.warning('请先勾选需要对比的文件')
    return
  }
  // 将勾选项传入 store
  store.pendingPreviewItems.value = unifiedRows.value
    .filter(r => store.checkedPaths.has(r._path))
    .map(r => ({
      _path: r._path,
      a_time: r.a_time,
      b_time: r.b_time,
      a_status: r.a_status,
      b_status: r.b_status,
    }))
  // 跳转到预览页
  navigate('preview')
}

function navigate(page: string) {
  // 通过自定义事件通知 AppContent 切换页面
  window.dispatchEvent(new CustomEvent('navigate', { detail: page }))
}

// 跳转备份页面，预填充 A 侧路径
function goBackup() {
  const path = sideA.value.path || sideB.value.path || ''
  navigate('backup')
  if (path) {
    // 延迟发送预填充事件，确保备份页面已挂载
    setTimeout(() => {
      window.dispatchEvent(new CustomEvent('backup-prefill', { detail: { path } }))
    }, 100)
  }
}

// 整行点击切换勾选（含复选框列、Shift 范围选择）
let lastClickedIndex = -1

function handleRowClick(row: UnifiedRow, event: MouseEvent) {
  // 检查点击位置：如果是复选框列（Naive UI selection 列），跳过——让 Naive UI 自己处理
  const td = (event.target as HTMLElement).closest('td')
  if (td && td.classList.contains('n-data-table-td--selection')) return

  if (event.shiftKey) {
    // Shift+点击：选中从上次点击到当前行之间的所有行
    const rows = unifiedRows.value
    const currentIdx = rows.findIndex(r => r._path === row._path)
    if (lastClickedIndex >= 0 && currentIdx >= 0) {
      const start = Math.min(lastClickedIndex, currentIdx)
      const end = Math.max(lastClickedIndex, currentIdx)
      for (let i = start; i <= end; i++) {
        store.checkedPaths.add(rows[i]._path)
      }
    } else {
      if (store.checkedPaths.has(row._path)) {
        store.checkedPaths.delete(row._path)
      } else {
        store.checkedPaths.add(row._path)
      }
    }
    lastClickedIndex = currentIdx
  } else {
    // 普通点击：切换当前行
    if (store.checkedPaths.has(row._path)) {
      store.checkedPaths.delete(row._path)
    } else {
      store.checkedPaths.add(row._path)
    }
    lastClickedIndex = unifiedRows.value.findIndex(r => r._path === row._path)
  }
}

// 全选/取消全选
function toggleSelectAll() {
  if (checkedCount.value === unifiedRows.value.length) {
    store.checkedPaths.clear()
  } else {
    for (const row of unifiedRows.value) {
      store.checkedPaths.add(row._path)
    }
  }
}

const checkboxColTitle = computed(() =>
  h('span', { style: { cursor: 'pointer' } },
    checkedCount.value === unifiedRows.value.length && unifiedRows.value.length > 0 ? '☑' : '☐'))

// 渲染文件名：单侧独有的文件染对应颜色
function renderFileName(row: UnifiedRow) {
  const path = row._path
  const fileName = row._file
  const dirPath = path.substring(0, path.lastIndexOf('/') + 1)

  // 仅A 或 仅B 的情况，文件名染对应颜色
  let fileColor: string | undefined
  if (row.a_status === '仅A') {
    fileColor = '#ff9800'
  } else if (row.b_status === '仅B') {
    fileColor = '#2196f3'
  } else if (row._hasDiff) {
    // 两侧都有但状态不同（Old/New），文件名也标一个提示色
    fileColor = '#aaa'
  }

  if (fileColor && dirPath) {
    return h('span', {}, [
      h('span', { style: { color: '#888' } }, dirPath),
      h('span', { style: { color: fileColor, fontWeight: 600 } }, fileName),
    ])
  }
  return path
}

// 统一表格列定义
const DIFF_TIME_COLOR = '#ffb347'

const unifiedColumns = computed(() => [
  {
    type: 'selection' as const,
    width: 40,
  },
  {
    title: '文件',
    key: '_path',
    resizable: true,
    ellipsis: { tooltip: true },
    render: renderFileName,
  },
  {
    title: t('col_a_time'),
    key: 'a_time',
    width: 90,
    resizable: true,
    render: (row: UnifiedRow) =>
      h('span', { style: { color: row._hasDiff ? DIFF_TIME_COLOR : undefined } }, row.a_time),
  },
  {
    title: t('col_a_status'),
    key: 'a_status',
    width: 50,
    resizable: true,
    render: (row: UnifiedRow) =>
      h('span', { style: { color: statusColor(row.a_status), fontWeight: row.a_status === 'New' || row.a_status === 'Old' ? 600 : 400 } }, statusText(row.a_status)),
  },
  {
    title: t('col_b_time'),
    key: 'b_time',
    width: 90,
    resizable: true,
    render: (row: UnifiedRow) =>
      h('span', { style: { color: row._hasDiff ? DIFF_TIME_COLOR : undefined } }, row.b_time),
  },
  {
    title: t('col_b_status'),
    key: 'b_status',
    width: 50,
    resizable: true,
    render: (row: UnifiedRow) =>
      h('span', { style: { color: statusColor(row.b_status), fontWeight: row.b_status === 'New' || row.b_status === 'Old' ? 600 : 400 } }, statusText(row.b_status)),
  },
])
</script>

<template>
  <div class="directory-panels">
    <!-- A/B 路径栏 -->
    <div class="panels-row">
      <!-- A 区路径栏 -->
      <div
        ref="panelARef"
        class="panel"
        :class="{ dragging: sideA.isDragging }"
      >
        <div class="drag-overlay"></div>
        <div class="panel-header">
          <div class="panel-path-row">
            <span class="panel-label">A 区</span>
            <div class="path-input-wrap">
              <n-dropdown
                trigger="click"
                :options="getFavoriteOptions(sideA.path).map(p => ({ label: p, key: p }))"
                @select="(key: string) => onPathSelect('A', key)"
                :disabled="store.favoritePaths.length === 0"
              >
                <n-input
                  v-model:value="sideA.path"
                  :placeholder="t('select_path')"
                  size="small"
                  class="path-input"
                />
              </n-dropdown>
            </div>
            <n-button size="small" :title="store.isFavorite(sideA.path) ? '取消收藏' : '加入收藏'" @click="store.toggleFavorite(sideA.path)">
              <span :style="{ color: store.isFavorite(sideA.path) ? '#f5c518' : undefined }">{{ store.isFavorite(sideA.path) ? '★' : '☆' }}</span>
            </n-button>
            <n-button size="small" @click="browsePath('A')">{{ t('browse') }}</n-button>
          </div>
        </div>
      </div>

      <!-- AB 交换按钮 -->
      <div class="swap-divider">
        <n-button circle size="small" type="primary" @click="swapAB" title="交换 A/B 路径">
          <span style="font-size: 14px; line-height: 1">⇄</span>
        </n-button>
      </div>

      <!-- B 区路径栏 -->
      <div
        ref="panelBRef"
        class="panel"
        :class="{ dragging: sideB.isDragging }"
      >
        <div class="drag-overlay"></div>
        <div class="panel-header">
          <div class="panel-path-row">
            <span class="panel-label">B 区</span>
            <div class="path-input-wrap">
              <n-dropdown
                trigger="click"
                :options="getFavoriteOptions(sideB.path).map(p => ({ label: p, key: p }))"
                @select="(key: string) => onPathSelect('B', key)"
                :disabled="store.favoritePaths.length === 0"
              >
                <n-input
                  v-model:value="sideB.path"
                  :placeholder="t('select_path')"
                  size="small"
                  class="path-input"
                />
              </n-dropdown>
            </div>
            <n-button size="small" :title="store.isFavorite(sideB.path) ? '取消收藏' : '加入收藏'" @click="store.toggleFavorite(sideB.path)">
              <span :style="{ color: store.isFavorite(sideB.path) ? '#f5c518' : undefined }">{{ store.isFavorite(sideB.path) ? '★' : '☆' }}</span>
            </n-button>
            <n-button size="small" @click="browsePath('B')">{{ t('browse') }}</n-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 统一对比表格 -->
    <div class="table-area">
      <n-data-table
        v-if="unifiedRows.length > 0"
        :columns="unifiedColumns"
        :data="unifiedRows"
        :checked-row-keys="Array.from(store.checkedPaths)"
        @update:checked-row-keys="(keys: string[]) => { store.checkedPaths = new Set(keys) }"
        size="small"
        striped
        class="config-table"
        :row-key="(row: UnifiedRow) => row._path"
        :row-props="(row: UnifiedRow) => ({
          style: { cursor: 'pointer' },
          onClick: (e: MouseEvent) => {
            e.stopPropagation()
            handleRowClick(row, e)
          },
        })"
      />
      <div v-else class="empty-hint">
        <div class="empty-content">
          <div class="empty-text">{{ t('drag_hint') }}</div>
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
          <div class="empty-subtext">{{ t('drag_hint_sub') }}</div>
        </div>
      </div>
    </div>

    <!-- 底部操作栏 -->
    <div class="action-bar">
      <n-button type="primary" size="large" @click="scanAll">全部扫描</n-button>
      <n-button type="info" size="large" :disabled="checkedCount === 0" @click="doCompare">
        {{ t('add_to_transfer_queue') }} ({{ checkedCount }})
      </n-button>
      <n-button size="large" :disabled="!sideA.path && !sideB.path" @click="goBackup">{{ t('backup') }}</n-button>
      <n-button size="large" @click="clearAll">{{ t('clear') }}</n-button>
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
  gap: 0;
  flex-shrink: 0;
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

.panel {
  flex: 1;
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

.path-input-wrap {
  flex: 1;
}

.path-input-wrap :deep(.n-input) {
  cursor: pointer;
}

/* 表格区域 */
.table-area {
  flex: 1;
  min-height: 0;
  overflow: hidden;
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

/* 表格样式 */
.config-table {
  width: 100%;
  height: 100%;
}
.config-table :deep(.n-data-table-wrapper) {
  height: 100%;
  overflow-y: auto !important;
}

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
