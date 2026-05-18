@echo off
REM ─────────────────────────────────────────────────────────────────────────
REM  git_add.cmd — Stage thay doi.
REM
REM  Cach dung:
REM    scripts\git_add.cmd                 -> stage tat ca (mac dinh)
REM    scripts\git_add.cmd src app.py      -> stage cu the
REM    scripts\git_add.cmd code            -> chi code (src + scripts + app.py)
REM    scripts\git_add.cmd db              -> chi chroma_db
REM    scripts\git_add.cmd data            -> chi data/
REM    scripts\git_add.cmd scripts         -> chi scripts/
REM ─────────────────────────────────────────────────────────────────────────
setlocal
cd /d %~dp0\..

if "%~1"=="" (
    echo Staging tat ca thay doi...
    git add -A
    goto :show
)

if /I "%~1"=="code" (
    echo Staging code (src scripts app.py requirements .env.example)...
    git add src scripts app.py requirements.txt .env.example .streamlit\config.toml .streamlit\secrets.toml.example 2>nul
    goto :show
)

if /I "%~1"=="db" (
    echo Staging chroma_db...
    git add chroma_db
    goto :show
)

if /I "%~1"=="data" (
    echo Staging data/ ...
    git add data
    goto :show
)

if /I "%~1"=="scripts" (
    echo Staging scripts/ ...
    git add scripts
    goto :show
)

REM Truyen thang xuong git add
git add %*

:show
echo.
echo === Staged ===
git diff --cached --stat
