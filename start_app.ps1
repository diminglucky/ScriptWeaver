# ========================================
# AI Story Creator Pro 启动脚本
# PowerShell版本 - 自动解决中文乱码问题
# ========================================

# 设置控制台编码为UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

# 设置窗口标题
$Host.UI.RawUI.WindowTitle = "AI Story Creator Pro"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AI Story Creator Pro" -ForegroundColor Green
Write-Host "  正在启动..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查conda是否可用
$condaExists = Get-Command conda -ErrorAction SilentlyContinue
if (-not $condaExists) {
    Write-Host "[错误] 未找到conda命令" -ForegroundColor Red
    Write-Host "请确保Anaconda已安装并添加到PATH" -ForegroundColor Yellow
    Write-Host "或者使用 Anaconda PowerShell Prompt 运行此脚本" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "按Enter键退出"
    exit 1
}

# 激活conda环境
Write-Host "[1/2] 激活conda环境: play" -ForegroundColor Yellow
try {
    # 使用conda的PowerShell初始化
    $condaPath = Split-Path (Get-Command conda).Source
    $condaRoot = Split-Path $condaPath -Parent
    
    # 执行conda初始化（如果需要）
    & "$condaRoot\shell\condabin\conda-hook.ps1"
    
    # 激活环境
    conda activate play
    
    Write-Host "✓ 环境激活成功" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "✗ 环境激活失败: $_" -ForegroundColor Red
    Read-Host "按Enter键退出"
    exit 1
}

# 运行程序
Write-Host "[2/2] 启动应用程序..." -ForegroundColor Yellow
Write-Host ""

python run_modern_app.py

# 检查退出状态
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[警告] 程序异常退出 (退出码: $LASTEXITCODE)" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "按Enter键退出"
}

