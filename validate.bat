@echo off
REM validate.bat — Auto-validate Water Meter OCR (Windows)
REM Standard: Ultralytics Val (mAP@50>=0.90 excellent, >=0.85 pass) + Exact Reading Accuracy >=0.85 pass
REM Usage:
REM   validate.bat                — DEFAULT: 20 images from meter_img\ (standard sample)
REM   validate.bat 5              — limit 5 images
REM   validate.bat 50 my_dataset  — limit 50 from my_dataset folder
REM   validate.bat 0 meter_img    — 0 = no limit (all)
REM   validate.bat all            — all images (alias for 0)
setlocal enabledelayedexpansion

set LIMIT=%~1
set IMGDIR=%~2

if "%IMGDIR%"=="" set IMGDIR=meter_img
REM Default when no args: 20 images (standard sample per TUTORIAL.md 3.4.3)
if "%LIMIT%"=="" set LIMIT=20
if /I "%LIMIT%"=="all" set LIMIT=0

if "%LIMIT%"=="0" (
    echo [validate] Standard sample: ALL images from %IMGDIR% (no limit)
    echo            Criteria: mAP@50^=0.90 excellent / Exact Reading Accuracy ^=0.85 pass (TUTORIAL.md 3.4.3)
    uv run python validate.py --dir "%IMGDIR%"
) else (
    echo [validate] Standard sample: %LIMIT% images from %IMGDIR% (default 20 per TUTORIAL.md 3.4.3)
    echo            Criteria: mAP@50^=0.90 / Exact Reading Accuracy ^=0.85
    uv run python validate.py --dir "%IMGDIR%" --limit %LIMIT%
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
