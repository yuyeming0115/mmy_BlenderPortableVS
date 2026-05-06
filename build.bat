@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   Blender Config Sync - 一键打包 (Windows)
echo ============================================================
echo.

:: 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+
    echo   下载地址: https://nodejs.org/
    pause
    exit /b 1
)

:: 进入项目目录
cd /d "%~dp0"

:: 安装依赖
echo [1/3] 安装依赖...
call npm install

:: 构建前端 + 打包
echo.
echo [2/3] 构建前端...
call npm run build
if errorlevel 1 (
    echo [错误] 前端构建失败
    pause
    exit /b 1
)

:: Tauri 打包
echo.
echo [3/3] 打包 Windows NSIS 安装版...
echo ------------------------------------------------------------
call npx tauri build --bundles nsis

:: 复制结果
echo.
echo ============================================================
echo   打包完成！
echo ============================================================
echo.

mkdir dist 2>nul

:: 复制便携版（单文件exe）
set PORTABLE_EXE=src-tauri\target\release\blender-config-sync.exe
if exist "%PORTABLE_EXE%" (
    copy "%PORTABLE_EXE%" "dist\Blender Config Sync Portable.exe" >nul
    echo   [便携版] Blender Config Sync Portable.exe
    for %%A in ("dist\Blender Config Sync Portable.exe") do echo   大小: %%~zA bytes
    echo.
)

:: 复制安装版
set OUTDIR=src-tauri\target\release\bundle\nsis
for %%F in (%OUTDIR%\*-setup.exe) do (
    copy "%%F" dist\ >nul
    echo   [安装版] %%~nxF
    for %%A in ("dist\%%~nxF") do echo   大小: %%~zA bytes
)

echo.
echo   按任意键打开 dist 文件夹...
pause >nul
explorer dist
