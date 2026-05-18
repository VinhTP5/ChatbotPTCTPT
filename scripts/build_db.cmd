@echo off
setlocal

set VARIANT=%1
set STRATEGY=%2
set EMBED=%3
set WINDOW_TOKENS=%4
set WINDOW_OVERLAP=%5

if "%VARIANT%"=="" set VARIANT=coarse
if "%STRATEGY%"=="" set STRATEGY=standard
if "%EMBED%"=="" set EMBED=minilm
if "%WINDOW_TOKENS%"=="" set WINDOW_TOKENS=512
if "%WINDOW_OVERLAP%"=="" set WINDOW_OVERLAP=64

cd /d %~dp0\..
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo [%TIME%] Build variant=%VARIANT% strategy=%STRATEGY% embed=%EMBED%
python src\build_db.py --mode rebuild --force ^
    --chunk-variant %VARIANT% ^
    --chunking-strategy %STRATEGY% ^
    --embed-model %EMBED% ^
    --window-tokens %WINDOW_TOKENS% ^
    --window-overlap %WINDOW_OVERLAP%

if %ERRORLEVEL% NEQ 0 (
    echo [%TIME%] BUILD FAILED (exit %ERRORLEVEL%)
    exit /b %ERRORLEVEL%
)

echo [%TIME%] BUILD OK
