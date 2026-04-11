"""
Blender 配置文件扫描器
负责读取和解析 Blender 的各种配置文件
"""

import json
import hashlib
import ast
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class ConfigFileInfo:
    """配置文件信息"""
    file_type: str
    path: str
    exists: bool
    size_bytes: int = 0
    modified_time: Optional[str] = None
    sha256_hash: Optional[str] = None
    content_preview: Optional[str] = None


@dataclass
class BookmarksData:
    """书签数据"""
    paths: List[str]
    count: int


@dataclass
class AddonInfo:
    """插件信息"""
    name: str
    path: str
    enabled: bool = False
    bl_info: Optional[Dict] = None
    compatibility: str = 'unknown'


class ConfigScanner:
    """配置文件扫描器"""

    SUPPORTED_CONFIG_TYPES = {
        'userpref_blend': {
            'description': '用户偏好设置',
            'contains': ['快捷键', '主题', '插件状态', '界面设置']
        },
        'bookmarks_txt': {
            'description': '文件浏览器书签',
            'contains': ['收藏夹路径']
        },
        'addons_dir': {
            'description': '用户安装的插件',
            'contains': ['.py 插件文件']
        },
        'keyconfig_presets': {
            'description': '键盘映射预设',
            'contains': ['自定义 .py 键位映射']
        },
        'startup_scripts_dir': {
            'description': '启动脚本',
            'contains': ['自动执行的 Python 脚本']
        }
    }

    def __init__(self, config_base_path: Path):
        """
        初始化扫描器

        Args:
            config_base_path: Blender 版本的配置基础路径（如 ~/.config/blender/4.2/）
        """
        self.config_base = config_base_path
        self.config_dir = config_base_path / 'config'
        self.scripts_dir = config_base_path / 'scripts'

    def scan_all_configs(self) -> Dict[str, Any]:
        """
        扫描所有关键配置文件

        Returns:
            Dict: 包含所有配置文件信息的字典
        """
        result = {
            'scan_time': datetime.now().isoformat(),
            'config_base': str(self.config_base),
            'configs': {},
            'summary': {}
        }

        total_size = 0
        existing_count = 0

        for config_type, meta in self.SUPPORTED_CONFIG_TYPES.items():
            file_info = self.scan_config(config_type)
            result['configs'][config_type] = asdict(file_info)

            if file_info.exists:
                existing_count += 1
                total_size += file_info.size_bytes

        result['summary'] = {
            'total_types_scanned': len(self.SUPPORTED_CONFIG_TYPES),
            'existing_count': existing_count,
            'total_size_bytes': total_size,
            'scan_status': 'complete' if existing_count > 0 else 'empty'
        }

        return result

    def scan_config(self, config_type: str) -> ConfigFileInfo:
        """
        扫描特定类型的配置文件

        Args:
            config_type: 配置文件类型（如 'userpref_blend', 'bookmarks_txt'）

        Returns:
            ConfigFileInfo: 配置文件信息
        """
        path = self._get_config_path(config_type)

        if not path:
            return ConfigFileInfo(
                file_type=config_type,
                path='',
                exists=False
            )

        exists = path.exists()

        info = ConfigFileInfo(
            file_type=config_type,
            path=str(path),
            exists=exists
        )

        if exists:
            is_dir = path.is_dir()
            stat = path.stat()
            info.size_bytes = 0 if is_dir else stat.st_size
            info.modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()

            # 只对文件计算哈希值
            if not is_dir:
                info.sha256_hash = self._calculate_hash(path)

                # 对于文本文件，提供内容预览
                if path.suffix in ['.txt', '.py', '.json']:
                    try:
                        content = path.read_text(encoding='utf-8', errors='ignore')
                        lines = content.split('\n')
                        preview_lines = lines[:5]
                        info.content_preview = '\n'.join(preview_lines)
                        if len(lines) > 5:
                            info.content_preview += f'\n... (共 {len(lines)} 行)'
                    except Exception:
                        info.content_preview = '[无法读取内容]'
            else:
                info.content_preview = '[目录]'

        return info

    def _get_config_path(self, config_type: str) -> Optional[Path]:
        """根据类型获取配置文件路径"""
        paths = {
            'userpref_blend': self.config_dir / 'userpref.blend',
            'startup_blend': self.config_dir / 'startup.blend',
            'bookmarks_txt': self.config_dir / 'bookmarks.txt',
            'recent_files_txt': self.config_dir / 'recent-files.txt',
            'addons_dir': self.scripts_dir / 'addons',
            'addons_contrib_dir': self.scripts_dir / 'addons_contrib',
            'startup_scripts_dir': self.scripts_dir / 'startup',
            'keyconfig_presets': self.scripts_dir / 'presets' / 'keyconfig',
        }
        return paths.get(config_type)

    def _calculate_hash(self, path: Path) -> str:
        """计算文件的 SHA256 哈希值"""
        sha256 = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def read_bookmarks(self) -> BookmarksData:
        """
        读取书签文件

        Returns:
            BookmarksData: 书签数据对象
        """
        bookmarks_path = self.config_dir / 'bookmarks.txt'

        default_result = BookmarksData(paths=[], count=0)

        if not bookmarks_path.exists():
            return default_result

        try:
            content = bookmarks_path.read_text(encoding='utf-8')
            bookmarks = []
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    bookmarks.append(line)

            return BookmarksData(paths=bookmarks, count=len(bookmarks))
        except Exception as e:
            print(f"❌ 读取书签失败: {e}")
            return default_result

    def write_bookmarks(self, bookmarks: List[str]) -> bool:
        """
        写入书签文件

        Args:
            bookmarks: 书签路径列表

        Returns:
            bool: 是否成功写入
        """
        bookmarks_path = self.config_dir / 'bookmarks.txt'

        try:
            bookmarks_path.parent.mkdir(parents=True, exist_ok=True)
            content = '\n'.join(bookmarks) + '\n' if bookmarks else ''
            bookmarks_path.write_text(content, encoding='utf-8')
            return True
        except Exception as e:
            print(f"❌ 写入书签失败: {e}")
            return False

    def list_addons(self) -> List[AddonInfo]:
        """
        列出所有已安装的插件

        Returns:
            List[AddonInfo]: 插件信息列表
        """
        addons_dir = self.scripts_dir / 'addons'
        addons = []

        if not addons_dir.exists():
            return addons

        for addon_file in addons_dir.glob('*.py'):
            addon_info = AddonInfo(
                name=addon_file.stem,
                path=str(addon_file)
            )

            # 解析 bl_info
            addon_info.bl_info = self._parse_bl_info(addon_file)
            addon_info.enabled = self._is_addon_enabled(addon_file.stem)

            addons.append(addon_info)

        # 也检查子目录形式的插件
        for addon_dir in addons_dir.iterdir():
            if addon_dir.is_dir() and (addon_dir / '__init__.py').exists():
                init_file = addon_dir / '__init__.py'
                addon_info = AddonInfo(
                    name=addon_dir.name,
                    path=str(addon_dir)
                )
                addon_info.bl_info = self._parse_bl_info(init_file)
                addon_info.enabled = self._is_addon_enabled(addon_dir.name)
                addons.append(addon_info)

        return addons

    def _parse_bl_info(self, file_path: Path) -> Optional[Dict]:
        """解析插件的 bl_info 字典"""
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == 'bl_info':
                            return ast.literal_eval(node.value)
        except Exception:
            pass

        return None

    def _is_addon_enabled(self, addon_name: str) -> bool:
        """
        检查插件是否启用（通过 userpref.blend 判断）

        注意：此方法需要 Blender 运行时环境才能准确判断。
        这里返回 False 作为默认值。

        Args:
            addon_name: 插件名称

        Returns:
            bool: 是否启用（默认 False）
        """
        # TODO: 可以通过解析 userpref.blend 或运行 Blender Python API 来准确判断
        return False

    def export_scan_report(self, output_path: Path = None) -> str:
        """
        导出扫描报告为 JSON 文件

        Args:
            output_path: 输出路径，如果为 None 则生成默认路径

        Returns:
            str: 生成的报告文件路径
        """
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = Path.cwd() / f'scan_report_{timestamp}.json'

        report_data = self.scan_all_configs()
        report_data['bookmarks'] = asdict(self.read_bookmarks())
        report_data['addons'] = [asdict(a) for a in self.list_addons()]

        output_path.write_text(
            json.dumps(report_data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

        return str(output_path)


def main():
    """测试用例"""
    from blender_config_sync.path_manager import BlenderPathManager

    manager = BlenderPathManager()
    versions = manager.detect_installed_versions()

    if not versions:
        print("❌ 未找到 Blender 安装")
        return

    # 使用最新版本进行演示
    latest_version = versions[0]
    print(f"\n🔍 正在扫描 Blender {latest_version.version} 的配置...\n")

    scanner = ConfigScanner(latest_version.config_path)
    report = scanner.scan_all_configs()

    print("=" * 60)
    print(f"📊 配置扫描报告")
    print("=" * 60)
    print(f"📁 配置目录: {report['config_base']}")
    print(f"⏰ 扫描时间: {report['scan_time']}")
    print(f"\n📈 统计摘要:")
    print(f"   • 扫描类型数: {report['summary']['total_types_scanned']}")
    print(f"   • 已存在配置: {report['summary']['existing_count']}")
    print(f"   • 总大小: {report['summary']['total_size_bytes'] / 1024:.1f} KB")

    print("\n📋 详细配置信息:")
    print("-" * 60)
    for config_type, info in report['configs'].items():
        status = "✅" if info['exists'] else "❌"
        size_str = f"{info['size_bytes'] / 1024:.1f} KB" if info['size_bytes'] > 0 else "-"
        print(f"{status} {config_type:<25} {size_str:>10}")

    # 显示书签
    bookmarks = scanner.read_bookmarks()
    print(f"\n📑 书签 ({bookmarks.count} 个):")
    if bookmarks.paths:
        for i, path in enumerate(bookmarks.paths[:10], 1):
            print(f"   {i}. {path}")
        if len(bookmarks.paths) > 10:
            print(f"   ... 还有 {len(bookmarks.paths) - 10} 个")
    else:
        print("   （无）")

    # 显示插件
    addons = scanner.list_addons()
    print(f"\n🔌 插件 ({len(addons)} 个):")
    if addons:
        for addon in addons[:15]:
            bl_ver = addon.bl_info.get('blender', '?') if addon.bl_info else '?'
            print(f"   • {addon.name:<30} [支持 Blender: {bl_ver}]")
        if len(addons) > 15:
            print(f"   ... 还有 {len(addons) - 15} 个")
    else:
        print("   （无）")


if __name__ == '__main__':
    main()
