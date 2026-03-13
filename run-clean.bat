@echo off
cd /d "%~dp0"
echo Clearing Python cache...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
echo.
echo Installing dependencies if needed...
pip install -r requirements.txt -q 2>nul
echo.
echo Starting PurNi Menu...
echo Open http://127.0.0.1:8000 in your browser
echo.
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
if errorlevel 1 pause
