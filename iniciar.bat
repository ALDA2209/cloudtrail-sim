@echo off
cd /d "%~dp0"
title CloudTrail Simulator

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python no esta instalado. Descargalo de https://www.python.org/downloads/
    echo Marca la opcion "Add Python to PATH" al instalar.
    pause
    exit /b
)

if not exist venv (
    echo Creando entorno virtual...
    python -m venv venv
)
call venv\Scripts\activate

echo Instalando dependencias...
pip install -q -r requirements.txt

set NUEVO=0
if not exist db.sqlite3 set NUEVO=1

python manage.py migrate --verbosity 0
if "%NUEVO%"=="1" (
    echo Cargando datos de demostracion...
    python manage.py cargar_demo
)

echo.
echo  CloudTrail Simulator listo en http://127.0.0.1:8000
echo  Para detenerlo cierra esta ventana o presiona Ctrl+C
echo.
start "" http://127.0.0.1:8000
python manage.py runserver
