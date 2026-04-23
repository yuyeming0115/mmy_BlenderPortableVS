"""
用户设置管理器
负责保存和加载用户的配置路径等设置
"""

import json
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict, field


@dataclass
class SavedPath:
    """保存的路径信息"""
    path: str
    version: str
    path_type: str = "portable"  # portable 或 installed


@dataclass
class UserSettings:
    """用户设置"""
    last_source_path: str = ""
    last_source_version: str = ""
    last_target_path: str = ""
    last_target_version: str = ""
    saved_paths: List[Dict] = field(default_factory=list)
    last_source_index: int = 0
    last_target_index: int = 1 if True else 0


class SettingsManager:
    """用户设置管理器"""

    CONFIG_FILENAME = ".blender_config_sync.json"

    def __init__(self, config_dir: Path = None):
        """
        初始化设置管理器

        Args:
            config_dir: 配置文件目录，默认为用户主目录
        """
        if config_dir is None:
            config_dir = Path.home()

        self.config_path = config_dir / self.CONFIG_FILENAME
        self.settings = self._load_settings()

    def _load_settings(self) -> UserSettings:
        """从文件加载设置"""
        if not self.config_path.exists():
            return UserSettings()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return UserSettings(**data)
        except Exception:
            return UserSettings()

    def save_settings(self):
        """保存设置到文件"""
        try:
            data = asdict(self.settings)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ 保存设置失败: {e}")

    def update_last_paths(
        self,
        source_path: str = None,
        source_version: str = None,
        target_path: str = None,
        target_version: str = None,
        source_index: int = None,
        target_index: int = None
    ):
        """更新上次使用的路径"""
        if source_path:
            self.settings.last_source_path = source_path
        if source_version:
            self.settings.last_source_version = source_version
        if target_path:
            self.settings.last_target_path = target_path
        if target_version:
            self.settings.last_target_version = target_version
        if source_index is not None:
            self.settings.last_source_index = source_index
        if target_index is not None:
            self.settings.last_target_index = target_index

        self.save_settings()

    def add_saved_path(self, path: str, version: str, path_type: str = "portable"):
        """添加一个保存的路径"""
        # 检查是否已存在
        for saved in self.settings.saved_paths:
            if saved['path'] == path:
                # 更新版本信息
                saved['version'] = version
                saved['path_type'] = path_type
                self.save_settings()
                return

        # 新增路径
        self.settings.saved_paths.append({
            'path': path,
            'version': version,
            'path_type': path_type
        })

        # 限制保存数量（最多10个）
        if len(self.settings.saved_paths) > 10:
            self.settings.saved_paths = self.settings.saved_paths[-10:]

        self.save_settings()

    def get_saved_paths(self) -> List[SavedPath]:
        """获取所有保存的路径"""
        return [SavedPath(**p) for p in self.settings.saved_paths]

    def get_last_source(self) -> Optional[SavedPath]:
        """获取上次使用的源路径"""
        if self.settings.last_source_path:
            return SavedPath(
                path=self.settings.last_source_path,
                version=self.settings.last_source_version,
                path_type="portable"
            )
        return None

    def get_last_target(self) -> Optional[SavedPath]:
        """获取上次使用的目标路径"""
        if self.settings.last_target_path:
            return SavedPath(
                path=self.settings.last_target_path,
                version=self.settings.last_target_version,
                path_type="portable"
            )
        return None

    def clear_saved_paths(self):
        """清除所有保存的路径"""
        self.settings.saved_paths = []
        self.settings.last_source_path = ""
        self.settings.last_source_version = ""
        self.settings.last_target_path = ""
        self.settings.last_target_version = ""
        self.save_settings()


if __name__ == '__main__':
    # 测试
    manager = SettingsManager()

    print(f"配置文件位置: {manager.config_path}")
    print(f"上次源路径: {manager.get_last_source()}")
    print(f"上次目标路径: {manager.get_last_target()}")
    print(f"保存的路径列表: {manager.get_saved_paths()}")