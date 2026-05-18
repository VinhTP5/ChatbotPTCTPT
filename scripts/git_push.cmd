@echo off
REM ─────────────────────────────────────────────────────────────────────────
REM  git_push.cmd — Day commit len remote.
REM
REM  Cach dung:
REM    scripts\git_push.cmd                    -> push branch hien tai len origin
REM    scripts\git_push.cmd force              -> force push (NGUY HIEM: ghi de remote)
REM    scripts\git_push.cmd lease              -> --force-with-lease (an toan hon force)
REM    scripts\git_push.cmd <remote> <branch>  -> push tuy chinh
REM ─────────────────────────────────────────────────────────────────────────
setlocal
cd /d %~dp0\..

if "%~1"=="" goto :normal
if /I "%~1"=="force" goto :force
if /I "%~1"=="lease" goto :lease
goto :custom

:normal
for /f "tokens=*" %%i in ('git branch --show-current') do set BR=%%i
echo Pushing %BR% -^> origin/%BR% ...
git push -u origin %BR%
goto :end

:force
echo CANH BAO: dang force-push, co the ghi de cong viec cua nguoi khac tren remote.
set /p CONFIRM="Tiep tuc? [y/N] "
if /I NOT "%CONFIRM%"=="y" (
    echo Huy bo.
    exit /b 0
)
git push --force
goto :end

:lease
echo Force-with-lease (an toan hon vi tu chuc neu remote co commit moi)...
git push --force-with-lease
goto :end

:custom
git push %*

:end
echo.
echo === Last commit on origin ===
git log --oneline -1
