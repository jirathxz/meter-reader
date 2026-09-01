@echo off
REM validate.bat — Auto-validate Water Meter OCR (Windows)
REM Usage:
REM   validate.bat                — all images in meter_img\
REM   validate.bat 5              — limit 5 images
REM   validate.bat 5 my_dataset   — limit 5 from my_dataset folder
REM   validate.bat 0 meter_img    — 0 = no limit (all)
setlocal enabledelayedexpansion

set LIMIT=%~1
set IMGDIR=%~2

if "%IMGDIR%"=="" set IMGDIR=meter_img
if "%LIMIT%"=="" (
    echo [validate] Running ALL images from %IMGDIR% ...
    uv run python validate.py --dir "%IMGDIR%"
) else (
    if "%LIMIT%"=="0" (
        echo [validate] Running ALL images from %IMGDIR% ...
        uv run python validate.py --dir "%IMGDIR%"
    ) else (
        echo [validate] Running limit %LIMIT% images from %IMGDIR% ...
        uv run python validate.py --dir "%IMGDIR%" --limit %LIMIT%
    )
)

if errorlevel 1 (
    echo.
    echo [ERROR] validate.py failed. Check that uv and dependencies are installed.
    echo         Try: uv pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo [DONE] Results saved to reviews\validation_results.json and .csv
if exist "reviews\validation_results.json" (
    echo        Open reviews\validation_results.json to see per-image results
)
pause
