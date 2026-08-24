@echo off
REM ============================================================
REM  run_dashboard.bat
REM  Cattle Breed Recognition — Expert Dashboard Launcher
REM  Windows (PowerShell / cmd compatible)
REM ============================================================

setlocal EnableDelayedExpansion

echo.
echo  ================================================================
echo    ^🐄  CattleAI Expert Dashboard Launcher
echo  ================================================================
echo.

REM ── Locate project root (directory containing this .bat) ──────────
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

REM ── Find Python executable ────────────────────────────────────────
set "PYTHON="

REM 1. Try venv first
if exist "%ROOT%\venv\Scripts\python.exe" (
    set "PYTHON=%ROOT%\venv\Scripts\python.exe"
    echo [INFO] Using virtual environment: %ROOT%\venv
    goto :found_python
)

REM 2. Try .venv
if exist "%ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
    echo [INFO] Using virtual environment: %ROOT%\.venv
    goto :found_python
)

REM 3. Fall back to system python
where python >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON=python"
    echo [WARN] No virtual environment found. Using system Python.
    goto :found_python
)

where python3 >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON=python3"
    echo [WARN] No virtual environment found. Using system python3.
    goto :found_python
)

echo [ERROR] Python not found. Please install Python 3.8+ or create a virtual environment.
pause
exit /b 1

:found_python
REM ── Check Python version ─────────────────────────────────────────
for /f "tokens=2 delims= " %%v in ('"%PYTHON%" --version 2^>^&1') do set "PY_VER=%%v"
echo [INFO] Python version: %PY_VER%

REM ── Install / verify dependencies ────────────────────────────────
echo.
echo [INFO] Checking dependencies…
"%PYTHON%" -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Flask not found — installing from expert-dashboard/requirements.txt…
    "%PYTHON%" -m pip install -r "%ROOT%\expert-dashboard\requirements.txt" --quiet
    if %errorlevel% neq 0 (
        echo [ERROR] pip install failed. Check your internet connection or install manually.
        pause
        exit /b 1
    )
    echo [OK]   Dependencies installed.
) else (
    echo [OK]   Flask found.
)

"%PYTHON%" -c "import onnxruntime" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] onnxruntime not found — installing…
    "%PYTHON%" -m pip install onnxruntime --quiet
)

"%PYTHON%" -c "import PIL" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Pillow not found — installing…
    "%PYTHON%" -m pip install Pillow --quiet
)

REM ── Model check ──────────────────────────────────────────────────
echo.
if exist "%ROOT%\models\cattle_breed.onnx" (
    echo [OK]   ONNX model found: models\cattle_breed.onnx
) else if exist "%ROOT%\models\cattle_breed.tflite" (
    echo [OK]   TFLite model found: models\cattle_breed.tflite
) else (
    echo [WARN] No model weights found in models\ — running in MOCK MODE.
    echo        Place a .onnx or .tflite file in models\ for real inference.
)

REM ── Run tests ────────────────────────────────────────────────────
echo.
set /p RUN_TESTS="[?] Run pytest tests before launching? (y/N): "
if /i "%RUN_TESTS%"=="y" (
    echo.
    echo [INFO] Running test suite…
    "%PYTHON%" -m pytest tests/test_pipeline.py -v --tb=short
    echo.
)

REM ── Launch dashboard ─────────────────────────────────────────────
echo.
echo  ================================================================
echo    Starting dashboard at http://127.0.0.1:5000
echo    Press Ctrl+C to stop
echo  ================================================================
echo.

REM Open browser after a short delay
start "" cmd /c "timeout /t 2 >nul && start http://127.0.0.1:5000"

cd /d "%ROOT%"
"%PYTHON%" expert-dashboard\app.py

pause
