@echo off
REM AI Story Creator Pro 快速启动脚本 (Windows)

echo.
echo 🎨 AI Story Creator Pro - 智能故事创作平台
echo ==========================================
echo.
echo 正在启动应用...
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未安装Python
    echo    请从 https://www.python.org/ 下载安装
    pause
    exit /b 1
)

REM 显示Python版本
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✓ Python版本: %PYTHON_VERSION%

REM 启动应用
echo.
echo ✨ 启动现代化UI界面...
echo.

python run_modern_app.py

echo.
echo 应用已关闭
pause

