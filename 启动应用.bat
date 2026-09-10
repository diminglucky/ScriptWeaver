@echo off
setlocal
chcp 65001 >nul

cd /d "%~dp0"

set "PYTHON_CMD="
if exist "%~dp0.venv\Scripts\python.exe" (
    echo Starting ScriptWeaver with local environment...
    "%~dp0.venv\Scripts\python.exe" "%~dp0.runtime\launch_gui.py"
    goto :app_done
)
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL%==0 (
        set "PYTHON_CMD=python"
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python not found in PATH.
    pause
    exit /b 1
)

echo Starting ScriptWeaver...
%PYTHON_CMD% run_modern_app.py

:app_done
echo.
echo Application exited.
pause
