#!/bin/bash
set -e

echo "============================================================"
echo "  Blender Config Sync - 一键打包工具 (macOS)"
echo "============================================================"

# 检查 Python
if ! command -v python3 &>/dev/null; then
    echo "[错误] 未找到 python3，请先安装 Python 3.9+"
    exit 1
fi

# 安装依赖
echo "[1/3] 检查 PyInstaller..."
pip3 show pyinstaller &>/dev/null || pip3 install pyinstaller PyQt6

# 清理旧文件
echo "[2/3] 清理旧构建文件..."
rm -rf build dist

# 执行打包
echo "[3/3] 开始打包..."
python3 -m PyInstaller --clean --noconfirm blender_config_sync.spec

# 检查结果
if [ -d "dist/BlenderConfigSync.app" ] || [ -f "dist/BlenderConfigSync" ]; then
    echo "============================================================"
    echo "  打包成功！文件位置: $(pwd)/dist/"
    echo "============================================================"
    open dist
else
    echo "[错误] 打包失败，请检查上方错误信息"
    exit 1
fi
