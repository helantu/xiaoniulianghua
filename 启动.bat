@echo off
chcp 65001 >nul
title 小牛量化交易系统

echo ========================================
echo    🐂 小牛量化交易系统 v1.0
echo ========================================
echo.

cd /d "%~dp0"

echo [启动中] 检查Python环境...

:: 直接使用python命令，依赖PATH
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [信息] Python环境正常
    set PYTHON=python
) else (
    echo [错误] 未找到Python，请先安装Python并添加到PATH
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
