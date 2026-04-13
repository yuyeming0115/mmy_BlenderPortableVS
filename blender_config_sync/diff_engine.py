"""
Blender 配置差异比较引擎
负责对比两个 Blender 版本之间的配置差异，生成详细的可视化报告
"""

import json
import ast
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from blender_config_sync.config_scanner import ConfigScanner, BookmarksData, AddonInfo


class DiffType(Enum):
    """差异类型枚举"""
    ONLY_IN_SOURCE = "only_in_source"      # 仅存在于源配置
    ONLY_IN_TARGET = "only_in_target"      # 仅存在于目标配置
    MODIFIED = "modified"                   # 两端都有但内容不同
    IDENTICAL = "identical"                 # 完全相同
    CONFLICT = "conflict"                   # 冲突（需要用户选择）


class SyncAction(Enum):
    """同步操作类型"""
    SYNC_TO_TARGET = "sync_to_target"       # 同步到目标
    KEEP_TARGET = "keep_target"             # 保留目标版本
    MERGE = "merge"                         # 合并两端
    SKIP = "skip"                           # 跳过此项


@dataclass
class DiffItem:
    """单个差异项"""
    category: str                          # 分类（bookmarks/addons/keymaps等）
    item_type: str                         # 具体类型
    name: str                              # 名称/标识
    diff_type: DiffType                    # 差异类型
    source_value: Any = None               # 源端值
    target_value: Any = None               # 目标端值
    recommended_action: SyncAction = SyncAction.SYNC_TO_TARGET  # 推荐操作
    user_action: Optional[SyncAction] = None  # 用户选择的操作
    details: Dict = field(default_factory=dict)  # 详细信息
    risk_level: str = "low"                # 风险等级: low/medium/high


@dataclass
class ComparisonResult:
    """比较结果"""
    source_version: str
    target_version: str
    scan_time: str
    total_items: int = 0
    diff_items: List[DiffItem] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)

    def get_items_by_category(self, category: str) -> List[DiffItem]:
        """按分类获取差异项"""
        return [item for item in self.diff_items if item.category == category]

    def get_items_by_diff_type(self, diff_type: DiffType) -> List[DiffItem]:
        """按差异类型获取差异项"""
        return [item for item in self.diff_items if item.diff_type == diff_type]

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        stats = {}
        for dt in DiffType:
            stats[dt.value] = len(self.get_items_by_diff_type(dt))
        return stats


