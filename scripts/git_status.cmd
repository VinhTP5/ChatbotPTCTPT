@echo off
REM git_status.cmd — Xem trang thai working tree + branch hien tai.
setlocal
cd /d %~dp0\..

echo === Branch hien tai ===
git branch --show-current
echo.
echo === Remote ===
git remote -v
echo.
echo === Status ===
git status
