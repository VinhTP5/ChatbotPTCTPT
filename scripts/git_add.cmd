@echo off
REM ─────────────────────────────────────────────────────────────────────────
REM  git_add.cmd — Stage thay doi.
REM
REM  Cach dung:
REM    scripts\git_add.cmd                 -> stage tat ca (mac dinh)
REM    scripts\git_add.cmd src app.py      -> stage cu the
REM    scripts\git_add.cmd code            -> chi code (src app.py requirements)
REM    scripts\git_add.cmd db              -> chi chroma_db + indexed_files
REM    scripts\git_add.cmd data            -> chi data/
REM ─────────────────────────────────────────────────────────────────────────
setlocal
cd /d %~dp0\..

if "%~1"=="" (
    echo Staging tat ca thay doi...
    git add -A
    goto :show
)

if /I "%~1"=="code" (
    echo Staging code (src app.py requirements .env.example)...
    git add src app.py requirements.txt .env.example .streamlit\config.toml .streamlit\secrets.toml.example 2>nul
    goto :show
)

if /I "%~1"=="db" (
    echo Staging chroma_db + indexed_files...
    git add chroma_db
    goto :show
)

if /I "%~1"=="data" (
    echo Staging data/ ...
    git add data
    goto :show
)

REM Truyen thang xuong git add
git add %*

:show
echo.
echo === Staged ===
git diff --cached --stat
