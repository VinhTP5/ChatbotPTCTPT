#!/usr/bin/env bash
# =============================================================================
#  build_db.sh — Build/sync MỘT combination (embed × variant × strategy).
#
#  Quy tắc mode tự động:
#    - Collection chưa tồn tại hoặc rỗng (0 vectors) → rebuild --force
#    - Collection đã có dữ liệu                       → sync
#      (chỉ index file mới/thay đổi, bỏ qua file đã index)
#
#  Cách dùng:
#    scripts/build_db.sh <variant> <strategy> <embed> [window_tokens] [window_overlap]
#
#  Ví dụ:
#    scripts/build_db.sh coarse   standard minilm
#    scripts/build_db.sh balanced late     mpnet
#    scripts/build_db.sh fine     long_late bge_m3 512 64
# =============================================================================
set -euo pipefail

VARIANT="${1:-coarse}"
STRATEGY="${2:-standard}"
EMBED="${3:-minilm}"
WINDOW_TOKENS="${4:-512}"
WINDOW_OVERLAP="${5:-64}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

# Kiểm tra collection có dữ liệu chưa → chọn mode
COUNT=$(python - <<EOF
import sys; sys.path.insert(0, "src")
import chromadb
from config import build_collection_name, CHROMA_DIR
name = build_collection_name("$EMBED", "$VARIANT", "$STRATEGY")
try:
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    print(client.get_collection(name).count())
except Exception:
    print(-1)
EOF
)

if [[ "$COUNT" -le 0 ]]; then
    MODE="rebuild"
    MODE_ARGS="--force"
else
    MODE="sync"
    MODE_ARGS=""
fi

echo "[$(date '+%H:%M:%S')] variant=${VARIANT}  strategy=${STRATEGY}  embed=${EMBED}"
echo "                   vectors hiện tại: ${COUNT}  →  mode: ${MODE}"

python src/build_db.py \
  --mode "$MODE" $MODE_ARGS \
  --chunk-variant   "$VARIANT" \
  --chunking-strategy "$STRATEGY" \
  --embed-model     "$EMBED" \
  --window-tokens   "$WINDOW_TOKENS" \
  --window-overlap  "$WINDOW_OVERLAP"

echo "[$(date '+%H:%M:%S')] ✓ OK  (${EMBED}__${VARIANT}__${STRATEGY})"
