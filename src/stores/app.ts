import { defineStore } from 'pinia'
import { invoke } from '@tauri-apps/api/core'
import { ref } from 'vue'

// ===== 数据类型定义 =====

export interface BlenderInstallation {
  version: string
  config_path: string
  executable_path: string | null
  is_portable: boolean
}

export interface PathValidation {
  valid: boolean
  version: string | null
  message: string
}

export interface ConfigFileInfo {
  file_type: string
  path: string
  exists: boolean
  size_bytes: number
  modified_time: string | null
  sha256_hash: string | null
  content_preview: string | null
}

export interface ScanSummary {
  total_types_scanned: number
  existing_count: number
  total_size_bytes: number
  scan_status: string
}

export interface ScanResult {
  scan_time: string
  config_base: string
  configs: Record<string, ConfigFileInfo>
  summary: ScanSummary
}

export interface BookmarksData {
  paths: string[]
  count: number
}

export interface AddonInfo {
  name: string
  path: string
  enabled: boolean
  bl_info: any
  compatibility: string
}

export interface RiskCounts {
  high: number
  medium: number
}

export interface RiskAssessment {
  level: string
  message: string
  counts: RiskCounts
}

export interface ComparisonSummary {
  stats: Record<string, number>
  categories: Record<string, number>
  risk_assessment: RiskAssessment
  recommendations: string[]
}

export interface DiffItem {
  category: string
  item_type: string
  name: string
  diff_type: string
  source_value: any
  target_value: any
  recommended_action: string
  user_action: string | null
  details: any
  risk_level: string
  checked?: boolean
}

export interface ComparisonResult {
  source_version: string
  target_version: string
  scan_time: string
  total_items: number
  diff_items: DiffItem[]
  summary: ComparisonSummary
}

export interface BackupManifest {
  version: string
  created_at: string
  source_blender_version: string
  source_config_path: string
  files: any[]
  total_size: number
  checksum: string
}

export interface BackupResult {
  success: boolean
  backup_path: string | null
  manifest: BackupManifest | null
  message: string
  warnings: string[]
}

export interface RestoreResult {
  success: boolean
  restored_files: number
  skipped_files: number
  errors: string[]
  rollback_available: boolean
  backup_path: string | null
}

export interface BackupInfo {
  filename: string
  path: string
  size_mb: number
  created_at: string
  blender_version: string
  source_config_path: string
  files_count: number
}

export interface SyncResult {
  success_count: number
  failed_count: number
  skipped_count: number
  errors: string[]
}

export interface SyncItemInput {
  category: string
  item_type: string
  name: string
  action: string
}

export interface DirectoryEntry {
  name: string
  path: string
  is_dir: boolean
  size_bytes: number
  modified_time: string | null
}

export interface AppConfig {
  language: string
  backup_dir: string | null
  auto_detect_on_startup: boolean
}

// ===== Store =====

