// config_scanner.rs - Blender 配置文件扫描

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sha2::{Sha256, Digest};
use std::fs;
use std::io::Read;
use std::path::PathBuf;
use walkdir::WalkDir;

#[derive(Debug, Serialize, Deserialize)]
pub struct ConfigFileInfo {
    pub file_type: String,
    pub path: String,
    pub exists: bool,
    pub size_bytes: u64,
    pub modified_time: Option<String>,
    pub sha256_hash: Option<String>,
    pub content_preview: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BookmarksData {
    pub paths: Vec<String>,
    pub count: usize,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AddonInfo {
    pub name: String,
    pub path: String,
    pub enabled: bool,
    pub bl_info: Option<serde_json::Value>,
    pub compatibility: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ScanResult {
    pub scan_time: String,
    pub config_base: String,
    pub configs: std::collections::HashMap<String, ConfigFileInfo>,
    pub summary: ScanSummary,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ScanSummary {
    pub total_types_scanned: usize,
    pub existing_count: usize,
    pub total_size_bytes: u64,
    pub scan_status: String,
}

const CONFIG_TYPES: [&str; 8] = [
    "userpref_blend",
    "startup_blend",
    "bookmarks_txt",
    "recent_files_txt",
    "addons_dir",
    "addons_contrib_dir",
    "startup_scripts_dir",
    "keyconfig_presets",
];

/// 扫描所有关键配置文件
pub fn scan_all_configs(config_path: &str) -> std::io::Result<ScanResult> {
    let base = PathBuf::from(config_path);
    let config_dir = base.join("config");
    let scripts_dir = base.join("scripts");

    let scan_time: DateTime<Utc> = Utc::now();
    let mut configs = std::collections::HashMap::new();
    let mut total_size = 0u64;
    let mut existing_count = 0usize;

    for config_type in CONFIG_TYPES.iter() {
        let path = get_config_path(config_type, &config_dir, &scripts_dir);
        let info = scan_config_file(config_type, &path);

        if info.exists {
            existing_count += 1;
            total_size += info.size_bytes;
        }

        configs.insert(config_type.to_string(), info);
    }

    Ok(ScanResult {
        scan_time: scan_time.to_rfc3339(),
        config_base: config_path.to_string(),
        configs,
        summary: ScanSummary {
            total_types_scanned: CONFIG_TYPES.len(),
            existing_count,
            total_size_bytes: total_size,
            scan_status: if existing_count > 0 { "complete".to_string() } else { "empty".to_string() },
        },
    })
}

/// 根据类型获取配置文件路径
fn get_config_path(config_type: &str, config_dir: &PathBuf, scripts_dir: &PathBuf) -> PathBuf {
    match config_type {
        "userpref_blend" => config_dir.join("userpref.blend"),
        "startup_blend" => config_dir.join("startup.blend"),
        "bookmarks_txt" => config_dir.join("bookmarks.txt"),
        "recent_files_txt" => config_dir.join("recent-files.txt"),
        "addons_dir" => scripts_dir.join("addons"),
        "addons_contrib_dir" => scripts_dir.join("addons_contrib"),
        "startup_scripts_dir" => scripts_dir.join("startup"),
        "keyconfig_presets" => scripts_dir.join("presets").join("keyconfig"),
        _ => PathBuf::new(),
    }
}

/// 扫描单个配置文件
fn scan_config_file(file_type: &str, path: &PathBuf) -> ConfigFileInfo {
    let exists = path.exists();

    if !exists {
        return ConfigFileInfo {
            file_type: file_type.to_string(),
            path: String::new(),
            exists: false,
            size_bytes: 0,
            modified_time: None,
            sha256_hash: None,
            content_preview: None,
        };
    }

    let is_dir = path.is_dir();
    let metadata = fs::metadata(path).ok();

    let size_bytes = if is_dir {
        calculate_dir_size(path)
    } else {
        metadata.as_ref().map(|m| m.len()).unwrap_or(0)
    };

    let modified_time = metadata
        .and_then(|m| m.modified().ok())
        .map(|t| {
            let dt: DateTime<Utc> = t.into();
            dt.to_rfc3339()
        });

    let sha256_hash = if !is_dir {
        calculate_file_hash(path).ok()
    } else {
        None
    };

    let content_preview = if is_dir {
        Some("[目录]".to_string())
    } else if path.extension().map(|e| e == "txt" || e == "py" || e == "json").unwrap_or(false) {
        read_file_preview(path).ok()
    } else {
        None
    };

    ConfigFileInfo {
        file_type: file_type.to_string(),
        path: path.to_string_lossy().to_string(),
        exists,
        size_bytes,
        modified_time,
        sha256_hash,
        content_preview,
    }
}

/// 计算文件哈希值
fn calculate_file_hash(path: &PathBuf) -> std::io::Result<String> {
    let mut file = fs::File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = [0u8; 8192];

    while file.read(&mut buffer[..])? > 0 {
        hasher.update(&buffer);
    }

    Ok(hex::encode(hasher.finalize()))
}

/// 计算目录总大小
fn calculate_dir_size(path: &PathBuf) -> u64 {
    WalkDir::new(path)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .filter_map(|e| e.metadata().ok())
        .map(|m| m.len())
        .sum()
}

/// 读取文件预览（前几行）
fn read_file_preview(path: &PathBuf) -> std::io::Result<String> {
    let content = fs::read_to_string(path)?;
    let lines: Vec<&str> = content.lines().take(5).collect();
    let preview = lines.join("\n");
    if content.lines().count() > 5 {
        Ok(format!("{}\n... (共 {} 行)", preview, content.lines().count()))
    } else {
        Ok(preview)
    }
}

/// 读取书签文件
pub fn read_bookmarks(config_path: &str) -> std::io::Result<BookmarksData> {
    let bookmarks_path = PathBuf::from(config_path).join("config").join("bookmarks.txt");

    if !bookmarks_path.exists() {
        return Ok(BookmarksData { paths: Vec::new(), count: 0 });
    }

    let content = fs::read_to_string(&bookmarks_path)?;
    let paths: Vec<String> = content
        .lines()
        .map(|l| l.trim())
        .filter(|l| !l.is_empty() && !l.starts_with('#'))
        .map(|l| l.to_string())
        .collect();

    let count = paths.len();
    Ok(BookmarksData { paths, count })
}

/// 列出所有已安装的插件
pub fn list_addons(config_path: &str) -> std::io::Result<Vec<AddonInfo>> {
    let addons_dir = PathBuf::from(config_path).join("scripts").join("addons");

    if !addons_dir.exists() {
        return Ok(Vec::new());
    }

    let mut addons = Vec::new();

    // 检查单文件插件 (.py)
    for entry in fs::read_dir(&addons_dir)? {
        let entry = entry?;
        let path = entry.path();

        if path.extension().map(|e| e == "py").unwrap_or(false) {
            let name = path.file_stem().unwrap().to_string_lossy().to_string();
            let bl_info = parse_bl_info(&path);

            addons.push(AddonInfo {
                name,
                path: path.to_string_lossy().to_string(),
                enabled: false, // 需要解析 userpref.blend 才能确定
                bl_info,
                compatibility: "unknown".to_string(),
            });
        }

        // 检查目录形式插件
        if path.is_dir() && path.join("__init__.py").exists() {
            let name = path.file_name().unwrap().to_string_lossy().to_string();
            let bl_info = parse_bl_info(&path.join("__init__.py"));

            addons.push(AddonInfo {
                name,
                path: path.to_string_lossy().to_string(),
                enabled: false,
                bl_info,
                compatibility: "unknown".to_string(),
            });
        }
    }

    Ok(addons)
}

/// 解析插件的 bl_info 字典
fn parse_bl_info(file_path: &PathBuf) -> Option<serde_json::Value> {
    let content = fs::read_to_string(file_path).ok()?;
    // 简化的解析：查找 bl_info = {...} 模式
    if let Some(start) = content.find("bl_info") {
        if let Some(eq_pos) = content[start..].find('=') {
            let rest = &content[start + eq_pos + 1..];
            // 找到第一个 { 和对应的 }
            if let Some(open) = rest.find('{') {
                let mut depth = 1;
                let mut close_pos = open + 1;
                for (i, c) in rest[open + 1..].char_indices() {
                    if c == '{' { depth += 1; }
                    if c == '}' { depth -= 1; }
                    if depth == 0 {
                        close_pos = i;
                        break;
                    }
                }
                let dict_str = &rest[open..open + close_pos + 1];
                // 尝试解析为 JSON（Python dict 格式类似）
                // 这里需要一些转换处理...
                return Some(serde_json::Value::String(dict_str.to_string()));
            }
        }
    }
    None
}