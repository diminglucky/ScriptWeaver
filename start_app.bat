@echo off
REM ========================================
REM  AI Story Creator Pro 启动脚本
REM  自动解决中文乱码问题
REM ========================================

REM 设置UTF-8编码（代码页65001）
chcp 65001 >nul 2>&1

REM 设置窗口标题
title AI Story Creator Pro

echo.
echo ========================================
echo   AI Story Creator Pro
echo   正在启动...
echo ========================================
echo.

REM 检查conda是否可用
where conda >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到conda命令
    echo 请确保Anaconda已安装并添加到PATH
    echo 或者使用 Anaconda PowerShell Prompt 运行此脚本
    echo.
    pause
    exit /b 1
)

REM 激活play环境
echo [1/2] 激活conda环境: play
call conda activate play
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 无法激活play环境
    pause
    exit /b 1
)

REM 运行程序
echo [2/2] 启动应用程序...
echo.
python run_modern_app.py

REM 如果程序异常退出，暂停查看错误
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [警告] 程序异常退出
    pause
)


