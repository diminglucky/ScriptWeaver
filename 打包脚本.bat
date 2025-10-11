@echo off
chcp 65001 >nul
echo ========================================
echo   AI故事创作工具 - Windows打包脚本
echo ========================================
echo.

:: 检查PyInstaller是否安装
python -m PyInstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到PyInstaller，正在安装...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo [失败] PyInstaller安装失败，请手动安装: pip install pyinstaller
        pause
        exit /b 1
    )
)

echo [信息] PyInstaller已安装
echo.

:: 显示选项
echo 请选择打包方式：
echo 1. 文件夹版本（推荐） - 启动快，体积小
echo 2. 单文件版本 - 方便分发，但启动慢
echo 3. 清理构建文件
echo 4. 退出
echo.

set /p choice=请输入选项 (1-4): 

if "%choice%"=="1" goto folder_build
if "%choice%"=="2" goto single_build
if "%choice%"=="3" goto clean
if "%choice%"=="4" goto end
echo [错误] 无效选项
pause
goto end

:folder_build
echo.
echo [开始] 打包文件夹版本...
echo.
pyinstaller build_windows.spec --clean
if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo [完成] 打包成功！
    echo 程序位置: dist\AI故事创作工具\AI故事创作工具.exe
    echo ========================================
    echo.
    echo 现在可以：
    echo 1. 测试运行程序
    echo 2. 将整个"dist\AI故事创作工具"文件夹分发给用户
    echo.
    
    :: 询问是否打开文件夹
    set /p open=是否打开程序所在文件夹？(Y/N): 
    if /i "%open%"=="Y" explorer "dist\AI故事创作工具"
) else (
    echo.
    echo [失败] 打包失败，请检查错误信息
)
pause
goto end

:single_build
echo.
echo [开始] 打包单文件版本...
echo [提示] 这可能需要较长时间，请耐心等待...
echo.
pyinstaller build_simple.spec --clean
if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo [完成] 打包成功！
    echo 程序位置: dist\AI故事创作工具.exe
    echo ========================================
    echo.
    echo 现在可以：
    echo 1. 测试运行程序
    echo 2. 将"AI故事创作工具.exe"分发给用户
    echo.
    
    :: 询问是否打开文件夹
    set /p open=是否打开程序所在文件夹？(Y/N): 
    if /i "%open%"=="Y" explorer "dist"
) else (
    echo.
    echo [失败] 打包失败，请检查错误信息
)
pause
goto end

:clean
echo.
echo [开始] 清理构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del /q "*.spec" 2>nul
echo [完成] 清理完成
echo.
pause
goto end

:end
echo.
echo 感谢使用！再见！
timeout /t 2 >nul

