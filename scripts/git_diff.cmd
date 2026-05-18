@echo off
REM ─────────────────────────────────────────────────────────────────────────
REM  git_diff.cmd — Xem thay doi.
REM
REM  Cach dung:
REM    scripts\git_diff.cmd          -> diff working tree (chua stage)
REM    scripts\git_diff.cmd staged   -> diff cua noi dung da stage
REM    scripts\git_diff.cmd stat     -> chi --stat (gon)
REM    scripts\git_diff.cmd <file>   -> diff 1 file cu the
REM ─────────────────────────────────────────────────────────────────────────
setlocal
cd /d %~dp0\..

if "%~1"=="" (
    git diff
    goto :end
)

if /I "%~1"=="staged" (
    git diff --cached
    goto :end
)

if /I "%~1"=="stat" (
    git diff --stat
    echo.
    echo === Staged ===
    git diff --cached --stat
    goto :end
)

git diff %*

:end
