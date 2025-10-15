@echo off
cd /d %~dp0
call venv\Scripts\activate
echo.
echo === ЗАПУЩЕН FASTAPI НА ПОРТУ 8000 ===
echo Открой: http://localhost:8000
echo ======================================
uvicorn back.main:app --reload --port 8000