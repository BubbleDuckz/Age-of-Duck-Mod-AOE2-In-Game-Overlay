@echo off
setlocal
set "PROJ=%~dp0"
pushd "%PROJ%" || (echo Project folder not found & pause & exit /b 1)

if not exist ".venv\Scripts\python.exe" (
  echo Creating local environment...
  call :create_env
  if errorlevel 1 goto fail
)

echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail

echo Done. Run AgeofDuck.bat or make EXE.bat.
popd
pause
exit /b 0

:create_env
rem Prefer the launcher, then any supported interpreter on PATH.
py -3 -c "import sys; sys.exit(sys.version_info < (3,11))" >nul 2>&1
if not errorlevel 1 (
  py -3 -m venv .venv
  exit /b
)
python -c "import sys; sys.exit(sys.version_info < (3,11))" >nul 2>&1
if not errorlevel 1 (
  python -m venv .venv
  exit /b
)
rem Retain the existing per-user locations when neither command is available.
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m venv .venv
  exit /b
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" -m venv .venv
  exit /b
)
echo Python 3.11 or newer was not found. Install it and enable the launcher or PATH option.
exit /b 1

:fail
echo Setup failed. See the error above; dependencies may be incomplete.
popd
pause
exit /b 1
