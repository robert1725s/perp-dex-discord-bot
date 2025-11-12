@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

echo ============================================================
echo   Perp DEX Discord Bot - Windows Launcher
echo ============================================================
echo.

REM Load .env file if exists
if exist .env (
    echo Loading environment variables from .env...
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if not "%%a"=="" if not "%%b"=="" (
            set %%a=%%b
        )
    )
)

echo Starting bot...
echo.

python main.py %*

if errorlevel 1 (
    echo.
    echo Error occurred! Press any key to exit...
    pause >nul
)
