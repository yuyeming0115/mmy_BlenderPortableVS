#!/usr/bin/env python3
"""
Blender Config Sync - 交互式终端界面 (TUI)
当 GUI 无法正常工作时使用的替代方案
提供友好的命令行交互体验
"""

import sys
from pathlib import Path


def print_header(title: str):
    """打印标题"""
    width = 70
    print("\n" + "=" * width)
    print(f" {title:^{width-2}} ")
    print("=" * width + "\n")


def print_menu(options: list, title: str = "主菜单"):
    """打印菜单选项"""
    print(f"📋 {title}\n")
    for i, option in enumerate(options, 1):
        print(f"  [{i}] {option}")
    print(f"\n  [0] 返回/退出")
    print()


def get_choice(max_option: int) -> int:
    """获取用户选择"""
    while True:
        try:
            choice = input("请输入选择: ").strip()
            if choice == '0':
                return 0
            num = int(choice)
            if 1 <= num <= max_option:
                return num
            print(f"❌ 请输入 0-{max_option} 之间的数字")
        except ValueError:
            print("❌ 请输入有效的数字")


def show_versions():
    """显示已安装的 Blender 版本"""
    from blender_config_sync.path_manager import BlenderPathManager
    
    print_header("🎨 已安装的 Blender 版本")
    
    manager = BlenderPathManager()
    versions = manager.detect_installed_versions()
    
    if not versions:
        print("⚠️  未检测到任何 Blender 安装！\n")
        print("可能的原因:")
        print("  • Blender 未安装")
        print("  • Blender 未在标准路径下")
        print("  • 从未保存过用户设置（Edit → Preferences → Save Preferences）")
        return
    
    print(f"✅ 检测到 {len(versions)} 个版本:\n")
    print("-" * 60)
    print(f"{'序号':<6}{'版本':<12}{'配置路径':<42}")
    print("-" * 60)
    
    for i, inst in enumerate(versions, 1):
        status = "✅ 完整" if (inst.config_path / 'config').exists() else "⚠️ 不完整"
        print(f"{i:<6}{inst.version:<12}{str(inst.config_path):<40}{status}")
    
    print("-" * 60)
    
    # 返回版本列表供后续使用
    return versions


def scan_config():
    """扫描指定版本的配置"""
    from blender_config_sync.path_manager import BlenderPathManager
    from blender_config_sync.config_scanner import ConfigScanner
    
    print_header("🔍 配置扫描器")
    
    manager = BlenderPathManager()
    versions = manager.detect_installed_versions()
    
    if not versions:
        print("❌ 没有可用的 Blender 版本")
        input("\n按回车键继续...")
        return
    
    # 让用户选择版本
    print("请选择要扫描的版本:\n")
    for i, v in enumerate(versions, 1):
        print(f"  [{i}] Blender {v.version}")
    
    choice = get_choice(len(versions))
    if choice == 0:
        return
    
    selected = versions[choice - 1]
    
    print(f"\n🔍 正在扫描 Blender {selected.version} 的配置...\n")
    
    scanner = ConfigScanner(selected.config_path)
    report = scanner.scan_all_configs()
    
    # 显示结果
    print("=" * 60)
    print(f"📊 扫描报告 - Blender {selected.version}")
    print("=" * 60)
    print(f"📍 配置路径: {report['config_base']}")
    print(f"⏰ 扫描时间: {report['scan_time']}")
    print(f"\n📈 统计摘要:")
    print(f"   • 扫描类型数: {report['summary']['total_types_scanned']}")
    print(f"   • 已存在配置: {report['summary']['existing_count']}")
    print(f"   • 总大小: {report['summary']['total_size_bytes'] / 1024:.1f} KB\n")
    
    print("📋 详细配置:\n")
    print("-" * 50)
    for cfg_type, info in report['configs'].items():
        status = "✅" if info['exists'] else "❌"
        size_str = f"{info['size_bytes'] / 1024:.1f} KB" if info['size_bytes'] > 0 else "-"
        modified = info.get('modified_time', 'N/A')[:19] if info.get('modified_time') else 'N/A'
        print(f"{status} {cfg_type:<25} {size_str:>10}  {modified}")
    
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
            print(f"   • {addon.name:<30} [支持: {bl_ver}]")
        if len(addons) > 15:
            print(f"   ... 还有 {len(addons) - 15} 个")
    else:
        print("   （无）")
    
    print("\n" + "-" * 50)
    
    # 询问是否导出报告
    export = input("\n是否导出完整报告到文件？(y/n): ").strip().lower()
    if export == 'y':
        output_path = scanner.export_scan_report()
        print(f"\n✅ 报告已导出到: {output_path}")
    
    input("\n按回车键继续...")


