// backup_engine.rs - Blender 配置备份与恢复引擎

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{Read, Write, Seek};
use std::path::PathBuf;
use walkdir::WalkDir;
use zip::{ZipArchive, ZipWriter, write::FileOptions, CompressionMethod};

#[derive(Debug, Serialize, Deserialize)]
pub struct BackupManifest {
    pub version: String,
    pub created_at: String,
    pub source_blender_version: String,
    pub source_config_path: String,
    pub files: Vec<FileInfo>,
    pub total_size: u64,
    pub checksum: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FileInfo {
    pub path: String,
    pub size: u64,
    pub modified: String,
    pub type_: String, // "file" or "dir"
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BackupResult {
    pub success: bool,
    pub backup_path: Option<String>,
    pub manifest: Option<BackupManifest>,
    pub message: String,
    pub warnings: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct RestoreResult {
    pub success: bool,
    pub restored_files: usize,
    pub skipped_files: usize,
    pub errors: Vec<String>,
    pub rollback_available: bool,
    pub backup_path: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BackupInfo {
    pub filename: String,
    pub path: String,
    pub size_mb: f64,
    pub created_at: String,
    pub blender_version: String,
    pub source_config_path: String,
    pub files_count: usize,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SyncResult {
    pub success_count: usize,
    pub failed_count: usize,
    pub skipped_count: usize,
    pub errors: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SyncItemInput {
    pub category: String,
    pub item_type: String,
    pub name: String,
    pub action: String,
}

const MANIFEST_FILENAME: &str = "manifest.json";
const MANIFEST_VERSION: &str = "1.0";

/// 获取备份目录
fn get_backup_dir() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("blender-config-sync")
        .join("backups")
}

/// 创建配置备份
pub fn create_backup(config_path: &str, version: &str, include_addons: bool, output_dir: Option<&str>) -> std::io::Result<BackupResult> {
    let config_path_buf = PathBuf::from(config_path);
    if !config_path_buf.exists() {
        return Ok(BackupResult {
            success: false,
            backup_path: None,
            manifest: None,
            message: format!("配置路径不存在: {}", config_path),
            warnings: Vec::new(),
        });
    }

    // 优先使用用户指定的输出目录，否则使用默认目录
    let backup_dir = match output_dir {
        Some(dir) => PathBuf::from(dir),
        None => get_backup_dir(),
    };
    fs::create_dir_all(&backup_dir)?;

    // 解析版本号，只保留主版本和次版本
    let version_short = version.split('.')
        .take(2)
        .collect::<Vec<_>>()
        .join(".");

    let timestamp: DateTime<Utc> = Utc::now();
    let timestamp_str = timestamp.format("%Y%m%d").to_string();
    let backup_filename = format!("Blender_{}_Portable_{}.zip", version_short, timestamp_str);
    let backup_path = backup_dir.join(&backup_filename);

    let mut warnings = Vec::new();
    let mut manifest = BackupManifest {
        version: MANIFEST_VERSION.to_string(),
        created_at: timestamp.to_rfc3339(),
        source_blender_version: version.to_string(),
        source_config_path: config_path.to_string(),
        files: Vec::new(),
        total_size: 0,
        checksum: String::new(),
    };

    // 创建 ZIP 文件
    let file = fs::File::create(&backup_path)?;
    let mut zip_writer = ZipWriter::new(file);
    let options = FileOptions::<()>::default()
        .compression_method(CompressionMethod::Deflated);

    let config_dir = config_path_buf.join("config");
    let scripts_dir = config_path_buf.join("scripts");

    // 备份 config 目录下的关键文件
    let config_files = ["userpref.blend", "startup.blend", "bookmarks.txt", "recent-files.txt"];
    for filename in config_files.iter() {
        let file_path = config_dir.join(filename);
        if file_path.exists() {
            let info = add_file_to_zip(&mut zip_writer, &file_path, format!("config/{}", filename), options)?;
            manifest.files.push(info);
        } else {
            warnings.push(format!("文件不存在: {}", filename));
        }
    }

    // 备份 scripts 目录（如果需要）
    if include_addons && scripts_dir.exists() {
        let script_dirs = [
            ("addons", "addons"),
            ("addons_contrib", "addons_contrib"),
            ("startup", "startup"),
            ("presets/keyconfig", "presets/keyconfig"),
        ];

        for (src_name, arc_name) in script_dirs.iter() {
            let source_dir = scripts_dir.join(src_name);
            if source_dir.exists() {
                let added_files = add_directory_to_zip(&mut zip_writer, &source_dir, format!("scripts/{}", arc_name), options)?;
                manifest.files.extend(added_files);
            }
        }
    }

    // 计算总大小
    manifest.total_size = manifest.files.iter().map(|f| f.size).sum();

    // 写入 manifest
    let manifest_json = serde_json::to_string_pretty(&manifest)?;
    zip_writer.start_file(MANIFEST_FILENAME, options)?;
    zip_writer.write_all(manifest_json.as_bytes())?;

    zip_writer.finish()?;

    // 计算备份文件的哈希值
    manifest.checksum = calculate_file_hash(&backup_path)?;

    // 在移动 manifest 之前获取需要的信息
    let files_count = manifest.files.len();
    let total_size_kb = manifest.total_size / 1024;

    Ok(BackupResult {
        success: true,
        backup_path: Some(backup_path.to_string_lossy().to_string()),
        manifest: Some(manifest),
        message: format!("备份成功！共 {} 个文件，总计 {} KB", files_count, total_size_kb),
        warnings,
    })
}

/// 添加单个文件到 ZIP
fn add_file_to_zip<W: Write + Seek>(
    zip_writer: &mut ZipWriter<W>,
    file_path: &PathBuf,
    arc_name: String,
    options: FileOptions<()>,
) -> std::io::Result<FileInfo> {
    let metadata = fs::metadata(file_path)?;
    let modified: DateTime<Utc> = metadata.modified()?.into();

    zip_writer.start_file(&arc_name, options)?;
    let mut file = fs::File::open(file_path)?;
    let mut buffer = Vec::new();
    file.read_to_end(&mut buffer)?;
    zip_writer.write_all(&buffer)?;

    Ok(FileInfo {
        path: arc_name,
        size: metadata.len(),
        modified: modified.to_rfc3339(),
        type_: "file".to_string(),
    })
}

/// 添加目录及其内容到 ZIP
fn add_directory_to_zip<W: Write + Seek>(
    zip_writer: &mut ZipWriter<W>,
    dir_path: &PathBuf,
    base_arc_name: String,
    options: FileOptions<()>,
) -> std::io::Result<Vec<FileInfo>> {
    let mut added_files = Vec::new();

    for entry in WalkDir::new(dir_path).into_iter().filter_map(|e| e.ok()) {
        if entry.file_type().is_file() {
            let rel_path = entry.path().strip_prefix(dir_path)
                .map_err(|e| std::io::Error::other(e.to_string()))?;
            let arc_name = format!("{}/{}", base_arc_name, rel_path.to_string_lossy());
            let info = add_file_to_zip(zip_writer, &entry.path().to_path_buf(), arc_name, options)?;
            added_files.push(info);
        }
    }

    Ok(added_files)
}

/// 计算文件哈希值
fn calculate_file_hash(path: &PathBuf) -> std::io::Result<String> {
    use sha2::{Sha256, Digest};
    let mut file = fs::File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = [0u8; 8192];

    while file.read(&mut buffer[..])? > 0 {
        hasher.update(&buffer);
    }

    Ok(hex::encode(hasher.finalize()))
}

/// 诊断信息：返回当前扫描的目录和找到的 ZIP 文件
pub fn diagnose_backups(backup_dir_override: Option<&str>) -> std::io::Result<serde_json::Value> {
    let backup_dir = match backup_dir_override {
        Some(dir) => PathBuf::from(dir),
        None => get_backup_dir(),
    };
    let mut result = serde_json::Map::new();
    result.insert("scanned_dir".to_string(), serde_json::Value::String(backup_dir.to_string_lossy().to_string()));
    result.insert("dir_exists".to_string(), serde_json::Value::Bool(backup_dir.exists()));

    let mut zip_files = Vec::new();
    if backup_dir.exists() {
        for entry in fs::read_dir(&backup_dir)? {
            let entry = entry?;
            let path = entry.path();
            let ext = path.extension().map(|e| e.to_string_lossy().to_string()).unwrap_or_default();
            if ext == "zip" {
                let metadata = fs::metadata(&path)?;
                let mut file_info = serde_json::Map::new();
                file_info.insert("name".to_string(), serde_json::Value::String(path.file_name().unwrap_or_default().to_string_lossy().to_string()));
                file_info.insert("size_bytes".to_string(), serde_json::Value::Number(serde_json::Number::from(metadata.len())));
                zip_files.push(serde_json::Value::Object(file_info));
            }
        }
    }
    result.insert("zip_files".to_string(), serde_json::Value::Array(zip_files.clone()));
    result.insert("zip_count".to_string(), serde_json::Value::Number(serde_json::Number::from(zip_files.len())));

    // 测试读取第一个 ZIP 的 manifest
    if let Some(first) = zip_files.first() {
        let name = first.get("name").and_then(|v| v.as_str()).unwrap_or("");
        if !name.is_empty() {
            let zip_path = backup_dir.join(name);
            let manifest_ok = read_manifest(&zip_path).is_ok();
            result.insert("first_manifest_ok".to_string(), serde_json::Value::Bool(manifest_ok));
        }
    }

    Ok(serde_json::Value::Object(result))
}

/// 列出所有备份
pub fn list_backups(backup_dir_override: Option<&str>) -> std::io::Result<Vec<BackupInfo>> {
    let backup_dir = match backup_dir_override {
        Some(dir) => PathBuf::from(dir),
        None => get_backup_dir(),
    };
    if !backup_dir.exists() {
        return Ok(Vec::new());
    }

    let mut backups = Vec::new();

    for entry in fs::read_dir(&backup_dir)? {
        let entry = entry?;
        let path = entry.path();

        if path.extension().map(|e| e == "zip").unwrap_or(false) {
            let metadata = fs::metadata(&path)?;
            let size_mb = metadata.len() as f64 / (1024.0 * 1024.0);

            let manifest = read_manifest(&path).ok();
            let filename = path.file_name().unwrap().to_string_lossy().to_string();

            backups.push(BackupInfo {
                filename,
                path: path.to_string_lossy().to_string(),
                size_mb: (size_mb * 100.0).round() / 100.0,
                created_at: manifest.as_ref().map(|m| m.created_at.clone()).unwrap_or_else(|| "未知".to_string()),
                blender_version: manifest.as_ref().map(|m| m.source_blender_version.clone()).unwrap_or_else(|| "未知".to_string()),
                source_config_path: manifest.as_ref().map(|m| m.source_config_path.clone()).unwrap_or_default(),
                files_count: manifest.as_ref().map(|m| m.files.len()).unwrap_or(0),
            });
        }
    }

    // 按创建时间排序（从新到旧）
    backups.sort_by(|a, b| b.created_at.cmp(&a.created_at));

    Ok(backups)
}

/// 读取备份文件中的 manifest
fn read_manifest(backup_path: &PathBuf) -> std::io::Result<BackupManifest> {
    let file = fs::File::open(backup_path)?;
    let mut archive = ZipArchive::new(file)?;

    let mut manifest_file = archive.by_name(MANIFEST_FILENAME)?;
    let mut content = String::new();
    manifest_file.read_to_string(&mut content)?;

    let manifest: BackupManifest = serde_json::from_str(&content)?;
    Ok(manifest)
}

/// 删除备份
pub fn delete_backup(path: &str) -> std::io::Result<bool> {
    let path_buf = PathBuf::from(path);
    if path_buf.exists() && path_buf.extension().map(|e| e == "zip").unwrap_or(false) {
        fs::remove_file(&path_buf)?;
        Ok(true)
    } else {
        Ok(false)
    }
}

/// 从备份恢复配置
pub fn restore_backup(backup_path: &str, target_path: &str, overwrite: bool) -> std::io::Result<RestoreResult> {
    let backup_path_buf = PathBuf::from(backup_path);
    let target_path_buf = PathBuf::from(target_path);

    if !backup_path_buf.exists() {
        return Ok(RestoreResult {
            success: false,
            restored_files: 0,
            skipped_files: 0,
            errors: vec![format!("备份文件不存在: {}", backup_path)],
            rollback_available: false,
            backup_path: None,
        });
    }

    if !target_path_buf.exists() {
        fs::create_dir_all(&target_path_buf)?;
    }

    let file = fs::File::open(&backup_path_buf)?;
    let mut archive = ZipArchive::new(file)?;

    let mut restored_count = 0usize;
    let mut skipped_count = 0usize;
    let errors: Vec<String> = Vec::new();

    for i in 0..archive.len() {
        let mut file = archive.by_index(i)?;
        let filename = file.name().to_string();

        if filename == MANIFEST_FILENAME {
            continue;
        }

        let target_file = target_path_buf.join(&filename);

        if target_file.exists() && !overwrite {
            skipped_count += 1;
            continue;
        }

        // 确保父目录存在
        if let Some(parent) = target_file.parent() {
            fs::create_dir_all(parent)?;
        }

        // 提取文件
        let mut output = fs::File::create(&target_file)?;
        std::io::copy(&mut file, &mut output)?;
        restored_count += 1;
    }

    Ok(RestoreResult {
        success: true,
        restored_files: restored_count,
        skipped_files: skipped_count,
        errors,
        rollback_available: false,
        backup_path: None,
    })
}

/// 同步选中项到目标
pub fn sync_items(items: &[SyncItemInput], source_path: &str, target_path: &str) -> std::io::Result<SyncResult> {
    let source_path_buf = PathBuf::from(source_path);
    let target_path_buf = PathBuf::from(target_path);

    let mut success_count = 0usize;
    let mut failed_count = 0usize;
    let mut skipped_count = 0usize;
    let mut errors = Vec::new();

    for item in items {
        let result = sync_single_item(item, &source_path_buf, &target_path_buf);

        match result {
            Ok(true) => success_count += 1,
            Ok(false) => skipped_count += 1,
            Err(e) => {
                failed_count += 1;
                errors.push(format!("{}: {}", item.name, e));
            }
        }
    }

    Ok(SyncResult {
        success_count,
        failed_count,
        skipped_count,
        errors,
    })
}

/// 同步单个项目
fn sync_single_item(item: &SyncItemInput, source: &PathBuf, target: &PathBuf) -> std::io::Result<bool> {
    match item.category.as_str() {
        "bookmarks" => sync_bookmarks(source, target),
        "addons" => sync_addon(&item.name, source, target),
        "preferences" => sync_preferences(source, target),
        "presets" => sync_preset(&item.name, &item.item_type, source, target),
        "startup_scripts" => sync_startup_script(&item.name, source, target),
        "folder_file" => sync_generic_file_or_dir(&item.name, source, target),
        _ => Ok(false),
    }
}

fn sync_bookmarks(source: &PathBuf, target: &PathBuf) -> std::io::Result<bool> {
    let src_file = source.join("config").join("bookmarks.txt");
    let dst_file = target.join("config").join("bookmarks.txt");

    if src_file.exists() {
        fs::create_dir_all(dst_file.parent().unwrap())?;
        fs::copy(&src_file, &dst_file)?;
        Ok(true)
    } else {
        Ok(false)
    }
}

fn sync_addon(name: &str, source: &PathBuf, target: &PathBuf) -> std::io::Result<bool> {
    let src_addon = source.join("scripts").join("addons").join(name);
    let dst_addon = target.join("scripts").join("addons").join(name);

    if src_addon.exists() {
        fs::create_dir_all(dst_addon.parent().unwrap())?;

        if src_addon.is_dir() {
            if dst_addon.exists() {
                fs::remove_dir_all(&dst_addon)?;
            }
            copy_dir_all(&src_addon, &dst_addon)?;
        } else {
            fs::copy(&src_addon, &dst_addon)?;
        }
        Ok(true)
    } else {
        Ok(false)
    }
}

/// 复制整个目录
fn copy_dir_all(src: &PathBuf, dst: &PathBuf) -> std::io::Result<()> {
    fs::create_dir_all(dst)?;
    for entry in fs::read_dir(src)? {
        let entry = entry?;
        let ty = entry.file_type()?;
        let src_path = entry.path();
        let dst_path = dst.join(entry.file_name());

        if ty.is_dir() {
            copy_dir_all(&src_path, &dst_path)?;
        } else {
            fs::copy(&src_path, &dst_path)?;
        }
    }
    Ok(())
}

fn sync_preferences(source: &PathBuf, target: &PathBuf) -> std::io::Result<bool> {
    let src_file = source.join("config").join("userpref.blend");
    let dst_file = target.join("config").join("userpref.blend");

    if src_file.exists() {
        fs::create_dir_all(dst_file.parent().unwrap())?;
        fs::copy(&src_file, &dst_file)?;
        Ok(true)
    } else {
        Ok(false)
    }
}

fn sync_preset(name: &str, preset_type: &str, source: &PathBuf, target: &PathBuf) -> std::io::Result<bool> {
    let src_preset = source.join("scripts").join("presets").join(preset_type).join(name);
    let dst_preset = target.join("scripts").join("presets").join(preset_type).join(name);

    if src_preset.exists() {
        fs::create_dir_all(dst_preset.parent().unwrap())?;

        if src_preset.is_dir() {
            if dst_preset.exists() {
                fs::remove_dir_all(&dst_preset)?;
            }
            copy_dir_all(&src_preset, &dst_preset)?;
        } else {
            fs::copy(&src_preset, &dst_preset)?;
        }
        Ok(true)
    } else {
        Ok(false)
    }
}

fn sync_startup_script(name: &str, source: &PathBuf, target: &PathBuf) -> std::io::Result<bool> {
    let src_file = source.join("scripts").join("startup").join(name);
    let dst_file = target.join("scripts").join("startup").join(name);

    if src_file.exists() {
        fs::create_dir_all(dst_file.parent().unwrap())?;
        fs::copy(&src_file, &dst_file)?;
        Ok(true)
    } else {
        Ok(false)
    }
}

/// 通用文件/目录同步（用于文件夹差异模块）
fn sync_generic_file_or_dir(rel_path: &str, source: &PathBuf, target: &PathBuf) -> std::io::Result<bool> {
    let src = source.join(rel_path);
    let dst = target.join(rel_path);

    if !src.exists() {
        return Ok(false);
    }

    if src.is_dir() {
        if dst.exists() {
            fs::remove_dir_all(&dst)?;
        }
        copy_dir_all(&src, &dst)?;
    } else {
        if let Some(parent) = dst.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::copy(&src, &dst)?;
    }

    Ok(true)
}