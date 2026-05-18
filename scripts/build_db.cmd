@echo off
REM =============================================================================
REM  build_db.cmd — Build/sync MỘT combination (embed x variant x strategy).
REM
REM  Quy tắc mode tự động:
REM    - Collection chưa tồn tại hoặc rỗng (0 vectors) -> rebuild --force
REM    - Collection đã có dữ liệu                       -> sync
REM      (chỉ index file mới/thay đổi, bỏ qua file đã index)
REM
REM  Cách dùng:
REM    scripts\build_db.cmd <variant> <strategy> <embed> [window_tokens] [window_overlap]
REM
REM  Ví dụ:
REM    scripts\build_db.cmd coarse   standard minilm
REM    scripts\build_db.cmd balanced late     mpnet
REM    scripts\build_db.cmd fine     long_late bge_m3 512 64
REM =============================================================================
setlocal enabledelayedexpansion

set VARIANT=%~1
set STRATEGY=%~2
set EMBED=%~3
set WINDOW_TOKENS=%~4
set WINDOW_OVERLAP=%~5

if "%VARIANT%"==""      set VARIANT=coarse
if "%STRATEGY%"==""     set STRATEGY=standard
if "%EMBED%"==""        set EMBED=minilm
if "%WINDOW_TOKENS%"="" set WINDOW_TOKENS=512
if "%WINDOW_OVERLAP%"="" set WINDOW_OVERLAP=64

cd /d %~dp0\..
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

REM --- Kiểm tra collection có dữ liệu chưa ---
for /f "delims=" %%i in ('python -c "import sys; sys.path.insert(0,'src'); import chromadb; from config import build_collection_name, CHROMA_DIR; name=build_collection_name('%EMBED%','%VARIANT%','%STRATEGY%');^
c=chromadb.PersistentClient(path=CHROMA_DIR);^
print(c.get_collection(name).count() if name in [x.name for x in c.list_collections()] else -1)" 2^>nul') do set COUNT=%%i
if "%COUNT%"=="" set COUNT=-1

set MODE=rebuild
set MODE_ARGS=--force
if %COUNT% GTR 0 (
    set MODE=sync
    set MODE_ARGS=
)

echo [%TIME%] variant=%VARIANT%  strategy=%STRATEGY%  embed=%EMBED%
echo            vectors hien tai: %COUNT%  -^>  mode: %MODE%

python src\build_db.py --mode %MODE% %MODE_ARGS% ^
    --chunk-variant     %VARIANT%      ^
    --chunking-strategy %STRATEGY%     ^
    --embed-model       %EMBED%        ^
    --window-tokens     %WINDOW_TOKENS% ^
    --window-overlap    %WINDOW_OVERLAP%

if %ERRORLEVEL% NEQ 0 (
    echo [%TIME%] FAILED  (%EMBED%__%VARIANT%__%STRATEGY%)
    exit /b %ERRORLEVEL%
)

echo [%TIME%] OK  (%EMBED%__%VARIANT%__%STRATEGY%)
endlocal