def create_backup():
    """创建配置备份"""
    from blender_config_sync.path_manager import BlenderPathManager
    from blender_config_sync.backup_engine import BackupEngine
    
    print_header("💾 创建配置备份")
    
    manager = BlenderPathManager()
    versions = manager.detect_installed_versions()
    
    if not versions:
        print("❌ 没有可用的 Blender 版本")
        input("\n按回车键继续...")
        return
    
    print("请选择要备份的版本:\n")
    for i, v in enumerate(versions, 1):
        print(f"  [{i}] Blender {v.version}")
    
    choice = get_choice(len(versions))
    if choice == 0:
        return
    
    selected = versions[choice - 1]
    
    include_addons = input("\n是否包含插件文件？(Y/n): ").strip().lower() != 'n'
    
    print(f"\n💾 正在备份 Blender {selected.version} 的配置...")
    print(f"   包含插件: {'是' if include_addons else '否'}\n")
    
    engine = BackupEngine()
    result = engine.create_backup(
        config_path=selected.config_path,
        blender_version=selected.version,
        include_addons=include_addons
    )
    
    print(result.message)
    
    if result.warnings:
        print("\n⚠️ 警告:")
        for w in result.warnings:
            print(f"   • {w}")
    
    input("\n按回车键继续...")


def list_backups():
    """列出所有备份"""
    from blender_config_sync.backup_engine import BackupEngine
    
    print_header("📋 备份管理")
    
    engine = BackupEngine()
    backups = engine.list_backups()
    
    if not backups:
        print("📭 没有找到任何备份记录\n")
        print("提示: 使用 '创建备份' 功能生成新的备份")
        input("\n按回车键继续...")
        return
    
    print(f"✅ 共 {len(backups)} 个备份记录:\n")
    print("-" * 80)
    print(f"{'序号':<6}{'文件名':<48}{'大小':>8}{'版本':>8}")
    print("-" * 80)
    
    for i, backup in enumerate(backups, 1):
        print(f"{i:<6}{backup['filename']:<48}"
              f"{backup['size_mb']:>7.2f}MB "
              f"{backup['blender_version']:>8}")
    
    print("-" * 80)
    
    # 询问是否删除
    delete = input("\n是否要删除某个备份？(y/n): ").strip().lower()
    if delete == 'y':
        try:
            num = int(input("请输入要删除的备份序号: "))
            if 1 <= num <= len(backups):
                backup_to_delete = backups[num - 1]
                confirm = input(f"确定要删除 '{backup_to_delete['filename']}' 吗？(y/n): ")
                if confirm.lower() == 'y':
                    import pathlib
                    backup_path = pathlib.Path.cwd() / 'backups' / backup_to_delete['filename']
                    if engine.delete_backup(backup_path):
                        print(f"\n✅ 备份已删除")
                    else:
                        print(f"\n❌ 删除失败")
            else:
                print("❌ 无效的序号")
        except ValueError:
            print("❌ 请输入有效的数字")
    
    input("\n按回车键继续...")


