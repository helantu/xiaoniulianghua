@echo off
chcp 65001 >nul
title 小牛量化交易系统

echo ========================================
echo    🐂 小牛量化交易系统 v1.0
echo ========================================
echo.

cd /d "%~dp0"

echo [启动中] 检查Python环境...
set PYTHON=C:\Users\lenovo\.workbuddy\binaries\python\envs\niuquant\Scripts\python.exe

if not exist "%PYTHON%" (
    echo [错误] Python环境未找到，请先运行:
    echo   C:\Users\lenovo\.workbuddy\binaries\python\versions\3.13.12\python.exe -m venv C:\Users\lenovo\.workbuddy\binaries\python\envs\niuquant
    echo.
    pause
    exit /b 1
)

echo [启动中] 运行主程序...
echo.
"%PYTHON%" main.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 程序异常退出，错误码: %errorlevel%
    pause
)
