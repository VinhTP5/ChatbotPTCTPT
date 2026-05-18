#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────
#  git_add.sh — Stage thay đổi.
#
#  Cách dùng:
#    scripts/git_add.sh                  -> stage tất cả (mặc định)
#    scripts/git_add.sh src app.py       -> stage cụ thể
#    scripts/git_add.sh code             -> chỉ code (src + scripts + app.py)
#    scripts/git_add.sh db               -> chỉ chroma_db
#    scripts/git_add.sh data             -> chỉ data/
#    scripts/git_add.sh scripts          -> chỉ scripts/
# ─────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ $# -eq 0 ]]; then
    echo "Staging tất cả thay đổi..."
    git add -A
elif [[ "$1" == "code" ]]; then
    echo "Staging code (src scripts app.py requirements .env.example)..."
    git add src scripts app.py requirements.txt .env.example
    [[ -f .streamlit/config.toml ]] && git add .streamlit/config.toml
    [[ -f .streamlit/secrets.toml.example ]] && git add .streamlit/secrets.toml.example
elif [[ "$1" == "db" ]]; then
    echo "Staging chroma_db..."
    git add chroma_db
elif [[ "$1" == "data" ]]; then
    echo "Staging data/ ..."
    git add data
elif [[ "$1" == "scripts" ]]; then
    echo "Staging scripts/ ..."
    git add scripts
else
    git add "$@"
fi

echo
echo "=== Staged ==="
git diff --cached --stat
