#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{
    menu::{MenuItem, MenuBuilder},
    tray::{TrayIconEvent},
    Manager,
};

mod config;

use config::{AppConfig, CardItem};

const APP_NAME: &str = "MMY Tauri App";

#[tauri::command]
fn init_app() -> Result<(), String> {
    config::ensure_dirs().map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
fn get_app_config() -> Result<AppConfig, String> {
    config::load_app_config().map_err(|e| e.to_string())
}

#[tauri::command]
fn save_app_config(cfg: AppConfig) -> Result<(), String> {
    config::save_app_config(&cfg).map_err(|e| e.to_string())
}

#[tauri::command]
fn get_items() -> Result<Vec<CardItem>, String> {
    config::load_items().map_err(|e| e.to_string())
}

#[derive(serde::Deserialize)]
pub struct ItemInput {
    pub id: Option<String>,
    pub name: String,
    pub icon: Option<String>,
}

#[tauri::command]
fn upsert_item(input: ItemInput) -> Result<CardItem, String> {
    config::upsert_item(input).map_err(|e| e.to_string())
}

#[tauri::command]
fn delete_item(id: String) -> Result<(), String> {
    config::delete_item(&id).map_err(|e| e.to_string())
}

#[tauri::command]
fn save_window_state(isDark: bool) -> Result<(), String> {
    config::save_window_state(isDark).map_err(|e| e.to_string())
}

#[tauri::command]
fn get_window_state() -> Result<Option<serde_json::Value>, String> {
    config::load_window_state().map_err(|e| e.to_string())
}

#[tauri::command]
fn hide_to_tray(app: tauri::AppHandle) -> Result<(), String> {
    if let Some(win) = app.get_webview_window("main") {
        win.hide().map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn setup_tray(app: &tauri::App) -> Result<(), Box<dyn std::error::Error>> {
    let show_item = MenuItem::new(app, "显示窗口", true, None::<&str>)?;
    let quit_item = MenuItem::new(app, "退出", true, None::<&str>)?;

    let menu = MenuBuilder::new(app)
        .item(&show_item)
        .item(&quit_item)
        .build()?;

    let _tray = app.tray_by_id("main")
        .expect("tray not found")
        .set_menu(Some(menu))?;

    Ok(())
}

fn run() {
    tauri::Builder::default()
        .setup(|app| {
            setup_tray(app)?;
            Ok(())
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
            get_items,
            upsert_item,
            delete_item,
            save_window_state,
            get_window_state,
            hide_to_tray,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn main() {
    run()
}