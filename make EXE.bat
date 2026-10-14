@echo off
setlocal

rem === Project folder ===
set "PROJ=%~dp0"
pushd "%PROJ%" || (echo Project folder not found & pause & exit /b 1)

if not exist ".venv\Scripts\python.exe" (
  echo Local Python environment not found.
  echo Run: setup_env.bat
  popd & pause & exit /b 1
)

rem === Build (ONEDIR) ===
".venv\Scripts\python.exe" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  "AgeOfDuck.spec"

if errorlevel 1 (
  echo Build failed.
  popd & pause & exit /b 1
)

echo.
if exist "dist\AgeOfDuck\AgeOfDuck.exe" (
  echo Built onedir: dist\AgeOfDuck\
) else (
  echo Build failed.
  popd & pause & exit /b 1
)

popd
echo Done. Open installer\AgeOfDuckInstaller.iss in Inno Setup and Compile.
pause

