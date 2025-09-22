@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo ========================================
echo    Smart Assistant exe 빌드
echo ========================================
echo.
echo PyInstaller를 사용하여 exe 파일을 생성합니다.
echo.

py build_exe.py

echo.
echo 빌드가 완료되었습니다.
pause
