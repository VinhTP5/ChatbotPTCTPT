@echo off
setlocal

call scripts\build_db.cmd coarse standard minilm
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

call scripts\build_db.cmd balanced standard mpnet
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

call scripts\build_db.cmd fine standard mpnet
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

call scripts\build_db.cmd balanced late mpnet
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

call scripts\build_db.cmd balanced long_late bge_m3
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

call scripts\build_db.cmd fine long_late bge_m3
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

python src\build_db.py --mode status
echo Done all variants.
