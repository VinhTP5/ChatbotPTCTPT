@echo off
REM build_all_variants.cmd
REM Build/sync 45 combinations: Embedding x Chunk variant x Chunking strategy
setlocal

cd /d %~dp0\..
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set DRY_RUN=0
if /I "%~1"=="--dry-run" set DRY_RUN=1

set ERRORS=0

echo ========================================================================
echo   BUILD ALL VARIANTS - 45 combinations
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

REM --- 10-18  mpnet ---
call :DO 10 mpnet fine     standard
call :DO 11 mpnet fine     late
call :DO 12 mpnet fine     long_late
call :DO 13 mpnet balanced standard
call :DO 14 mpnet balanced late
call :DO 15 mpnet balanced long_late
call :DO 16 mpnet coarse   standard
call :DO 17 mpnet coarse   late
call :DO 18 mpnet coarse   long_late

REM --- 19-27  e5_base ---
call :DO 19 e5_base fine     standard
call :DO 20 e5_base fine     late
call :DO 21 e5_base fine     long_late
call :DO 22 e5_base balanced standard
call :DO 23 e5_base balanced late
call :DO 24 e5_base balanced long_late
call :DO 25 e5_base coarse   standard
call :DO 26 e5_base coarse   late
call :DO 27 e5_base coarse   long_late

REM --- 28-36  e5_large ---
call :DO 28 e5_large fine     standard
call :DO 29 e5_large fine     late
call :DO 30 e5_large fine     long_late
call :DO 31 e5_large balanced standard
call :DO 32 e5_large balanced late
call :DO 33 e5_large balanced long_late
call :DO 34 e5_large coarse   standard
call :DO 35 e5_large coarse   late
call :DO 36 e5_large coarse   long_late

REM --- 37-45  bge_m3 ---
call :DO 37 bge_m3 fine     standard
call :DO 38 bge_m3 fine     late
call :DO 39 bge_m3 fine     long_late
call :DO 40 bge_m3 balanced standard
call :DO 41 bge_m3 balanced late
call :DO 42 bge_m3 balanced long_late
call :DO 43 bge_m3 coarse   standard
call :DO 44 bge_m3 coarse   late
call :DO 45 bge_m3 coarse   long_late

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
echo [%_SEQ%/45] %_EMBED%__%_VARIANT%__%_STRATEGY%
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
