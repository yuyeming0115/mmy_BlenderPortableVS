// diff_engine.rs - Blender 配置差异比较引擎

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::fs;
use std::path::PathBuf;
use walkdir::WalkDir;

use crate::config_scanner;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub enum DiffType {
    OnlyInSource,
    OnlyInTarget,
    Modified,
    Identical,
    Conflict,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub enum SyncAction {
    SyncToTarget,
    KeepTarget,
    Merge,
    Skip,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DiffItem {
    pub category: String,
    pub item_type: String,
    pub name: String,
    pub diff_type: DiffType,
    pub source_value: Option<serde_json::Value>,
    pub target_value: Option<serde_json::Value>,
    pub recommended_action: SyncAction,
    pub user_action: Option<SyncAction>,
    pub details: serde_json::Value,
    pub risk_level: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ComparisonResult {
    pub source_version: String,
    pub target_version: String,
    pub scan_time: String,
    pub total_items: usize,
    pub diff_items: Vec<DiffItem>,
    pub summary: ComparisonSummary,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ComparisonSummary {
    pub stats: std::collections::HashMap<String, usize>,
    pub categories: std::collections::HashMap<String, usize>,
    pub risk_assessment: RiskAssessment,
    pub recommendations: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct RiskAssessment {
    pub level: String,
    pub message: String,
    pub counts: RiskCounts,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct RiskCounts {
    pub high: usize,
    pub medium: usize,
}

#[allow(dead_code)]
const CATEGORIES: [(&str, &str, &str); 6] = [
    ("bookmarks", "文件浏览器书签", "收藏夹路径列表"),
    ("addons", "已安装插件", "Python 插件及其启用状态"),
    ("keymaps", "自定义快捷键", "键盘映射和鼠标绑定"),
    ("preferences", "偏好设置", "界面主题、语言、保存选项等"),
    ("startup_scripts", "启动脚本", "自动执行的 Python 脚本"),
    ("presets", "预设配置", "快捷键预设、界面主题等"),
];

/// 执行完整的配置比较
pub fn compare_configs(
    source_path: &str,
    target_path: &str,
    source_version: &str,
    target_version: &str,
) -> std::io::Result<ComparisonResult> {
    let scan_time: DateTime<Utc> = Utc::now();
    let mut diff_items = Vec::new();

    let source_path_buf = PathBuf::from(source_path);
    let target_path_buf = PathBuf::from(target_path);

    // 1. 比较书签
    let bookmark_diffs = compare_bookmarks(&source_path_buf, &target_path_buf)?;
    diff_items.extend(bookmark_diffs);

    // 2. 比较插件
    let addon_diffs = compare_addons(&source_path_buf, &target_path_buf)?;
    diff_items.extend(addon_diffs);

    // 3. 比较启动脚本
    let startup_diffs = compare_startup_scripts(&source_path_buf, &target_path_buf)?;
    diff_items.extend(startup_diffs);

    // 4. 比较预设配置
    let preset_diffs = compare_presets(&source_path_buf, &target_path_buf)?;
    diff_items.extend(preset_diffs);

    // 5. 比较配置文件
    let config_diffs = compare_config_files(&source_path_buf, &target_path_buf)?;
    diff_items.extend(config_diffs);

    // 生成统计
    let total_items = diff_items.len();
    let stats = calculate_stats(&diff_items);
    let categories = count_by_category(&diff_items);
    let risk_assessment = assess_risk(&diff_items);
    let recommendations = generate_recommendations(&stats);

    Ok(ComparisonResult {
        source_version: source_version.to_string(),
        target_version: target_version.to_string(),
        scan_time: scan_time.to_rfc3339(),
        total_items,
        diff_items,
        summary: ComparisonSummary {
            stats,
            categories,
            risk_assessment,
            recommendations,
        },
    })
}

/// 比较书签差异
fn compare_bookmarks(source: &PathBuf, target: &PathBuf) -> std::io::Result<Vec<DiffItem>> {
    let mut diffs = Vec::new();

    let source_bookmarks = config_scanner::read_bookmarks(&source.to_string_lossy())?;
    let target_bookmarks = config_scanner::read_bookmarks(&target.to_string_lossy())?;

    let source_set: HashSet<String> = source_bookmarks.paths.into_iter().collect();
    let target_set: HashSet<String> = target_bookmarks.paths.into_iter().collect();

    // 仅在源端存在的书签
    for path in source_set.difference(&target_set) {
        diffs.push(DiffItem {
            category: "bookmarks".to_string(),
            item_type: "bookmark_path".to_string(),
            name: path.clone(),
            diff_type: DiffType::OnlyInSource,
            source_value: Some(serde_json::Value::String(path.clone())),
            target_value: None,
            recommended_action: SyncAction::SyncToTarget,
            user_action: None,
            details: serde_json::json!({"path_type": "directory"}),
            risk_level: "low".to_string(),
        });
    }

    // 仅在目标端存在的书签
    for path in target_set.difference(&source_set) {
        diffs.push(DiffItem {
            category: "bookmarks".to_string(),
            item_type: "bookmark_path".to_string(),
            name: path.clone(),
            diff_type: DiffType::OnlyInTarget,
            source_value: None,
            target_value: Some(serde_json::Value::String(path.clone())),
            recommended_action: SyncAction::KeepTarget,
            user_action: None,
            details: serde_json::json!({"note": "目标端独有，可选择保留或删除"}),
            risk_level: "low".to_string(),
        });
    }

    // 两端都有的书签
    for path in source_set.intersection(&target_set) {
        diffs.push(DiffItem {
            category: "bookmarks".to_string(),
            item_type: "bookmark_path".to_string(),
            name: path.clone(),
            diff_type: DiffType::Identical,
            source_value: Some(serde_json::Value::String(path.clone())),
            target_value: Some(serde_json::Value::String(path.clone())),
            recommended_action: SyncAction::Skip,
            user_action: None,
            details: serde_json::json!({}),
            risk_level: "low".to_string(),
        });
    }

    Ok(diffs)
}

/// 比较插件差异
fn compare_addons(source: &PathBuf, target: &PathBuf) -> std::io::Result<Vec<DiffItem>> {
    let mut diffs = Vec::new();

    let source_addons = config_scanner::list_addons(&source.to_string_lossy())?;
    let target_addons = config_scanner::list_addons(&target.to_string_lossy())?;

    let source_dict: std::collections::HashMap<String, config_scanner::AddonInfo> =
        source_addons.into_iter().map(|a| (a.name.clone(), a)).collect();
    let target_dict: std::collections::HashMap<String, config_scanner::AddonInfo> =
        target_addons.into_iter().map(|a| (a.name.clone(), a)).collect();

    let source_names: HashSet<String> = source_dict.keys().cloned().collect();
    let target_names: HashSet<String> = target_dict.keys().cloned().collect();

    // 仅在源端安装的插件
    for name in source_names.difference(&target_names) {
        let addon = source_dict.get(name).unwrap();
        diffs.push(DiffItem {
            category: "addons".to_string(),
            item_type: "addon".to_string(),
            name: name.clone(),
            diff_type: DiffType::OnlyInSource,
            source_value: Some(serde_json::json!({"enabled": addon.enabled})),
            target_value: None,
            recommended_action: SyncAction::SyncToTarget,
            user_action: None,
            details: serde_json::json!({"path": addon.path}),
            risk_level: assess_addon_risk(addon),
        });
    }

    // 仅在目标端安装的插件
    for name in target_names.difference(&source_names) {
        let addon = target_dict.get(name).unwrap();
        diffs.push(DiffItem {
            category: "addons".to_string(),
            item_type: "addon".to_string(),
            name: name.clone(),
            diff_type: DiffType::OnlyInTarget,
            source_value: None,
            target_value: Some(serde_json::json!({"enabled": addon.enabled})),
            recommended_action: SyncAction::KeepTarget,
            user_action: None,
            details: serde_json::json!({"path": addon.path, "note": "目标端独有插件"}),
            risk_level: "low".to_string(),
        });
    }

    // 两端都安装的插件
    for name in source_names.intersection(&target_names) {
        diffs.push(DiffItem {
            category: "addons".to_string(),
            item_type: "addon".to_string(),
            name: name.clone(),
            diff_type: DiffType::Identical,
            source_value: None,
            target_value: None,
            recommended_action: SyncAction::Skip,
            user_action: None,
            details: serde_json::json!({}),
            risk_level: "low".to_string(),
        });
    }

    Ok(diffs)
}

/// 比较启动脚本差异
fn compare_startup_scripts(source: &PathBuf, target: &PathBuf) -> std::io::Result<Vec<DiffItem>> {
    let mut diffs = Vec::new();

    let source_startup_dir = source.join("scripts").join("startup");
    let target_startup_dir = target.join("scripts").join("startup");

    let source_files = collect_files_recursive(&source_startup_dir);
    let target_files = collect_files_recursive(&target_startup_dir);

    let source_set: HashSet<String> = source_files.keys().cloned().collect();
    let target_set: HashSet<String> = target_files.keys().cloned().collect();

    // 仅在源端的文件
    for rel_path in source_set.difference(&target_set) {
        diffs.push(DiffItem {
            category: "startup_scripts".to_string(),
            item_type: "script".to_string(),
            name: rel_path.clone(),
            diff_type: DiffType::OnlyInSource,
            source_value: Some(serde_json::Value::String(source_files.get(rel_path).unwrap().clone())),
            target_value: None,
            recommended_action: SyncAction::SyncToTarget,
            user_action: None,
            details: serde_json::json!({"type": "startup_file"}),
            risk_level: "medium".to_string(),
        });
    }

    // 仅在目标端的文件
    for rel_path in target_set.difference(&source_set) {
        diffs.push(DiffItem {
            category: "startup_scripts".to_string(),
            item_type: "script".to_string(),
            name: rel_path.clone(),
            diff_type: DiffType::OnlyInTarget,
            source_value: None,
            target_value: Some(serde_json::Value::String(target_files.get(rel_path).unwrap().clone())),
            recommended_action: SyncAction::KeepTarget,
            user_action: None,
            details: serde_json::json!({"type": "startup_file"}),
            risk_level: "medium".to_string(),
        });
    }

    // 共有的文件（检查哈希）
    for rel_path in source_set.intersection(&target_set) {
        let src_path = source_startup_dir.join(rel_path);
        let tgt_path = target_startup_dir.join(rel_path);

        let src_hash = calculate_file_hash(&src_path).ok();
        let tgt_hash = calculate_file_hash(&tgt_path).ok();

        if src_hash != tgt_hash {
            let src_hash_str = src_hash.clone().unwrap_or_default();
            let tgt_hash_str = tgt_hash.clone().unwrap_or_default();
            let src_preview = &src_hash_str[..16.min(src_hash_str.len())];
            let tgt_preview = &tgt_hash_str[..16.min(tgt_hash_str.len())];

            diffs.push(DiffItem {
                category: "startup_scripts".to_string(),
                item_type: "script".to_string(),
                name: rel_path.clone(),
                diff_type: DiffType::Modified,
                source_value: Some(serde_json::json!({"hash": src_preview})),
                target_value: Some(serde_json::json!({"hash": tgt_preview})),
                recommended_action: SyncAction::SyncToTarget,
                user_action: None,
                details: serde_json::json!({}),
                risk_level: "medium".to_string(),
            });
        } else {
            diffs.push(DiffItem {
                category: "startup_scripts".to_string(),
                item_type: "script".to_string(),
                name: rel_path.clone(),
                diff_type: DiffType::Identical,
                source_value: None,
                target_value: None,
                recommended_action: SyncAction::Skip,
                user_action: None,
                details: serde_json::json!({}),
                risk_level: "low".to_string(),
            });
        }
    }

    Ok(diffs)
}

/// 比较预设配置
fn compare_presets(source: &PathBuf, target: &PathBuf) -> std::io::Result<Vec<DiffItem>> {
    let mut diffs = Vec::new();

    let source_presets_dir = source.join("scripts").join("presets");
    let target_presets_dir = target.join("scripts").join("presets");

    if !source_presets_dir.exists() && !target_presets_dir.exists() {
        return Ok(diffs);
    }

    let source_types: HashSet<String> = if source_presets_dir.exists() {
        fs::read_dir(&source_presets_dir)?
            .filter_map(|e| e.ok())
            .filter(|e| e.path().is_dir())
            .map(|e| e.file_name().to_string_lossy().to_string())
            .collect()
    } else {
        HashSet::new()
    };

    let target_types: HashSet<String> = if target_presets_dir.exists() {
        fs::read_dir(&target_presets_dir)?
            .filter_map(|e| e.ok())
            .filter(|e| e.path().is_dir())
            .map(|e| e.file_name().to_string_lossy().to_string())
            .collect()
    } else {
        HashSet::new()
    };

    for preset_type in source_types.union(&target_types) {
        let source_type_dir = source_presets_dir.join(preset_type);
        let target_type_dir = target_presets_dir.join(preset_type);

        let source_files: HashSet<String> = if source_type_dir.exists() {
            fs::read_dir(&source_type_dir)?
                .filter_map(|e| e.ok())
                .filter(|e| e.path().is_file())
                .map(|e| e.file_name().to_string_lossy().to_string())
                .collect()
        } else {
            HashSet::new()
        };

        let target_files: HashSet<String> = if target_type_dir.exists() {
            fs::read_dir(&target_type_dir)?
                .filter_map(|e| e.ok())
                .filter(|e| e.path().is_file())
                .map(|e| e.file_name().to_string_lossy().to_string())
                .collect()
        } else {
            HashSet::new()
        };

        for file in source_files.difference(&target_files) {
            diffs.push(DiffItem {
                category: "presets".to_string(),
                item_type: preset_type.clone(),
                name: file.clone(),
                diff_type: DiffType::OnlyInSource,
                source_value: Some(serde_json::Value::String(source_type_dir.join(file).to_string_lossy().to_string())),
                target_value: None,
                recommended_action: SyncAction::SyncToTarget,
                user_action: None,
                details: serde_json::json!({"preset_type": preset_type}),
                risk_level: "medium".to_string(),
            });
        }

        for file in target_files.difference(&source_files) {
            diffs.push(DiffItem {
                category: "presets".to_string(),
                item_type: preset_type.clone(),
                name: file.clone(),
                diff_type: DiffType::OnlyInTarget,
                source_value: None,
                target_value: Some(serde_json::Value::String(target_type_dir.join(file).to_string_lossy().to_string())),
                recommended_action: SyncAction::KeepTarget,
                user_action: None,
                details: serde_json::json!({"preset_type": preset_type}),
                risk_level: "low".to_string(),
            });
        }

        for file in source_files.intersection(&target_files) {
            diffs.push(DiffItem {
                category: "presets".to_string(),
                item_type: preset_type.clone(),
                name: file.clone(),
                diff_type: DiffType::Identical,
                source_value: None,
                target_value: None,
                recommended_action: SyncAction::Skip,
                user_action: None,
                details: serde_json::json!({"preset_type": preset_type}),
                risk_level: "low".to_string(),
            });
        }
    }

    Ok(diffs)
}

/// 比较关键配置文件
fn compare_config_files(source: &PathBuf, target: &PathBuf) -> std::io::Result<Vec<DiffItem>> {
    let mut diffs = Vec::new();

    let config_files = ["userpref.blend", "bookmarks.txt", "recent-files.txt"];

    for filename in config_files.iter() {
        let source_config = source.join("config").join(filename);
        let target_config = target.join("config").join(filename);

        let source_exists = source_config.exists();
        let target_exists = target_config.exists();

        if source_exists && !target_exists {
            diffs.push(DiffItem {
                category: "preferences".to_string(),
                item_type: "config_file".to_string(),
                name: filename.to_string(),
                diff_type: DiffType::OnlyInSource,
                source_value: Some(serde_json::json!({"size": fs::metadata(&source_config)?.len()})),
                target_value: None,
                recommended_action: SyncAction::SyncToTarget,
                user_action: None,
                details: serde_json::json!({"file_type": if filename.contains("blend") { "binary" } else { "text" }}),
                risk_level: "low".to_string(),
            });
        } else if !source_exists && target_exists {
            diffs.push(DiffItem {
                category: "preferences".to_string(),
                item_type: "config_file".to_string(),
                name: filename.to_string(),
                diff_type: DiffType::OnlyInTarget,
                source_value: None,
                target_value: Some(serde_json::json!({"size": fs::metadata(&target_config)?.len()})),
                recommended_action: SyncAction::KeepTarget,
                user_action: None,
                details: serde_json::json!({}),
                risk_level: "low".to_string(),
            });
        } else if source_exists && target_exists {
            let src_hash = calculate_file_hash(&source_config).ok();
            let tgt_hash = calculate_file_hash(&target_config).ok();

            if src_hash != tgt_hash {
                diffs.push(DiffItem {
                    category: "preferences".to_string(),
                    item_type: "config_file".to_string(),
                    name: filename.to_string(),
                    diff_type: DiffType::Modified,
                    source_value: None,
                    target_value: None,
                    recommended_action: SyncAction::SyncToTarget,
                    user_action: None,
                    details: serde_json::json!({}),
                    risk_level: "medium".to_string(),
                });
            } else {
                diffs.push(DiffItem {
                    category: "preferences".to_string(),
                    item_type: "config_file".to_string(),
                    name: filename.to_string(),
                    diff_type: DiffType::Identical,
                    source_value: None,
                    target_value: None,
                    recommended_action: SyncAction::Skip,
                    user_action: None,
                    details: serde_json::json!({}),
                    risk_level: "low".to_string(),
                });
            }
        }
    }

    Ok(diffs)
}

/// 收集目录下所有文件（递归）
fn collect_files_recursive(dir: &PathBuf) -> std::collections::HashMap<String, String> {
    let mut files = std::collections::HashMap::new();

    if !dir.exists() {
        return files;
    }

    for entry in WalkDir::new(dir).into_iter().filter_map(|e| e.ok()) {
        if entry.file_type().is_file() {
            let rel_path = entry.path().strip_prefix(dir).unwrap().to_string_lossy().to_string();
            files.insert(rel_path, entry.path().to_string_lossy().to_string());
        }
    }

    files
}

/// 计算文件哈希值
fn calculate_file_hash(path: &PathBuf) -> std::io::Result<String> {
    use sha2::{Sha256, Digest};
    let mut file = fs::File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = [0u8; 8192];

    loop {
        let n = std::io::Read::read(&mut file, &mut buffer)?;
        if n == 0 { break; }
        hasher.update(&buffer[..n]);
    }

    Ok(hex::encode(hasher.finalize()))
}

/// 评估插件同步风险
fn assess_addon_risk(addon: &config_scanner::AddonInfo) -> String {
    if addon.bl_info.is_none() {
        return "medium".to_string();
    }
    "low".to_string()
}

/// 计算统计信息
fn calculate_stats(items: &[DiffItem]) -> std::collections::HashMap<String, usize> {
    let mut stats = std::collections::HashMap::new();

    for item in items {
        let key = match item.diff_type {
            DiffType::OnlyInSource => "only_in_source",
            DiffType::OnlyInTarget => "only_in_target",
            DiffType::Modified => "modified",
            DiffType::Identical => "identical",
            DiffType::Conflict => "conflict",
        };
        *stats.entry(key.to_string()).or_insert(0) += 1;
    }

    stats
}

/// 按分类计数
fn count_by_category(items: &[DiffItem]) -> std::collections::HashMap<String, usize> {
    let mut counts = std::collections::HashMap::new();
    for item in items {
        *counts.entry(item.category.clone()).or_insert(0) += 1;
    }
    counts
}

/// 评估整体操作风险
fn assess_risk(items: &[DiffItem]) -> RiskAssessment {
    let high_count = items.iter().filter(|i| i.risk_level == "high").count();
    let medium_count = items.iter().filter(|i| i.risk_level == "medium").count();

    let (level, message) = if high_count > 0 {
        ("high".to_string(), format!("检测到 {} 个高风险项，请仔细检查", high_count))
    } else if medium_count > items.len() / 3 {
        ("medium".to_string(), "部分配置可能存在兼容性问题".to_string())
    } else {
        ("low".to_string(), "配置看起来安全，可以放心同步".to_string())
    };

    RiskAssessment {
        level,
        message,
        counts: RiskCounts { high: high_count, medium: medium_count },
    }
}

/// 生成操作建议
fn generate_recommendations(stats: &std::collections::HashMap<String, usize>) -> Vec<String> {
    let mut recommendations = Vec::new();

    if let Some(only_source) = stats.get("only_in_source") {
        if *only_source > 0 {
            recommendations.push(format!("有 {} 项配置仅存在于源端，建议同步", only_source));
        }
    }

    if let Some(only_target) = stats.get("only_in_target") {
        if *only_target > 0 {
            recommendations.push(format!("有 {} 项配置仅存在于目标端，可考虑保留", only_target));
        }
    }

    if let Some(modified) = stats.get("modified") {
        if *modified > 0 {
            recommendations.push(format!("有 {} 项配置两端不同，需要决定使用哪个版本", modified));
        }
    }

    recommendations
}