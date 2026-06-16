@echo off
REM setup.bat — create venv, install deps, launch the app (CMD fallback)
REM Run from the project root:  setup.bat

echo Creating virtual environment...
python -m venv .venv

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Setup complete. Launching SynthPop Desktop...
python main.py
