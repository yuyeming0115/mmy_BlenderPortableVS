"""
Blender 配置备份与恢复引擎
负责配置文件的打包、压缩、导入和导出
"""

import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field


@dataclass
class BackupManifest:
    """备份清单"""
    version: str = "1.0"
    created_at: str = ""
    source_blender_version: str = ""
    source_config_path: str = ""
    files: List[Dict] = field(default_factory=list)
    total_size: int = 0
    checksum: str = ""


@dataclass
class BackupResult:
    """备份操作结果"""
    success: bool
    backup_path: str = ""
    manifest: Optional[BackupManifest] = None
    message: str = ""
    warnings: List[str] = field(default_factory=list)


@dataclass
class RestoreResult:
    """恢复操作结果"""
    success: bool
    restored_files: int = 0
    skipped_files: int = 0
    errors: List[str] = field(default_factory=list)
    rollback_available: bool = False
    backup_path: str = ""


class BackupEngine:
    """配置备份引擎"""

    BACKUP_DIR_NAME = "backups"
    MANIFEST_FILENAME = "manifest.json"

    # 需要备份的关键文件/目录
    BACKUP_TARGETS = {
        'config': [
            'userpref.blend',
            'startup.blend',
            'bookmarks.txt',
            'recent-files.txt',
        ],
        'scripts': {
            'addons': 'addons',
            'addons_contrib': 'addons_contrib',
            'startup': 'startup',
            'presets/keyconfig': 'presets/keyconfig',
        }
    }

    def __init__(self, output_base_dir: Path = None):
        """
        初始化备份引擎

        Args:
            output_base_dir: 备份输出基础目录，默认为当前工作目录下的 backups/
        """
        if output_base_dir is None:
            output_base_dir = Path.cwd() / self.BACKUP_DIR_NAME

        self.output_base = output_base_dir
        self.output_base.mkdir(parents=True, exist_ok=True)

    def create_backup(self, config_path: Path, blender_version: str,
                      include_addons: bool = True, compression: int = zipfile.ZIP_DEFLATED,
                      backup_type: str = "") -> BackupResult:
        """
        创建配置备份

        Args:
            config_path: Blender 配置目录路径
            blender_version: Blender 版本号
            include_addons: 是否包含插件
            compression: 压缩类型
            backup_type: 备份类型标记（'source' 或 'target'），用于文件名区分

        Returns:
            BackupResult: 备份结果
        """
        result = BackupResult(success=False)

        if not config_path.exists():
            result.message = f"❌ 配置路径不存在: {config_path}"
            return result

        # 优先从上级目录读取版本号（Blender标准目录结构）
        # 例如 config_path = ~/.config/blender/4.2/config，则上级目录是 4.2
        parent_dir = config_path.parent
        version_from_parent = parent_dir.name if parent_dir.name else ""
        
        # 检查上级目录名是否是有效版本号格式（如 4.2, 3.6, 4.2.1）
        is_valid_version = False
        if version_from_parent:
            parts = version_from_parent.replace('.', '').split()
            is_valid_version = parts[0].isdigit() and len(parts) >= 1
        
        # 决定使用的版本号：优先上级目录，否则用传入的版本号
        if is_valid_version and version_from_parent.replace('.', '').isdigit():
            final_version = version_from_parent
        else:
            final_version = blender_version
        
        # 解析版本号，只保留主版本和次版本（如 4.2.1 -> 4.2）
        version_parts = final_version.split('.')
        version_short = f"{version_parts[0]}.{version_parts[1]}" if len(version_parts) >= 2 else final_version
        
        # 创建文件名: Blender_X.X_Portable_YYYYMMDD.zip
        timestamp = datetime.now().strftime('%Y%m%d')
        backup_filename = f'Blender_{version_short}_Portable_{timestamp}.zip'
        backup_path = self.output_base / backup_filename

        try:
            manifest = BackupManifest(
                created_at=datetime.now().isoformat(),
                source_blender_version=blender_version,
                source_config_path=str(config_path)
            )

            with zipfile.ZipFile(backup_path, 'w', compression=compression) as zf:
                config_dir = config_path / 'config'
                scripts_dir = config_path / 'scripts'

                # 备份 config 目录下的关键文件
                for filename in self.BACKUP_TARGETS['config']:
                    file_path = config_dir / filename
                    if file_path.exists():
                        file_info = self._add_file_to_zip(zf, file_path, f'config/{filename}')
                        manifest.files.append(file_info)
                    else:
                        result.warnings.append(f"⚠️ 文件不存在: {filename}")

                # 备份 scripts 目录（如果需要）
                if include_addons and scripts_dir.exists():
                    for dir_name, relative_name in self.BACKUP_TARGETS['scripts'].items():
                        source_dir = scripts_dir / dir_name
                        if source_dir.exists():
                            added_files = self._add_directory_to_zip(
                                zf, source_dir, f'scripts/{relative_name}'
                            )
                            manifest.files.extend(added_files)

                # 计算总大小
                manifest.total_size = sum(f['size'] for f in manifest.files)

            # 写入清单文件
            manifest_data = json.dumps(asdict(manifest), indent=2, ensure_ascii=False)
            self._update_manifest_in_zip(backup_path, manifest_data)
            manifest.checksum = self._calculate_file_hash(backup_path)

            result.success = True
            result.backup_path = str(backup_path)
            result.manifest = manifest
            result.message = f"✅ 备份成功！共 {len(manifest.files)} 个文件，总计 {manifest.total_size / 1024:.1f} KB"

        except Exception as e:
            result.message = f"❌ 备份失败: {str(e)}"
            if backup_path.exists():
                backup_path.unlink()

        return result

    def _add_file_to_zip(self, zf: zipfile.ZipFile, file_path: Path, arcname: str) -> Dict:
        """添加单个文件到 ZIP"""
        stat = file_path.stat()
        zf.write(file_path, arcname)

        return {
            'path': arcname,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'type': 'file'
        }

    def _add_directory_to_zip(self, zf: zipfile.ZipFile, dir_path: Path, base_arcname: str) -> List[Dict]:
        """添加目录及其内容到 ZIP"""
        added_files = []

        for item in dir_path.rglob('*'):
            if item.is_file():
                rel_path = item.relative_to(dir_path)
                arcname = f'{base_arcname}/{rel_path}'
                added_files.append(self._add_file_to_zip(zf, item, arcname))

        return added_files

    def _update_manifest_in_zip(self, zip_path: Path, manifest_json: str):
        """更新 ZIP 文件中的清单"""
        temp_path = zip_path.with_suffix('.tmp.zip')

        with zipfile.ZipFile(zip_path, 'r') as zin:
            with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zout:
                zout.writestr(self.MANIFEST_FILENAME, manifest_json)
                for item in zin.infolist():
                    if item.filename != self.MANIFEST_FILENAME:
                        zout.writestr(item, zin.read(item.filename))

        temp_path.replace(zip_path)

    def restore_backup(self, backup_path: Path, target_config_path: Path,
                       overwrite: bool = False, create_backup_first: bool = True) -> RestoreResult:
        """
        从备份恢复配置

        Args:
            backup_path: 备份文件路径
            target_config_path: 目标配置目录
            overwrite: 是否覆盖已存在的文件
            create_backup_first: 是否在恢复前先备份目标

        Returns:
            RestoreResult: 恢复结果
        """
        result = RestoreResult(success=False)

        if not backup_path.exists():
            result.errors.append(f"❌ 备份文件不存在: {backup_path}")
            return result

        if not target_config_path.exists():
            target_config_path.mkdir(parents=True, exist_ok=True)

        try:
            # 可选：先备份现有配置
            if create_backup_first:
                pre_restore_backup = self._pre_restore_backup(target_config_path)
                if pre_restore_backup:
                    result.rollback_available = True
                    result.backup_path = pre_restore_backup

            # 读取清单
            manifest = self.read_manifest(backup_path)
            if not manifest:
                result.errors.append("❌ 无法读取备份清单")
                return result

            restored_count = 0
            skipped_count = 0

            with zipfile.ZipFile(backup_path, 'r') as zf:
                for file_info in zf.infolist():
                    if file_info.filename == self.MANIFEST_FILENAME:
                        continue

                    target_file = target_config_path / file_info.filename

                    # 检查是否覆盖
                    if target_file.exists() and not overwrite:
                        skipped_count += 1
                        continue

                    # 确保父目录存在
                    target_file.parent.mkdir(parents=True, exist_ok=True)

                    # 提取文件
                    zf.extract(file_info, target_config_path)
                    restored_count += 1

            result.success = True
            result.restored_files = restored_count
            result.skipped_files = skipped_count

        except Exception as e:
            result.errors.append(f"❌ 恢复失败: {str(e)}")

        return result

    def _pre_restore_backup(self, config_path: Path) -> Optional[str]:
        """恢复前自动备份"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pre_backup_filename = f'pre_restore_{timestamp}.zip'

            # 尝试检测版本号
            version = config_path.name if config_path.name else 'unknown'

            result = self.create_backup(
                config_path=config_path,
                blender_version=version,
                include_addons=True
            )

            if result.success:
                # 重命名备份文件
                new_path = self.output_base / pre_backup_filename
                Path(result.backup_path).rename(new_path)
                return str(new_path)

        except Exception:
            pass

        return None

    def read_manifest(self, backup_path: Path) -> Optional[BackupManifest]:
        """读取备份文件的清单"""
        try:
            with zipfile.ZipFile(backup_path, 'r') as zf:
                if self.MANIFEST_FILENAME not in zf.namelist():
                    return None

                manifest_data = zf.read(self.MANIFEST_FILENAME).decode('utf-8')
                data = json.loads(manifest_data)

                return BackupManifest(**data)
        except Exception:
            return None

    def list_backups(self) -> List[Dict]:
        """
        列出所有可用的备份

        Returns:
            List[Dict]: 备份信息列表
        """
        backups = []

        if not self.output_base.exists():
            return backups

        for backup_file in sorted(self.output_base.glob('*.zip'), reverse=True):
            manifest = self.read_manifest(backup_file)
            size_mb = backup_file.stat().st_size / (1024 * 1024)

            backup_info = {
                'filename': backup_file.name,
                'path': str(backup_file),
                'size_mb': round(size_mb, 2),
                'created_at': manifest.created_at if manifest else '未知',
                'blender_version': manifest.source_blender_version if manifest else '未知',
                'files_count': len(manifest.files) if manifest else 0,
            }

            backups.append(backup_info)

        return backups

    def delete_backup(self, backup_path: Path) -> bool:
        """删除指定的备份"""
        try:
            if backup_path.exists() and backup_path.suffix == '.zip':
                backup_path.unlink()
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def _calculate_file_hash(file_path: Path) -> str:
        """计算文件哈希值"""
        import hashlib
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()


def main():
    """测试用例"""
    from blender_config_sync.path_manager import BlenderPathManager

    print("=" * 70)
    print("🎨 Blender Config Sync - 备份引擎测试")
    print("=" * 70)

    manager = BlenderPathManager()
    versions = manager.detect_installed_versions()

    if not versions:
        print("\n❌ 未找到 Blender 安装")
        return

    latest = versions[0]
    print(f"\n📌 使用版本: Blender {latest.version}")
    print(f"📁 配置路径: {latest.config_path}\n")

    engine = BackupEngine()

    # 创建备份
    print("📦 正在创建备份...")
    result = engine.create_backup(
        config_path=latest.config_path,
        blender_version=latest.version,
        include_addons=True
    )

    print(f"\n{result.message}")

    if result.warnings:
        print("\n⚠️ 警告:")
        for warning in result.warnings:
            print(f"   • {warning}")

    if result.success:
        print(f"\n💾 备份文件位置: {result.backup_path}")
        print(f"📊 清单信息:")
        print(f"   • Blender 版本: {result.manifest.source_blender_version}")
        print(f"   • 创建时间: {result.manifest.created_at}")
        print(f"   • 文件数量: {len(result.manifest.files)}")
        print(f"   • 总大小: {result.manifest.total_size / 1024:.1f} KB")
        print(f"   • 校验和: {result.manifest.checksum[:16]}...")

        # 列出所有备份
        print("\n📋 所有备份记录:")
        backups = engine.list_backups()
        for i, backup in enumerate(backups[:5], 1):
            print(f"   {i}. {backup['filename']:<45} "
                  f"{backup['size_mb']:>6.2f} MB  "
                  f"{backup['created_at'][:16]}  "
                  f"Blender {backup['blender_version']}")


if __name__ == '__main__':
    main()
