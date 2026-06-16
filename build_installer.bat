@echo off
REM build_installer.bat — PyInstaller + Inno Setup pipeline (CMD fallback)
REM Run from the project root:  build_installer.bat
REM Output: dist\installer\SynthPop_Desktop_Setup_1.0.0.exe

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Cleaning previous build artefacts...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo.
echo Step 1/2 - Building app with PyInstaller...
pyinstaller packaging\synthpop_desktop.spec
if errorlevel 1 (
    echo PyInstaller failed.
    exit /b 1
)
echo PyInstaller done.

echo.
echo Step 2/2 - Building installer with Inno Setup...

set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
)
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe
)

if "%ISCC%"=="" (
    echo.
    echo Inno Setup not found. Install from: https://jrsoftware.org/isdl.php
    echo Then run: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\installer.iss
    echo.
    echo PyInstaller output is ready at: dist\SynthPop Desktop\
    exit /b 0
)

"%ISCC%" packaging\installer.iss
if errorlevel 1 (
    echo Inno Setup failed.
    exit /b 1
)

echo.
echo Done! Installer is in dist\installer\
