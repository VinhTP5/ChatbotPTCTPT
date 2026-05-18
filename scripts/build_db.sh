#!/usr/bin/env bash
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

echo "[$(date '+%H:%M:%S')] Build variant=${VARIANT} strategy=${STRATEGY} embed=${EMBED}"
python src/build_db.py \
  --mode rebuild \
  --force \
  --chunk-variant "$VARIANT" \
  --chunking-strategy "$STRATEGY" \
  --embed-model "$EMBED" \
  --window-tokens "$WINDOW_TOKENS" \
  --window-overlap "$WINDOW_OVERLAP"

echo "[$(date '+%H:%M:%S')] BUILD OK"
