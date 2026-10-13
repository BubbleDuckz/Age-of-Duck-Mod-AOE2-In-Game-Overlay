@echo off
setlocal

rem === Project folder ===
set "PROJ=%~dp0"
pushd "%PROJ%" || (echo Project folder not found & pause & exit /b 1)

rem Optional clean
rmdir /s /q build dist 2>nul
del /q AgeOfDuck.spec 2>nul
del /q AgeofDuck.spec 2>nul

if not exist ".venv\Scripts\python.exe" (
  echo Local Python environment not found.
  echo Run: setup_env.bat
  popd & pause & exit /b 1
)

rem === Build (ONEDIR) ===
".venv\Scripts\python.exe" -m PyInstaller ^
  --onedir ^
  --windowed ^
  --noconfirm ^
  --clean ^
  --name "AgeOfDuck" ^
  --icon="duck.ico" ^
  --add-data "duck.png;." ^
  --add-data "profile.png;." ^
  --add-data "civ_data.json;." ^
  --add-data "units_db.json;." ^
  --add-data "typical_strategies.json;." ^
  --add-data "Units;Units" ^
  --add-data "CivIcons;CivIcons" ^
  --add-data "AgeIcons;AgeIcons" ^
  --add-data "tc_reminder/*.json;tc_reminder" ^
  --add-data "tc_reminder/*.wav;tc_reminder" ^
  --add-data "tc_reminder/templates;tc_reminder/templates" ^
  --add-data "tc_reminder/samples;tc_reminder/samples" ^
  "AgeofDuck.py"

echo.
if exist "dist\AgeOfDuck\AgeOfDuck.exe" (
  echo Built onedir: dist\AgeOfDuck\
) else (
  echo Build failed.
  popd & pause & exit /b 1
)

popd
echo Done. Open AgeOfDuck.iss in Inno Setup and Compile.
pause
