// dir_diff.rs - 通用文件夹差异检测与同步

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use walkdir::WalkDir;

/// 扫描目录中的所有文件（递归，最大深度 5 层）
#[derive(Debug, Serialize, Deserialize)]
pub struct FileEntry {
    /// 相对于根目录的相对路径
    pub rel_path: String,
    /// 绝对路径
    pub abs_path: String,
    pub is_dir: bool,
    pub size_bytes: u64,
    pub modified_time: Option<String>,
}

/// 差异项
#[derive(Debug, Serialize, Deserialize)]
pub struct DiffEntry {
    /// 相对路径
    pub rel_path: String,
    /// 差异类型
    pub diff_type: String, // "OnlyInSource" | "OnlyInTarget" | "Modified" | "Same"
    /// A 侧时间
    pub a_time: Option<String>,
    /// B 侧时间
    pub b_time: Option<String>,
    /// A 侧大小
    pub a_size: u64,
    /// B 侧大小
    pub b_size: u64,
    /// 是否是目录
    pub is_dir: bool,
}

/// 扫描结果汇总
#[derive(Debug, Serialize, Deserialize)]
pub struct DiffSummary {
    pub total_a: usize,
    pub total_b: usize,
    pub only_in_source: usize,
    pub only_in_target: usize,
    pub modified: usize,
    pub same: usize,
}

/// 差异对比结果
#[derive(Debug, Serialize, Deserialize)]
pub struct DiffResult {
    pub source_path: String,
    pub target_path: String,
    pub scan_time: String,
    pub entries: Vec<DiffEntry>,
    pub summary: DiffSummary,
}

/// 扫描目录树（递归，最大深度 5 层，不计算哈希）
pub fn scan_dir_tree(dir_path: &str) -> std::io::Result<Vec<FileEntry>> {
    let dir = PathBuf::from(dir_path);
    if !dir.exists() || !dir.is_dir() {
        return Ok(Vec::new());
    }

    let mut entries = Vec::new();
    let max_depth = 5; // 限制深度，避免扫描过深

    for entry in WalkDir::new(&dir).max_depth(max_depth).into_iter().filter_map(|e| e.ok()) {
        let path = entry.path();
        let rel = path.strip_prefix(&dir)
            .map(|p| p.to_string_lossy().to_string())
            .unwrap_or_default();

        if rel.is_empty() {
            continue; // 跳过根目录本身
        }

        let metadata = fs::metadata(path).ok();
        let is_dir = path.is_dir();
        let size_bytes = metadata.as_ref().map(|m| m.len()).unwrap_or(0);
        let modified_time = metadata
            .and_then(|m| m.modified().ok())
            .map(|t| {
                let dt: DateTime<Utc> = t.into();
                dt.to_rfc3339()
            });

        entries.push(FileEntry {
            rel_path: rel,
            abs_path: path.to_string_lossy().to_string(),
            is_dir,
            size_bytes,
            modified_time,
        });
    }

    // 目录排前面，然后按路径排序
    entries.sort_by(|a, b| {
        match (a.is_dir, b.is_dir) {
            (true, false) => std::cmp::Ordering::Less,
            (false, true) => std::cmp::Ordering::Greater,
            _ => a.rel_path.cmp(&b.rel_path),
        }
    });

    Ok(entries)
}

/// 对比两个目录
pub fn diff_dirs(source_path: &str, target_path: &str) -> std::io::Result<DiffResult> {
    let source_entries = scan_dir_tree(source_path)?;
    let target_entries = scan_dir_tree(target_path)?;

    // 建立查找表
    let source_map: std::collections::HashMap<String, &FileEntry> = source_entries
        .iter()
        .map(|e| (e.rel_path.clone(), e))
        .collect();
    let target_map: std::collections::HashMap<String, &FileEntry> = target_entries
        .iter()
        .map(|e| (e.rel_path.clone(), e))
        .collect();

    let mut all_paths: std::collections::BTreeSet<String> = source_map.keys().cloned().collect();
    all_paths.extend(target_map.keys().cloned());

    let mut diff_entries = Vec::new();
    let mut only_source = 0usize;
    let mut only_target = 0usize;
    let mut modified = 0usize;
    let mut same = 0usize;

    for rel_path in all_paths {
        let a = source_map.get(&rel_path);
        let b = target_map.get(&rel_path);

        let diff_type = match (a, b) {
            (Some(_), None) => {
                only_source += 1;
                "OnlyInSource".to_string()
            }
            (None, Some(_)) => {
                only_target += 1;
                "OnlyInTarget".to_string()
            }
            (Some(sa), Some(sb)) => {
                // 两边都有，对比是否相同
                if sa.is_dir != sb.is_dir {
                    modified += 1;
                    "Modified".to_string()
                } else if sa.is_dir {
                    // 目录：只对比是否存在
                    same += 1;
                    "Same".to_string()
                } else {
                    // 文件：比大小+时间
                    let is_same = sa.size_bytes == sb.size_bytes
                        && sa.modified_time == sb.modified_time;
                    if is_same {
                        same += 1;
                        "Same".to_string()
                    } else {
                        modified += 1;
                        "Modified".to_string()
                    }
                }
            }
            (None, None) => continue,
        };

        diff_entries.push(DiffEntry {
            rel_path,
            diff_type,
            a_time: a.and_then(|e| e.modified_time.clone()),
            b_time: b.and_then(|e| e.modified_time.clone()),
            a_size: a.map(|e| e.size_bytes).unwrap_or(0),
            b_size: b.map(|e| e.size_bytes).unwrap_or(0),
            is_dir: a.map(|e| e.is_dir).or(b.map(|e| e.is_dir)).unwrap_or(false),
        });
    }

    // 目录排前面
    diff_entries.sort_by(|a, b| {
        match (a.is_dir, b.is_dir) {
            (true, false) => std::cmp::Ordering::Less,
            (false, true) => std::cmp::Ordering::Greater,
            _ => a.rel_path.cmp(&b.rel_path),
        }
    });

    Ok(DiffResult {
        source_path: source_path.to_string(),
        target_path: target_path.to_string(),
        scan_time: Utc::now().to_rfc3339(),
        entries: diff_entries,
        summary: DiffSummary {
            total_a: source_entries.len(),
            total_b: target_entries.len(),
            only_in_source: only_source,
            only_in_target: only_target,
            modified,
            same,
        },
    })
}
