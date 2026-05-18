#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────
#  deploy.sh — Build 1 collection + commit + push (all-in-one).
#
#  Cách dùng:
#    scripts/deploy.sh <chunk_variant> <strategy> <embed_alias>
#    scripts/deploy.sh balanced long_late bge_m3
#
#  Script này sẽ:
#    1) Build collection theo cấu hình bạn truyền
#    2) git add chroma_db data src app.py requirements.txt docs
#    3) Hiển thị diff --stat và hỏi xác nhận
#    4) commit + push origin main
# ─────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

scripts/build_db.sh "$@"

git add -A chroma_db data src app.py requirements.txt docs

git diff --cached --stat

read -r -p "Commit và push? [y/N] " CONFIRM
if [[ "${CONFIRM,,}" != "y" ]]; then
    echo "Đã huỷ (chưa commit, chưa push)."
    exit 0
fi

VARIANT="${1:-coarse}"
STRATEGY="${2:-standard}"
EMBED="${3:-minilm}"
git commit -m "Build DB: ${VARIANT}/${STRATEGY}/${EMBED}"
git push origin main
echo "Done."
