@echo off
REM build_all_variants.cmd
REM Build/sync 18 combinations: Embedding x Chunk variant x Chunking strategy
setlocal

cd /d %~dp0\..
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set DRY_RUN=0
if /I "%~1"=="--dry-run" set DRY_RUN=1

set ERRORS=0

echo ========================================================================
echo   BUILD ALL VARIANTS - 18 combinations
echo   Start: %DATE% %TIME%
if "%DRY_RUN%"=="1" echo   [DRY RUN] Preview only - not actually running.
echo ========================================================================

REM --- 01-09  minilm ---
call :DO 01 minilm fine     standard
call :DO 02 minilm fine     late
call :DO 03 minilm fine     long_late
call :DO 04 minilm balanced standard
call :DO 05 minilm balanced late
call :DO 06 minilm balanced long_late
call :DO 07 minilm coarse   standard
call :DO 08 minilm coarse   late
call :DO 09 minilm coarse   long_late

REM --- 10-18  bge_m3 ---
call :DO 10 bge_m3 fine     standard
call :DO 11 bge_m3 fine     late
call :DO 12 bge_m3 fine     long_late
call :DO 13 bge_m3 balanced standard
call :DO 14 bge_m3 balanced late
call :DO 15 bge_m3 balanced long_late
call :DO 16 bge_m3 coarse   standard
call :DO 17 bge_m3 coarse   late
call :DO 18 bge_m3 coarse   long_late

REM --- Summary ---
echo.
echo ========================================================================
echo   DONE - %DATE% %TIME%
if %ERRORS% GTR 0 goto :HASERRORS
echo   All combinations completed successfully
goto :SHOWDONE
:HASERRORS
echo   ERRORS: %ERRORS% combination(s) failed
:SHOWDONE
echo ========================================================================
echo.
python src\build_db.py --mode status
goto :EOF

REM =============================================================================
REM  :DO  seq  embed  variant  strategy
REM =============================================================================
:DO
set _SEQ=%~1
set _EMBED=%~2
set _VARIANT=%~3
set _STRATEGY=%~4
set _COUNT=

for /f "usebackq tokens=* delims=" %%i in (`python scripts\_check_collection.py %_EMBED% %_VARIANT% %_STRATEGY% 2^>nul`) do set _COUNT=%%i
if not defined _COUNT set _COUNT=-1

echo.
echo [%_SEQ%/18] %_EMBED%__%_VARIANT%__%_STRATEGY%
echo        current vectors: %_COUNT%

if "%DRY_RUN%"=="1" (
    echo        [DRY RUN] skipped
    set _COUNT=
    goto :EOF
)

call scripts\build_db.cmd %_VARIANT% %_STRATEGY% %_EMBED%
set _ERR=%ERRORLEVEL%
if %_ERR% NEQ 0 (
    echo        [FAILED] continuing to next combination...
    set /a ERRORS+=1
)
set _COUNT=
set _ERR=
goto :EOF
