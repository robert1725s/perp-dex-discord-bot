@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

echo ============================================================
echo   Perp DEX Discord Bot - Test Mode (Windows)
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

echo Running in test mode (--once)...
echo.

python main.py --once

echo.
echo Test completed. Press any key to exit...
pause >nul
