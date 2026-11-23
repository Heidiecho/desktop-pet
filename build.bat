@echo off
cd /d "%~dp0"
echo ============================================
echo   桌面宠物 一键打包 (Windows)
echo ============================================
echo.
where python >nul 2>nul
if %errorlevel%==0 (
    python build.py
    pause
    exit /b 0
)
where py >nul 2>nul
if %errorlevel%==0 (
    py build.py
    pause
    exit /b 0
)
echo [提示] 系统 PATH 里没有 python 命令。
echo 推荐改用 PyCharm：打开本项目文件夹，右键 build.py -^> Run，即可自动打包。
echo 或在 PyCharm 底部 Terminal 里输入:  python build.py
echo.
pause
