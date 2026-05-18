@echo off
REM ─────────────────────────────────────────────────────────────────────────
REM  git_rebase.cmd — Rebase branch hien tai len remote/main moi nhat.
REM
REM  Cach dung:
REM    scripts\git_rebase.cmd                 -> fetch + rebase len origin/main
REM    scripts\git_rebase.cmd <branch>        -> rebase len <branch> tuy chinh
REM    scripts\git_rebase.cmd continue        -> tiep tuc sau khi resolve conflict
REM    scripts\git_rebase.cmd abort           -> huy bo rebase
REM ─────────────────────────────────────────────────────────────────────────
setlocal
cd /d %~dp0\..

if /I "%~1"=="continue" (
    git rebase --continue
    goto :end
)
if /I "%~1"=="abort" (
    git rebase --abort
    echo Da huy rebase.
    goto :end
)

set TARGET=%1
if "%TARGET%"=="" set TARGET=origin/main

echo === Fetch remote ===
git fetch origin

echo.
echo === Rebase len %TARGET% ===
git rebase %TARGET%
if errorlevel 1 (
    echo.
    echo Rebase co conflict. Sau khi resolve, chay:
    echo   scripts\git_rebase.cmd continue
    echo Hoac de huy:
    echo   scripts\git_rebase.cmd abort
    exit /b 1
)

echo.
echo === Lich su sau rebase ===
git log --oneline -5

:end
