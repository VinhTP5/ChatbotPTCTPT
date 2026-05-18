@echo off
REM ─────────────────────────────────────────────────────────────────────────
REM  git_init.cmd — Khoi tao git repo va ket noi remote.
REM
REM  Cach dung:
REM    scripts\git_init.cmd <remote_url> [branch]
REM    scripts\git_init.cmd https://github.com/VinhTP5/ChatbotPTCTPT.git
REM    scripts\git_init.cmd https://github.com/VinhTP5/ChatbotPTCTPT.git main
REM ─────────────────────────────────────────────────────────────────────────
setlocal
cd /d %~dp0\..

set REMOTE=%1
set BRANCH=%2
if "%REMOTE%"=="" (
    echo Thieu remote URL. Vi du:
    echo   scripts\git_init.cmd https://github.com/USER/REPO.git
    exit /b 1
)
if "%BRANCH%"=="" set BRANCH=main

if exist .git (
    echo Repo da co .git\ — bo qua git init.
) else (
    git init
    git branch -M %BRANCH%
)

git remote remove origin 2>nul
git remote add origin %REMOTE%

echo === Da ket noi ===
git remote -v
echo.
echo Buoc tiep theo:
echo   scripts\git_add.cmd
echo   scripts\git_commit.cmd "Initial commit"
echo   scripts\git_push.cmd
