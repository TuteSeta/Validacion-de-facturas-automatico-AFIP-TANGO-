@echo off
setlocal
cd /d "%~dp0"

py -3.12 -m venv .venv-windows
if errorlevel 1 exit /b 1

call .venv-windows\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
python -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1

python -m unittest discover -s tests -v
if errorlevel 1 exit /b 1
python -m PyInstaller --noconfirm --clean ValidadorFacturas.spec
if errorlevel 1 exit /b 1
copy /Y config.yaml dist\config.yaml >nul
if errorlevel 1 exit /b 1

echo Distribucion generada en dist\ValidadorFacturas.exe y dist\config.yaml