export const useAppStore = defineStore('app', () => {
  const config = ref<AppConfig>({
    language: 'zh',
    backup_dir: null,
    auto_detect_on_startup: true,
  })

  // A/B 面板路径与版本
  const pathA = ref('')
  const pathB = ref('')
  const versionA = ref('')
  const versionB = ref('')

  const installedVersions = ref<BlenderInstallation[]>([])
  const scanResultA = ref<ScanResult | null>(null)
  const scanResultB = ref<ScanResult | null>(null)
  const dirEntriesA = ref<DirectoryEntry[]>([])
  const dirEntriesB = ref<DirectoryEntry[]>([])
  const comparisonResult = ref<ComparisonResult | null>(null)
  const backups = ref<BackupInfo[]>([])

  // 选中同步的项
  const selectedSyncItems = ref<DiffItem[]>([])

  // 传输结果
  const transferResult = ref<SyncResult | null>(null)

  // ===== 初始化 =====
  async function init() {
    await invoke('init_app')
    await loadConfig()
    await detectVersions()
  }

  // ===== 配置 =====
  async function loadConfig() {
    config.value = await invoke<AppConfig>('get_app_config')
  }

  async function saveConfig() {
    await invoke('save_app_config', { cfg: config.value })
  }

  // ===== 版本检测 =====
  async function detectVersions() {
    installedVersions.value = await invoke<BlenderInstallation[]>('detect_installed_versions')
  }

  async function validatePath(path: string) {
    return await invoke<PathValidation>('validate_custom_path', { path })
  }

  // ===== 配置扫描 =====
  async function scanPathA(path: string) {
    pathA.value = path
    // 先验证获取版本号
    const validation = await invoke<PathValidation>('validate_custom_path', { path })
    versionA.value = validation.version || ''
    // 再扫描
    scanResultA.value = await invoke<ScanResult>('scan_all_configs', { configPath: path })
    dirEntriesA.value = await invoke<DirectoryEntry[]>('scan_directory_tree', { dirPath: path })
  }

  async function scanPathB(path: string) {
    pathB.value = path
    // 先验证获取版本号
    const validation = await invoke<PathValidation>('validate_custom_path', { path })
    versionB.value = validation.version || ''
    // 再扫描
    scanResultB.value = await invoke<ScanResult>('scan_all_configs', { configPath: path })
    dirEntriesB.value = await invoke<DirectoryEntry[]>('scan_directory_tree', { dirPath: path })
  }

  /** 仅更新路径和版本号（拖放验证后调用） */
  function setSideVersion(side: 'A' | 'B', path: string, version: string) {
    if (side === 'A') {
      pathA.value = path
      versionA.value = version
    } else {
      pathB.value = path
      versionB.value = version
    }
  }

  // ===== 差异比较 =====
  async function comparePaths(
    sourcePath: string,
    targetPath: string,
    sourceVersion: string,
    targetVersion: string,
  ) {
    comparisonResult.value = await invoke<ComparisonResult>('compare_configs', {
      sourcePath,
      targetPath,
      sourceVersion,
      targetVersion,
    })
  }

  // ===== 书签 =====
  async function getBookmarks(configPath: string) {
    return await invoke<BookmarksData>('read_bookmarks', { configPath })
  }

  // ===== 插件 =====
  async function getAddons(configPath: string) {
    return await invoke<AddonInfo[]>('list_addons', { configPath })
  }

  // ===== 备份 =====
  async function createBackup(configPath: string, version: string, includeAddons: boolean) {
    return await invoke<BackupResult>('create_backup', {
      configPath,
      version,
      includeAddons,
    })
  }

  async function loadBackups() {
    backups.value = await invoke<BackupInfo[]>('list_backups')
  }

  async function deleteBackupItem(path: string) {
    return await invoke<boolean>('delete_backup', { path })
  }

  async function restoreBackupItem(backupPath: string, targetPath: string, overwrite: boolean) {
    return await invoke<RestoreResult>('restore_backup', {
      backupPath,
      targetPath,
      overwrite,
    })
  }

  // ===== 传输同步 =====
  async function executeSync(
    items: SyncItemInput[],
    sourcePath: string,
    targetPath: string,
  ) {
    transferResult.value = await invoke<SyncResult>('sync_items', {
      items,
      sourcePath,
      targetPath,
    })
  }

  // ===== 窗口状态 =====
  async function saveWindowState(isDark: boolean) {
    await invoke('save_window_state', { isDark })
  }

  async function loadWindowState() {
    return await invoke<any>('get_window_state')
  }

  return {
    config,
    pathA,
    pathB,
    versionA,
    versionB,
    installedVersions,
    scanResultA,
    scanResultB,
    dirEntriesA,
    dirEntriesB,
    comparisonResult,
    backups,
    selectedSyncItems,
    transferResult,
    init,
    loadConfig,
    saveConfig,
    detectVersions,
    validatePath,
    scanPathA,
    scanPathB,
    setSideVersion,
    comparePaths,
    getBookmarks,
    getAddons,
    createBackup,
    loadBackups,
    deleteBackupItem,
    restoreBackupItem,
    executeSync,
    saveWindowState,
    loadWindowState,
  }
})
