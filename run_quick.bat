@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo ========================================
echo    Smart Assistant 빠른 시작
echo ========================================
echo.
echo AI 기반 스마트 어시스턴트가 메신저 메시지를
echo 분석하여 TODO 리스트를 생성하는 과정을 보여줍니다.
echo.

py quick_start.py

echo.
echo 테스트가 완료되었습니다.
pause
