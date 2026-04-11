"""
单元测试 - 差异比较引擎
"""

import pytest
import tempfile
from pathlib import Path

from blender_config_sync.diff_engine import (
    DiffEngine, DiffType, SyncAction, ComparisonResult,
    DiffItem, generate_text_report
)
from blender_config_sync.config_scanner import ConfigScanner


class TestDiffEngine:
    """差异引擎核心功能测试"""

    def setup_method(self):
        """创建两个模拟的 Blender 配置目录用于比较"""
        self.temp_dir = Path(tempfile.mkdtemp())

        # 源配置（Blender 4.2）
        self.source_dir = self.temp_dir / 'blender_4.2'
        source_config = self.source_dir / 'config'
        source_scripts = self.source_dir / 'scripts'
        source_config.mkdir(parents=True, exist_ok=True)
        source_scripts.mkdir(parents=True, exist_ok=True)

        # 目标配置（Blender 3.6）
        self.target_dir = self.temp_dir / 'blender_3.6'
        target_config = self.target_dir / 'config'
        target_scripts = self.target_dir / 'scripts'
        target_config.mkdir(parents=True, exist_ok=True)
        target_scripts.mkdir(parents=True, exist_ok=True)

        # 设置源配置
        (source_config / 'userpref.blend').write_bytes(b'source_userpref')
        (source_config / 'bookmarks.txt').write_text(
            '/Source/Path1\n/Source/Path2\n/Common/Path\n',
            encoding='utf-8'
        )

        # 设置目标配置
        (target_config / 'userpref.blend').write_bytes(b'target_userpref')
        (target_config / 'bookmarks.txt').write_text(
            '/Target/PathA\n/Common/Path\n',
            encoding='utf-8'
        )

        # 源端插件
        source_addons = source_scripts / 'addons'
        source_addons.mkdir(exist_ok=True)
        (source_addons / 'addon_source_only.py').write_text(
            'bl_info = {"name": "Addon Source", "blender": (4.0, 0)}\n',
            encoding='utf-8'
        )
        (source_addons / 'addon_common.py').write_text(
            'bl_info = {"name": "Addon Common", "blender": (3.0, 0)}\n',
            encoding='utf-8'
        )

        # 目标端插件
        target_addons = target_scripts / 'addons'
        target_addons.mkdir(exist_ok=True)
        (target_addons / 'addon_target_only.py').write_text(
            'bl_info = {"name": "Addon Target", "blender": (3.0, 0)}\n',
            encoding='utf-8'
        )
        (target_addons / 'addon_common.py').write_text(
            'bl_info = {"name": "Addon Common", "blender": (3.0, 0)}\n',
            encoding='utf-8'
        )

        # 源端启动脚本
        source_startup = source_scripts / 'startup'
        source_startup.mkdir(exist_ok=True)
        (source_startup / 'auto_source.py').write_text('# source startup', encoding='utf-8')

        # 目标端启动脚本
        target_startup = target_scripts / 'startup'
        target_startup.mkdir(exist_ok=True)
        (target_startup / 'auto_target.py').write_text('# target startup', encoding='utf-8')

        self.engine = DiffEngine()

    def test_compare_basic(self):
        """测试基本比较功能"""
        result = self.engine.compare(
            source_path=self.source_dir,
            target_path=self.target_dir,
            source_version='4.2',
            target_version='3.6'
        )

        assert isinstance(result, ComparisonResult)
        assert result.source_version == '4.2'
        assert result.target_version == '3.6'
        assert result.total_items > 0
        assert len(result.diff_items) > 0

    def test_bookmark_comparison(self):
        """测试书签比较"""
        result = self.engine.compare(
            source_path=self.source_dir,
            target_path=self.target_dir
        )

        bookmark_diffs = result.get_items_by_category('bookmarks')
        assert len(bookmark_diffs) > 0

        # 应该有仅源端的书签
        only_source = [d for d in bookmark_diffs if d.diff_type == DiffType.ONLY_IN_SOURCE]
        assert len(only_source) > 0
        assert any('/Source/Path1' in d.name or '/Source/Path2' in d.name for d in only_source)

        # 应该有仅目标端的书签
        only_target = [d for d in bookmark_diffs if d.diff_type == DiffType.ONLY_IN_TARGET]
        assert len(only_target) > 0
        assert any('/Target/PathA' in d.name for d in only_target)

        # 应该有共同的书签
        identical = [d for d in bookmark_diffs if d.diff_type == DiffType.IDENTICAL]
        assert any(d.name == '/Common/Path' for d in identical)

    def test_addon_comparison(self):
        """测试插件比较"""
        result = self.engine.compare(
            source_path=self.source_dir,
            target_path=self.target_dir
        )

        addon_diffs = result.get_items_by_category('addons')
        assert len(addon_diffs) > 0

        # 仅源端的插件
        only_source = [d for d in addon_diffs if d.diff_type == DiffType.ONLY_IN_SOURCE]
        assert any(d.name == 'addon_source_only' for d in only_source)

        # 仅目标端的插件
        only_target = [d for d in addon_diffs if d.diff_type == DiffType.ONLY_IN_TARGET]
        assert any(d.name == 'addon_target_only' for d in only_target)

        # 共同的插件
        common = [d for d in addon_diffs if d.diff_type == DiffType.IDENTICAL]
        assert any(d.name == 'addon_common' for d in common)

    def test_config_file_comparison(self):
        """测试配置文件比较"""
        result = self.engine.compare(
            source_path=self.source_dir,
            target_path=self.target_dir
        )

        pref_diffs = result.get_items_by_category('preferences')
        assert len(pref_diffs) > 0

        # userpref.blend 应该不同（内容不同）
        modified = [d for d in pref_diffs if d.item_type == 'config_file' and d.diff_type == DiffType.MODIFIED]
        assert len(modified) > 0

    def test_stats(self):
        """测试统计信息"""
        result = self.engine.compare(
            source_path=self.source_dir,
            target_path=self.target_dir
        )

        stats = result.get_stats()
        assert 'only_in_source' in stats
        assert 'only_in_target' in stats
        assert 'modified' in stats
        assert 'identical' in stats

        # 验证统计总数正确
        total_from_stats = sum(stats.values())
        assert total_from_stats == result.total_items

    def test_summary_generation(self):
        """测试摘要生成"""
        result = self.engine.compare(
            source_path=self.source_dir,
            target_path=self.target_dir
        )

        assert 'stats' in result.summary
        assert 'categories' in result.summary
        assert 'risk_assessment' in result.summary
        assert 'recommendations' in result.summary

        risk = result.summary['risk_assessment']
        assert 'level' in risk
        assert 'message' in risk
        assert risk['level'] in ['low', 'medium', 'high']

        recommendations = result.summary['recommendations']
        assert isinstance(recommendations, list)


