@echo off
cd /d %~dp0\admin_panel
call venv_django\Scripts\activate
echo.
echo === ЗАПУЩЕН DJANGO НА ПОРТУ 8080 ===
echo Открой: http://localhost:8080/admin
echo =====================================
python manage.py runserver 8080