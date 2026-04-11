"""
单元测试 - 备份引擎
"""

import pytest
import json
import zipfile
import tempfile
from pathlib import Path

from blender_config_sync.backup_engine import BackupEngine, BackupManifest


class TestBackupEngine:
    """备份引擎测试"""

    def setup_method(self):
        """创建临时目录结构模拟 Blender 配置"""
        self.temp_dir = Path(tempfile.mkdtemp())

        # 创建模拟的 Blender 配置目录
        config_dir = self.temp_dir / 'blender_4.2' / 'config'
        scripts_dir = self.temp_dir / 'blender_4.2' / 'scripts'

        config_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir.mkdir(parents=True, exist_ok=True)

        # 创建测试文件
        (config_dir / 'userpref.blend').write_bytes(b'userpref_test_data')
        (config_dir / 'bookmarks.txt').write_text('/test/path\n', encoding='utf-8')
        (config_dir / 'startup.blend').write_bytes(b'startup_test_data')

        # 创建测试插件
        addons_dir = scripts_dir / 'addons'
        addons_dir.mkdir(exist_ok=True)
        (addons_dir / 'my_plugin.py').write_text('# test plugin', encoding='utf-8')

        # 创建启动脚本
        startup_dir = scripts_dir / 'startup'
        startup_dir.mkdir(exist_ok=True)
        (startup_dir / 'auto_run.py').write_text('# auto run script', encoding='utf-8')

        self.config_path = self.temp_dir / 'blender_4.2'
        self.output_dir = self.temp_dir / 'backups'
        self.engine = BackupEngine(output_base_dir=self.output_dir)

    def test_create_backup_success(self):
        """测试成功创建备份"""
        result = self.engine.create_backup(
            config_path=self.config_path,
            blender_version='4.2',
            include_addons=True
        )

        assert result.success is True
        assert Path(result.backup_path).exists()
        assert result.manifest is not None
        assert len(result.manifest.files) > 0
        assert result.manifest.source_blender_version == '4.2'

    def test_backup_contains_manifest(self):
        """测试备份包含清单文件"""
        result = self.engine.create_backup(
            config_path=self.config_path,
            blender_version='4.2'
        )

        with zipfile.ZipFile(result.backup_path, 'r') as zf:
            assert 'manifest.json' in zf.namelist()

            manifest_data = json.loads(zf.read('manifest.json'))
            assert manifest_data['version'] == '1.0'
            assert manifest_data['source_blender_version'] == '4.2'

    def test_backup_contains_config_files(self):
        """测试备份包含配置文件"""
        result = self.engine.create_backup(
            config_path=self.config_path,
            blender_version='4.2'
        )

        with zipfile.ZipFile(result.backup_path, 'r') as zf:
            filenames = zf.namelist()
            assert any('userpref.blend' in f for f in filenames)
            assert any('bookmarks.txt' in f for f in filenames)

    def test_backup_includes_addons(self):
        """测试备份包含插件（当 include_addons=True）"""
        result = self.engine.create_backup(
            config_path=self.config_path,
            blender_version='4.2',
            include_addons=True
        )

        with zipfile.ZipFile(result.backup_path, 'r') as zf:
            filenames = zf.namelist()
            assert any('my_plugin.py' in f for f in filenames)

    def test_backup_excludes_addons(self):
        """测试备份不包含插件（当 include_addons=False）"""
        result = self.engine.create_backup(
            config_path=self.config_path,
            blender_version='4.2',
            include_addons=False
        )

        with zipfile.ZipFile(result.backup_path, 'r') as zf:
            filenames = zf.namelist()
            addon_files = [f for f in filenames if 'addons' in f]
            assert len(addon_files) == 0

    def test_read_manifest(self):
        """测试读取备份清单"""
        result = self.engine.create_backup(
            config_path=self.config_path,
            blender_version='4.2'
        )

        manifest = self.engine.read_manifest(Path(result.backup_path))

        assert manifest is not None
        assert isinstance(manifest, BackupManifest)
        assert manifest.source_blender_version == '4.2'
        assert len(manifest.files) > 0

    def test_restore_backup(self):
        """测试恢复备份"""
        # 创建备份
        backup_result = self.engine.create_backup(
            config_path=self.config_path,
            blender_version='4.2'
        )

        # 创建新的目标目录用于恢复
        restore_target = self.temp_dir / 'restore_target'
        restore_result = self.engine.restore_backup(
            backup_path=Path(backup_result.backup_path),
            target_config_path=restore_target,
            overwrite=True,
            create_backup_first=False
        )

        assert restore_result.success is True
        assert restore_result.restored_files > 0

        # 验证文件已恢复
        assert (restore_target / 'config' / 'userpref.blend').exists()
        assert (restore_target / 'config' / 'bookmarks.txt').exists()

    def test_list_backups(self):
        """测试列出所有备份"""
        import time

        # 清空现有备份以确保测试准确
        for existing in self.output_dir.glob('*.zip'):
            existing.unlink()

        # 创建两个备份，间隔1秒确保时间戳不同
        self.engine.create_backup(config_path=self.config_path, blender_version='4.2')
        time.sleep(1.1)  # 确保时间戳不同
        self.engine.create_backup(config_path=self.config_path, blender_version='4.2')

        backups = self.engine.list_backups()

        assert len(backups) == 2
        assert all('blender_config_' in b['filename'] for b in backups)

    def test_delete_backup(self):
        """测试删除备份"""
        result = self.engine.create_backup(
            config_path=self.config_path,
            blender_version='4.2'
        )
        backup_path = Path(result.backup_path)

        assert backup_path.exists()
        deleted = self.engine.delete_backup(backup_path)
        assert deleted is True
        assert not backup_path.exists()


class TestBackupEdgeCases:
    """备份边界情况测试"""

    def test_backup_nonexistent_path(self):
        """测试对不存在的路径进行备份"""
        engine = BackupEngine()
        result = engine.create_backup(
            config_path=Path('/nonexistent/path'),
            blender_version='9.9'
        )

        assert result.success is False
        assert '不存在' in result.message

    def test_restore_nonexistent_backup(self):
        """测试从不存在的备份文件恢复"""
        engine = BackupEngine()
        result = engine.restore_backup(
            backup_path=Path('/nonexistent/backup.zip'),
            target_config_path=Path(tempfile.mkdtemp())
        )

        assert result.success is False
        assert len(result.errors) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
