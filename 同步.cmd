@echo off
chcp 65001 >nul
title TA 学习日志 - 同步到 GitHub
cd /d "%~dp0"

echo.
echo   ============================================
echo     TA 学习日志 - 同步到 GitHub
echo   ============================================
echo.

"C:\Users\zj\Anaconda3\python.exe" "%~dp0sync.py"

echo.
echo   按任意键关闭...
pause >nul
