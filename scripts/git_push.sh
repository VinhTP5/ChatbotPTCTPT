#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────
#  git_push.sh — Đẩy commit lên remote.
#
#  Cách dùng:
#    scripts/git_push.sh                     -> push branch hiện tại lên origin
#    scripts/git_push.sh force               -> force push (NGUY HIỂM)
#    scripts/git_push.sh lease               -> --force-with-lease (an toàn hơn)
#    scripts/git_push.sh <remote> <branch>   -> push tuỳ chỉnh
# ─────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ $# -eq 0 ]]; then
    BR="$(git branch --show-current)"
    echo "Pushing ${BR} -> origin/${BR} ..."
    git push -u origin "$BR"
elif [[ "$1" == "force" ]]; then
    echo "CẢNH BÁO: force-push có thể ghi đè công việc trên remote."
    read -r -p "Tiếp tục? [y/N] " CONFIRM
    if [[ "${CONFIRM,,}" != "y" ]]; then
        echo "Huỷ bỏ."
        exit 0
    fi
    git push --force
elif [[ "$1" == "lease" ]]; then
    echo "Force-with-lease (an toàn hơn vì tự chối nếu remote có commit mới)..."
    git push --force-with-lease
else
    git push "$@"
fi

echo
echo "=== Last commit ==="
git log --oneline -1
