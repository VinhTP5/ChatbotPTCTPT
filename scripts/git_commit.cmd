@echo off
REM ─────────────────────────────────────────────────────────────────────────
REM  git_commit.cmd — Tao commit voi message tu user.
REM
REM  Cach dung:
REM    scripts\git_commit.cmd "Mo ta thay doi"
REM    scripts\git_commit.cmd                  -> mo editor de viet message
REM
REM  Tip: dat trong dau " neu message co dau cach.
REM ─────────────────────────────────────────────────────────────────────────
setlocal
cd /d %~dp0\..

REM Kiem tra co gi de commit
git diff --cached --quiet
if not errorlevel 1 (
    echo Khong co thay doi nao trong staging area.
    echo Hay chay 'scripts\git_add.cmd' truoc.
    exit /b 0
)

if "%~1"=="" (
    git commit
) else (
    git commit -m %1
)

if errorlevel 1 (
    echo Commit that bai.
    exit /b 1
)

echo.
echo === Commit moi nhat ===
git log --oneline -1
