@echo off
REM ─────────────────────────────────────────────────────────────────────────
REM  db_status.cmd — Hien thi thong ke ChromaDB (so collections, vectors).
REM
REM  Cach dung:
REM    scripts\db_status.cmd                    -> liet ke toan bo collection
REM    scripts\db_status.cmd minilm coarse standard
REM                                             -> chi 1 collection cu the
REM
REM  Tham so:
REM    1. embed alias    (vd: minilm | mpnet | e5_base | e5_large | bge_m3)
REM    2. chunk variant  (vd: fine | balanced | coarse)
REM    3. strategy       (vd: standard | late | long_late)
REM ─────────────────────────────────────────────────────────────────────────
setlocal
cd /d %~dp0\..

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set EMBED=%1
set VARIANT=%2
set STRATEGY=%3

if "%EMBED%"=="" (
    python src\build_db.py --mode status
) else (
    if "%VARIANT%"==""  set VARIANT=coarse
    if "%STRATEGY%"=="" set STRATEGY=standard
    python src\build_db.py --mode status ^
        --embed-model %EMBED% ^
        --chunk-variant %VARIANT% ^
        --chunking-strategy %STRATEGY%
)
