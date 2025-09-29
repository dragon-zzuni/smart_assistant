@echo off
chcp 65001 >nul
setlocal
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

conda run -n assist python "%~dp0run_gui.py" %*