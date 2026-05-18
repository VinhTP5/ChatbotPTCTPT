@echo off
REM =============================================================================
REM  build_all_variants.cmd — Build/sync đầy đủ 45 combinations
REM                           Embedding x Chunk variant x Chunking strategy
REM
REM  Quy tắc (áp dụng cho từng combination, xem build_db.cmd):
REM    - Collection chưa tồn tại hoặc rỗng (0 vectors) -> rebuild --force
REM    - Collection đã có dữ liệu                       -> sync
REM
REM  Thứ tự — nhóm theo embedding (load model 1 lần/nhóm):
REM    01-09  minilm   | 10-18  mpnet  | 19-27  e5_base
REM    28-36  e5_large | 37-45  bge_m3
REM
REM  Mỗi nhóm embed x 3 variants (fine/balanced/coarse) x 3 strategies
REM  (standard/late/long_late) theo thứ tự từ nhẹ đến nặng.
REM
REM  Cách dùng:
REM    scripts\build_all_variants.cmd            :: build tất cả 45
REM    scripts\build_all_variants.cmd --dry-run  :: chỉ xem sẽ làm gì
REM =============================================================================
setlocal enabledelayedexpansion

cd /d %~dp0\..
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set DRY_RUN=0
if /I "%~1"=="--dry-run" set DRY_RUN=1
if %DRY_RUN%==1 echo [DRY RUN] Chi hien thi - khong thuc su chay.

set ERRORS=0
set SEQ=0

echo ========================================================================
echo   BUILD ALL VARIANTS - 45 combinations
echo   Bat dau: %DATE% %TIME%
echo ========================================================================

REM =============================================================================
REM  01-09  minilm
REM =============================================================================
call :RUN minilm fine     standard
call :RUN minilm fine     late
call :RUN minilm fine     long_late
call :RUN minilm balanced standard
call :RUN minilm balanced late
call :RUN minilm balanced long_late
call :RUN minilm coarse   standard
call :RUN minilm coarse   late
call :RUN minilm coarse   long_late

REM =============================================================================
REM  10-18  mpnet
REM =============================================================================
call :RUN mpnet fine     standard
call :RUN mpnet fine     late
call :RUN mpnet fine     long_late
call :RUN mpnet balanced standard
call :RUN mpnet balanced late
call :RUN mpnet balanced long_late
call :RUN mpnet coarse   standard
call :RUN mpnet coarse   late
call :RUN mpnet coarse   long_late

REM =============================================================================
REM  19-27  e5_base
REM =============================================================================
call :RUN e5_base fine     standard
call :RUN e5_base fine     late
call :RUN e5_base fine     long_late
call :RUN e5_base balanced standard
call :RUN e5_base balanced late
call :RUN e5_base balanced long_late
call :RUN e5_base coarse   standard
call :RUN e5_base coarse   late
call :RUN e5_base coarse   long_late

REM =============================================================================
REM  28-36  e5_large
REM =============================================================================
call :RUN e5_large fine     standard
call :RUN e5_large fine     late
call :RUN e5_large fine     long_late
call :RUN e5_large balanced standard
call :RUN e5_large balanced late
call :RUN e5_large balanced long_late
call :RUN e5_large coarse   standard
call :RUN e5_large coarse   late
call :RUN e5_large coarse   long_late

REM =============================================================================
REM  37-45  bge_m3
REM =============================================================================
call :RUN bge_m3 fine     standard
call :RUN bge_m3 fine     late
call :RUN bge_m3 fine     long_late
call :RUN bge_m3 balanced standard
call :RUN bge_m3 balanced late
call :RUN bge_m3 balanced long_late
call :RUN bge_m3 coarse   standard
call :RUN bge_m3 coarse   late
call :RUN bge_m3 coarse   long_late

REM =============================================================================
REM  Tổng kết
REM =============================================================================
echo.
echo ========================================================================
echo   HOAN TAT - %DATE% %TIME%
if %ERRORS% GTR 0 (
    echo   LOI: %ERRORS% combination that bai
) else (
    echo   Tat ca thanh cong
)
echo ========================================================================
echo.

python src\build_db.py --mode status
goto :EOF

REM =============================================================================
REM  Subroutine :RUN  embed  variant  strategy
REM =============================================================================
:RUN
set _EMBED=%~1
set _VARIANT=%~2
set _STRATEGY=%~3
set /a SEQ+=1

REM Đệm số thứ tự thành 2 chữ số
set _LABEL=0%SEQ%
if %SEQ% GEQ 10 set _LABEL=%SEQ%

REM Kiểm tra số vectors hiện tại
for /f "delims=" %%i in ('python -c "import sys; sys.path.insert(0,\"src\"); import chromadb; from config import build_collection_name, CHROMA_DIR; name=build_collection_name(\"%_EMBED%\",\"%_VARIANT%\",\"%_STRATEGY%\"); c=chromadb.PersistentClient(path=CHROMA_DIR); cols=[x.name for x in c.list_collections()]; print(c.get_collection(name).count() if name in cols else -1)" 2^>nul') do set _COUNT=%%i
if "%_COUNT%"=="" set _COUNT=-1

echo.
echo [%_LABEL%/45] %_EMBED%__%_VARIANT%__%_STRATEGY%
echo        vectors: %_COUNT%

if %DRY_RUN%==1 (
    echo        [DRY RUN] bo qua
    goto :EOF
)

call scripts\build_db.cmd %_VARIANT% %_STRATEGY% %_EMBED%
if %ERRORLEVEL% NEQ 0 (
    echo        [LOI] tiep tuc combination tiep theo...
    set /a ERRORS+=1
)
goto :EOF
