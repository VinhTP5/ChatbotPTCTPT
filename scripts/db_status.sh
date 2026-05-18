#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────
#  db_status.sh — Hiển thị thống kê ChromaDB.
#
#  Cách dùng:
#    scripts/db_status.sh                       -> liệt kê toàn bộ collection
#    scripts/db_status.sh minilm coarse standard
#                                               -> chỉ 1 collection cụ thể
#
#  Tham số:
#    1. embed alias    (minilm | mpnet | e5_base | e5_large | bge_m3)
#    2. chunk variant  (fine | balanced | coarse)
#    3. strategy       (standard | late | long_late)
# ─────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

EMBED="${1:-}"
VARIANT="${2:-coarse}"
STRATEGY="${3:-standard}"

if [[ -z "$EMBED" ]]; then
    python src/build_db.py --mode status
else
    python src/build_db.py --mode status \
        --embed-model "$EMBED" \
        --chunk-variant "$VARIANT" \
        --chunking-strategy "$STRATEGY"
fi
