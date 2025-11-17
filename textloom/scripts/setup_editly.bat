@echo off
REM ============================================================================
REM Editly 视频引擎快速部署脚本 (Windows)
REM
REM 用法:
REM   scripts\setup_editly.bat
REM
REM 功能:
REM   - 检查系统依赖 (Node.js, FFmpeg)
REM   - 安装 Editly
REM   - 创建测试目录
REM   - 运行测试验证
REM
REM 作者: Claude
REM 创建: 2025-11-17
REM ============================================================================

echo ============================================================
echo   Editly 视频引擎部署脚本 (Windows)
echo ============================================================
echo.

REM 1. 检查 Node.js
echo [INFO] 检查 Node.js...
where node >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
    echo [INFO] 已安装 Node.js: %NODE_VERSION%
) else (
    echo [ERROR] Node.js 未安装
    echo [ERROR] 请安装 Node.js (LTS 版本)
    echo [ERROR] 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

REM 2. 检查 FFmpeg
echo.
echo [INFO] 检查 FFmpeg...
where ffmpeg >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] 已安装 FFmpeg
) else (
    echo [ERROR] FFmpeg 未安装
    echo [ERROR] 安装方式:
    echo [ERROR]   1. 使用 Chocolatey: choco install ffmpeg
    echo [ERROR]   2. 手动下载: https://ffmpeg.org/download.html
    pause
    exit /b 1
)

REM 3. 安装 Editly
echo.
echo [INFO] 检查 Editly...
where editly >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Editly 已安装
) else (
    echo [WARN] Editly 未安装，开始安装...
    echo [INFO] 运行: npm install -g editly
    call npm install -g editly
    if %ERRORLEVEL% EQU 0 (
        echo [INFO] Editly 安装成功
    ) else (
        echo [ERROR] Editly 安装失败
        pause
        exit /b 1
    )
)

REM 4. 创建测试目录
echo.
echo [INFO] 创建测试目录...
if not exist workspace\materials\images mkdir workspace\materials\images
if not exist workspace\materials\videos mkdir workspace\materials\videos
if not exist workspace\output mkdir workspace\output
if not exist logs mkdir logs
echo [INFO] 目录创建完成

REM 5. 生成示例素材
echo.
echo [INFO] 生成示例素材...
ffmpeg -f lavfi -i color=c=blue:s=1080x1920:d=1 -frames:v 1 workspace\materials\images\sample1.jpg -y >nul 2>&1
ffmpeg -f lavfi -i color=c=red:s=1080x1920:d=1 -frames:v 1 workspace\materials\images\sample2.jpg -y >nul 2>&1
ffmpeg -f lavfi -i color=c=green:s=1080x1920:d=1 -frames:v 1 workspace\materials\images\sample3.jpg -y >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [INFO] 示例素材生成完成
) else (
    echo [WARN] 示例素材生成失败，请手动添加图片
)

REM 6. 运行 Python 测试
echo.
echo [INFO] 检查 Python 环境...
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
    echo [INFO] 已安装 Python: %PYTHON_VERSION%

    echo [INFO] 运行测试脚本...
    python test_editly_engine.py
) else (
    echo [WARN] Python 未安装，跳过测试
)

REM 7. 完成
echo.
echo ============================================================
echo [INFO] 🎉 Editly 视频引擎部署完成！
echo ============================================================
echo.
echo [INFO] 下一步操作:
echo   1. 查看文档: docs\EDITLY_INTEGRATION_GUIDE.md
echo   2. 运行测试: python test_editly_engine.py
echo   3. 生成视频: 参考集成指南中的示例代码
echo.
echo [INFO] 快速测试:
echo   cd textloom
echo   python test_editly_engine.py
echo.

pause
