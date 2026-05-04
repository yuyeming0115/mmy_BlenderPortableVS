use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

/// 获取应用数据目录
fn app_data_dir() -> PathBuf {
    // TODO: 根据你的应用名称修改
    let base = dirs::data_local_dir().unwrap_or_else(|| PathBuf::from("."));
    base.join("mmy-tauri-app")
}

/// 确保目录存在
pub fn ensure_dirs() -> std::io::Result<()> {
    let dir = app_data_dir();
    if !dir.exists() {
        fs::create_dir_all(&dir)?;
    }
    Ok(())
}

// === 数据类型定义 ===

#[derive(Serialize, Deserialize, Clone)]
pub struct AppConfig {
    pub language: String,
    // TODO: 添加你的配置字段
}

impl Default for AppConfig {
    fn default() -> Self {
        Self { language: "zh".to_string() }
    }
}

#[derive(Serialize, Deserialize, Clone)]
pub struct CardItem {
    pub id: String,
    pub name: String,
    pub icon: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

// === 配置管理 ===

fn config_path() -> PathBuf {
    app_data_dir().join("config.json")
}

pub fn load_app_config() -> std::io::Result<AppConfig> {
    let path = config_path();
    if !path.exists() {
        return Ok(AppConfig::default());
    }
    let content = fs::read_to_string(&path)?;
    Ok(serde_json::from_str(&content)?)
}

pub fn save_app_config(cfg: &AppConfig) -> std::io::Result<()> {
    let path = config_path();
    let content = serde_json::to_string_pretty(cfg)?;
    fs::write(&path, content)?;
    Ok(())
}

// === 数据管理 ===

fn items_path() -> PathBuf {
    app_data_dir().join("items.json")
}

pub fn load_items() -> std::io::Result<Vec<CardItem>> {
    let path = items_path();
    if !path.exists() {
        return Ok(Vec::new());
    }
    let content = fs::read_to_string(&path)?;
    Ok(serde_json::from_str(&content)?)
}

fn save_items(items: &Vec<CardItem>) -> std::io::Result<()> {
    let path = items_path();
    let content = serde_json::to_string_pretty(items)?;
    fs::write(&path, content)?;
    Ok(())
}

#[derive(Deserialize)]
pub struct ItemInput {
    pub id: Option<String>,
    pub name: String,
    pub icon: Option<String>,
}

pub fn upsert_item(input: ItemInput) -> std::io::Result<CardItem> {
    let mut items = load_items()?;
    let now = chrono::Utc::now().to_rfc3339();

    let id = input.id.unwrap_or_else(|| format!("item_{}", chrono::Utc::now().timestamp_millis()));

    let existing = items.iter().position(|i| i.id == id);

    let item = CardItem {
        id: id.clone(),
        name: input.name,
        icon: input.icon,
        created_at: existing.map(|_| items[existing.unwrap()].created_at.clone()).unwrap_or_else(|| now.clone()),
        updated_at: now,
    };

    if let Some(idx) = existing {
        items[idx] = item.clone();
    } else {
        items.push(item.clone());
    }

    save_items(&items)?;
    Ok(item)
}

pub fn delete_item(id: &str) -> std::io::Result<()> {
    let mut items = load_items()?;
    items.retain(|i| i.id != id);
    save_items(&items)?;
    Ok(())
}

// === 窗口状态 ===

fn window_state_path() -> PathBuf {
    app_data_dir().join("window_state.json")
}

#[derive(Serialize, Deserialize)]
struct WindowState {
    is_dark: bool,
}

pub fn save_window_state(isDark: bool) -> std::io::Result<()> {
    let state = WindowState { is_dark: isDark };
    let path = window_state_path();
    let content = serde_json::to_string(&state)?;
    fs::write(&path, content)?;
    Ok(())
}

pub fn load_window_state() -> std::io::Result<Option<serde_json::Value>> {
    let path = window_state_path();
    if !path.exists() {
        return Ok(None);
    }
    let content = fs::read_to_string(&path)?;
    Ok(Some(serde_json::from_str(&content)?))
}