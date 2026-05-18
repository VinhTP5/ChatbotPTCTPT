#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────
#  git_diff.sh — Xem thay đổi.
#
#  Cách dùng:
#    scripts/git_diff.sh           -> diff working tree (chưa stage)
#    scripts/git_diff.sh staged    -> diff của nội dung đã stage
#    scripts/git_diff.sh stat      -> chỉ --stat (gọn)
#    scripts/git_diff.sh <file>    -> diff 1 file cụ thể
# ─────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ $# -eq 0 ]]; then
    git diff
elif [[ "$1" == "staged" ]]; then
    git diff --cached
elif [[ "$1" == "stat" ]]; then
    git diff --stat
    echo
    echo "=== Staged ==="
    git diff --cached --stat
else
    git diff "$@"
fi
