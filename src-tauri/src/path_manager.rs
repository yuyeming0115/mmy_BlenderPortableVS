// path_manager.rs - Blender 路径检测

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use regex::Regex;

#[derive(Debug, Serialize, Deserialize)]
pub struct BlenderInstallation {
    pub version: String,
    pub config_path: String,
    pub executable_path: Option<String>,
    pub is_portable: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PathValidation {
    pub valid: bool,
    pub version: Option<String>,
    pub message: String,
}

/// 获取用户配置基础目录
fn get_user_config_base() -> PathBuf {
    #[cfg(target_os = "windows")]
    {
        // Windows: %APPDATA%\Blender Foundation\Blender\
        dirs::data_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("Blender Foundation")
            .join("Blender")
    }

    #[cfg(target_os = "macos")]
    {
        // macOS: ~/Library/Application Support/Blender/
        dirs::data_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("Blender")
    }

    #[cfg(target_os = "linux")]
    {
        // Linux: ~/.config/blender/ 或 $XDG_CONFIG_HOME/blender/
        dirs::config_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("blender")
    }

    #[cfg(not(any(target_os = "windows", target_os = "macos", target_os = "linux")))]
    {
        PathBuf::from(".")
    }
}

/// 验证版本字符串是否有效
fn is_valid_version(version_str: &str) -> bool {
    let re = Regex::new(r"^(\d+)\.(\d+)(\.\d+)?$").unwrap();
    if let Some(caps) = re.captures(version_str) {
        let major: u32 = caps[1].parse().unwrap_or(0);
        let minor: u32 = caps[2].parse().unwrap_or(0);
        // Blender 2.8+ 才使用新的配置系统
        major >= 2 && (major > 2 || minor >= 80)
    } else {
        false
    }
}

/// 解析版本号为元组（用于排序）
fn parse_version_tuple(version_str: &str) -> (u32, u32, u32) {
    let parts: Vec<u32> = version_str
        .split('.')
        .filter_map(|p| p.parse().ok())
        .collect();
    match parts.len() {
        0 => (0, 0, 0),
        1 => (parts[0], 0, 0),
        2 => (parts[0], parts[1], 0),
        _ => (parts[0], parts[1], parts[2]),
    }
}

/// 检测系统上已安装的所有 Blender 版本
pub fn detect_installed_versions() -> std::io::Result<Vec<BlenderInstallation>> {
    let config_base = get_user_config_base();
    if !config_base.exists() {
        return Ok(Vec::new());
    }

    let mut installations = Vec::new();

    for entry in fs::read_dir(config_base)? {
        let entry = entry?;
        let path = entry.path();

        if !path.is_dir() {
            continue;
        }

        let version_str = path.file_name().unwrap().to_string_lossy().to_string();
        if !is_valid_version(&version_str) {
            continue;
        }

        // 检查是否为便携式安装
        let is_portable = path.parent()
            .map(|p| p.join("portable").exists())
            .unwrap_or(false);

        // 尝试查找可执行文件
        let executable_path = find_executable(&version_str);

        installations.push(BlenderInstallation {
            version: version_str,
            config_path: path.to_string_lossy().to_string(),
            executable_path,
            is_portable,
        });
    }

    // 按版本号排序（从新到旧）
    installations.sort_by(|a, b| {
        let va = parse_version_tuple(&a.version);
        let vb = parse_version_tuple(&b.version);
        vb.cmp(&va)
    });

    Ok(installations)
}

/// 查找指定版本的 Blender 可执行文件
fn find_executable(_version: &str) -> Option<String> {
    #[cfg(target_os = "windows")]
    {
        let program_files = dirs::data_dir().unwrap_or_else(|| PathBuf::from("."));
        let possible_paths = [
            program_files.join("Blender Foundation").join("Blender").join("blender.exe"),
            PathBuf::from("C:\\Program Files").join("Blender Foundation").join("Blender").join("blender.exe"),
        ];
        for path in possible_paths.iter() {
            if path.exists() {
                return Some(path.to_string_lossy().to_string());
            }
        }
    }

    #[cfg(target_os = "macos")]
    {
        let possible_paths = [
            PathBuf::from("/Applications").join("Blender.app").join("Contents").join("MacOS").join("Blender"),
            dirs::home_dir().unwrap_or_else(|| PathBuf::from("."))
                .join("Applications")
                .join("Blender.app")
                .join("Contents")
                .join("MacOS")
                .join("Blender"),
        ];
        for path in possible_paths.iter() {
            if path.exists() {
                return Some(path.to_string_lossy().to_string());
            }
        }
    }

    #[cfg(target_os = "linux")]
    {
        let possible_paths = [
            PathBuf::from("/usr/bin/blender"),
            PathBuf::from("/usr/local/bin/blender"),
        ];
        for path in possible_paths.iter() {
            if path.exists() {
                return Some(path.to_string_lossy().to_string());
            }
        }
    }

    None
}

/// 验证自定义路径是否有效
pub fn validate_custom_path(path: &str) -> std::io::Result<PathValidation> {
    let path_buf = PathBuf::from(path);

    if !path_buf.exists() {
        return Ok(PathValidation {
            valid: false,
            version: None,
            message: "路径不存在".to_string(),
        });
    }

    // 检查是否包含 config 或 scripts 目录
    let has_config = path_buf.join("config").exists();
    let has_scripts = path_buf.join("scripts").exists();

    if !has_config && !has_scripts {
        return Ok(PathValidation {
            valid: false,
            version: None,
            message: "路径不包含 Blender 配置目录结构".to_string(),
        });
    }

    // 尝试从路径提取版本号
    let version = extract_version_from_path(&path_buf);

    Ok(PathValidation {
        valid: true,
        version,
        message: "路径有效".to_string(),
    })
}

/// 从路径中提取版本号
fn extract_version_from_path(path: &PathBuf) -> Option<String> {
    let re = Regex::new(r"(\d+\.\d+(\.\d+)?)").unwrap();

    // 尝试从路径各部分提取版本号
    for component in path.components().rev() {
        let name = component.as_os_str().to_string_lossy();
        if let Some(caps) = re.captures(&name) {
            return Some(caps[1].to_string());
        }
    }

    // 检查父目录的兄弟目录中是否有版本号格式
    if let Some(parent) = path.parent() {
        if let Ok(entries) = fs::read_dir(parent) {
            for entry in entries.flatten() {
                let name = entry.file_name().to_string_lossy().to_string();
                if is_valid_version(&name) {
                    return Some(name);
                }
            }
        }
    }

    None
}