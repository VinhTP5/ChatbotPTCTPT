#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────
#  git_init.sh — Khởi tạo git repo và kết nối remote.
#
#  Cách dùng:
#    scripts/git_init.sh <remote_url> [branch]
#    scripts/git_init.sh https://github.com/VinhTP5/ChatbotPTCTPT.git
#    scripts/git_init.sh https://github.com/VinhTP5/ChatbotPTCTPT.git main
# ─────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REMOTE="${1:-}"
BRANCH="${2:-main}"

if [[ -z "$REMOTE" ]]; then
    echo "Thiếu remote URL. Ví dụ:"
    echo "  scripts/git_init.sh https://github.com/USER/REPO.git"
    exit 1
fi

if [[ -d .git ]]; then
    echo "Repo đã có .git/ — bỏ qua git init."
else
    git init
    git branch -M "$BRANCH"
fi

git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE"

echo "=== Đã kết nối ==="
git remote -v
echo
echo "Bước tiếp theo:"
echo "  scripts/git_add.sh"
echo "  scripts/git_commit.sh \"Initial commit\""
echo "  scripts/git_push.sh"
