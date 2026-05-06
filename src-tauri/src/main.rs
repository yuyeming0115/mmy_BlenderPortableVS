#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{
    menu::{MenuItem, MenuBuilder},
    tray::TrayIconEvent,
    Manager,
};

mod path_manager;
mod config_scanner;
mod backup_engine;
mod diff_engine;
mod app_config;
mod dir_diff;

use app_config::{AppConfig, load_app_config, save_app_config as save_config_to_file};

// ===== 应用初始化 =====

#[tauri::command]
fn init_app() -> Result<(), String> {
    app_config::ensure_dirs().map_err(|e| e.to_string())?;
    Ok(())
}

// ===== 配置管理 =====

#[tauri::command]
fn get_app_config() -> Result<AppConfig, String> {
    load_app_config().map_err(|e| e.to_string())
}

#[tauri::command]
fn save_app_config(cfg: AppConfig) -> Result<(), String> {
    save_config_to_file(&cfg).map_err(|e| e.to_string())
}

// ===== 路径记忆 =====

#[tauri::command]
fn save_last_paths(last_path_a: Option<String>, last_path_b: Option<String>) -> Result<(), String> {
    let mut cfg = load_app_config().map_err(|e| e.to_string())?;
    cfg.last_path_a = last_path_a;
    cfg.last_path_b = last_path_b;
    save_config_to_file(&cfg).map_err(|e| e.to_string())
}

#[tauri::command]
fn get_last_paths() -> Result<serde_json::Value, String> {
    let cfg = load_app_config().map_err(|e| e.to_string())?;
    Ok(serde_json::json!({
        "last_path_a": cfg.last_path_a,
        "last_path_b": cfg.last_path_b,
    }))
}

// ===== 版本检测 =====

#[tauri::command]
fn detect_installed_versions() -> Result<Vec<path_manager::BlenderInstallation>, String> {
    path_manager::detect_installed_versions().map_err(|e| e.to_string())
}

#[tauri::command]
fn validate_custom_path(path: String) -> Result<path_manager::PathValidation, String> {
    path_manager::validate_custom_path(&path).map_err(|e| e.to_string())
}

// ===== 配置扫描 =====

#[tauri::command]
fn scan_all_configs(config_path: String) -> Result<config_scanner::ScanResult, String> {
    config_scanner::scan_all_configs(&config_path).map_err(|e| e.to_string())
}

#[tauri::command]
fn read_bookmarks(config_path: String) -> Result<config_scanner::BookmarksData, String> {
    config_scanner::read_bookmarks(&config_path).map_err(|e| e.to_string())
}

#[tauri::command]
fn list_addons(config_path: String) -> Result<Vec<config_scanner::AddonInfo>, String> {
    config_scanner::list_addons(&config_path).map_err(|e| e.to_string())
}

// ===== 目录扫描 =====

#[tauri::command]
fn scan_directory_tree(dir_path: String) -> Result<Vec<config_scanner::DirectoryEntry>, String> {
    config_scanner::scan_directory_tree(&dir_path).map_err(|e| e.to_string())
}

// ===== 备份管理 =====

#[tauri::command]
fn create_backup(
    config_path: String,
    version: String,
    include_addons: bool,
    output_dir: Option<String>,
) -> Result<backup_engine::BackupResult, String> {
    backup_engine::create_backup(&config_path, &version, include_addons, output_dir.as_deref()).map_err(|e| e.to_string())
}

#[tauri::command]
fn list_backups() -> Result<Vec<backup_engine::BackupInfo>, String> {
    let cfg = load_app_config().map_err(|e| e.to_string())?;
    let backup_dir = cfg.backup_dir.as_deref();
    backup_engine::list_backups(backup_dir).map_err(|e| e.to_string())
}

#[tauri::command]
fn diagnose_backups() -> Result<serde_json::Value, String> {
    let cfg = load_app_config().map_err(|e| e.to_string())?;
    let backup_dir = cfg.backup_dir.as_deref();
    backup_engine::diagnose_backups(backup_dir).map_err(|e| e.to_string())
}

#[tauri::command]
fn delete_backup(path: String) -> Result<bool, String> {
    backup_engine::delete_backup(&path).map_err(|e| e.to_string())
}

#[tauri::command]
fn restore_backup(
    backup_path: String,
    target_path: String,
    overwrite: bool,
) -> Result<backup_engine::RestoreResult, String> {
    backup_engine::restore_backup(&backup_path, &target_path, overwrite).map_err(|e| e.to_string())
}

