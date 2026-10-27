@echo off
title Duck Debugger 🦆
chcp 65001 > nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
echo ==============================================
echo    🦆 Starting Duck Debugger...
echo ==============================================
cd /d "%~dp0"
python -m streamlit run app.py
pause