def compare_configs():
    """比较两个版本的配置差异"""
    from blender_config_sync.path_manager import BlenderPathManager
    from blender_config_sync.diff_engine import DiffEngine, generate_text_report
    
    print_header("⚖️ 配置差异比较")
    
    manager = BlenderPathManager()
    versions = manager.detect_installed_versions()
    
    if len(versions) < 2:
        print("❌ 至少需要检测到 2 个 Blender 版本才能进行比较\n")
        print("当前只检测到 {} 个版本".format(len(versions)))
        input("\n按回车键继续...")
        return
    
    print("请选择源版本（要同步的配置来源）:\n")
    for i, v in enumerate(versions, 1):
        print(f"  [{i}] Blender {v.version}")
    
    source_choice = get_choice(len(versions))
    if source_choice == 0:
        return
    
    print("\n请选择目标版本（被同步到的目标）:\n")
    for i, v in enumerate(versions, 1):
        marker = " ← 当前选择" if i == source_choice else ""
        print(f"  [{i}] Blender {v.version}{marker}")
    
    target_choice = get_choice(len(versions))
    if target_choice == 0:
        return
    
    if source_choice == target_choice:
        print("\n❌ 源版本和目标版本不能相同")
        input("\n按回车键继续...")
        return
    
    source_inst = versions[source_choice - 1]
    target_inst = versions[target_choice - 1]
    
    print(f"\n⚖️ 正在比较配置差异...")
    print(f"   源版本: Blender {source_inst.version}")
    print(f"   目标版本: Blender {target_inst.version}\n")
    
    diff_engine = DiffEngine()
    result = diff_engine.compare(
        source_path=source_inst.config_path,
        target_path=target_inst.config_path,
        source_version=source_inst.version,
        target_version=target_inst.version
    )
    
    # 显示报告
    text_report = generate_text_report(result)
    print(text_report)
    
    # 询问是否导出
    export = input("\n是否将详细报告导出到 JSON 文件？(y/n): ").strip().lower()
    if export == 'y':
        output = diff_engine.export_comparison_report(result)
        print(f"\n✅ 详细报告已导出到: {output}")
    
    input("\n按回车键继续...")


def main():
    """主程序入口"""
    print("\n" + "█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "  🎨 Blender 配置同步工具 v0.2 - 终端版 ".center(66) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70 + "\n")
    
    while True:
        print_menu([
            "🔄 检测并查看已安装的 Blender 版本",
            "🔍 扫描指定版本的详细配置",
            "💾 创建配置备份",
            "📋 查看和管理备份",
            "⚖️ 比较两个版本的配置差异",
            "ℹ️ 关于此工具"
        ], "🎯 主菜单")
        
        choice = get_choice(6)
        
        if choice == 0:
            print("\n感谢使用 Blender 配置同步工具！再见 👋\n")
            break
        elif choice == 1:
            show_versions()
        elif choice == 2:
            scan_config()
        elif choice == 3:
            create_backup()
        elif choice == 4:
            list_backups()
        elif choice == 5:
            compare_configs()
        elif choice == 6:
            print_header("ℹ️ 关于")
            print("""
Blender 配置同步工具 v0.2
========================

一款专业的 Blender 个人配置管理工具，
帮助你轻松在不同版本间同步收藏夹、快捷键、插件等配置。

核心功能：
• 自动检测已安装的 Blender 版本
• 配置文件扫描与分析
• 一键备份与恢复
• 跨版本配置差异比较
• 选择性同步与风险评估

技术栈：
Python 3.9+ | 纯标准库实现 | 零外部依赖

作者: MMY
License: MIT
GitHub: https://github.com/yuyeming0115/mmy_BlenderPortableVS

使用提示：
• 如果 GUI 无法正常工作，可以使用这个终端版本
• 所有功能都可以通过菜单访问
• 支持批量操作和自动化脚本集成
""")
            input("\n按回车键返回主菜单...")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，程序退出")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")
