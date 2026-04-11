"""
Blender 配置同步工具 - 主程序入口
提供命令行界面和基本功能调用
"""

import argparse
import sys
import json
from pathlib import Path

from blender_config_sync.path_manager import BlenderPathManager, BlenderInstallation
from blender_config_sync.config_scanner import ConfigScanner
from blender_config_sync.backup_engine import BackupEngine
from blender_config_sync.diff_engine import DiffEngine, generate_text_report


def cmd_scan(args):
    """扫描命令：扫描指定或最新的 Blender 配置"""
    manager = BlenderPathManager()

    if args.version:
        installations = [inst for inst in manager.detect_installed_versions()
                         if inst.version == args.version]
        if not installations:
            print(f"❌ 未找到 Blender {args.version}")
            sys.exit(1)
        installation = installations[0]
    else:
        versions = manager.detect_installed_versions()
        if not versions:
            print("❌ 未检测到任何 Blender 安装")
            sys.exit(1)
        installation = versions[0]

    print(f"\n🔍 扫描 Blender {installation.version} 配置...\n")
    scanner = ConfigScanner(installation.config_path)

    if args.export:
        report_path = scanner.export_scan_report(Path(args.export))
        print(f"✅ 报告已导出: {report_path}")
    else:
        report = scanner.scan_all_configs()
        print(json.dumps(report, indent=2, ensure_ascii=False))


def cmd_backup(args):
    """备份命令：创建配置备份"""
    manager = BlenderPathManager()

    if args.version:
        installations = [inst for inst in manager.detect_installed_versions()
                         if inst.version == args.version]
        if not installations:
            print(f"❌ 未找到 Blender {args.version}")
            sys.exit(1)
        installation = installations[0]
    else:
        versions = manager.detect_installed_versions()
        if not versions:
            print("❌ 未检测到任何 Blender 安装")
            sys.exit(1)
        installation = versions[0]

    engine = BackupEngine()
    result = engine.create_backup(
        config_path=installation.config_path,
        blender_version=installation.version,
        include_addons=not args.no_addons
    )

    print(result.message)

    if result.warnings:
        for w in result.warnings:
            print(w)


def cmd_list(args):
    """列出命令：显示所有备份"""
    engine = BackupEngine()
    backups = engine.list_backups()

    if not backups:
        print("📭 没有找到备份记录")
        return

    print(f"\n📋 共 {len(backups)} 个备份:\n")
    print("-" * 80)
    print(f"{'文件名':<50} {'大小':>8} {'版本':>8} {'时间'}")
    print("-" * 80)

    for backup in backups[:20]:
        print(f"{backup['filename']:<50} "
              f"{backup['size_mb']:>6.2f}MB "
              f"{backup['blender_version']:>8} "
              f"{backup['created_at'][:19]}")


def cmd_versions(args):
    """版本命令：列出已安装的 Blender 版本"""
    manager = BlenderPathManager()
    manager.print_installed_versions_summary()


def cmd_compare(args):
    """比较命令：比较两个版本的配置差异"""
    manager = BlenderPathManager()
    installations = manager.detect_installed_versions()

    if len(installations) < 2:
        print("❌ 至少需要检测到 2 个 Blender 版本才能进行比较")
        sys.exit(1)

    source_ver = args.source or installations[0].version
    target_ver = args.target or (installations[1].version if len(installations) > 1 else None)

    if not target_ver or source_ver == target_ver:
        print("❌ 请指定不同的源版本和目标版本")
        sys.exit(1)

    source_inst = next((i for i in installations if i.version == source_ver), None)
    target_inst = next((i for i in installations if i.version == target_ver), None)

    if not source_inst or not target_inst:
        print(f"❌ 未找到指定的版本（源: {source_ver}, 目标: {target_ver}）")
        sys.exit(1)

    print(f"\n⚖️ 正在比较配置差异...")
    print(f"   源版本: Blender {source_ver}")
    print(f"   目标版本: Blender {target_ver}\n")

    diff_engine = DiffEngine()
    result = diff_engine.compare(
        source_path=source_inst.config_path,
        target_path=target_inst.config_path,
        source_version=source_ver,
        target_version=target_ver
    )

    # 显示文本报告
    text_report = generate_text_report(result)
    print(text_report)

    # 可选：导出 JSON 报告
    if args.export:
        export_path = Path(args.export)
        output = diff_engine.export_comparison_report(result, export_path)
        print(f"\n✅ 详细报告已导出: {output}")


def cmd_gui(args):
    """GUI 命令：启动图形界面"""
    try:
        from blender_config_sync.gui import BlenderConfigSyncApp
        app = BlenderConfigSyncApp()
        app.run()
    except ImportError as e:
        print(f"❌ 无法启动 GUI: {e}")
        print("   请确保已安装 Tkinter（通常随 Python 一起安装）")
        sys.exit(1)
    except Exception as e:
        print(f"❌ GUI 启动失败: {e}")
        sys.exit(1)


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        prog='blender-config-sync',
        description='Blender 配置同步工具 - 跨版本配置备份、恢复与管理',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s gui               # 启动图形界面（推荐）
  %(prog)s scan              # 扫描最新版本的配置
  %(prog)s scan -v 4.2       # 扫描 Blender 4.2 的配置
  %(prog)s backup            # 备份最新版本配置
  %(prog)s backup --no-addons  # 备份但不包含插件
  %(prog)s compare --source 4.2 --target 3.6  # 比较两个版本
  %(prog)s list              # 列出所有备份
  %(prog)s versions          # 显示已安装的 Blender 版本
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # GUI 子命令
    subparsers.add_parser('gui', help='启动图形用户界面')

    # scan 子命令
    scan_parser = subparsers.add_parser('scan', help='扫描 Blender 配置')
    scan_parser.add_argument('-v', '--version', help='指定 Blender 版本')
    scan_parser.add_argument('-e', '--export', metavar='FILE',
                             help='导出报告到 JSON 文件')

    # backup 子命令
    backup_parser = subparsers.add_parser('backup', help='创建配置备份')
    backup_parser.add_argument('-v', '--version', help='指定 Blender 版本')
    backup_parser.add_argument('--no-addons', action='store_true',
                               help='不包含插件文件')

    # compare 子命令
    compare_parser = subparsers.add_parser('compare', help='比较两个版本的配置差异')
    compare_parser.add_argument('--source', '-s', metavar='VERSION',
                               help='源 Blender 版本号')
    compare_parser.add_argument('--target', '-t', metavar='VERSION',
                               help='目标 Blender 版本号')
    compare_parser.add_argument('-e', '--export', metavar='FILE',
                               help='导出详细报告到 JSON 文件')

    # list 子命令
    subparsers.add_parser('list', help='列出所有备份')

    # versions 子命令
    subparsers.add_parser('versions', help='列出已安装的 Blender 版本')

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        'gui': cmd_gui,
        'scan': cmd_scan,
        'backup': cmd_backup,
        'compare': cmd_compare,
        'list': cmd_list,
        'versions': cmd_versions,
    }

    command_func = commands.get(args.command)
    if command_func:
        command_func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
