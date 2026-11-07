@echo off
chcp 65001 >nul
cd /d "%~dp0"
title UPC2026 Problem B 点球轨迹预测实验台
echo ============================================
echo   UPC 2026 Problem B - 点球轨迹预测实验台
echo ============================================
echo.

if not exist .venv (
    echo [1/3] 首次运行：创建 Python 虚拟环境...
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 未找到 Python，请先安装 Python 3.10 或更高版本：
        echo        https://www.python.org/downloads/
        echo        安装时务必勾选 "Add Python to PATH"
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat

echo [2/3] 检查并安装依赖（首次约 1-2 分钟）...
python -m pip install -r requirements.txt --quiet

echo [3/3] 启动实验台...
echo 浏览器将自动打开，如未打开请手动访问 http://localhost:8501
python -m streamlit run app_main.py

pause
