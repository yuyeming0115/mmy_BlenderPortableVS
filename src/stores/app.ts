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
  // 主页面勾选的文件路径集合（跨页面持久化）
  const checkedPaths = ref<Set<string>>(new Set())
  // 是否已完成过自动勾选初始化（跨页面持久化，避免切换页面后重新自动勾选）
  const autoCheckDone = ref(false)
  // 收藏夹路径列表
  const favoritePaths = ref<string[]>([])
  // 预览清单的选中项（来自对比页）
  interface PendingItem {
    _path: string
    a_time: string
    b_time: string
    a_status: string
    b_status: string
  }
  const pendingPreviewItems = ref<PendingItem[]>([])

  // ===== 文件夹差异对比 =====
  interface FolderDiffEntry {
    rel_path: string
    diff_type: string
    a_time: string | null
    b_time: string | null
    a_size: number
    b_size: number
    is_dir: boolean
    checked?: boolean
  }

  interface FolderDiffResult {
    source_path: string
    target_path: string
    scan_time: string
    entries: FolderDiffEntry[]
    summary: {
      total_a: number
      total_b: number
      only_in_source: number
      only_in_target: number
      modified: number
      same: number
    }
  }

  const folderDiffResult = ref<FolderDiffResult | null>(null)
  const folderPathA = ref('')
  const folderPathB = ref('')

  // 传输结果
  const transferResult = ref<SyncResult | null>(null)

  // ===== 初始化 =====
  async function init() {
    await invoke('init_app')
    await loadConfig()
    await detectVersions()
    // 恢复上次的路径（仅显示路径，不验证版本号——版本号在扫描后才显示）
    try {
      const last = await invoke<{ last_path_a?: string; last_path_b?: string }>('get_last_paths')
      if (last.last_path_a) pathA.value = last.last_path_a
      if (last.last_path_b) pathB.value = last.last_path_b
    } catch { }
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
    const validation = await invoke<PathValidation>('validate_custom_path', { path })
    versionA.value = validation.version || ''
    scanResultA.value = await invoke<ScanResult>('scan_all_configs', { configPath: path })
    dirEntriesA.value = await invoke<DirectoryEntry[]>('scan_directory_tree', { dirPath: path })
    await saveLastPaths()
  }

  async function scanPathB(path: string) {
    pathB.value = path
    const validation = await invoke<PathValidation>('validate_custom_path', { path })
    versionB.value = validation.version || ''
    scanResultB.value = await invoke<ScanResult>('scan_all_configs', { configPath: path })
    dirEntriesB.value = await invoke<DirectoryEntry[]>('scan_directory_tree', { dirPath: path })
    await saveLastPaths()
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

  /** 持久化路径到本地配置 */
  async function saveLastPaths() {
    await invoke('save_last_paths', {
      lastPathA: pathA.value || null,
      lastPathB: pathB.value || null,
    })
  }

  // ===== 收藏夹 =====
  function loadFavorites() {
    try {
      const saved = localStorage.getItem('mmy_favorites')
      if (saved) favoritePaths.value = JSON.parse(saved)
    } catch { }
  }

  function saveFavorites() {
    localStorage.setItem('mmy_favorites', JSON.stringify(favoritePaths.value))
  }

  function toggleFavorite(path: string) {
    const idx = favoritePaths.value.indexOf(path)
    if (idx >= 0) {
      favoritePaths.value.splice(idx, 1)
    } else {
      favoritePaths.value.push(path)
    }
    saveFavorites()
  }

  function isFavorite(path: string) {
    return favoritePaths.value.includes(path)
  }

  /** 清空所有路径和扫描结果 */
  function clearAll() {
    pathA.value = ''
    pathB.value = ''
    versionA.value = ''
    versionB.value = ''
    scanResultA.value = null
    scanResultB.value = null
    dirEntriesA.value = []
    dirEntriesB.value = []
    saveLastPaths()
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
    // 清空旧的选择
    selectedSyncItems.value = []
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
  async function createBackup(configPath: string, version: string, includeAddons: boolean, outputDir?: string) {
    return await invoke<BackupResult>('create_backup', {
      configPath,
      version,
      includeAddons,
      outputDir: outputDir || null,
    })
  }

  async function loadBackups() {
    backups.value = await invoke<BackupInfo[]>('list_backups')
  }

  async function diagnoseBackups() {
    return await invoke<any>('diagnose_backups')
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

  // ===== 文件夹差异对比 =====
  async function scanAndDiffFolders(sourcePath: string, targetPath: string) {
    folderPathA.value = sourcePath
    folderPathB.value = targetPath
    folderDiffResult.value = await invoke<FolderDiffResult>('diff_dirs', {
      sourcePath,
      targetPath,
    })
  }

  async function syncFolderDiffItems(items: any[], sourcePath: string, targetPath: string) {
    transferResult.value = await invoke<SyncResult>('sync_dir_items', {
      items,
      sourcePath,
      targetPath,
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
    checkedPaths,
    autoCheckDone,
    favoritePaths,
    pendingPreviewItems,
    transferResult,
    folderDiffResult,
    folderPathA,
    folderPathB,
    init,
    loadConfig,
    saveConfig,
    detectVersions,
    validatePath,
    scanPathA,
    scanPathB,
    setSideVersion,
    saveLastPaths,
    loadFavorites,
    saveFavorites,
    toggleFavorite,
    isFavorite,
    clearAll,
    comparePaths,
    getBookmarks,
    getAddons,
    createBackup,
    loadBackups,
    diagnoseBackups,
    deleteBackupItem,
    restoreBackupItem,
    executeSync,
    saveWindowState,
    loadWindowState,
    scanAndDiffFolders,
    syncFolderDiffItems,
  }
})