class DiffEngine:
    """配置差异比较引擎"""

    CATEGORIES = {
        'bookmarks': {
            'name': '文件浏览器书签',
            'icon': '📑',
            'description': '收藏夹路径列表'
        },
        'addons': {
            'name': '已安装插件',
            'icon': '🔌',
            'description': 'Python 插件及其启用状态'
        },
        'keymaps': {
            'name': '自定义快捷键',
            'icon': '⌨️',
            'description': '键盘映射和鼠标绑定'
        },
        'preferences': {
            'name': '偏好设置',
            'icon': '⚙️',
            'description': '界面主题、语言、保存选项等'
        },
        'startup_scripts': {
            'name': '启动脚本',
            'icon': '🚀',
            'description': '自动执行的 Python 脚本'
        },
        'presets': {
            'name': '预设配置',
            'icon': '🎨',
            'description': '快捷键预设、界面主题等'
        }
    }

    def __init__(self):
        self.scanner_cache = {}

    def get_scanner(self, config_path: Path) -> ConfigScanner:
        """获取或创建扫描器实例（带缓存）"""
        path_str = str(config_path)
        if path_str not in self.scanner_cache:
            self.scanner_cache[path_str] = ConfigScanner(config_path)
        return self.scanner_cache[path_str]

    def compare(self, source_path: Path, target_path: Path,
                source_version: str = "", target_version: str = "") -> ComparisonResult:
        """
        执行完整的配置比较

        Args:
            source_path: 源配置路径（要同步的配置）
            target_path: 目标配置路径（被同步到的配置）
            source_version: 源 Blender 版本号
            target_version: 目标 Blender 版本号

        Returns:
            ComparisonResult: 完整的比较结果
        """
        result = ComparisonResult(
            source_version=source_version,
            target_version=target_version,
            scan_time=datetime.now().isoformat()
        )

        source_scanner = self.get_scanner(source_path)
        target_scanner = self.get_scanner(target_path)

        # 1. 比较书签
        bookmark_diffs = self._compare_bookmarks(source_scanner, target_scanner)
        result.diff_items.extend(bookmark_diffs)

        # 2. 比较插件
        addon_diffs = self._compare_addons(source_scanner, target_scanner)
        result.diff_items.extend(addon_diffs)

        # 3. 比较启动脚本
        startup_diffs = self._compare_startup_scripts(source_scanner, target_scanner)
        result.diff_items.extend(startup_diffs)

        # 4. 比较预设配置
        preset_diffs = self._compare_presets(source_scanner, target_scanner)
        result.diff_items.extend(preset_diffs)

        # 5. 比较配置文件存在性
        config_diffs = self._compare_config_files(source_scanner, target_scanner)
        result.diff_items.extend(config_diffs)

        # 生成统计摘要
        result.total_items = len(result.diff_items)
        result.summary = {
            'stats': result.get_stats(),
            'categories': {cat: len(result.get_items_by_category(cat)) for cat in self.CATEGORIES},
            'risk_assessment': self._assess_risk(result),
            'recommendations': self._generate_recommendations(result)
        }

        return result

    def _compare_bookmarks(self, source: ConfigScanner, target: ConfigScanner) -> List[DiffItem]:
        """比较书签差异"""
        diffs = []
        source_bookmarks = source.read_bookmarks()
        target_bookmarks = target.read_bookmarks()

        source_set = set(source_bookmarks.paths)
        target_set = set(target_bookmarks.paths)

        # 仅在源端存在的书签
        for path in sorted(source_set - target_set):
            diffs.append(DiffItem(
                category='bookmarks',
                item_type='bookmark_path',
                name=path,
                diff_type=DiffType.ONLY_IN_SOURCE,
                source_value=path,
                target_value=None,
                recommended_action=SyncAction.SYNC_TO_TARGET,
                details={'path_type': 'directory' if not Path(path).suffix else 'file'}
            ))

        # 仅在目标端存在的书签
        for path in sorted(target_set - source_set):
            diffs.append(DiffItem(
                category='bookmarks',
                item_type='bookmark_path',
                name=path,
                diff_type=DiffType.ONLY_IN_TARGET,
                source_value=None,
                target_value=path,
                recommended_action=SyncAction.KEEP_TARGET,
                details={'note': '目标端独有，可选择保留或删除'}
            ))

        # 两端都有的书签（理论上应该相同）
        for path in sorted(source_set & target_set):
            diffs.append(DiffItem(
                category='bookmarks',
                item_type='bookmark_path',
                name=path,
                diff_type=DiffType.IDENTICAL,
                source_value=path,
                target_value=path,
                recommended_action=SyncAction.SKIP
            ))

        return diffs

    def _compare_addons(self, source: ConfigScanner, target: ConfigScanner) -> List[DiffItem]:
        """比较插件差异"""
        diffs = []
        source_addons = source.list_addons()
        target_addons = target.list_addons()

        source_dict = {a.name: a for a in source_addons}
        target_dict = {a.name: a for a in target_addons}

        source_names = set(source_dict.keys())
        target_names = set(target_dict.keys())

        # 仅在源端安装的插件
        for name in sorted(source_names - target_names):
            addon = source_dict[name]
            bl_ver = addon.bl_info.get('blender', '?') if addon.bl_info else '未知'

            diffs.append(DiffItem(
                category='addons',
                item_type='addon',
                name=name,
                diff_type=DiffType.ONLY_IN_SOURCE,
                source_value={'version': bl_ver, 'enabled': addon.enabled},
                target_value=None,
                recommended_action=SyncAction.SYNC_TO_TARGET,
                details={
                    'blender_support': str(bl_ver),
                    'path': addon.path,
                    'has_bl_info': addon.bl_info is not None
                },
                risk_level=self._assess_addon_risk(addon)
            ))

        # 仅在目标端安装的插件
        for name in sorted(target_names - source_names):
            addon = target_dict[name]
            diffs.append(DiffItem(
                category='addons',
                item_type='addon',
                name=name,
                diff_type=DiffType.ONLY_IN_TARGET,
                source_value=None,
                target_value={'enabled': addon.enabled},
                recommended_action=SyncAction.KEEP_TARGET,
                details={
                    'path': addon.path,
                    'note': '目标端独有插件'
                }
            ))

        # 两端都安装的插件
        for name in sorted(source_names & target_names):
            src_addon = source_dict[name]
            tgt_addon = target_dict[name]

            # 检查是否有差异（版本不同或状态不同）
            src_info = src_addon.bl_info or {}
            tgt_info = tgt_addon.bl_info or {}

            if src_info.get('version') != tgt_info.get('version'):
                diffs.append(DiffItem(
                    category='addons',
                    item_type='addon',
                    name=name,
                    diff_type=DiffType.MODIFIED,
                    source_value={'version': src_info.get('version', '?')},
                    target_value={'version': tgt_info.get('version', '?')},
                    recommended_action=SyncAction.SYNC_TO_TARGET,
                    details={
                        'source_version': src_info.get('version'),
                        'target_version': tgt_info.get('version'),
                        'note': '插件版本不同'
                    }
                ))
            else:
                diffs.append(DiffItem(
                    category='addons',
                    item_type='addon',
                    name=name,
                    diff_type=DiffType.IDENTICAL,
                    source_value={'version': src_info.get('version')},
                    target_value={'version': tgt_info.get('version')},
                    recommended_action=SyncAction.SKIP
                ))

        return diffs

    def _compare_startup_scripts(self, source: ConfigScanner, target: ConfigScanner) -> List[DiffItem]:
        """比较启动脚本差异"""
        diffs = []

        source_startup_dir = source.scripts_dir / 'startup'
        target_startup_dir = target.scripts_dir / 'startup'

        source_scripts = set()
        if source_startup_dir.exists():
            source_scripts = {f.name for f in source_startup_dir.glob('*.py')}

        target_scripts = set()
        if target_startup_dir.exists():
            target_scripts = {f.name for f in target_startup_dir.glob('*.py')}

        # 仅在源端的脚本
        for script in sorted(source_scripts - target_scripts):
            diffs.append(DiffItem(
                category='startup_scripts',
                item_type='script',
                name=script,
                diff_type=DiffType.ONLY_IN_SOURCE,
                source_value=f'{source_startup_dir / script}',
                recommended_action=SyncAction.SYNC_TO_TARGET,
                risk_level='medium',
                details={'type': 'startup_script'}
            ))

        # 仅在目标端的脚本
        for script in sorted(target_scripts - source_scripts):
            diffs.append(DiffItem(
                category='startup_scripts',
                item_type='script',
                name=script,
                diff_type=DiffType.ONLY_IN_TARGET,
                target_value=f'{target_startup_dir / script}',
                recommended_action=SyncAction.KEEP_TARGET,
                details={'type': 'startup_script'}
            ))

        # 共有的脚本
        for script in sorted(source_scripts & target_scripts):
            diffs.append(DiffItem(
                category='startup_scripts',
                item_type='script',
                name=script,
                diff_type=DiffType.IDENTICAL,
                recommended_action=SyncAction.SKIP
            ))

        return diffs

    def _compare_presets(self, source: ConfigScanner, target: ConfigScanner) -> List[DiffItem]:
        """比较预设配置（keyconfig、interface_theme等）"""
        diffs = []
        
        source_presets_dir = source.scripts_dir / 'presets'
        target_presets_dir = target.scripts_dir / 'presets'
        
        if not source_presets_dir.exists() and not target_presets_dir.exists():
            return diffs
        
        source_preset_types = set()
        target_preset_types = set()
        
        if source_presets_dir.exists():
            source_preset_types = {d.name for d in source_presets_dir.iterdir() if d.is_dir()}
        if target_presets_dir.exists():
            target_preset_types = {d.name for d in target_presets_dir.iterdir() if d.is_dir()}
        
        all_preset_types = source_preset_types | target_preset_types
        
        for preset_type in sorted(all_preset_types):
            source_type_dir = source_presets_dir / preset_type
            target_type_dir = target_presets_dir / preset_type
            
            source_files = set()
            target_files = set()
            
            if source_type_dir.exists():
                source_files = {f.name for f in source_type_dir.glob('*') if f.is_file()}
            if target_type_dir.exists():
                target_files = {f.name for f in target_type_dir.glob('*') if f.is_file()}
            
            type_label = preset_type.replace('_', ' ').title()
            
            for file in sorted(source_files - target_files):
                diffs.append(DiffItem(
                    category='presets',
                    item_type=preset_type,
                    name=file,
                    diff_type=DiffType.ONLY_IN_SOURCE,
                    source_value=str(source_type_dir / file),
                    recommended_action=SyncAction.SYNC_TO_TARGET,
                    risk_level='medium',
                    details={'preset_type': type_label}
                ))
            
            for file in sorted(target_files - source_files):
                diffs.append(DiffItem(
                    category='presets',
                    item_type=preset_type,
                    name=file,
                    diff_type=DiffType.ONLY_IN_TARGET,
                    target_value=str(target_type_dir / file),
                    recommended_action=SyncAction.KEEP_TARGET,
                    details={'preset_type': type_label}
                ))
            
            for file in sorted(source_files & target_files):
                src_path = source_type_dir / file
                tgt_path = target_type_dir / file
                
                src_hash = self._calculate_file_hash(src_path)
                tgt_hash = self._calculate_file_hash(tgt_path)
                
                if src_hash != tgt_hash:
                    diffs.append(DiffItem(
                        category='presets',
                        item_type=preset_type,
                        name=file,
                        diff_type=DiffType.MODIFIED,
                        source_value={'hash': src_hash[:16] if src_hash else None},
                        target_value={'hash': tgt_hash[:16] if tgt_hash else None},
                        recommended_action=SyncAction.SYNC_TO_TARGET,
                        risk_level='medium',
                        details={'preset_type': type_label}
                    ))
                else:
                    diffs.append(DiffItem(
                        category='presets',
                        item_type=preset_type,
                        name=file,
                        diff_type=DiffType.IDENTICAL,
                        recommended_action=SyncAction.SKIP
                    ))
        
        return diffs
    
    def _calculate_file_hash(self, path: Path) -> str:
        """计算文件哈希值"""
        import hashlib
        if not path.exists() or not path.is_file():
            return ''
        try:
            sha256 = hashlib.sha256()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception:
            return ''

    def _compare_config_files(self, source: ConfigScanner, target: ConfigScanner) -> List[DiffItem]:
        """比较关键配置文件的存在性和修改时间"""
        diffs = []
        config_files = ['userpref_blend', 'bookmarks_txt', 'recent_files_txt']

        for config_type in config_files:
            source_info = source.scan_config(config_type)
            target_info = target.scan_config(config_type)

            if source_info.exists and not target_info.exists:
                diffs.append(DiffItem(
                    category='preferences',
                    item_type='config_file',
                    name=config_type,
                    diff_type=DiffType.ONLY_IN_SOURCE,
                    source_value={
                        'size': source_info.size_bytes,
                        'modified': source_info.modified_time
                    },
                    recommended_action=SyncAction.SYNC_TO_TARGET,
                    risk_level='low',
                    details={'file_type': 'binary' if 'blend' in config_type else 'text'}
                ))
            elif not source_info.exists and target_info.exists:
                diffs.append(DiffItem(
                    category='preferences',
                    item_type='config_file',
                    name=config_type,
                    diff_type=DiffType.ONLY_IN_TARGET,
                    target_value={
                        'size': target_info.size_bytes,
                        'modified': target_info.modified_time
                    },
                    recommended_action=SyncAction.KEEP_TARGET
                ))
            elif source_info.exists and target_info.exists:
                # 文件都存在，检查是否相同（通过哈希）
                if source_info.sha256_hash != target_info.sha256_hash:
                    diffs.append(DiffItem(
                        category='preferences',
                        item_type='config_file',
                        name=config_type,
                        diff_type=DiffType.MODIFIED,
                        source_value={'modified': source_info.modified_time},
                        target_value={'modified': target_info.modified_time},
                        recommended_action=SyncAction.SYNC_TO_TARGET,
                        risk_level='medium',
                        details={
                            'source_hash': source_info.sha256_hash[:16],
                            'target_hash': target_info.sha256_hash[:16]
                        }
                    ))
                else:
                    diffs.append(DiffItem(
                        category='preferences',
                        item_type='config_file',
                        name=config_type,
                        diff_type=DiffType.IDENTICAL,
                        recommended_action=SyncAction.SKIP
                    ))

        return diffs

    def _assess_addon_risk(self, addon: AddonInfo) -> str:
        """
        评估插件同步的风险等级

        Returns:
            str: 'low' | 'medium' | 'high'
        """
        if not addon.bl_info:
            return 'medium'  # 无法判断风险

        blender_support = addon.bl_info.get('blender', [])

        if isinstance(blender_support, (list, tuple)) and len(blender_support) >= 2:
            min_ver, max_ver = blender_support[0], blender_support[-1]
            # 如果插件支持的范围很宽，风险低
            if max_ver >= 5.0:  # 支持到未来版本
                return 'low'
            elif max_ver >= 4.0:
                return 'low'
            else:
                return 'medium'

        return 'medium'

    def _assess_risk(self, result: ComparisonResult) -> Dict:
        """评估整体操作风险"""
        high_risk_count = sum(1 for item in result.diff_items if item.risk_level == 'high')
        medium_risk_count = sum(1 for item in result.diff_items if item.risk_level == 'medium')
        total_diffs = sum(1 for item in result.diff_items
                         if item.diff_type in [DiffType.ONLY_IN_SOURCE, DiffType.MODIFIED])

        if high_risk_count > 0:
            level = 'high'
            message = f'检测到 {high_risk_count} 个高风险项，请仔细检查'
        elif medium_risk_count > total_diffs * 0.3:
            level = 'medium'
            message = f'部分配置可能存在兼容性问题'
        else:
            level = 'low'
            message = '配置看起来安全，可以放心同步'

        return {
            'level': level,
            'message': message,
            'counts': {'high': high_risk_count, 'medium': medium_risk_count}
        }

    def _generate_recommendations(self, result: ComparisonResult) -> List[str]:
        """生成操作建议"""
        recommendations = []

        stats = result.get_stats()
        only_in_source = stats.get('only_in_source', 0)
        only_in_target = stats.get('only_in_target', 0)
        modified = stats.get('modified', 0)

        if only_in_source > 0:
            recommendations.append(f'📥 有 {only_in_source} 项配置仅存在于源端，建议同步')

        if only_in_target > 0:
            recommendations.append(f'📤 有 {only_in_target} 项配置仅存在于目标端，可考虑保留')

        if modified > 0:
            recommendations.append(f'⚠️ 有 {modified} 项配置两端不同，需要决定使用哪个版本')

        risk_assessment = result.summary.get('risk_assessment')
        if risk_assessment and risk_assessment.get('level') == 'high':
            recommendations.append('🚨 建议先备份目标配置再进行同步')

        return recommendations

    def export_comparison_report(self, result: ComparisonResult, output_path: Path = None) -> str:
        """
        导出比较报告为 JSON 文件

        Args:
            result: 比较结果
            output_path: 输出路径

        Returns:
            str: 生成的报告文件路径
        """
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = Path.cwd() / f'comparison_report_{timestamp}.json'

        report_data = {
            'metadata': {
                'source_version': result.source_version,
                'target_version': result.target_version,
                'scan_time': result.scan_time,
                'generated_by': 'Blender Config Sync v0.2'
            },
            'summary': result.summary,
            'diff_items': [
                {
                    'category': item.category,
                    'item_type': item.item_type,
                    'name': item.name,
                    'diff_type': item.diff_type.value,
                    'recommended_action': item.recommended_action.value,
                    'user_action': item.user_action.value if item.user_action else None,
                    'risk_level': item.risk_level,
                    'details': item.details
                }
                for item in result.diff_items
            ]
        }

        output_path.write_text(
            json.dumps(report_data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

        return str(output_path)


def generate_text_report(result: ComparisonResult) -> str:
    """生成人类可读的文本报告"""
    lines = []
    lines.append("=" * 70)
    lines.append("📊 Blender 配置差异比较报告")
    lines.append("=" * 70)
    lines.append(f"\n📍 源版本: {result.source_version}")
    lines.append(f"📍 目标版本: {result.target_version}")
    lines.append(f"⏰ 扫描时间: {result.scan_time}")
    lines.append(f"\n📈 总差异项数: {result.total_items}")

    # 统计信息
    stats = result.get_stats()
    lines.append("\n📋 差异统计:")
    lines.append("-" * 50)
    for dt, count in stats.items():
        icon = {
            'only_in_source': '🟢 仅源端',
            'only_in_target': '🔵 仅目标端',
            'modified': '🟡 已修改',
            'identical': '⚪ 相同',
            'conflict': '🔴 冲突'
        }.get(dt, dt)
        lines.append(f"  {icon:<15} : {count:>3} 项")

    # 按分类显示详情
    lines.append("\n\n📂 详细差异:")
    lines.append("=" * 70)

    for category, meta in DiffEngine.CATEGORIES.items():
        items = result.get_items_by_category(category)
        if not items:
            continue

        lines.append(f"\n{meta['icon']} {meta['name']} ({len(items)} 项)")
        lines.append("-" * 50)

        for item in items[:10]:  # 只显示前10个
            diff_icon = {
                DiffType.ONLY_IN_SOURCE: '➕',
                DiffType.ONLY_IN_TARGET: '➖',
                DiffType.MODIFIED: '✏️',
                DiffType.IDENTICAL: '✅',
                DiffType.CONFLICT: '⚠️'
            }.get(item.diff_type, '?')

            action_icon = {
                SyncAction.SYNC_TO_TARGET: '→',
                SyncAction.KEEP_TARGET: '←',
                SyncAction.MERGE: '↔',
                SyncAction.SKIP: '⊘'
            }.get(item.recommended_action, '?')

            risk_icon = {'low': '🟢', 'medium': '🟡', 'high': '🔴'}.get(item.risk_level, '')

            line = f"  {diff_icon} {item.name:<35} {action_icon} {risk_icon}"
            lines.append(line)

        if len(items) > 10:
            lines.append(f"  ... 还有 {len(items) - 10} 项")

    # 风险评估和建议
    lines.append("\n\n⚠️ 风险评估:")
    lines.append("-" * 50)
    risk = result.summary['risk_assessment']
    lines.append(f"  等级: {risk['level'].upper()}")
    lines.append(f"  说明: {risk['message']}")

    lines.append("\n💡 建议:")
    for rec in result.summary['recommendations']:
        lines.append(f"  • {rec}")

    lines.append("\n" + "=" * 70)

    return '\n'.join(lines)


if __name__ == '__main__':
    print("✅ DiffEngine 模块加载成功")
    print("   可用于比较两个 Blender 版本的配置差异")
