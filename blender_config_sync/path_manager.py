"""
Blender 配置路径管理器
负责检测和定位不同操作系统中 Blender 的配置目录
"""

import os
import sys
import platform
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class BlenderInstallation:
    """Blender 安装信息"""
    version: str
    config_path: Path
    executable_path: Optional[Path] = None
    is_portable: bool = False


class BlenderPathManager:
    """Blender 路径检测与管理"""

    # 支持的最低 Blender 版本（主版本号）
    MIN_SUPPORTED_VERSION = 2.80

    # 常见的 Blender 可执行文件名
    EXECUTABLE_NAMES = {
        'Windows': ['blender.exe'],
        'Darwin': ['Blender', 'blender'],
        'Linux': ['blender']
    }

    def __init__(self):
        self.system = platform.system()
        self.home = Path.home()

    def get_user_config_base(self) -> Path:
        """
        获取用户配置基础目录

        Returns:
            Path: 系统特定的 Blender 用户配置基础路径
        """
        if self.system == 'Windows':
            base = Path(os.environ.get('APPDATA', '')) / 'Blender Foundation' / 'Blender'
        elif self.system == 'Darwin':  # macOS
            base = self.home / 'Library' / 'Application Support' / 'Blender'
        elif self.system == 'Linux':
            xdg_config = os.environ.get('XDG_CONFIG_HOME', '')
            if xdg_config:
                base = Path(xdg_config) / 'blender'
            else:
                base = self.home / '.config' / 'blender'
        else:
            raise NotImplementedError(f"不支持的操作系统: {self.system}")

        return base

    def detect_installed_versions(self) -> List[BlenderInstallation]:
        """
        检测系统上已安装的所有 Blender 版本

        Returns:
            List[BlenderInstallation]: 检测到的 Blender 版本列表
        """
        installations = []
        config_base = self.get_user_config_base()

        if not config_base.exists():
            return installations

        for version_dir in config_base.iterdir():
            if not version_dir.is_dir():
                continue

            # 尝试解析版本号
            version_str = version_dir.name
            if not self._is_valid_version(version_str):
                continue

            installation = BlenderInstallation(
                version=version_str,
                config_path=version_dir,
                is_portable=self._is_portable_installation(version_dir)
            )

            # 尝试查找可执行文件
            installation.executable_path = self._find_executable(version_str)

            installations.append(installation)

        # 按版本号排序（从新到旧）
        installations.sort(key=lambda x: self._parse_version(x.version), reverse=True)
        return installations

    def _is_valid_version(self, version_str: str) -> bool:
        """
        验证版本字符串是否有效

        Args:
            version_str: 版本字符串（如 "4.2", "3.6.1"）

        Returns:
            bool: 是否为有效的 Blender 版本格式
        """
        try:
            parts = version_str.split('.')
            if len(parts) < 2 or len(parts) > 3:
                return False

            major = int(parts[0])
            minor = int(parts[1])

            # Blender 2.8+ 才使用新的配置系统
            if major < 2 or (major == 2 and minor < 8):
                return False

            return True
        except ValueError:
            return False

    def _parse_version(self, version_str: str) -> tuple:
        """解析版本号为元组，用于排序"""
        parts = version_str.split('.')
        return tuple(int(p) for p in parts)

    def _is_portable_installation(self, config_path: Path) -> bool:
        """检查是否为便携式安装"""
        portable_marker = config_path.parent / 'portable'
        return portable_marker.exists()

    def _find_executable(self, version: str) -> Optional[Path]:
        """
        查找指定版本的 Blender 可执行文件

        Args:
            version: Blender 版本号

        Returns:
            Optional[Path]: 可执行文件路径，如果未找到则返回 None
        """
        common_paths = []

        if self.system == 'Windows':
            # Windows 常见安装位置
            program_files = [
                Path(os.environ.get('ProgramFiles', 'C:\\Program Files')),
                Path(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')),
                Path(os.environ.get('LOCALAPPDATA', '')),
            ]
            for pf in program_files:
                common_paths.append(pf / 'Blender Foundation' / f'Blender {version}' / 'blender.exe')

        elif self.system == 'Darwin':
            # macOS 常见安装位置
            common_paths.extend([
                Path('/Applications') / f'Blender.app' / 'Contents' / 'MacOS' / 'Blender',
                self.home / 'Applications' / f'Blender.app' / 'Contents' / 'MacOS' / 'Blender',
            ])

        elif self.system == 'Linux':
            # Linux 常见安装位置
            common_paths.extend([
                Path('/usr/bin') / 'blender',
                Path('/opt') / 'blender' / f'{version}' / 'blender',
                Path('/usr/local/bin') / 'blender',
            ])

        for path in common_paths:
            if path.exists() and path.is_file():
                return path

        return None

    def get_config_files(self, installation: BlenderInstallation) -> Dict[str, Path]:
        """
        获取指定 Blender 版本的关键配置文件列表

        Args:
            installation: Blender 安装信息

        Returns:
            Dict[str, Path]: 配置文件类型到路径的映射
        """
        config_dir = installation.config_path / 'config'
        scripts_dir = installation.config_path / 'scripts'

        config_files = {
            # 核心配置文件
            'userpref_blend': config_dir / 'userpref.blend',
            'startup_blend': config_dir / 'startup.blend',
            'bookmarks_txt': config_dir / 'bookmarks.txt',
            'recent_files_txt': config_dir / 'recent-files.txt',

            # 插件相关
            'addons_dir': scripts_dir / 'addons',
            'addons_contrib_dir': scripts_dir / 'addons_contrib',
            'startup_scripts_dir': scripts_dir / 'startup',

            # 快捷键预设
            'keyconfig_presets': scripts_dir / 'presets' / 'keyconfig',

            # 数据文件
            'datafiles_dir': installation.config_path / 'datafiles',

            # 扩展（Blender 4.2+）
            'extensions_dir': installation.config_path / 'extensions',
        }

        return config_files

    def get_version_info(self, version: str) -> Dict:
        """
        获取特定版本的详细信息

        Args:
            version: Blender 版本号

        Returns:
            Dict: 包含版本详细信息的字典
        """
        config_base = self.get_user_config_base()
        version_path = config_base / version

        if not version_path.exists():
            raise ValueError(f"未找到 Blender {version} 的配置目录")

        config_files = self.get_config_files(BlenderInstallation(
            version=version,
            config_path=version_path
        ))

        info = {
            'version': version,
            'config_path': str(version_path),
            'has_userpref': config_files['userpref_blend'].exists(),
            'has_bookmarks': config_files['bookmarks_txt'].exists(),
            'addon_count': len(list(config_files['addons_dir'].glob('*.py'))) if config_files['addons_dir'].exists() else 0,
            'startup_script_count': len(list(config_files['startup_scripts_dir'].glob('*.py'))) if config_files['startup_scripts_dir'].exists() else 0,
        }

        return info

    def print_installed_versions_summary(self):
        """打印已安装版本的摘要信息"""
        versions = self.detect_installed_versions()

        if not versions:
            print("⚠️  未检测到任何 Blender 安装")
            return

        print(f"\n🎨 检测到 {len(versions)} 个 Blender 版本：\n")
        print("-" * 60)
        print(f"{'版本':<12} {'配置路径':<45} {'状态'}")
        print("-" * 60)

        for inst in versions:
            status = "✅ 完整" if (inst.config_path / 'config').exists() else "⚠️  不完整"
            executable = "📦" if inst.executable_path else ""
            print(f"{inst.version:<12} {str(inst.config_path):<45} {status} {executable}")

        print("-" * 60)


if __name__ == '__main__':
    manager = BlenderPathManager()
    manager.print_installed_versions_summary()
