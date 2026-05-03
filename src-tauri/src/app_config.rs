// app_config.rs - 应用配置管理

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize)]
pub struct AppConfig {
    pub language: String,
    pub backup_dir: Option<String>,
    pub auto_detect_on_startup: bool,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            language: "zh".to_string(),
            backup_dir: None,
            auto_detect_on_startup: true,
        }
    }
}

fn get_config_dir() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("blender-config-sync")
}

fn get_config_file() -> PathBuf {
    get_config_dir().join("config.json")
}

pub fn ensure_dirs() -> std::io::Result<()> {
    fs::create_dir_all(get_config_dir())?;
    fs::create_dir_all(get_backup_dir())?;
    Ok(())
}

fn get_backup_dir() -> PathBuf {
    get_config_dir().join("backups")
}

pub fn load_app_config() -> std::io::Result<AppConfig> {
    let path = get_config_file();
    if !path.exists() {
        return Ok(AppConfig::default());
    }
    let content = fs::read_to_string(path)?;
    let config: AppConfig = serde_json::from_str(&content).unwrap_or_default();
    Ok(config)
}

pub fn save_app_config(config: &AppConfig) -> std::io::Result<()> {
    let path = get_config_file();
    ensure_dirs()?;
    let content = serde_json::to_string_pretty(config)?;
    fs::write(path, content)?;
    Ok(())
}

pub fn save_window_state(is_dark: bool) -> std::io::Result<()> {
    let path = get_config_dir().join("window_state.json");
    let state = serde_json::json!({ "is_dark": is_dark });
    fs::write(path, serde_json::to_string(&state)?)?;
    Ok(())
}

pub fn load_window_state() -> std::io::Result<Option<serde_json::Value>> {
    let path = get_config_dir().join("window_state.json");
    if !path.exists() {
        return Ok(None);
    }
    let content = fs::read_to_string(path)?;
    Ok(Some(serde_json::from_str(&content)?))
}