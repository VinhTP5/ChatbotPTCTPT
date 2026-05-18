#!/usr/bin/env bash
# =============================================================================
#  build_all_variants.sh — Build/sync đầy đủ 45 combinations
#                          Embedding × Chunk variant × Chunking strategy
#
#  Quy tắc (áp dụng cho từng combination, xem build_db.sh):
#    - Collection chưa tồn tại hoặc rỗng (0 vectors) → rebuild --force
#    - Collection đã có dữ liệu                       → sync
#
#  Thứ tự — nhóm theo embedding (load model 1 lần/nhóm):
#    01–09  minilm   │ 10–18  mpnet  │ 19–27  e5_base
#    28–36  e5_large │ 37–45  bge_m3
#
#  Mỗi nhóm embed × 3 variants (fine/balanced/coarse) × 3 strategies
#  (standard/late/long_late) theo thứ tự từ nhẹ đến nặng.
#
#  Cách dùng:
#    bash scripts/build_all_variants.sh            # build tất cả 45
#    bash scripts/build_all_variants.sh --dry-run  # chỉ xem sẽ làm gì
# =============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=1
    echo "[DRY RUN] Chỉ hiển thị — không thực sự chạy."
fi

TOTAL=45
SEQ=0
ERRORS=0
START_TIME=$(date +%s)

# ── Helper ───────────────────────────────────────────────────────────────────
run_one() {
    local embed="$1" variant="$2" strategy="$3"
    SEQ=$((SEQ + 1))
    local label
    label=$(printf "%02d" "$SEQ")

    # Kiểm tra trạng thái collection hiện tại
    local count
    count=$(python - <<EOF
import sys; sys.path.insert(0, "src")
import chromadb
from config import build_collection_name, CHROMA_DIR
name = build_collection_name("$embed", "$variant", "$strategy")
try:
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col_names = [c.name for c in client.list_collections()]
    print(client.get_collection(name).count() if name in col_names else -1)
except Exception:
    print(-1)
EOF
)

    local mode
    if [[ "$count" -le 0 ]]; then
        mode="rebuild"
    else
        mode="sync"
    fi

    echo ""
    echo "┌─ [${label}/${TOTAL}] ${embed}__${variant}__${strategy}"
    echo "│  vectors: ${count}  →  mode: ${mode}"

    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "└─ [DRY RUN] bỏ qua"
        return
    fi

    echo "│  $(date '+%H:%M:%S') bắt đầu..."
    if bash scripts/build_db.sh "$variant" "$strategy" "$embed"; then
        echo "└─ $(date '+%H:%M:%S') ✓ xong"
    else
        echo "└─ $(date '+%H:%M:%S') ✗ LỖI  (tiếp tục combination tiếp theo)"
        ERRORS=$((ERRORS + 1))
    fi
}

echo "========================================================================"
echo "  BUILD ALL VARIANTS — 45 combinations"
echo "  Bắt đầu: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================================================"

# ── 01–09  minilm ─────────────────────────────────────────────────────────────
run_one minilm fine     standard
run_one minilm fine     late
run_one minilm fine     long_late
run_one minilm balanced standard
run_one minilm balanced late
run_one minilm balanced long_late
run_one minilm coarse   standard
run_one minilm coarse   late
run_one minilm coarse   long_late

# ── 10–18  mpnet ─────────────────────────────────────────────────────────────
run_one mpnet fine     standard
run_one mpnet fine     late
run_one mpnet fine     long_late
run_one mpnet balanced standard
run_one mpnet balanced late
run_one mpnet balanced long_late
run_one mpnet coarse   standard
run_one mpnet coarse   late
run_one mpnet coarse   long_late

# ── 19–27  e5_base ───────────────────────────────────────────────────────────
run_one e5_base fine     standard
run_one e5_base fine     late
run_one e5_base fine     long_late
run_one e5_base balanced standard
run_one e5_base balanced late
run_one e5_base balanced long_late
run_one e5_base coarse   standard
run_one e5_base coarse   late
run_one e5_base coarse   long_late

# ── 28–36  e5_large ──────────────────────────────────────────────────────────
run_one e5_large fine     standard
run_one e5_large fine     late
run_one e5_large fine     long_late
run_one e5_large balanced standard
run_one e5_large balanced late
run_one e5_large balanced long_late
run_one e5_large coarse   standard
run_one e5_large coarse   late
run_one e5_large coarse   long_late

# ── 37–45  bge_m3 ────────────────────────────────────────────────────────────
run_one bge_m3 fine     standard
run_one bge_m3 fine     late
run_one bge_m3 fine     long_late
run_one bge_m3 balanced standard
run_one bge_m3 balanced late
run_one bge_m3 balanced long_late
run_one bge_m3 coarse   standard
run_one bge_m3 coarse   late
run_one bge_m3 coarse   long_late

# ── Tổng kết ─────────────────────────────────────────────────────────────────
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

echo ""
echo "========================================================================"
echo "  HOÀN TẤT — $(date '+%Y-%m-%d %H:%M:%S')"
echo "  Tổng thời gian: ${MINUTES}m ${SECONDS}s"
if [[ "$ERRORS" -gt 0 ]]; then
    echo "  ⚠  Lỗi: ${ERRORS} combination thất bại"
else
    echo "  ✓  Tất cả thành công"
fi
echo "========================================================================"
echo ""

python src/build_db.py --mode status
