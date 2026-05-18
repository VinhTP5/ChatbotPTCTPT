@echo off
setlocal
cd /d %~dp0\..

call scripts\build_db.cmd %*
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

git add -A chroma_db data src app.py requirements.txt docs

git diff --cached --stat
set /p CONFIRM=Commit and push? [y/N] 
if /I NOT "%CONFIRM%"=="y" (
    echo Aborted.
    exit /b 0
)

git commit -m "Build DB: %1/%2/%3"
git push origin main
echo Done.