class TestTextReportGeneration:
    """文本报告生成测试"""

    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        source_dir = self.temp_dir / 'source'
        target_dir = self.temp_dir / 'target'

        for d in [source_dir / 'config', source_dir / 'scripts', target_dir / 'config']:
            d.mkdir(parents=True, exist_ok=True)

        (source_dir / 'config' / 'bookmarks.txt').write_text('/test/path\n', encoding='utf-8')
        (target_dir / 'config' / 'bookmarks.txt').write_text('/other/path\n', encoding='utf-8')

        engine = DiffEngine()
        self.result = engine.compare(source_path=source_dir, target_path=target_dir)

    def test_generate_text_report(self):
        """测试文本报告生成"""
        report = generate_text_report(self.result)

        assert isinstance(report, str)
        assert len(report) > 0
        assert 'Blender 配置差异比较报告' in report
        assert '差异统计' in report
        assert '风险评估' in report

    def test_report_contains_data(self):
        """测试报告包含实际数据"""
        report = generate_text_report(self.result)

        assert str(self.result.total_items) in report or '项' in report


class TestDiffEngineEdgeCases:
    """边界情况测试"""

    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.engine = DiffEngine()

    def test_empty_directories(self):
        """测试空目录比较"""
        source = self.temp_dir / 'empty_src'
        target = self.temp_dir / 'empty_tgt'
        source.mkdir()
        target.mkdir()

        result = self.engine.compare(
            source_path=source,
            target_path=target,
            source_version='1.0',
            target_version='2.0'
        )

        assert result.total_items >= 0  # 可能为0或只有配置文件检查结果

    def test_identical_configs(self):
        """测试完全相同的配置"""
        config_dir = self.temp_dir / 'same_config'
        source = self.temp_dir / 'src'
        target = self.temp_dir / 'tgt'

        for base in [source, target]:
            (base / 'config').mkdir(parents=True)
            (base / 'config' / 'bookmarks.txt').write_text('/same/path\n', encoding='utf-8')

        result = self.engine.compare(source_path=source, target_path=target)

        bookmarks = result.get_items_by_category('bookmarks')
        identical_count = sum(1 for b in bookmarks if b.diff_type == DiffType.IDENTICAL)
        assert identical_count > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
