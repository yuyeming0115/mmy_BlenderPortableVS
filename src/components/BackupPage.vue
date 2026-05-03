<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage, useDialog } from 'naive-ui'
import { useAppStore } from '../stores/app'
import { open } from '@tauri-apps/plugin-dialog'

const { t } = useI18n()
const store = useAppStore()
const msg = useMessage()
const dialog = useDialog()

const loading = ref(false)
const createLoading = ref(false)
const restoreLoading = ref(false)

const createForm = ref({
  configPath: '',
  version: '',
  includeAddons: true,
})

const restoreForm = ref({
  backupPath: '',
  targetPath: '',
  overwrite: false,
})

onMounted(() => {
  loadBackupList()
})

async function loadBackupList() {
  loading.value = true
  try {
    await store.loadBackups()
  } catch (e: any) {
    msg.error(`加载备份列表失败: ${e}`)
  } finally {
    loading.value = false
  }
}

async function browseCreatePath() {
  const selected = await open({ directory: true, multiple: false, title: '选择 Blender 配置目录' })
  if (selected) createForm.value.configPath = selected as string
}

async function browseRestoreBackup() {
  const selected = await open({
    multiple: false,
    title: '选择备份文件',
    filters: [{ name: 'ZIP', extensions: ['zip'] }]
  })
  if (selected) restoreForm.value.backupPath = selected as string
}

async function browseRestoreTarget() {
  const selected = await open({ directory: true, multiple: false, title: '选择恢复目标目录' })
  if (selected) restoreForm.value.targetPath = selected as string
}

async function doCreateBackup() {
  if (!createForm.value.configPath || !createForm.value.version) {
    msg.warning('请填写配置路径和 Blender 版本')
    return
  }
  createLoading.value = true
  try {
    const result = await store.createBackup(
      createForm.value.configPath,
      createForm.value.version,
      createForm.value.includeAddons,
    )
    if (result.success) {
      msg.success(result.message)
      await loadBackupList()
    } else {
      msg.error(result.message)
    }
  } catch (e: any) {
    msg.error(`创建备份失败: ${e}`)
  } finally {
    createLoading.value = false
  }
}

async function doRestoreBackup(backup: any) {
  if (!restoreForm.value.targetPath) {
    msg.warning('请选择恢复目标目录')
    return
  }
  restoreForm.value.backupPath = backup.path
  restoreLoading.value = true
  try {
    const result = await store.restoreBackupItem(
      restoreForm.value.backupPath,
      restoreForm.value.targetPath,
      restoreForm.value.overwrite,
    )
    if (result.success) {
      msg.success(`恢复成功！恢复了 ${result.restored_files} 个文件`)
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
</script>

<template>
  <div class="backup-page">
    <div class="page-header">
      <span class="page-title">{{ t('nav_backup') }}</span>
    </div>

    <!-- 创建备份 -->
    <div class="section">
      <h3>{{ t('create_backup') }}</h3>
      <div class="form-row">
        <n-input v-model:value="createForm.configPath" :placeholder="t('select_path')" size="small" style="flex:1" />
        <n-button size="small" @click="browseCreatePath">{{ t('browse') }}</n-button>
      </div>
      <div class="form-row">
        <n-input v-model:value="createForm.version" placeholder="Blender 版本 (如 4.5)" size="small" style="flex:1" />
        <n-checkbox v-model:checked="createForm.includeAddons">{{ t('include_addons') }}</n-checkbox>
      </div>
      <n-button type="primary" :loading="createLoading" @click="doCreateBackup">{{ t('create_backup') }}</n-button>
    </div>

    <!-- 恢复备份 -->
    <div class="section">
      <h3>{{ t('restore') }}</h3>
      <div class="form-row">
        <n-input v-model:value="restoreForm.backupPath" :placeholder="t('backup')" size="small" style="flex:1" />
        <n-button size="small" @click="browseRestoreBackup">{{ t('browse') }}</n-button>
      </div>
      <div class="form-row">
        <n-input v-model:value="restoreForm.targetPath" :placeholder="t('restore')" size="small" style="flex:1" />
        <n-button size="small" @click="browseRestoreTarget">{{ t('browse') }}</n-button>
      </div>
      <div class="form-row">
        <n-checkbox v-model:checked="restoreForm.overwrite">{{ t('overwrite') }}</n-checkbox>
      </div>
    </div>

    <!-- 备份列表 -->
    <div class="section">
      <h3>{{ t('backup_list') }}</h3>
      <n-data-table
        v-if="store.backups.length > 0"
        :columns="[
          { title: t('backup_name'), key: 'filename', ellipsis: { tooltip: true } },
          { title: t('backup_size'), key: 'size_mb', width: 80, render: (row: any) => row.size_mb.toFixed(2) + ' MB' },
          { title: t('backup_version'), key: 'blender_version', width: 100 },
          { title: t('backup_date'), key: 'created_at', width: 160 },
          { title: t('backup_files_count'), key: 'files_count', width: 60 },
          {
            title: '操作',
            key: 'actions',
            width: 120,
            render: (row: any) => row
          },
        ]"
        :data="store.backups"
        size="small"
        :loading="loading"
      >
        <template #body-cell-actions="{ row }">
          <n-space>
            <n-button size="tiny" @click="doRestoreBackup(row)">{{ t('restore') }}</n-button>
            <n-button size="tiny" type="error" @click="doDeleteBackup(row)">{{ t('delete') }}</n-button>
          </n-space>
        </template>
      </n-data-table>
      <div v-else class="empty-hint">{{ t('empty') }}</div>
    </div>
  </div>
</template>

<style scoped>
.backup-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  padding: 12px 16px;
}

.page-header {
  margin-bottom: 16px;
}
.page-title {
  font-size: 16px;
  font-weight: 700;
}

.section {
  margin-bottom: 20px;
  padding: 12px;
  border: 1px solid #444;
  border-radius: 8px;
}
body:not(.dark) .section {
  border-color: #ddd;
}

.section h3 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #888;
}

.form-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.empty-hint {
  text-align: center;
  color: #666;
  padding: 20px;
}
</style>
