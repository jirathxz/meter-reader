@echo off
REM validate_ablation.bat — OpenCV ablation (Windows)
REM Usage:
REM   validate_ablation.bat              — all modes on meter_img
REM   validate_ablation.bat 5            — limit 5 images per mode
REM   validate_ablation.bat 5 my_dataset — limit 5 from my_dataset
setlocal

set LIMIT=%~1
set IMGDIR=%~2
if "%IMGDIR%"=="" set IMGDIR=meter_img

if "%LIMIT%"=="" (
    echo [ablation] Running ALL images from %IMGDIR% (5 modes) — this takes ~5x longer ...
    uv run python validate_ablation.py --dir "%IMGDIR%"
) else (
    echo [ablation] Running limit %LIMIT% images from %IMGDIR% (5 modes) ...
    uv run python validate_ablation.py --dir "%IMGDIR%" --limit %LIMIT%
)

if errorlevel 1 (
    echo [ERROR] validate_ablation.py failed.
    pause
    exit /b 1
)
echo [DONE] Saved to reviews\ablation.json and reviews\ablation.csv
pause
