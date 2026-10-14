@echo off
setlocal

set "PROJ=%~dp0"
pushd "%PROJ%" || (echo Project folder not found & pause & exit /b 1)

if exist ".venv\Scripts\python.exe" (
  echo Local environment already exists.
) else (
  echo Creating local environment...
  if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m venv .venv
  ) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" -m venv .venv
  ) else (
    echo Python was not found.
    echo Install Python 3.11 or newer from https://www.python.org/downloads/windows/
    echo During install, tick "Add python.exe to PATH", then run this file again.
    popd & pause & exit /b 1
  )
)

echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo Done. You can run:
echo   .venv\Scripts\python.exe AgeofDuck.py
echo or build:
echo   make EXE.bat
popd
pause
