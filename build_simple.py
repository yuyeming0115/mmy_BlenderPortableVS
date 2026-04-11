#!/usr/bin/env python3
"""
Blender Config Sync - 简化版打包工具
避免 macOS 权限问题的安全打包方案
"""

import subprocess
import sys
import platform
from pathlib import Path


def main():
    """主函数"""
    project_root = Path(__file__).parent
    
    print("\n" + "=" * 60)
    print("🎨 Blender Config Sync - 打包工具 (简化版)")
    print("=" * 60)
    print(f"\n📍 项目目录: {project_root}")
    print(f"💻 平台: {platform.system()} {platform.machine()}")
    
    # 清理旧的构建文件
    build_dir = project_root / "build"
    dist_dir = project_root / "dist"
    
    if build_dir.exists():
        import shutil
        try:
            shutil.rmtree(build_dir, ignore_errors=True)
            print("🧹 已清理旧构建文件")
        except:
            pass  # 忽略错误
    
    # 使用最简化的 PyInstaller 命令
    print("\n🔨 开始打包...")
    print("-" * 60)
    print("⏳ 这可能需要 1-2 分钟，请稍候...\n")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "BlenderConfigSync",
        "--windowed",           # 不显示控制台窗口 (GUI 应用)
        "--onefile",            # 打包成单个可执行文件
        "--noconfirm",          # 覆盖已存在的文件
        "--clean",              # 清理缓存
        "--strip",              # 去除调试符号减小体积
        "start_gui.py"          # 入口文件
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0:
            # 检查输出文件
            system = platform.system()
            
            if system == "Darwin":  # macOS
                # 在 macOS 上 --onefile 会生成 Unix 可执行文件
                exe_path = dist_dir / "BlenderConfigSync"
                app_path = dist_dir / "BlenderConfigSync.app"
                
                if exe_path.exists():
                    size_mb = exe_path.stat().st_size / (1024 * 1024)
                    
                    print("\n" + "=" * 60)
                    print("✅ 打包成功！")
                    print("=" * 60)
                    print(f"\n📦 可执行文件位置:")
                    print(f"   {exe_path}")
                    print(f"\n📊 文件大小: {size_mb:.1f} MB")
                    print(f"\n🚀 使用方法:")
                    print(f"   方法 1: 双击运行该文件")
                    print(f"   方法 2: 终端运行:")
                    print(f"           cd {dist_dir}")
                    print(f"           ./BlenderConfigSync")
                    print(f"\n💡 提示:")
                    print(f"   • 首次运行可能需要在 '系统偏好设置 → 安全性' 中允许")
                    print(f"   • 可以将此文件复制到任何位置使用")
                    print(f"   • 无需安装 Python 或任何依赖")
                    return True
                    
            elif system == "Windows":
                exe_path = dist_dir / "BlenderConfigSync.exe"
                if exe_path.exists():
                    size_mb = exe_path.stat().st_size / (1024 * 1024)
                    print(f"\n✅ 打包成功!")
                    print(f"\n📦 文件位置: {exe_path}")
                    print(f"📊 大小: {size_mb:.1f} MB")
                    print(f"🚀 双击即可运行")
                    return True
                    
            else:  # Linux
                exe_path = dist_dir / "BlenderConfigSync"
                if exe_path.exists():
                    size_mb = exe_path.stat().st_size / (1024 * 1024)
                    print(f"\n✅ 打包成功!")
                    print(f"\n📦 文件位置: {exe_path}")
                    print(f"📊 大小: {size_mb:.1f} MB")
                    print(f"🚀 运行: chmod +x {exe_path} && ./{exe_path.name}")
                    return True
            
            print("⚠️ 打包完成但未找到输出文件")
            print(f"请检查 dist 目录: {dist_dir}")
            return False
            
        else:
            print("❌ 打包失败!")
            print(f"\n错误信息:\n{result.stderr[-500:]}")  # 显示最后500字符的错误
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 打包超时（超过5分钟）")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    
    if not success:
        print("\n💡 备选方案：使用终端版本")
        print("   python -m blender_config_sync.tui\n")
    
    input("\n按回车键退出...")
