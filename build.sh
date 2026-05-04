#!/bin/bash
set -e

echo "============================================================"
echo "  Blender Config Sync - 一键打包 (macOS)"
echo "============================================================"

cd "$(dirname "$0")"

# 检查 Node.js
if ! command -v node &>/dev/null; then
    echo "[错误] 未找到 Node.js，请先安装 Node.js 18+"
    exit 1
fi

# 安装依赖
echo "[1/3] 安装依赖..."
npm install

# 构建前端
echo ""
echo "[2/3] 构建前端..."
npm run build

# Tauri 打包
echo ""
echo "[3/3] 打包 macOS DMG..."
echo "------------------------------------------------------------"
npx tauri build --bundles dmg

# 复制结果
echo ""
echo "============================================================"
echo "  打包完成！"
echo "============================================================"
echo ""

mkdir -p dist
OUTDIR="src-tauri/target/release/bundle/dmg"
for dmg in "$OUTDIR"/*.dmg; do
    [ -f "$dmg" ] || continue
    cp "$dmg" dist/
    echo "  已复制: $(basename "$dmg")"
done
echo ""
echo "  打开 dist 文件夹..."
open dist
