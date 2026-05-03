<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore, type DiffItem } from '../stores/app'

const { t } = useI18n()
const store = useAppStore()

const loading = ref(false)

function getCategoryLabel(cat: string) {
  const map: Record<string, string> = {
    bookmarks: t('cat_bookmarks'),
    addons: t('cat_addons'),
    keymaps: t('cat_keymaps'),
    preferences: t('cat_preferences'),
    startup_scripts: t('cat_startup_scripts'),
    presets: t('cat_presets'),
  }
  return map[cat] || cat
}

function getDiffLabel(type: string) {
  const map: Record<string, string> = {
    OnlyInSource: t('diff_only_source'),
    OnlyInTarget: t('diff_only_target'),
    Modified: t('diff_modified'),
    Identical: t('diff_identical'),
  }
  return map[type] || type
}

function getRiskLabel(level: string) {
  const map: Record<string, string> = {
    high: t('risk_high'),
    medium: t('risk_medium'),
    low: t('risk_low'),
  }
  return map[level] || level
}

function getActionLabel(action: string) {
  const map: Record<string, string> = {
    SyncToTarget: t('action_sync_to_target'),
    KeepTarget: t('action_keep_target'),
    Merge: t('action_merge'),
    Skip: t('action_skip'),
  }
  return map[action] || action
}

function toggleCheck(item: DiffItem) {
  item.checked = !item.checked
  if (item.checked) {
    if (!store.selectedSyncItems.includes(item)) {
      store.selectedSyncItems.push(item)
    }
  } else {
    const idx = store.selectedSyncItems.indexOf(item)
    if (idx > -1) store.selectedSyncItems.splice(idx, 1)
  }
}
</script>

<template>
  <div class="preview-page">
    <div class="page-header">
      <span class="page-title">{{ t('nav_preview') }}</span>
      <n-button
        type="primary"
        size="small"
        :loading="loading"
        @click="loading = true; store.comparePaths('', '', '', '').finally(() => loading = false)"
      >
        {{ t('compare') }}
      </n-button>
    </div>

    <!-- 风险概览 -->
    <div v-if="store.comparisonResult" class="risk-summary">
      <n-tag :type="store.comparisonResult.summary.risk_assessment.level === 'high' ? 'error' : store.comparisonResult.summary.risk_assessment.level === 'medium' ? 'warning' : 'success'" size="large">
        {{ store.comparisonResult.summary.risk_assessment.message }}
      </n-tag>
      <span class="stats-text">
        共 {{ store.comparisonResult.total_items }} 项 |
        仅源端: {{ store.comparisonResult.summary.stats.only_in_source || 0 }} |
        仅目标端: {{ store.comparisonResult.summary.stats.only_in_target || 0 }} |
        已修改: {{ store.comparisonResult.summary.stats.modified || 0 }} |
        相同: {{ store.comparisonResult.summary.stats.identical || 0 }}
      </span>
    </div>

    <!-- 差异列表 -->
    <div v-if="store.comparisonResult" class="diff-list">
      <n-data-table
        :columns="[
          {
            type: 'selection',
            width: 40,
          },
          { title: '分类', key: 'category', width: 100, render: (row: DiffItem) => getCategoryLabel(row.category) },
          { title: t('file_name'), key: 'name', ellipsis: { tooltip: true } },
          { title: '差异类型', key: 'diff_type', width: 90, render: (row: DiffItem) => getDiffLabel(row.diff_type) },
          { title: '风险', key: 'risk_level', width: 70, render: (row: DiffItem) => getRiskLabel(row.risk_level) },
          { title: '建议操作', key: 'recommended_action', width: 100, render: (row: DiffItem) => getActionLabel(row.recommended_action) },
        ]"
        :data="store.comparisonResult.diff_items"
        size="small"
        striped
        :row-key="(row: DiffItem) => row.category + row.name + row.diff_type"
        :row-props="(row: DiffItem) => ({
          style: { cursor: 'pointer' },
          onClick: () => toggleCheck(row)
        })"
      />
    </div>

    <div v-else class="empty-hint">
      请先在主页面扫描 A/B 目录并点击"比较"按钮
    </div>

    <!-- 底部 -->
    <div class="page-footer">
      <span>已选 {{ store.selectedSyncItems.length }} 项</span>
      <n-button type="info" :disabled="store.selectedSyncItems.length === 0">
        加入传输队列
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

.diff-list {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 8px;
}

.empty-hint {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-size: 14px;
}

.page-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-top: 1px solid #444;
  flex-shrink: 0;
  font-size: 12px;
  color: #888;
}
body:not(.dark) .page-footer {
  border-top-color: #ddd;
}
</style>
