#!/usr/bin/env bash
# git_status.sh — Xem trạng thái working tree + branch hiện tại.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Branch hiện tại ==="
git branch --show-current
echo
echo "=== Remote ==="
git remote -v
echo
echo "=== Status ==="
git status
