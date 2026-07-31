@echo off
chcp 65001 >nul
title AI Daily Agent - 一键启动

echo.
echo ============================================================
echo   AI Daily Agent - 一键启动
echo ============================================================
echo.

REM 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python 已就绪

REM 检查是否首次运行
if not exist ".env" (
    echo.
    echo 🎯 首次运行，正在自动配置...
    python start.py
    if errorlevel 1 (
        echo ❌ 配置失败
        pause
        exit /b 1
    )
    echo ✅ 配置完成
    echo.
)

REM 运行 Agent
echo 🚀 正在运行 AI Daily Agent...
echo.
python start.py

echo.
if errorlevel 1 (
    echo ❌ 运行失败，请检查日志
) else (
    echo ✅ 任务完成
)

echo.
pause
