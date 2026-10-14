@echo off
setlocal
pushd "%~dp0" || (echo Project folder not found & pause & exit /b 1)
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" AgeofDuck.py
) else (
  python AgeofDuck.py
)
set "RESULT=%ERRORLEVEL%"
popd
pause
exit /b %RESULT%
