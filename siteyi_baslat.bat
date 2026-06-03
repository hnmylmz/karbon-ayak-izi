@echo off
echo Karbon Ayak Izi Takipcisi baslatiliyor...
echo.
cd /d "%~dp0"
set PYTHONUTF8=1
python app.py
pause
