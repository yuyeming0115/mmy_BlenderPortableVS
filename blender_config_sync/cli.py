"""
Blender 配置同步工具 - 主程序入口
提供命令行界面和基本功能调用
"""

import argparse
import sys
from pathlib import Path

from blender_config_sync.path_manager import BlenderPathManager, BlenderInstallation
from blender_config_sync.config_scanner import ConfigScanner
from blender_config_sync.backup_engine import BackupEngine


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


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        prog='blender-config-sync',
        description='Blender 配置同步工具 - 跨版本配置备份、恢复与管理',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s scan              # 扫描最新版本的配置
  %(prog)s scan -v 4.2       # 扫描 Blender 4.2 的配置
  %(prog)s backup            # 备份最新版本配置
  %(prog)s backup --no-addons  # 备份但不包含插件
  %(prog)s list              # 列出所有备份
  %(prog)s versions          # 显示已安装的 Blender 版本
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

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

    # list 子命令
    subparsers.add_parser('list', help='列出所有备份')

    # versions 子命令
    subparsers.add_parser('versions', help='列出已安装的 Blender 版本')

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        'scan': cmd_scan,
        'backup': cmd_backup,
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
