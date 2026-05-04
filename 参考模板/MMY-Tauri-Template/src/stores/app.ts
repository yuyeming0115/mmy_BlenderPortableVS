import { defineStore } from 'pinia'
import { invoke } from '@tauri-apps/api/core'
import { ref } from 'vue'

// TODO: 根据你的业务定义数据类型
export interface CardItem {
  id: string
  name: string
  icon?: string
  created_at: string
  updated_at: string
}

export interface AppConfig {
  language: string
  // TODO: 添加你的配置字段
}

export const useAppStore = defineStore('app', () => {
  const items = ref<CardItem[]>([])
  const config = ref<AppConfig>({ language: 'zh' })

  /// 初始化应用
  async function init() {
    await invoke('init_app')
    await loadConfig()
    await loadItems()
  }

  /// 加载配置
  async function loadConfig() {
    config.value = await invoke<AppConfig>('get_app_config')
  }

  /// 保存配置
  async function saveConfig(cfg: AppConfig) {
    await invoke('save_app_config', { cfg })
    await loadConfig()
  }

  /// 加载数据列表
  async function loadItems() {
    items.value = await invoke<CardItem[]>('get_items')
  }

  /// 添加/更新数据
  async function upsertItem(input: object) {
    await invoke('upsert_item', { input })
    await loadItems()
  }

  /// 删除数据
  async function deleteItem(id: string) {
    await invoke('delete_item', { id })
    await loadItems()
  }

  return {
    items,
    config,
    init,
    loadConfig,
    saveConfig,
    loadItems,
    upsertItem,
    deleteItem,
  }
})