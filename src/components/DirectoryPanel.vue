<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import { useAppStore } from '../stores/app'
import { open } from '@tauri-apps/plugin-dialog'

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

async function browsePath(side: 'A' | 'B') {
  try {
    const selected = await open({
      directory: true,
      multiple: false,
      title: side === 'A' ? '选择 A 目录' : '选择 B 目录',
    })
    if (selected && typeof selected === 'string') {
      if (side === 'A') {
        sideA.value.path = selected
      } else {
        sideB.value.path = selected
      }
    } else if (Array.isArray(selected) && selected.length > 0) {
      const path = selected[0]
      if (side === 'A') {
        sideA.value.path = path
      } else {
        sideB.value.path = path
      }
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

function handleDragOver(e: DragEvent, side: 'A' | 'B') {
  e.preventDefault()
  if (side === 'A') sideA.value.isDragging = true
  else sideB.value.isDragging = true
}

function handleDragLeave(e: DragEvent, side: 'A' | 'B') {
  e.preventDefault()
  if (side === 'A') sideA.value.isDragging = false
  else sideB.value.isDragging = false
}

async function handleDrop(e: DragEvent, side: 'A' | 'B') {
  e.preventDefault()
  if (side === 'A') sideA.value.isDragging = false
  else sideB.value.isDragging = false

  const items = e.dataTransfer?.items
  if (items) {
    for (let i = 0; i < items.length; i++) {
      if (items[i].kind === 'file') {
        const entry = items[i].webkitGetAsEntry()
        if (entry && (entry as any).isDirectory && (entry as any).fullPath) {
          if (side === 'A') {
            sideA.value.path = entry.fullPath
          } else {
            sideB.value.path = entry.fullPath
          }
          break
        }
      }
    }
  }
}

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
</script>

<template>
  <div class="directory-panels">
    <!-- A/B 并排 -->
    <div class="panels-row">
      <!-- A 区 -->
      <div
        class="panel"
        :class="{ dragging: sideA.isDragging }"
        @dragover.prevent="handleDragOver($event, 'A')"
        @dragleave="handleDragLeave($event, 'A')"
        @drop="handleDrop($event, 'A')"
      >
        <div class="panel-header">
          <span class="panel-label">A 区</span>
          <div class="panel-path-row">
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
            v-if="store.scanResultA"
            :columns="[
              { type: 'selection', width: 40 },
              { title: t('folder'), key: 'file_type', width: 80 },
              { title: t('file_name'), key: 'file_type', ellipsis: { tooltip: true } },
              { title: t('date_time'), key: 'modified_time', width: 160 },
              { title: t('sync_status'), key: 'exists', width: 80 },
            ]"
            :data="Object.values(store.scanResultA.configs)"
            size="small"
            striped
            :max-height="400"
            :row-key="(row: any) => row.file_type"
          />
          <div v-else class="empty-hint">
            {{ t('drag_hint') }}
          </div>
        </div>
      </div>

      <!-- B 区 -->
      <div
        class="panel"
        :class="{ dragging: sideB.isDragging }"
        @dragover.prevent="handleDragOver($event, 'B')"
        @dragleave="handleDragLeave($event, 'B')"
        @drop="handleDrop($event, 'B')"
      >
        <div class="panel-header">
          <span class="panel-label">B 区</span>
          <div class="panel-path-row">
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
            v-if="store.scanResultB"
            :columns="[
              { type: 'selection', width: 40 },
              { title: t('folder'), key: 'file_type', width: 80 },
              { title: t('file_name'), key: 'file_type', ellipsis: { tooltip: true } },
              { title: t('date_time'), key: 'modified_time', width: 160 },
              { title: t('sync_status'), key: 'exists', width: 80 },
            ]"
            :data="Object.values(store.scanResultB.configs)"
            size="small"
            striped
            :max-height="400"
            :row-key="(row: any) => row.file_type"
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
  margin-bottom: 6px;
  display: block;
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
  overflow-y: auto;
  padding: 8px;
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
</style>
