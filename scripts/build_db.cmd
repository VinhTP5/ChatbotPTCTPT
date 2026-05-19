@echo off
REM build_db.cmd - Build/sync MOT combination (embed x variant x strategy).
REM
REM Usage:
REM   scripts\build_db.cmd <variant> <strategy> <embed> [window_tokens] [window_overlap]
setlocal

set VARIANT=%~1
set STRATEGY=%~2
set EMBED=%~3
set WINDOW_TOKENS=%~4
set WINDOW_OVERLAP=%~5

if "%VARIANT%"==""       set VARIANT=coarse
if "%STRATEGY%"==""      set STRATEGY=standard
if "%EMBED%"==""         set EMBED=minilm
if "%WINDOW_TOKENS%"=""  set WINDOW_TOKENS=512
if "%WINDOW_OVERLAP%"="" set WINDOW_OVERLAP=64

cd /d %~dp0\..
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

REM --- Kiem tra collection co du lieu chua ---
set COUNT=
for /f "usebackq tokens=* delims=" %%i in (`python scripts\_check_collection.py %EMBED% %VARIANT% %STRATEGY% 2^>nul`) do set COUNT=%%i
if not defined COUNT set COUNT=-1

set MODE=rebuild
set MODE_ARGS=--force
if %COUNT% GTR 0 (
    set MODE=sync
    set MODE_ARGS=
)

echo [%TIME%] variant=%VARIANT%  strategy=%STRATEGY%  embed=%EMBED%
echo            vectors hien tai: %COUNT%  ->  mode: %MODE%

python src\build_db.py --mode %MODE% %MODE_ARGS% ^
    --chunk-variant     %VARIANT%       ^
    --chunking-strategy %STRATEGY%      ^
    --embed-model       %EMBED%         ^
    --window-tokens     %WINDOW_TOKENS% ^
    --window-overlap    %WINDOW_OVERLAP%

set _RET=%ERRORLEVEL%
if %_RET% NEQ 0 (
    echo [%TIME%] FAILED  (%EMBED%__%VARIANT%__%STRATEGY%)
    exit /b %_RET%
)

echo [%TIME%] OK  (%EMBED%__%VARIANT%__%STRATEGY%)
endlocal
