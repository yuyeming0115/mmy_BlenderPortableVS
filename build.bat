@echo off
chcp 65001 >nul
echo.
echo ============================================================
echo   Blender Config Sync - 一键打包工具
echo ============================================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.9+
    echo   下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 安装依赖
echo [1/3] 检查 PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [安装] 正在安装 PyInstaller...
    pip install pyinstaller PyQt6
)

:: 清理旧文件
echo.
echo [2/3] 清理旧构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

:: 执行打包
echo.
echo [3/3] 开始打包...
echo ------------------------------------------------------------
python -m PyInstaller --clean --noconfirm blender_config_sync.spec

:: 检查结果
echo.
if exist dist\BlenderConfigSync.exe (
    echo ============================================================
    echo   打包成功！
    echo ============================================================
    echo.
    echo   文件位置: %~dp0dist\BlenderConfigSync.exe
    for %%A in (dist\BlenderConfigSync.exe) do echo   文件大小: %%~zA bytes
    echo.
    echo   按任意键打开 dist 文件夹...
    pause >nul
    explorer dist
) else (
    echo ============================================================
    echo   打包失败！
    echo ============================================================
    echo.
    echo   请检查上方错误信息
    pause
)
