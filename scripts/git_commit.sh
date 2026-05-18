#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────
#  git_commit.sh — Tạo commit với message từ user.
#
#  Cách dùng:
#    scripts/git_commit.sh "Mô tả thay đổi"
#    scripts/git_commit.sh                    -> mở editor để viết message
# ─────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if git diff --cached --quiet; then
    echo "Không có thay đổi nào trong staging area."
    echo "Hãy chạy 'scripts/git_add.sh' trước."
    exit 0
fi

if [[ $# -eq 0 ]]; then
    git commit
else
    git commit -m "$*"
fi

echo
echo "=== Commit mới nhất ==="
git log --oneline -1