// ===== 差异比较 =====

#[tauri::command]
fn compare_configs(
    source_path: String,
    target_path: String,
    source_version: String,
    target_version: String,
) -> Result<diff_engine::ComparisonResult, String> {
    diff_engine::compare_configs(&source_path, &target_path, &source_version, &target_version)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn sync_items(
    items: Vec<backup_engine::SyncItemInput>,
    source_path: String,
    target_path: String,
) -> Result<backup_engine::SyncResult, String> {
    backup_engine::sync_items(&items, &source_path, &target_path).map_err(|e| e.to_string())
}

// ===== 通用文件夹差异对比 =====

#[tauri::command]
fn scan_dir_tree(dir_path: String) -> Result<Vec<dir_diff::FileEntry>, String> {
    dir_diff::scan_dir_tree(&dir_path).map_err(|e| e.to_string())
}

#[tauri::command]
fn diff_dirs(source_path: String, target_path: String) -> Result<dir_diff::DiffResult, String> {
    dir_diff::diff_dirs(&source_path, &target_path).map_err(|e| e.to_string())
}

#[tauri::command]
fn sync_dir_items(
    items: Vec<dir_diff::DiffEntry>,
    source_path: String,
    target_path: String,
) -> Result<backup_engine::SyncResult, String> {
    // 将 DiffEntry 转换为 SyncItemInput
    let sync_items: Vec<backup_engine::SyncItemInput> = items.iter().map(|item| backup_engine::SyncItemInput {
        category: "folder_file".to_string(),
        item_type: if item.is_dir { "dir".to_string() } else { "file".to_string() },
        name: item.rel_path.clone(),
        action: "SyncToTarget".to_string(),
    }).collect();
    backup_engine::sync_items(&sync_items, &source_path, &target_path).map_err(|e| e.to_string())
}

// ===== 窗口与托盘 =====

#[tauri::command]
fn hide_to_tray(app: tauri::AppHandle) -> Result<(), String> {
    if let Some(win) = app.get_webview_window("main") {
        win.hide().map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
fn exit_app(app: tauri::AppHandle) {
    app.exit(0);
}

#[tauri::command]
fn save_window_state(is_dark: bool, width: Option<u32>, height: Option<u32>, maximized: bool) -> Result<(), String> {
    app_config::save_window_state(is_dark, width, height, maximized).map_err(|e| e.to_string())
}

#[tauri::command]
fn get_window_state() -> Result<Option<serde_json::Value>, String> {
    app_config::load_window_state().map_err(|e| e.to_string())
}

// ===== 托盘设置 =====

fn setup_tray(app: &tauri::App) -> Result<(), Box<dyn std::error::Error>> {
    let show_item = MenuItem::with_id(app, "show", "显示窗口", true, None::<&str>)?;
    let quit_item = MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;

    let menu = MenuBuilder::new(app)
        .item(&show_item)
        .item(&quit_item)
        .build()?;

    app.tray_by_id("main")
        .expect("tray not found")
        .set_menu(Some(menu))?;

    Ok(())
}

// ===== 主函数 =====

fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            setup_tray(app)?;
            Ok(())
        })
        .on_menu_event(|app, event| {
            // 根据菜单项 ID 处理点击事件
            match event.id.as_ref() {
                "show" => {
                    if let Some(win) = app.get_webview_window("main") {
                        win.show().unwrap();
                        win.set_focus().unwrap();
                    }
                }
                "quit" => {
                    app.exit(0);
                }
                _ => {}
            }
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click { button, .. } = event {
                if button == tauri::tray::MouseButton::Left {
                    if let Some(win) = tray.app_handle().get_webview_window("main") {
                        win.show().unwrap();
                        win.set_focus().unwrap();
                    }
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            init_app,
            get_app_config,
            save_app_config,
            get_last_paths,
            save_last_paths,
            detect_installed_versions,
            validate_custom_path,
            scan_all_configs,
            read_bookmarks,
            list_addons,
            scan_directory_tree,
            create_backup,
            list_backups,
            diagnose_backups,
            delete_backup,
            restore_backup,
            compare_configs,
            sync_items,
            scan_dir_tree,
            diff_dirs,
            sync_dir_items,
            hide_to_tray,
            exit_app,
            save_window_state,
            get_window_state,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn main() {
    run()
}