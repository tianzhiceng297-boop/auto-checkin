@echo off
chcp 65001 >nul
echo ========================================
echo   腾讯会议自动签到 - 启动中...
echo ========================================
echo.

cd /d "%~dp0"

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 检查依赖
python -c "import wxauto" >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 正在安装依赖...
    pip install -r requirements.txt
)

REM 检查配置
if not exist config.yaml (
    echo [错误] 未找到 config.yaml，请从 config.example.yaml 复制并修改
    pause
    exit /b 1
)

echo [提示] 请确保微信和腾讯会议客户端已打开
echo [提示] 程序将在后台运行，关闭此窗口将停止程序
echo.
echo 按 Ctrl+C 可停止程序
echo.

python main.py

pause
