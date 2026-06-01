@echo off
chcp 65001 >nul
echo ========================================
echo   腾讯会议自动签到 - 注册开机自启
echo ========================================
echo.

cd /d "%~dp0"

REM 获取当前脚本完整路径
set "SCRIPT_PATH=%~dp0start.bat"

REM 创建 VBS 脚本实现无窗口启动
set "VBS_PATH=%~dp0start_silent.vbs"
echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_PATH%"
echo WshShell.Run "cmd /c ""%SCRIPT_PATH%""", 0, False >> "%VBS_PATH%"

REM 注册到启动文件夹
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
copy "%VBS_PATH%" "%STARTUP_FOLDER%\auto_checkin.vbs" >nul 2>&1

if %errorlevel% equ 0 (
    echo [成功] 已注册开机自启!
    echo.
    echo 下次开机后程序将自动在后台运行。
    echo 如需取消，删除以下文件:
    echo   %STARTUP_FOLDER%\auto_checkin.vbs
) else (
    echo [错误] 注册失败，请手动将 start_silent.vbs 复制到启动文件夹
)

pause
