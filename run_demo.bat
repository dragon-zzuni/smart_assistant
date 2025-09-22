@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo ========================================
echo    Smart Assistant 데모 실행
echo ========================================
echo.
echo 이 데모는 AI 기반 스마트 어시스턴트가
echo 이메일과 메신저 메시지를 분석하여
echo TODO 리스트를 생성하는 과정을 보여줍니다.
echo.

py demo_simple.py

echo.
echo 데모가 완료되었습니다.
pause
