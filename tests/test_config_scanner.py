"""
单元测试 - 配置扫描器
"""

import pytest
import tempfile
from pathlib import Path

from blender_config_sync.config_scanner import ConfigScanner, BookmarksData


class TestConfigScanner:
    """配置扫描器测试"""

    def setup_method(self):
        """每个测试方法前执行：创建临时配置目录"""
        self.temp_dir = Path(tempfile.mkdtemp())
        config_dir = self.temp_dir / 'config'
        scripts_dir = self.temp_dir / 'scripts'
        config_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir.mkdir(parents=True, exist_ok=True)

        # 创建测试文件
        (config_dir / 'userpref.blend').write_bytes(b'test_userpref_data')
        (config_dir / 'bookmarks.txt').write_text(
            '/Projects/3D\n/Textures\n/Assets\n',
            encoding='utf-8'
        )

        addons_dir = scripts_dir / 'addons'
        addons_dir.mkdir(exist_ok=True)
        test_addon = addons_dir / 'test_addon.py'
        test_addon.write_text(
            'bl_info = {\n'
            '    "name": "Test Addon",\n'
            '    "blender": (3.0, 0),\n'
            '    "category": "Test"\n'
            '}\n',
            encoding='utf-8'
        )

        self.scanner = ConfigScanner(self.temp_dir)

    def test_scan_all_configs(self):
        """测试扫描所有配置"""
        report = self.scanner.scan_all_configs()

        assert report['scan_time'] is not None
        assert report['summary']['existing_count'] >= 2
        assert 'userpref_blend' in report['configs']
        assert 'bookmarks_txt' in report['configs']

    def test_scan_existing_file(self):
        """测试扫描已存在的文件"""
        info = self.scanner.scan_config('userpref_blend')

        assert info.exists is True
        assert info.size_bytes > 0
        assert info.sha256_hash is not None
        assert info.modified_time is not None

    def test_scan_nonexistent_file(self):
        """测试扫描不存在的文件"""
        info = self.scanner.scan_config('startup_blend')

        assert info.exists is False
        assert info.size_bytes == 0

    def test_read_bookmarks(self):
        """测试读取书签"""
        bookmarks = self.scanner.read_bookmarks()

        assert isinstance(bookmarks, BookmarksData)
        assert bookmarks.count == 3
        assert '/Projects/3D' in bookmarks.paths
        assert '/Textures' in bookmarks.paths

    def test_write_bookmarks(self):
        """测试写入书签"""
        new_bookmarks = ['/New/Path1', '/New/Path2']
        success = self.scanner.write_bookmarks(new_bookmarks)

        assert success is True

        read_back = self.scanner.read_bookmarks()
        assert read_back.count == 2
        assert '/New/Path1' in read_back.paths

    def test_list_addons(self):
        """测试列出插件"""
        addons = self.scanner.list_addons()

        assert len(addons) == 1
        assert addons[0].name == 'test_addon'
        assert addons[0].bl_info is not None
        assert addons[0].bl_info['name'] == 'Test Addon'

    def test_export_report(self):
        """测试导出报告"""
        output_path = self.temp_dir / 'test_report.json'
        result_path = self.scanner.export_scan_report(output_path)

        assert Path(result_path).exists()

        import json
        with open(result_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert 'configs' in data
        assert 'bookmarks' in data
        assert 'addons' in data


class TestBookmarksEdgeCases:
    """书签边界情况测试"""

    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        config_dir = self.temp_dir / 'config'
        config_dir.mkdir(exist_ok=True)
        self.scanner = ConfigScanner(self.temp_dir)

    def test_empty_bookmarks(self):
        """测试空书签文件"""
        (self.temp_dir / 'config' / 'bookmarks.txt').write_text('', encoding='utf-8')
        bookmarks = self.scanner.read_bookmarks()
        assert bookmarks.count == 0
        assert len(bookmarks.paths) == 0

    def test_no_bookmarks_file(self):
        """测试无书签文件"""
        bookmarks = self.scanner.read_bookmarks()
        assert bookmarks.count == 0

    def test_bookmarks_with_comments(self):
        """测试包含注释的书签"""
        (self.temp_dir / 'config' / 'bookmarks.txt').write_text(
            '# This is a comment\n/Valid/Path\n# Another comment\n/Another/Path\n',
            encoding='utf-8'
        )
        bookmarks = self.scanner.read_bookmarks()
        assert bookmarks.count == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
