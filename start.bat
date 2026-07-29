@echo off
echo === OWNEX v5.1.0 - Starting... ===

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat
echo Virtual environment activated.

echo Installing dependencies...
pip install -e . --quiet

echo Starting OWNEX API...
python -m api.main

pause