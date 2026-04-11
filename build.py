#!/usr/bin/env python3
"""
Blender Config Sync - 一键打包工具
将项目打包为独立的可执行应用程序
"""

import subprocess
import sys
import platform
from pathlib import Path


def install_pyinstaller():
    """安装 PyInstaller"""
    print("📦 正在检查/安装 PyInstaller...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "pyinstaller", "--quiet"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"❌ 安装失败: {result.stderr}")
        return False
    print("✅ PyInstaller 已就绪")
    return True


def build_app():
    """执行打包"""
    project_root = Path(__file__).parent
    spec_file = project_root / "blender_config_sync.spec"
    dist_dir = project_root / "dist"
    
    print("\n" + "=" * 60)
    print("🎨 Blender Config Sync - 打包工具")
    print("=" * 60)
    print(f"\n📍 项目目录: {project_root}")
    print(f"💻 平台: {platform.system()} {platform.machine()}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    
    # 检查 spec 文件
    if not spec_file.exists():
        print(f"❌ 未找到配置文件: {spec_file}")
        return False
    
    print("\n🔨 开始打包...")
    print("-" * 60)
    
    # 执行 PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",  # 清理旧的构建文件
        "--noconfirm",  # 覆盖输出文件
        str(spec_file)
    ]
    
    try:
        result = subprocess.run(cmd, cwd=str(project_root), check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 打包失败!")
        print(f"错误代码: {e.returncode}")
        return False
    
    # 检查输出
    system = platform.system()
    
    if system == "Darwin":  # macOS
        app_path = dist_dir / "BlenderConfigSync.app"
        if app_path.exists():
            size_mb = sum(f.stat().st_size for f in app_path.rglob('*') if f.is_file()) / (1024 * 1024)
            print("\n" + "=" * 60)
            print("✅ 打包成功！")
            print("=" * 60)
            print(f"\n📦 应用程序位置:")
            print(f"   {app_path}")
            print(f"\n📊 文件大小: {size_mb:.1f} MB")
            print(f"\n🚀 使用方法:")
            print(f"   1. 双击打开: {app_path}")
            print(f"   或终端运行: open '{app_path}'")
            print(f"\n💡 提示: 可以将 .app 拖到 Applications 文件夹")
            return True
    
    elif system == "Windows":
        exe_path = dist_dir / "BlenderConfigSync.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\n" + "=" * 60)
            print("✅ 打包成功！")
            print("=" * 60)
            print(f"\n📦 可执行文件位置:")
            print(f"   {exe_path}")
            print(f"\n📊 文件大小: {size_mb:.1f} MB")
            print(f"\n🚀 使用方法: 直接双击运行")
            return True
    
    else:  # Linux
        exe_path = dist_dir / "BlenderConfigSync"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\n" + "=" * 60)
            print("✅ 打包成功！")
            print("=" * 60)
            print(f"\n📦 可执行文件位置:")
            print(f"   {exe_path}")
            print(f"\n📊 文件大小: {size_mb:.1f} MB")
            print(f"\n🚀 使用方法: ./BlenderConfigSync 或 chmod +x 后双击")
            return True
    
    print("⚠️ 打包完成但未找到输出文件")
    print(f"请检查 dist 目录: {dist_dir}")
    return False


def main():
    """主函数"""
    print("\n🚀 Blender 配置同步工具 - 打包器\n")
    
    # Step 1: 安装依赖
    if not install_pyinstaller():
        print("\n❌ 无法继续，请手动安装: pip install pyinstaller")
        input("\n按回车键退出...")
        return
    
    # Step 2: 执行打包
    success = build_app()
    
    if success:
        print("\n🎉 恭喜！打包完成！\n")
    else:
        print("\n⚠️ 打包未完全成功，请查看上方错误信息\n")
    
    input("按回车键退出...")


if __name__ == '__main__':
    main()
