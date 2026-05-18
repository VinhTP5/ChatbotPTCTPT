#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────
#  git_rebase.sh — Rebase branch hiện tại lên remote/main mới nhất.
#
#  Cách dùng:
#    scripts/git_rebase.sh                   -> fetch + rebase lên origin/main
#    scripts/git_rebase.sh <branch>          -> rebase lên <branch> tuỳ chỉnh
#    scripts/git_rebase.sh continue          -> tiếp tục sau khi resolve conflict
#    scripts/git_rebase.sh abort             -> huỷ bỏ rebase
# ─────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

case "${1:-}" in
    continue)
        git rebase --continue
        ;;
    abort)
        git rebase --abort
        echo "Đã huỷ rebase."
        ;;
    "")
        echo "=== Fetch remote ==="
        git fetch origin
        echo
        echo "=== Rebase lên origin/main ==="
        if ! git rebase origin/main; then
            echo
            echo "Rebase có conflict. Sau khi resolve, chạy:"
            echo "  scripts/git_rebase.sh continue"
            echo "Hoặc để huỷ:"
            echo "  scripts/git_rebase.sh abort"
            exit 1
        fi
        ;;
    *)
        echo "=== Fetch remote ==="
        git fetch origin
        echo
        echo "=== Rebase lên $1 ==="
        if ! git rebase "$1"; then
            echo
            echo "Rebase có conflict. Sau khi resolve:"
            echo "  scripts/git_rebase.sh continue"
            exit 1
        fi
        ;;
esac

echo
echo "=== Lịch sử sau rebase ==="
git log --oneline -5
