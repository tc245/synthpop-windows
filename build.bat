@echo off
REM build.bat — build the Windows .exe with PyInstaller (CMD fallback)
REM Run from the project root:  build.bat
REM Output: dist\SynthPop Desktop\SynthPop Desktop.exe

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Cleaning previous build artefacts...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo Running PyInstaller...
pyinstaller packaging\synthpop_desktop.spec

if errorlevel 1 (
    echo PyInstaller failed.
    exit /b 1
)

echo.
echo Build complete!
echo Output: dist\SynthPop Desktop\
echo Distribute the entire folder, not just the .exe.
